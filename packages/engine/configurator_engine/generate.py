"""Render a spec into a complete project (section 4.4).

Pipeline: validate -> resolve modules (rules) -> build template context -> render
every module's files -> merge shared files -> write PROMPT_PACK.md, DECISIONS.md.

No network, no LLM. The only inputs are the spec and the modules folder, so the
same spec renders byte-identical output every time (golden tests rely on this).
"""

from __future__ import annotations

import io
import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from configurator_spec import Spec, dump_spec

from . import merger
from .codeparts import merge_imports, split_imports
from .compiler import END, CompiledGraph
from .registry import Module, load_registry, load_versions, modules_dir
from .rules import Resolution, resolve

PRESERVED_PREFIX = "backend/app/custom/"
# Files rendered after everything else, so they can list the final file map.
LATE_FILES = {"PROMPT_PACK.md", "README.md", "DECISIONS.md"}


class GenerationError(Exception):
    def __init__(self, resolution: Resolution) -> None:
        self.resolution = resolution
        msgs = "; ".join(i.message for i in resolution.errors)
        super().__init__(f"spec has errors: {msgs}")


@dataclass
class Output:
    files: dict[str, str]
    resolution: Resolution
    owners: dict[str, list[str]] = field(default_factory=dict)  # path -> [module id, item id]
    node_files: dict[str, list[str]] = field(default_factory=dict)

    def tree(self) -> list[str]:
        return sorted(self.files)


# ------------------------------------------------------------------ jinja filters


def _pystr(value: Any) -> str:
    """A Python string literal. JSON string syntax is valid Python."""
    if value is None:
        return "None"
    return json.dumps(str(value), ensure_ascii=False)


def _pytext(value: str, indent: int = 4) -> str:
    """A readable multi-line Python string: one literal per line, implicitly joined."""
    text = str(value)
    if "\n" not in text and len(text) < 90:
        return _pystr(text)
    parts = text.splitlines(keepends=True)
    pad = " " * indent
    body = "\n".join(f"{pad}    {_pystr(p)}" for p in parts)
    return f"(\n{body}\n{pad})"


def _py(value: Any) -> str:
    """Python literal for simple JSON-like values."""
    if value is None:
        return "None"
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, int | float):
        return repr(value)
    if isinstance(value, str):
        return _pystr(value)
    if isinstance(value, list):
        return "[" + ", ".join(_py(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{_pystr(k)}: {_py(v)}" for k, v in value.items()) + "}"
    raise TypeError(f"can't render {type(value)} as a Python literal")


def _make_env(root: Path) -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(root)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        autoescape=False,
    )
    env.filters["pystr"] = _pystr
    env.filters["pytext"] = _pytext
    env.filters["py"] = _py
    env.filters["pytuple"] = lambda v: "(" + ", ".join(_py(x) for x in v) + ("," if len(v) == 1 else "") + ")"
    env.filters["tojson"] = lambda v, indent=None: json.dumps(v, indent=indent, ensure_ascii=False)
    return env


# ------------------------------------------------------------------ context


def _target(cg: CompiledGraph, node_id: str) -> str:
    return "END" if cg.is_end(node_id) else _pystr(node_id)


def build_context(res: Resolution) -> dict[str, Any]:
    spec, cg = res.spec, res.graph
    mods = set(res.modules)
    mem = cg.memory
    short_term = mem.data["short_term"] if mem else "memory"
    long_term = bool(mem and mem.data["long_term"])

    def tools_of(t: str) -> list[Any]:
        return [r for r in cg.tools if r.type == t]

    mcp = tools_of("mcp_server")
    needs_node_runtime = any(r.data["transport"] == "stdio" and r.data["command"] in {"npx", "node", "npm"} for r in mcp)
    needs_uv = any(r.data["transport"] == "stdio" and r.data["command"] in {"uvx", "uv"} for r in mcp)
    needs_postgres = short_term == "postgres" or any(k.data["vector_store"] == "pgvector" for k in cg.knowledge)

    custom_tools = tools_of("custom_tool")
    tool_imports: list[list[str]] = []
    tool_bodies: list[dict[str, Any]] = []
    for r in custom_tools:
        code = (r.data.get("code") or "").strip()
        if code:
            imps, body = split_imports(code)
            tool_imports.append(imps)
            tool_bodies.append({"res": r, "body": body, "stub": False})
        else:
            tool_bodies.append({"res": r, "body": "", "stub": True})
    tool_import_lines = merge_imports(tool_imports, always=["from langchain_core.tools import tool"])

    steps = cg.of_type("custom_step")
    step_imports: list[list[str]] = []
    step_bodies: list[dict[str, Any]] = []
    for n in steps:
        code = (n.data.get("code") or "").strip()
        if code:
            imps, body = split_imports(code)
            step_imports.append(imps)
            step_bodies.append({"node": n, "body": body, "stub": False})
        else:
            step_bodies.append({"node": n, "body": "", "stub": True})
    step_import_lines = merge_imports(step_imports, always=["from typing import Any"])

    extra_py = sorted({d for r in custom_tools for d in r.data.get("python_deps", [])})
    custom_env = sorted({e for r in custom_tools for e in r.data.get("env", [])})

    flow_count = max(1, len(cg.nodes))
    loops = sum(n.data.get("max_iterations", 0) + n.data.get("max_rounds", 0) for n in cg.nodes.values())
    recursion_limit = max(50, (flow_count + 2) * (loops + 3))

    def branch_map(n: Any) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for w in n.workers:
            out[w] = [_pystr(w)]
        for b in n.branches:
            key = b.handle.split(":", 1)[1] if b.handle.startswith("route:") else b.handle
            targets = list(dict.fromkeys(_target(cg, t) for t in b.targets)) or ["END"]
            out[key] = targets
        return out

    def branch_destinations(n: Any) -> list[str]:
        return list(dict.fromkeys(t for ts in branch_map(n).values() for t in ts))

    def reject_ends(n: Any) -> bool:
        rejected = next((b for b in n.branches if b.handle == "rejected"), None)
        return rejected is None or all(cg.is_end(t) for t in rejected.targets)

    labels = {n.id: n.label for n in cg.nodes.values()}
    labels.update({r.id: r.label for r in cg.resources.values()})

    return {
        "spec": spec,
        "project": spec.project,
        "llm": spec.llm,
        "ui": spec.ui,
        "deploy": spec.deploy,
        "observability": spec.observability,
        "g": cg,
        "END": END,
        "target": lambda node_id: _target(cg, node_id),
        "modules": mods,
        "nodes": list(cg.nodes.values()),
        "graph_nodes": [n for n in cg.nodes.values() if n.id not in cg.unreachable],
        "branch_map": branch_map,
        "branch_destinations": branch_destinations,
        "reject_ends": reject_ends,
        "agents": cg.of_type("agent"),
        "supervisors": cg.of_type("supervisor"),
        "routers": cg.of_type("router"),
        "critics": cg.of_type("critic"),
        "approvals": cg.of_type("approval"),
        "guardrails": cg.of_type("guardrail"),
        "retrievers": cg.of_type("retriever"),
        "prompt_steps": cg.of_type("prompt"),
        "custom_steps": steps,
        "resources": list(cg.resources.values()),
        "tools": cg.tools,
        "web_search_tools": tools_of("web_search"),
        "web_fetch_tools": tools_of("web_fetch"),
        "http_tools": tools_of("http_api"),
        "mcp_servers": mcp,
        "calculators": tools_of("calculator"),
        "sql_tools": tools_of("sql_database"),
        "custom_tools": custom_tools,
        "custom_tool_imports": tool_import_lines,
        "custom_tool_bodies": tool_bodies,
        "custom_step_imports": step_import_lines,
        "custom_step_bodies": step_bodies,
        "custom_env": custom_env,
        "extra_python_deps": extra_py,
        "knowledge": cg.knowledge,
        "attached_knowledge": [k for k in cg.knowledge if any(cg.nodes[a].type == "agent" for a in k.attached_to if a in cg.nodes)],
        "memory": mem,
        "short_term": short_term,
        "long_term": long_term,
        "has_rag": bool(cg.knowledge),
        "has_approval": bool(cg.of_type("approval")),
        "has_ui": spec.ui.framework == "nextjs",
        "has_compose": spec.deploy.target == "docker_compose",
        "needs_postgres": needs_postgres,
        "needs_node_runtime": needs_node_runtime,
        "needs_uv": needs_uv,
        "recursion_limit": recursion_limit,
        "labels": labels,
        "speaking_nodes": [n.id for n in cg.nodes.values() if n.type in {"agent", "prompt", "supervisor", "guardrail", "approval", "custom_step"}],
        "gaps": res.gaps,
        "issues": res.issues,
        "spec_json": dump_spec(spec),
        "stores": sorted({k.data["vector_store"] for k in cg.knowledge}),
        "embeddings": sorted({k.data["embedding"] for k in cg.knowledge}),
        "rerankers": sorted({k.data["reranker"] for k in cg.knowledge} - {"none"}),
        "hybrid": any(k.data["retrieval"] == "hybrid" for k in cg.knowledge),
        "title": spec.ui.title or spec.project.name.replace("-", " ").title(),
        "greeting": next((n.data.greeting for n in spec.graph.nodes if n.type == "input"), "Hi! What can I help you with?"),  # type: ignore[union-attr]
    }


# ------------------------------------------------------------------ render


def _module_order(res: Resolution, registry: dict[str, Module]) -> list[Module]:
    missing = [m for m in res.modules if m not in registry]
    if missing:
        raise KeyError(f"modules not found in registry: {', '.join(missing)}")
    return [registry[m] for m in res.modules]


def generate(spec: Spec, *, allow_errors: bool = False) -> Output:
    res = resolve(spec)
    if not res.ok and not allow_errors:
        raise GenerationError(res)
    root = modules_dir()
    registry = load_registry(str(root))
    versions = load_versions(str(root))
    mods = _module_order(res, registry)
    ctx = build_context(res)
    env = _make_env(root)

    files: dict[str, str] = {}
    owners: dict[str, list[str]] = {}
    late: list[tuple[Module, Any, dict[str, Any]]] = []

    def render_one(mod: Module, fs: Any, local: dict[str, Any]) -> None:
        dest = env.from_string(fs.dest).render(**local)
        if dest in LATE_FILES and "file_list" not in local:
            late.append((mod, fs, local))
            return
        if fs.src.endswith(".j2"):
            content = env.get_template(f"{mod.path.name}/{fs.src}").render(**local)
        else:  # static file: copied byte for byte
            content = (mod.path / fs.src).read_text(encoding="utf-8")
        if not content.strip() and not dest.endswith("__init__.py") and not dest.endswith(".gitkeep"):
            return
        files[dest] = content
        owners[dest] = [mod.id, local.get("item_id", "")]

    for mod in mods:
        for fs in mod.template_files():
            items: list[Any] = [None]
            if fs.foreach:
                items = list(ctx[fs.foreach])
            for item in items:
                local = dict(ctx)
                local["module"] = mod
                if item is not None:
                    local["item"] = item
                    local["item_id"] = getattr(item, "id", "")
                if fs.when and not env.compile_expression(fs.when)(**local):
                    continue
                render_one(mod, fs, local)

    # ------------------------------------------------ merged files
    py_deps, dev_deps = merger.python_deps(mods, versions["python"], ctx["extra_python_deps"])
    files["backend/pyproject.toml"] = merger.pyproject(spec.project.name, spec.project.description, py_deps, dev_deps)
    files["backend/requirements.txt"] = merger.requirements(py_deps)
    owners["backend/pyproject.toml"] = ["core", ""]
    owners["backend/requirements.txt"] = ["core", ""]
    pkg = merger.package_json(spec.project.name, mods, versions["node"])
    if pkg:
        files["frontend/package.json"] = pkg
        owners["frontend/package.json"] = ["ui.nextjs", ""]
    fragments = []
    for m in mods:
        if m.compose:
            fragments.append(json.loads(env.from_string(json.dumps(m.compose)).render(**ctx)))
    compose = merger.compose(fragments) if spec.deploy.target == "docker_compose" else None
    if compose:
        files["docker-compose.yml"] = compose
        owners["docker-compose.yml"] = ["deploy.docker_compose", ""]
    env_groups = []
    for m in mods:
        rendered = []
        for e in m.env:
            # A name template may expand to several comma-separated names (one per block).
            for name in env.from_string(e.name).render(**ctx).split(","):
                if name.strip():
                    rendered.append({"name": name.strip(), "value": env.from_string(e.value).render(**ctx), "comment": e.comment})
        if rendered:
            env_groups.append((m.title, rendered))
    if ctx["custom_env"]:
        env_groups.append(("Custom tools", [{"name": e, "value": "", "comment": "Used by a custom tool"} for e in ctx["custom_env"]]))
    files[".env.example"] = merger.env_example(env_groups)
    owners[".env.example"] = ["core", ""]
    files["spec.json"] = ctx["spec_json"]
    owners["spec.json"] = ["core", ""]

    # ------------------------------------------------ late files (need the file map)
    decisions = [{"module": m.id, "title": m.title, **m.explain} for m in mods if m.explain]
    for mod, fs, local in late:
        local = dict(local)
        local["file_list"] = sorted(set(files) | {env.from_string(f.dest).render(**local) for _, f, _ in late})
        local["decisions"] = decisions
        local["env_groups"] = env_groups
        render_one(mod, fs, local)

    files = dict(sorted(files.items()))
    return Output(files=files, resolution=res, owners=owners, node_files=_node_files(res, owners))


def _node_files(res: Resolution, owners: dict[str, list[str]]) -> dict[str, list[str]]:
    """Which files each canvas node produces or shapes, for the code preview."""
    cg = res.graph
    out: dict[str, list[str]] = {}
    by_module: dict[str, list[str]] = {}
    by_item: dict[str, list[str]] = {}
    for path, (mod, item) in owners.items():
        by_module.setdefault(mod, []).append(path)
        if item:
            by_item.setdefault(item, []).append(path)
    for n in cg.nodes.values():
        paths = ["backend/app/graph.py", "backend/app/prompts.py"] + by_module.get(f"node.{n.type}", []) + by_item.get(n.id, [])
        if n.type == "custom_step":
            paths.append("backend/app/custom/nodes.py")
        out[n.id] = sorted({p for p in paths if p in owners})
    for r in cg.resources.values():
        key = {"knowledge": "rag.core", "memory": f"memory.{r.data.get('short_term', 'memory')}"}.get(r.type, f"tool.{r.type}")
        paths = by_module.get(key, []) + by_item.get(r.id, []) + ["backend/app/tools/__init__.py"]
        if r.type == "custom_tool":
            paths.append("backend/app/custom/tools.py")
        if r.type == "memory" and r.data.get("long_term"):
            paths += by_module.get("memory.long_term", [])
        out[r.id] = sorted({p for p in paths if p in owners})
    if cg.input_id:
        out[cg.input_id] = sorted(p for p in ["backend/app/main.py", "backend/app/streaming.py"] if p in owners)
    for o in cg.outputs:
        out[o] = sorted(p for p in ["backend/app/streaming.py", "frontend/src/components/chat.tsx"] if p in owners)
    return out


# ------------------------------------------------------------------ output


def write(output: Output, target: str | Path, *, overwrite_custom: bool = False) -> list[str]:
    """Write files to disk. Files under backend/app/custom/ are kept if they exist."""
    base = Path(target)
    skipped = []
    for rel, content in output.files.items():
        path = base / rel
        if rel.startswith(PRESERVED_PREFIX) and path.exists() and not overwrite_custom:
            skipped.append(rel)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        if rel.endswith(".sh"):
            path.chmod(0o755)
    return skipped


def to_zip(output: Output, folder: str | None = None) -> bytes:
    """Deterministic zip: fixed timestamps and sorted entries."""
    prefix = (folder or output.resolution.spec.project.name).strip("/") + "/"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in sorted(output.files):
            info = zipfile.ZipInfo(prefix + rel, date_time=(2024, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if rel.endswith(".sh") else 0o644) << 16
            zf.writestr(info, output.files[rel])
    return buf.getvalue()
