"""The only places an LLM is used (section 5 of the brief):

1. text_to_spec: a description becomes a proposed graph. The user confirms it.
2. fill_gaps: the fallback router writes code for Custom tool and Custom step blocks.
3. write_prompt: drafts an agent's instructions from its role (prompt wording).

Everything else is deterministic templates.

Contract for generated code (fill_gaps): Claude receives the target function name,
signature, file, an example and the test it must pass, and answers with structured
output (code is a field, never free text). The code is checked statically, then run
against its contract test in a throwaway container with no network when Docker is
available. Failures go back to Claude with the error, up to three attempts. After
that the block stays open and is listed in PROMPT_PACK.md.

Claude API notes: model defaults to claude-opus-5-5 (CONFIGURATOR_MODEL overrides),
native structured outputs via messages.parse, effort set per task, and server-side
refusal fallbacks on by default (CONFIGURATOR_REFUSAL_FALLBACK=off disables them).
"""

from __future__ import annotations

import ast
import contextvars
import json
import logging
import os
import re
import subprocess
import tempfile
import textwrap
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from configurator_spec import Spec, parse_spec
from configurator_spec.catalog import NODE_TYPES

from .catalogue import blueprint_index, load_blueprint
from .layout import auto_layout
from .rules import resolve

log = logging.getLogger("configurator.ai")

DEFAULT_MODEL = "claude-opus-5-5"
# USD per million tokens (input, output), for the per-request cost log.
PRICES = {
    "claude-opus-5-5": (4.0, 20.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-fable-5-1": (10.0, 50.0),
}


class AIUnavailable(RuntimeError):
    """No API key configured, or the API declined. Callers fall back to deterministic paths."""


@dataclass
class Usage:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0

    def add(self, model: str, usage: Any) -> None:
        inp = int(getattr(usage, "input_tokens", 0) or 0)
        out = int(getattr(usage, "output_tokens", 0) or 0)
        price_in, price_out = PRICES.get(model, PRICES[DEFAULT_MODEL])
        self.calls += 1
        self.input_tokens += inp
        self.output_tokens += out
        self.cost_usd += inp / 1e6 * price_in + out / 1e6 * price_out


USAGE = Usage()


# A key supplied per request (hosted mode, "bring your own key"). Never stored.
_request_key: contextvars.ContextVar[str | None] = contextvars.ContextVar("anthropic_key", default=None)


def use_key(key: str | None) -> contextvars.Token[str | None]:
    return _request_key.set(key or None)


def available() -> bool:
    return bool(_request_key.get() or os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def model_name() -> str:
    return os.environ.get("CONFIGURATOR_MODEL", DEFAULT_MODEL)


def _client() -> Any:
    if not available():
        raise AIUnavailable("Set ANTHROPIC_API_KEY to use Claude features.")
    import anthropic

    key = _request_key.get()
    return anthropic.Anthropic(api_key=key) if key else anthropic.Anthropic()


def _call_structured(system: str, user: str, schema: type[BaseModel], effort: str = "medium", max_tokens: int = 16000) -> Any:
    """One structured-output call. Returns a validated instance of `schema`."""
    import anthropic

    client = _client()
    model = model_name()
    kwargs: dict[str, Any] = {}
    if os.environ.get("CONFIGURATOR_REFUSAL_FALLBACK", "default") == "default" and model.startswith(("claude-opus-5", "claude-sonnet-5-5", "claude-fable-5-1")):
        kwargs = {"extra_headers": {"anthropic-beta": "server-side-fallback-2026-07-01"}, "extra_body": {"fallbacks": "default"}}
    started = time.monotonic()
    try:
        resp = client.messages.parse(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_format=schema,
            output_config={"effort": effort},
            **kwargs,
        )
    except anthropic.BadRequestError as exc:
        if kwargs and "fallback" in str(exc).lower():
            # Fallbacks not enabled for this account: retry without them.
            resp = client.messages.parse(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_format=schema,
                output_config={"effort": effort},
            )
        else:
            raise AIUnavailable(f"Claude rejected the request: {exc.message}") from exc
    except anthropic.AuthenticationError as exc:
        raise AIUnavailable("The Anthropic API key was rejected. Check ANTHROPIC_API_KEY.") from exc
    except anthropic.RateLimitError as exc:
        raise AIUnavailable("Rate limited by the Anthropic API. Try again in a minute.") from exc
    except anthropic.APIConnectionError as exc:
        raise AIUnavailable("Couldn't reach the Anthropic API.") from exc
    except anthropic.APIStatusError as exc:
        raise AIUnavailable(f"Anthropic API error {exc.status_code}.") from exc
    USAGE.add(model, resp.usage)
    log.info(
        "claude call model=%s in=%s out=%s secs=%.1f total_cost=$%.4f",
        model,
        getattr(resp.usage, "input_tokens", "?"),
        getattr(resp.usage, "output_tokens", "?"),
        time.monotonic() - started,
        USAGE.cost_usd,
    )
    if resp.stop_reason == "refusal":
        raise AIUnavailable("Claude declined this request.")
    if resp.stop_reason == "max_tokens":
        raise AIUnavailable("The answer was cut off. Try a shorter description.")
    if resp.parsed_output is None:
        raise AIUnavailable("Claude's answer didn't match the expected format.")
    return resp.parsed_output


# =========================================================================== 1. text to spec

FLOW_TYPE_NAMES = Literal[
    "input", "output", "agent", "supervisor", "prompt", "router", "critic", "approval", "guardrail", "retriever", "custom_step",
    "knowledge", "memory", "web_search", "web_fetch", "http_api", "mcp_server", "calculator", "sql_database", "custom_tool",
]


class DraftRoute(BaseModel):
    id: str = Field(description="lower_snake_case id")
    label: str
    description: str


class DraftNode(BaseModel):
    id: str = Field(description="lower_snake_case id, unique")
    type: FLOW_TYPE_NAMES
    label: str = Field(description="Short name shown on the canvas")
    role: str = Field(description="Agents: their job in one line. Others: empty")
    instructions: str = Field(description="Agents: system prompt. LLM step / supervisor: instructions. Review loop: criteria. Approval: question for the reviewer. Custom step / custom tool: what it does. Knowledge: what's inside. Others: empty")
    routes: list[DraftRoute] = Field(description="Routers only: the branches. Others: empty list")


class DraftEdge(BaseModel):
    source: str
    target: str
    handle: str = Field(
        description="'out' for normal flow; supervisor: 'delegate' (to a worker) or 'done'; router: 'route:<route id>'; "
        "review loop: 'pass' or 'revise'; approval: 'approved' or 'rejected'; guardrail: 'pass' or 'blocked'; "
        "resource (tool/knowledge/memory) into an agent or retrieve step: 'attach'"
    )


class Draft(BaseModel):
    project_name: str = Field(description="lower-case-with-hyphens")
    summary: str = Field(description="Two sentences: what the app does and how the loop works")
    nodes: list[DraftNode]
    edges: list[DraftEdge]


def _catalog_brief() -> str:
    lines = []
    for n in NODE_TYPES:
        outs = n["outputs"]
        handles = "route:<id> per branch" if outs == "routes" else ", ".join(o["id"] for o in outs) or "none"
        lines.append(f"- {n['type']} ({n['title']}, {n['role']}): {n['explain']} Outputs: {handles}.")
    return "\n".join(lines)


TEXT_TO_SPEC_SYSTEM = f"""You design agent workflows for a visual builder. Turn the user's description into a graph of blocks.

Blocks you can use:
{_catalog_brief()}

Rules:
- Exactly one input block, at least one output block.
- Flow blocks connect with handle 'out' (or their branch handles). Resources (tools, knowledge, memory) connect INTO an agent with handle 'attach'; knowledge may also attach into a retriever.
- Supervisor workers are connected with 'delegate' and report back automatically; connect 'done' to what happens after.
- Every loop must pass through a router, review loop, supervisor, approval or guardrail so it can end.
- Prefer the smallest graph that does the job well. Use a human approval before irreversible actions (refunds, emails, payments, publishing).
- Write real, specific instructions for agents (3-6 sentences), not placeholders.
- Use custom_tool only when no built-in tool fits, and describe precisely what it must do."""


@dataclass
class TextToSpecResult:
    spec: Spec
    summary: str
    source: Literal["claude", "blueprint"]
    notes: list[str] = field(default_factory=list)


def _draft_to_spec(draft: Draft) -> Spec:
    field_for = {
        "agent": "system_prompt",
        "supervisor": "instructions",
        "prompt": "instructions",
        "router": "instructions",
        "critic": "criteria",
        "approval": "prompt",
        "custom_step": "description",
        "custom_tool": "description",
        "knowledge": "description",
        "http_api": "description",
    }
    nodes: list[dict[str, Any]] = []
    types: dict[str, str] = {}
    for n in draft.nodes:
        nid = re.sub(r"[^a-z0-9_]", "_", n.id.lower()).strip("_")[:40] or "node"
        if not nid[0].isalpha():
            nid = "n_" + nid
        data: dict[str, Any] = {"label": n.label[:60]}
        key = field_for.get(n.type)
        if key and n.instructions.strip():
            data[key] = n.instructions.strip()
        if n.type == "agent" and n.role:
            data["role"] = n.role[:300]
        if n.type == "router" and n.routes:
            data["routes"] = [
                {"id": re.sub(r"[^a-z0-9_]", "_", r.id.lower()) or f"r{i}", "label": r.label[:40], "description": r.description[:300]}
                for i, r in enumerate(n.routes)
            ]
        if n.type == "custom_tool":
            data["tool_name"] = nid
        types[n.id] = n.type
        types[nid] = n.type
        nodes.append({"id": nid, "type": n.type, "data": data, "_orig": n.id})
    remap = {nd["_orig"]: nd["id"] for nd in nodes}
    for nd in nodes:
        nd.pop("_orig")
    resource_types = {"knowledge", "memory", "web_search", "web_fetch", "http_api", "mcp_server", "calculator", "sql_database", "custom_tool"}
    edges = []
    for i, e in enumerate(draft.edges):
        s, t = remap.get(e.source), remap.get(e.target)
        if not s or not t:
            continue
        if types[s] in resource_types:
            sh, th = "attach", "knowledge" if types[t] == "retriever" else "tools"
        else:
            sh, th = (e.handle or "out"), "in"
        edges.append({"id": f"e{i}-{s}-{t}", "source": s, "target": t, "sourceHandle": sh, "targetHandle": th})
    auto_layout(nodes, edges)
    name = re.sub(r"[^a-z0-9-]", "-", draft.project_name.lower()).strip("-")[:48] or "my-agent"
    if not name[0].isalpha():
        name = "app-" + name
    return parse_spec({"spec_version": "0.2", "project": {"name": name, "description": draft.summary[:500]}, "graph": {"nodes": nodes, "edges": edges}})


KEYWORDS = {
    "support-bot": ["support", "ticket", "customer", "refund", "billing", "helpdesk", "triage"],
    "research-team": ["research", "report", "analyst", "investigate", "market", "team", "multi-agent", "supervisor"],
    "content-studio": ["write", "blog", "content", "copy", "draft", "marketing", "newsletter", "post", "publish"],
    "data-analyst": ["sql", "database", "query", "analytics", "metrics", "warehouse", "table"],
    "mcp-assistant": ["mcp", "files", "filesystem", "personal", "assistant", "remember", "memory"],
    "docs-qa": ["docs", "documents", "pdf", "handbook", "policy", "knowledge", "faq", "manual"],
    "rag-starter": ["rag", "retrieve", "notes", "search my", "citations"],
}


def closest_blueprint(description: str) -> str:
    text = description.lower()
    scores = {bid: sum(1 for k in words if k in text) for bid, words in KEYWORDS.items()}
    best = max(scores, key=lambda b: scores[b])
    return best if scores[best] > 0 else "blank"


def text_to_spec(description: str, *, attempts: int = 3) -> TextToSpecResult:
    """Draft a spec from plain words. Without an API key, returns the closest blueprint."""
    description = description.strip()[:4000]
    if not available():
        bid = closest_blueprint(description)
        spec = load_blueprint(bid)
        title = next(b["title"] for b in blueprint_index() if b["id"] == bid)
        return TextToSpecResult(
            spec=spec,
            summary=f"No ANTHROPIC_API_KEY set, so this starts from the closest blueprint: {title}. Adjust it on the canvas.",
            source="blueprint",
        )
    feedback = ""
    last_error = ""
    for _ in range(attempts):
        user = f"Describe-to-graph request:\n<description>\n{description}\n</description>"
        if feedback:
            user += f"\n\nYour previous graph had these problems. Fix them:\n{feedback}"
        draft: Draft = _call_structured(TEXT_TO_SPEC_SYSTEM, user, Draft, effort="medium")
        try:
            spec = _draft_to_spec(draft)
        except ValidationError as exc:
            feedback = str(exc)[:2000]
            last_error = feedback
            continue
        res = resolve(spec)
        if res.ok:
            notes = [i.message for i in res.issues if i.level == "warning"]
            return TextToSpecResult(spec=spec, summary=draft.summary, source="claude", notes=notes)
        feedback = "\n".join(f"- {i.message} (block: {i.node_id})" for i in res.errors)
        last_error = feedback
    raise AIUnavailable(f"Couldn't produce a valid graph after {attempts} tries: {last_error[:500]}")


# =========================================================================== 2. fallback router


class GeneratedCode(BaseModel):
    code: str = Field(description="Complete Python source: imports first, then exactly one function. No markdown fences.")
    python_deps: list[str] = Field(description="Extra PyPI packages needed beyond langchain-core, httpx and pydantic. Usually empty.")
    env: list[str] = Field(description="Environment variable names the code reads (secrets). Usually empty.")
    notes: str = Field(description="One or two sentences on assumptions the developer should check.")


FORBIDDEN = {
    ("os", "system"),
    ("os", "popen"),
    ("subprocess", "*"),
    ("shutil", "rmtree"),
    ("builtins", "eval"),
    ("builtins", "exec"),
}


def static_check(code: str, name: str, *, is_tool: bool) -> list[str]:
    """Problems found without running the code."""
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [f"SyntaxError: {exc}"]
    problems = []
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)]
    target = [f for f in funcs if f.name == name]
    if len(target) != 1:
        problems.append(f"Define exactly one top-level function named `{name}`.")
    elif is_tool:
        decos = [ast.unparse(d) for d in target[0].decorator_list]
        if not any(d == "tool" or d.startswith("tool(") for d in decos):
            problems.append(f"Decorate `{name}` with @tool from langchain_core.tools.")
        if not ast.get_docstring(target[0]):
            problems.append("Give the tool a docstring: the model reads it to decide when to call the tool.")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Name) and fn.id in {"eval", "exec", "compile", "__import__"}:
                problems.append(f"Don't call {fn.id}().")
            if (
                isinstance(fn, ast.Attribute)
                and isinstance(fn.value, ast.Name)
                and ((fn.value.id, fn.attr) in FORBIDDEN or (fn.value.id, "*") in FORBIDDEN)
            ):
                problems.append(f"Don't call {fn.value.id}.{fn.attr}().")
        if isinstance(node, ast.Import | ast.ImportFrom):
            mod = node.module if isinstance(node, ast.ImportFrom) else node.names[0].name
            if (mod or "").split(".")[0] in {"subprocess", "ctypes", "pickle"}:
                problems.append(f"Don't import {mod}.")
    return problems


def _tool_contract(data: dict[str, Any]) -> tuple[str, str]:
    name = data["tool_name"]
    params = ", ".join(f"{i['name']}: {i['type']}" for i in data["inputs"])
    sample = ", ".join(f"{i['name']!r}: {({'str': 'test', 'int': 1, 'float': 1.5, 'bool': True})[i['type']]!r}" for i in data["inputs"])
    spec = textwrap.dedent(
        f"""
        Write a LangChain tool for an agent.

        Target file: backend/app/custom/tools.py (your code is inserted there; imports are hoisted)
        Function: `{name}`
        Signature: `@tool` then `def {name}({params}) -> str:` (async def is fine)
        What it must do: {data['description']}
        Inputs:
        """
    ).strip()
    for i in data["inputs"]:
        spec += f"\n- {i['name']} ({i['type']}): {i.get('description') or 'no description'}"
    if data.get("env"):
        spec += f"\nSecrets available as environment variables: {', '.join(data['env'])}"
    spec += textwrap.dedent(
        f"""

        Rules:
        - Import `tool` from langchain_core.tools. Prefer the standard library, httpx and pydantic.
        - Read secrets with os.environ.get(...). Never hard-code keys or URLs that contain secrets.
        - Return a short string the model can read. On any failure return an explanatory string; never raise.
        - Use timeouts on network calls.

        Example of the expected shape:
        ```python
        import os

        import httpx
        from langchain_core.tools import tool


        @tool
        def get_weather(city: str) -> str:
            \"\"\"Current weather for a city. Use when the user asks about weather.\"\"\"
            key = os.environ.get("WEATHER_API_KEY")
            if not key:
                return "Weather lookup isn't configured: set WEATHER_API_KEY."
            try:
                res = httpx.get("https://api.example.com/weather", params={{"q": city, "key": key}}, timeout=15)
                res.raise_for_status()
            except httpx.HTTPError as exc:
                return f"Weather lookup failed: {{exc}}"
            return res.text[:2000]
        ```

        The test it must pass (run with no network and no secrets set):
        ```python
        from app.custom.tools import {name}
        from langchain_core.tools import BaseTool
        assert isinstance({name}, BaseTool)
        result = {name}.invoke({{{sample}}})   # or ainvoke for async tools
        assert isinstance(result, str) and result
        ```
        """
    )
    return name, spec


def _step_contract(node_id: str, data: dict[str, Any]) -> tuple[str, str]:
    spec = textwrap.dedent(
        f"""
        Write a custom step for a LangGraph agent loop.

        Target file: backend/app/custom/nodes.py (your code is inserted there; imports are hoisted)
        Function: `def {node_id}(state: dict[str, Any]) -> dict[str, Any]:` (async def is fine)
        What it must do: {data['description']}

        The state dict has:
        - "messages": list of LangChain messages. The user's messages are HumanMessage without a name;
          replies are AIMessage(name=<step id>).
        - "decisions", "counters", "context": dicts keyed by step id.
        Return only the keys you change. To add a reply, return {{"messages": [AIMessage(content=..., name="{node_id}")]}}.
        Return {{}} to change nothing. Never raise; handle errors and return {{}}.

        The test it must pass (no network, no secrets):
        ```python
        from langchain_core.messages import HumanMessage
        from app.custom.nodes import {node_id}
        out = {node_id}({{"messages": [HumanMessage(content="hello")], "decisions": {{}}, "counters": {{}}, "context": {{}}}})
        # (awaited if async)
        assert isinstance(out, dict)
        ```
        """
    ).strip()
    return node_id, spec


ROUTER_SYSTEM = (
    "You write small, correct, production-quality Python for agentic applications. "
    "Follow the contract exactly: function name, signature, return type and the rules. "
    "Return only what the schema asks for."
)

_SANDBOX_IMAGE = "configurator-sandbox:py312"
_SANDBOX_DOCKERFILE = """FROM python:3.12-slim
RUN pip install --no-cache-dir langchain-core==1.6.6 httpx==0.28.1 pydantic==2.13.5
"""


def _ensure_sandbox_image() -> bool:
    from .verifier import docker_available

    if not docker_available():
        return False
    have = subprocess.run(["docker", "image", "inspect", _SANDBOX_IMAGE], capture_output=True).returncode == 0
    if have:
        return True
    with tempfile.TemporaryDirectory() as d:
        Path(d, "Dockerfile").write_text(_SANDBOX_DOCKERFILE)
        return subprocess.run(["docker", "build", "-q", "-t", _SANDBOX_IMAGE, d], capture_output=True, timeout=900).returncode == 0


def run_contract_test(code: str, name: str, *, is_tool: bool, inputs: list[dict[str, Any]], deps: list[str]) -> tuple[bool | None, str]:
    """Run the contract test in a container with no network. Returns (None, reason) if no sandbox."""
    if not _ensure_sandbox_image():
        return None, "Docker isn't running, so the code was checked statically but not executed."
    sample = {i["name"]: {"str": "test", "int": 1, "float": 1.5, "bool": True}[i["type"]] for i in inputs}
    if is_tool:
        test = textwrap.dedent(
            f"""
            import asyncio, inspect
            from langchain_core.tools import BaseTool
            from app.custom.tools import {name} as t
            assert isinstance(t, BaseTool), "not a tool"
            args = {json.dumps(sample)}
            r = asyncio.run(t.ainvoke(args)) if getattr(t, "coroutine", None) else t.invoke(args)
            assert isinstance(r, str) and r, f"expected a non-empty string, got {{r!r}}"
            print("OK", r[:200])
            """
        )
        module = "tools.py"
    else:
        test = textwrap.dedent(
            f"""
            import asyncio, inspect
            from langchain_core.messages import HumanMessage
            from app.custom.nodes import {name} as f
            state = {{"messages": [HumanMessage(content="hello")], "decisions": {{}}, "counters": {{}}, "context": {{}}}}
            out = f(state)
            if inspect.isawaitable(out):
                out = asyncio.run(out)
            assert isinstance(out, dict), f"expected a dict, got {{type(out)}}"
            print("OK", out)
            """
        )
        module = "nodes.py"
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "app/custom").mkdir(parents=True)
        (root / "app/__init__.py").write_text("")
        (root / "app/custom/__init__.py").write_text("")
        body = "\n".join(line for line in code.splitlines() if line.strip() != "from __future__ import annotations")
        (root / "app/custom" / module).write_text("from __future__ import annotations\n\nfrom typing import Any\n\n" + body + "\n")
        (root / "contract_test.py").write_text(test)
        install = f"pip install -q {' '.join(deps)} >/dev/null 2>&1; " if deps else ""
        network = [] if deps else ["--network", "none"]
        cmd = [
            "docker", "run", "--rm", *network, "--memory", "512m", "--cpus", "1",
            "-v", f"{root}:/work:ro", "-w", "/work", _SANDBOX_IMAGE,
            "sh", "-c", f"{install}timeout 60 python contract_test.py",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    out = (proc.stdout + proc.stderr).strip()[-3000:]
    return proc.returncode == 0, out


@dataclass
class FillResult:
    node_id: str
    ok: bool
    attempts: int
    verified: Literal["executed", "static", "failed"]
    message: str


def generate_code(spec: Spec, node_id: str, *, max_attempts: int = 3, log_fn: Callable[[str], None] = lambda _m: None) -> tuple[Spec, FillResult]:
    """Write code for one Custom tool or Custom step block and store it in the spec."""
    raw = spec.model_dump(mode="json", by_alias=True)
    node = next(n for n in raw["graph"]["nodes"] if n["id"] == node_id)
    is_tool = node["type"] == "custom_tool"
    if node["type"] not in {"custom_tool", "custom_step"}:
        raise ValueError(f"{node_id} is not a custom block")
    name, contract = _tool_contract(node["data"]) if is_tool else _step_contract(node_id, node["data"])
    feedback = ""
    last = ""
    for attempt in range(1, max_attempts + 1):
        log_fn(f"{node_id}: asking Claude (attempt {attempt}/{max_attempts})")
        user = contract + (f"\n\nYour previous attempt failed:\n{feedback}\nFix it." if feedback else "")
        gen: GeneratedCode = _call_structured(ROUTER_SYSTEM, user, GeneratedCode, effort="high")
        code = re.sub(r"^```(?:python)?\s*|\s*```$", "", gen.code.strip())
        problems = static_check(code, name, is_tool=is_tool)
        if problems:
            feedback = "Static check failed:\n" + "\n".join(f"- {p}" for p in problems)
            last = feedback
            continue
        inputs = node["data"].get("inputs", []) if is_tool else []
        passed, output = run_contract_test(code, name, is_tool=is_tool, inputs=inputs, deps=gen.python_deps)
        if passed is False:
            feedback = f"Contract test failed:\n{output}"
            last = feedback
            continue
        node["data"]["code"] = code
        node["data"]["generated_by"] = "claude"
        if is_tool:
            node["data"]["python_deps"] = sorted(set(node["data"].get("python_deps", [])) | set(gen.python_deps))
            node["data"]["env"] = sorted(set(node["data"].get("env", [])) | {e for e in gen.env if re.fullmatch(r"[A-Z][A-Z0-9_]*", e)})
        verified: Literal["executed", "static"] = "executed" if passed else "static"
        note = gen.notes + ("" if passed else f" ({output})")
        return parse_spec(raw), FillResult(node_id, True, attempt, verified, note.strip())
    return spec, FillResult(node_id, False, max_attempts, "failed", f"Left open after {max_attempts} attempts. {last[:400]}")


def fill_gaps(spec: Spec, *, log: Callable[[str], None] = lambda _m: None) -> tuple[Spec, list[str]]:
    """Write code for every custom block that has none. Returns the new spec and a report."""
    res = resolve(spec)
    if not res.gaps:
        return spec, ["No custom blocks need code."]
    if not available():
        return spec, ["ANTHROPIC_API_KEY isn't set: custom blocks will be exported as typed stubs listed in PROMPT_PACK.md."]
    report = []
    for gap in res.gaps:
        spec, result = generate_code(spec, gap.node_id, log_fn=log)
        if result.ok:
            report.append(f"✓ {gap.node_id}: written in {result.attempts} attempt(s), {result.verified} check. {result.message}")
        else:
            report.append(f"✗ {gap.node_id}: {result.message} It stays open in PROMPT_PACK.md.")
    return spec, report


# =========================================================================== 3. prompt help


class DraftPrompt(BaseModel):
    prompt: str = Field(description="The instructions, 3 to 8 sentences, second person, plain English")


def write_prompt(kind: str, label: str, role: str, context: str = "", tools: list[str] | None = None) -> str:
    """Draft instructions for one block on the canvas."""
    tool_line = f"Tools available to it: {', '.join(tools)}." if tools else "It has no tools."
    user = (
        f"Write the instructions for a '{kind}' block called '{label}' in an agent workflow.\n"
        f"Its job: {role or label}.\n{tool_line}\n"
        f"Other context about the app: {context or 'none'}\n"
        "Be specific about what good output looks like, when to use each tool, and what to do when unsure. "
        "No preamble, no markdown headings."
    )
    result: DraftPrompt = _call_structured(
        "You write clear, effective system prompts for production agents.", user, DraftPrompt, effort="low", max_tokens=4000
    )
    return result.prompt.strip()
