"""Rules engine: plain if/else checks, no LLM.

It does four jobs (section 4.3 of the brief):
1. Resolves which modules a spec needs.
2. Blocks invalid combinations with a clear message.
3. Picks which templates apply (via the module list).
4. Reports gaps (custom code nobody has written yet) for the fallback router.

Every issue can point at a node, so the canvas can put a badge on it.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

from configurator_spec import FLOW_TYPES, TOOL_TYPES, Spec

from .compiler import CompiledGraph, compile_graph, find_cycles

Level = Literal["error", "warning", "info"]

LOOP_BREAKERS = {"critic", "router", "supervisor", "approval", "guardrail"}
SAMPLING_FREE_PREFIXES = ("claude-opus-5", "claude-sonnet-5", "claude-fable-5", "claude-mythos", "claude-opus-4-7", "claude-opus-4-8")


@dataclass
class Issue:
    level: Level
    code: str
    message: str
    node_id: str | None = None
    fix: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        return asdict(self)


@dataclass
class Gap:
    """Something no template can produce. The fallback router (or a human) fills it."""

    node_id: str
    kind: Literal["custom_tool", "custom_step"]
    description: str


@dataclass
class Resolution:
    spec: Spec
    graph: CompiledGraph
    modules: list[str]
    issues: list[Issue] = field(default_factory=list)
    gaps: list[Gap] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(i.level == "error" for i in self.issues)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "error"]


def resolve(spec: Spec) -> Resolution:
    cg = compile_graph(spec)
    res = Resolution(spec=spec, graph=cg, modules=[])
    add = res.issues.append

    # ------------------------------------------------------------------ project
    if spec.backend.language == "typescript":
        add(Issue("error", "backend.typescript", "The TypeScript backend is not available yet. Switch the backend to Python.", fix="backend.language=python"))
    if spec.deploy.backend_port == spec.deploy.frontend_port:
        add(Issue("error", "deploy.ports", "The API and UI ports must be different."))
    model = spec.llm.model
    if spec.llm.provider == "anthropic" and not model.startswith("claude-"):
        add(Issue("warning", "llm.model", f"'{model}' doesn't look like a Claude model id."))
    if spec.llm.provider == "openai" and model.startswith("claude-"):
        add(Issue("error", "llm.model", f"'{model}' is a Claude model but the provider is OpenAI."))
    if spec.llm.provider == "openai" and spec.llm.effort:
        add(Issue("info", "llm.effort", "Reasoning effort only applies to Claude models; it will be ignored."))

    # ------------------------------------------------------------------ structure
    nodes = spec.graph.nodes
    inputs = [n for n in nodes if n.type == "input"]
    if not nodes:
        add(Issue("error", "graph.empty", "The canvas is empty. Start from a template or drag a Chat input onto the canvas."))
        return _finish(res)
    if not inputs:
        add(Issue("error", "graph.no_input", "Add a Chat input. It is where the user's message enters the loop."))
    elif len(inputs) > 1:
        for n in inputs[1:]:
            add(Issue("error", "graph.multiple_inputs", "Only one Chat input is allowed.", n.id))
    if inputs and not cg.entry:
        add(Issue("error", "graph.input_unconnected", "Connect the Chat input to the first step.", inputs[0].id))
    if not any(n.type == "output" for n in nodes):
        add(Issue("info", "graph.no_output", "No Reply block: the run ends wherever a branch stops. Adding one makes the end explicit."))
    memories = [m for m in nodes if m.type == "memory"]
    for extra in memories[1:]:
        add(Issue("error", "graph.multiple_memory", "Only one Memory block is allowed per project.", extra.id))
    if not any(n.type in {"agent", "supervisor", "prompt"} for n in nodes):
        add(Issue("warning", "graph.no_model", "Nothing here calls a model yet. Add an Agent or an LLM step."))

    by_id = {n.id: n for n in nodes}
    for e in spec.graph.edges:
        src, dst = by_id[e.source], by_id[e.target]
        if e.source == e.target:
            add(Issue("error", "edge.self", "A block can't connect to itself. Use a Review loop to repeat work.", e.source))
        if src.type in FLOW_TYPES and dst.type not in FLOW_TYPES:
            add(Issue("error", "edge.into_resource", f"{_label(src)} can't connect into {_label(dst)}. Drag from the resource up into an agent instead.", e.source))
        if src.type not in FLOW_TYPES:
            if dst.type not in FLOW_TYPES:
                add(Issue("error", "edge.resource_to_resource", "Resources attach to agents or retrieve steps, not to each other.", e.source))
            elif src.type in TOOL_TYPES and dst.type != "agent":
                add(Issue("error", "edge.tool_target", f"Tools attach to an Agent. {_label(dst)} can't use tools.", e.source))
            elif src.type == "knowledge" and dst.type not in {"agent", "retriever"}:
                add(Issue("error", "edge.knowledge_target", "Attach a knowledge base to an Agent or a Retrieve step.", e.source))
            elif src.type == "memory" and dst.type != "agent":
                add(Issue("error", "edge.memory_target", "Attach Memory to an Agent to give it long-term recall.", e.source))
        if dst.type == "input":
            add(Issue("error", "edge.into_input", "Nothing can flow back into the Chat input.", e.target))

    # ------------------------------------------------------------------ per node
    for fn in cg.nodes.values():
        if fn.id in cg.unreachable:
            add(Issue("warning", "node.unreachable", f"{fn.label} is never reached from the Chat input.", fn.id))
        if fn.type == "supervisor":
            if not fn.workers:
                add(Issue("error", "supervisor.no_workers", f"{fn.label} has no workers. Connect its Delegate output to one or more agents.", fn.id))
            for w in fn.workers:
                worker = cg.nodes[w]
                if worker.out:
                    add(Issue("info", "supervisor.worker_out", f"{worker.label} reports back to {fn.label}, so its own outgoing connections are ignored.", w))
        if fn.type == "router":
            routes = fn.data["routes"]
            if len(routes) < 2:
                add(Issue("warning", "router.few_routes", f"{fn.label} has fewer than two branches.", fn.id))
            for b in fn.branches:
                if not b.targets:
                    add(Issue("warning", "router.branch_unconnected", f"Branch '{b.label}' of {fn.label} isn't connected; that branch ends the run.", fn.id))
            if fn.data["mode"] == "keywords" and not any(r["keywords"] for r in routes):
                add(Issue("warning", "router.no_keywords", f"{fn.label} decides with keywords but no branch has any. Everything goes to the last branch.", fn.id))
        if fn.type == "critic":
            revise = next(b for b in fn.branches if b.handle == "revise")
            if not revise.targets:
                add(Issue("warning", "critic.no_revise", f"Connect the Revise output of {fn.label} back to the step that should redo the work.", fn.id))
        if fn.type == "retriever" and not fn.knowledge:
            add(Issue("error", "retriever.no_knowledge", f"Attach a Knowledge base to {fn.label}.", fn.id))
        if fn.type == "approval" and not cg.memory:
            add(Issue("info", "approval.memory", "Approvals pause the run. Without a Memory block, paused runs are kept in RAM and lost on restart.", fn.id))
        if fn.type == "agent":
            model_id = fn.data.get("model") or spec.llm.model
            if fn.data.get("temperature") is not None and model_id.startswith(SAMPLING_FREE_PREFIXES):
                add(Issue("info", "agent.temperature", f"{model_id} doesn't accept temperature; it will be ignored. Use effort instead.", fn.id))
        if fn.type == "custom_step" and not (fn.data.get("code") or "").strip():
            res.gaps.append(Gap(fn.id, "custom_step", fn.data["description"]))
            add(Issue("info", "custom_step.no_code", f"{fn.label} has no code yet. Generate it with Claude, write it, or export a stub.", fn.id))

    for r in cg.resources.values():
        if r.type in TOOL_TYPES | {"knowledge"} and not r.attached_to:
            add(Issue("warning", "resource.unattached", f"{r.label} isn't attached to anything, so it won't be used.", r.id))
        if r.type == "custom_tool" and not (r.data.get("code") or "").strip():
            res.gaps.append(Gap(r.id, "custom_tool", r.data["description"]))
            add(Issue("info", "custom_tool.no_code", f"{r.label} has no code yet. Generate it with Claude, write it, or export a stub.", r.id))
        if r.type == "mcp_server" and r.data["transport"] != "stdio" and not r.data["url"]:
            add(Issue("error", "mcp.url", f"{r.label} needs a server URL.", r.id))
        if r.type == "knowledge" and r.data["embedding"].startswith("openai") and spec.llm.provider == "anthropic":
            add(Issue("info", "knowledge.openai_key", "OpenAI embeddings need OPENAI_API_KEY as well as your Anthropic key. Pick Local embeddings to avoid a second key.", r.id))

    tool_names: dict[str, str] = {}
    for r in cg.tools:
        name = r.data.get("tool_name")
        if name:
            if name in tool_names:
                add(Issue("error", "tool.duplicate_name", f"Two tools are called '{name}'. Tool names must be unique.", r.id))
            tool_names[name] = r.id

    # ------------------------------------------------------------------ loops
    for comp in find_cycles(cg):
        types = {cg.nodes[i].type for i in comp}
        if not types & LOOP_BREAKERS:
            first = comp[0]
            add(Issue("error", "graph.infinite_loop", "This loop has no way out. Add a Review loop, Router or Supervisor to decide when to stop.", first))

    res.modules = _modules(spec, cg)
    return _finish(res)


def _label(node: object) -> str:
    data = getattr(node, "data", None)
    return (getattr(data, "label", "") or getattr(node, "id", "")) or "This block"


def _finish(res: Resolution) -> Resolution:
    order = {"error": 0, "warning": 1, "info": 2}
    res.issues.sort(key=lambda i: (order[i.level], i.code, i.node_id or ""))
    return res


def _modules(spec: Spec, cg: CompiledGraph) -> list[str]:
    mods = ["core", f"provider.{spec.llm.provider}"]
    if any(n.data.get("model") for n in cg.nodes.values()):
        # Per-node models may name the other provider.
        for n in cg.nodes.values():
            m = n.data.get("model") or ""
            if m.startswith("claude-") and spec.llm.provider != "anthropic":
                mods.append("provider.anthropic")
            if m and not m.startswith("claude-") and spec.llm.provider != "openai":
                mods.append("provider.openai")
    for t in sorted(cg.node_types):
        mods.append(f"node.{t}")
    for t in sorted(cg.resource_types & TOOL_TYPES):
        mods.append(f"tool.{t}")
    if cg.knowledge:
        mods.append("rag.core")
        for kb in cg.knowledge:
            mods.append(f"vector_store.{kb.data['vector_store']}")
            mods.append(f"embedding.{kb.data['embedding'].split('_')[0]}")
            if kb.data["retrieval"] == "hybrid":
                mods.append("retrieval.hybrid")
            if kb.data["reranker"] != "none":
                mods.append(f"reranker.{kb.data['reranker']}")
    mem = cg.memory
    short_term = mem.data["short_term"] if mem else "memory"
    mods.append(f"memory.{short_term}")
    if mem and mem.data["long_term"]:
        mods.append("memory.long_term")
    if spec.ui.framework == "nextjs":
        mods.append("ui.nextjs")
    if spec.deploy.target == "docker_compose":
        mods.append("deploy.docker_compose")
    if spec.observability.langsmith:
        mods.append("observability.langsmith")
    return list(dict.fromkeys(mods))
