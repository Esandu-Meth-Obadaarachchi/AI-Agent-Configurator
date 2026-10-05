"""Compile a spec graph into an intermediate representation (IR).

The canvas speaks in nodes, edges and handles. The templates want answers to plain
questions: which nodes run first, which tools does this agent have, where does the
'revise' branch of this review loop go. The compiler answers those questions once,
so every template stays simple.

The compiler never raises on a half-built graph. Missing branches end the run, and
problems are left for the rules engine to report.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from configurator_spec import FLOW_TYPES, TOOL_TYPES, Spec

END = "__end__"

# Which output handles each branching node type has. Router handles come from its routes.
BRANCH_HANDLES: dict[str, list[str]] = {
    "critic": ["pass", "revise"],
    "approval": ["approved", "rejected"],
    "guardrail": ["pass", "blocked"],
}
SIMPLE_TYPES = {"input", "agent", "prompt", "retriever", "custom_step"}
WORKER_TYPES = {"agent", "prompt", "custom_step", "retriever"}


@dataclass
class Branch:
    handle: str
    label: str
    targets: list[str]  # node ids; an output node id or END means "finish"


@dataclass
class FlowNode:
    id: str
    type: str
    label: str
    data: dict[str, Any]
    out: list[str] = field(default_factory=list)
    branches: list[Branch] = field(default_factory=list)
    workers: list[str] = field(default_factory=list)
    supervisor: str | None = None
    tools: list[str] = field(default_factory=list)
    knowledge: list[str] = field(default_factory=list)
    long_term_memory: bool = False

    @property
    def is_branching(self) -> bool:
        return bool(self.branches) or self.type in {"router", "critic", "approval", "guardrail", "supervisor"}


@dataclass
class Resource:
    id: str
    type: str
    label: str
    data: dict[str, Any]
    attached_to: list[str] = field(default_factory=list)


@dataclass
class CompiledGraph:
    input_id: str | None
    entry: list[str]
    nodes: dict[str, FlowNode]  # flow nodes except input/output, in run order
    outputs: set[str]
    resources: dict[str, Resource]
    unreachable: list[str]
    edge_ids: dict[tuple[str, str, str], str]

    # ------------------------------------------------------------------ helpers
    def is_end(self, node_id: str) -> bool:
        return node_id == END or node_id in self.outputs

    def of_type(self, *types: str) -> list[FlowNode]:
        return [n for n in self.nodes.values() if n.type in types]

    def resources_of(self, *types: str) -> list[Resource]:
        return [r for r in self.resources.values() if r.type in types]

    @property
    def tools(self) -> list[Resource]:
        return [r for r in self.resources.values() if r.type in TOOL_TYPES]

    @property
    def knowledge(self) -> list[Resource]:
        return self.resources_of("knowledge")

    @property
    def memory(self) -> Resource | None:
        mem = self.resources_of("memory")
        return mem[0] if mem else None

    @property
    def node_types(self) -> set[str]:
        return {n.type for n in self.nodes.values()}

    @property
    def resource_types(self) -> set[str]:
        return {r.type for r in self.resources.values()}

    def successors(self, node_id: str) -> list[str]:
        n = self.nodes[node_id]
        if n.supervisor:
            return [n.supervisor]
        out = list(n.out)
        for b in n.branches:
            out.extend(b.targets)
        out.extend(n.workers)
        return [t for t in out if not self.is_end(t)]


def _dump(model: Any) -> dict[str, Any]:
    return model.model_dump(mode="json")


def compile_graph(spec: Spec) -> CompiledGraph:
    g = spec.graph
    by_id = {n.id: n for n in g.nodes}
    outgoing: dict[tuple[str, str], list[str]] = defaultdict(list)
    attach: dict[str, list[tuple[str, str]]] = defaultdict(list)  # resource -> [(flow node, target handle)]
    edge_ids: dict[tuple[str, str, str], str] = {}

    for e in g.edges:
        src, dst = by_id[e.source], by_id[e.target]
        sh = e.source_handle or ("attach" if src.type not in FLOW_TYPES else "out")
        edge_ids[(e.source, sh, e.target)] = e.id
        if src.type not in FLOW_TYPES:
            if dst.type in FLOW_TYPES:
                attach[src.id].append((dst.id, e.target_handle or "tools"))
            continue
        if dst.type not in FLOW_TYPES:
            continue  # flow -> resource edges are meaningless; rules report them
        outgoing[(src.id, sh)].append(dst.id)

    for key in outgoing:
        outgoing[key] = sorted(set(outgoing[key]), key=lambda i: (by_id[i].position.y, by_id[i].position.x, i))

    inputs = [n for n in g.nodes if n.type == "input"]
    input_id = inputs[0].id if inputs else None
    outputs = {n.id for n in g.nodes if n.type == "output"}

    flow: dict[str, FlowNode] = {}
    for n in g.nodes:
        if n.type not in FLOW_TYPES or n.type in {"input", "output"}:
            continue
        data = _dump(n.data)
        fn = FlowNode(id=n.id, type=n.type, label=data.get("label") or n.id, data=data)
        if n.type in SIMPLE_TYPES:
            fn.out = outgoing.get((n.id, "out"), [])
        elif n.type == "router":
            for r in n.data.routes:
                fn.branches.append(Branch(f"route:{r.id}", r.label or r.id, outgoing.get((n.id, f"route:{r.id}"), [])))
        elif n.type in BRANCH_HANDLES:
            for h in BRANCH_HANDLES[n.type]:
                fn.branches.append(Branch(h, h.capitalize(), outgoing.get((n.id, h), [])))
        elif n.type == "supervisor":
            fn.workers = [w for w in outgoing.get((n.id, "delegate"), []) if by_id[w].type in WORKER_TYPES]
            fn.branches.append(Branch("done", "Done", outgoing.get((n.id, "done"), [])))
        flow[n.id] = fn

    for sup in [f for f in flow.values() if f.type == "supervisor"]:
        for w in sup.workers:
            if w in flow and flow[w].supervisor is None:
                flow[w].supervisor = sup.id

    resources: dict[str, Resource] = {}
    for n in g.nodes:
        if n.type in FLOW_TYPES:
            continue
        data = _dump(n.data)
        res = Resource(id=n.id, type=n.type, label=data.get("label") or n.id, data=data)
        for target, handle in sorted(attach.get(n.id, [])):
            if target not in flow:
                continue
            fnode = flow[target]
            if n.type in TOOL_TYPES and fnode.type == "agent":
                fnode.tools.append(n.id)
            elif n.type == "knowledge" and fnode.type == "agent":
                fnode.knowledge.append(n.id)
            elif n.type == "knowledge" and fnode.type == "retriever":
                fnode.knowledge.append(n.id)
            elif n.type == "memory" and fnode.type == "agent":
                fnode.long_term_memory = bool(n.data.long_term)  # type: ignore[union-attr]
            else:
                continue
            res.attached_to.append(target)
        resources[n.id] = res

    entry = outgoing.get((input_id, "out"), []) if input_id else []

    # Order nodes by first visit from the entry (stable, readable generated code).
    order: list[str] = []
    seen: set[str] = set()
    queue = [t for t in entry if t in flow]
    while queue:
        cur = queue.pop(0)
        if cur in seen:
            continue
        seen.add(cur)
        order.append(cur)
        fn = flow[cur]
        nxt = list(fn.out) + fn.workers + [t for b in fn.branches for t in b.targets]
        if fn.supervisor:
            nxt.append(fn.supervisor)
        queue.extend(t for t in nxt if t in flow and t not in seen)
    unreachable = sorted(i for i in flow if i not in seen)
    ordered = {i: flow[i] for i in order + unreachable}

    return CompiledGraph(
        input_id=input_id,
        entry=entry,
        nodes=ordered,
        outputs=outputs,
        resources=resources,
        unreachable=unreachable,
        edge_ids=edge_ids,
    )


# ---------------------------------------------------------------------- cycles


def find_cycles(cg: CompiledGraph) -> list[list[str]]:
    """Strongly connected components with more than one node (or a self loop)."""
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    sccs: list[list[str]] = []
    counter = [0]

    def strong(v: str) -> None:
        index[v] = low[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        on_stack.add(v)
        for w in cg.successors(v):
            if w not in cg.nodes:
                continue
            if w not in index:
                strong(w)
                low[v] = min(low[v], low[w])
            elif w in on_stack:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp = []
            while True:
                w = stack.pop()
                on_stack.discard(w)
                comp.append(w)
                if w == v:
                    break
            if len(comp) > 1 or v in cg.successors(v):
                sccs.append(sorted(comp))

    for v in cg.nodes:
        if v not in index:
            strong(v)
    return sccs


# ---------------------------------------------------------------------- trace


def simulate(cg: CompiledGraph, max_steps: int = 40) -> list[dict[str, Any]]:
    """A deterministic dry run the canvas animates.

    Decisions follow the happy path, but loops go round once so people can see them:
    routers take their first connected branch, review loops revise once then pass,
    approvals are approved, guardrails pass, supervisors call each worker once.
    """
    steps: list[dict[str, Any]] = []
    if not cg.input_id:
        return steps
    steps.append({"nodes": [cg.input_id], "edges": [], "note": "User message arrives"})

    def edge(src: str, handle: str, dst: str) -> str | None:
        return cg.edge_ids.get((src, handle, dst))

    frontier: list[tuple[str, str | None]] = [(t, edge(cg.input_id, "out", t)) for t in cg.entry]
    critic_rounds: dict[str, int] = defaultdict(int)
    sup_done: dict[str, list[str]] = defaultdict(list)

    while frontier and len(steps) < max_steps:
        nodes = []
        edges = []
        notes = []
        nxt: list[tuple[str, str | None]] = []
        for node_id, via in frontier:
            if via:
                edges.append(via)
            if node_id in nodes:
                continue
            nodes.append(node_id)
            if cg.is_end(node_id):
                notes.append("Reply sent")
                continue
            fn = cg.nodes.get(node_id)
            if fn is None:
                continue
            if fn.supervisor:
                back = edge(fn.supervisor, "delegate", fn.id)
                nxt.append((fn.supervisor, back))
                notes.append(f"{fn.label} reports back")
            elif fn.type in SIMPLE_TYPES:
                if fn.tools or fn.knowledge:
                    notes.append(f"{fn.label} uses its tools")
                nxt.extend((t, edge(fn.id, "out", t)) for t in fn.out)
                if not fn.out:
                    notes.append("Reply sent")
            elif fn.type == "supervisor":
                pending = [w for w in fn.workers if w not in sup_done[fn.id]]
                if pending:
                    w = pending[0]
                    sup_done[fn.id].append(w)
                    nxt.append((w, edge(fn.id, "delegate", w)))
                    notes.append(f"{fn.label} delegates to {cg.nodes[w].label if w in cg.nodes else w}")
                else:
                    done = next(b for b in fn.branches if b.handle == "done")
                    nxt.extend((t, edge(fn.id, "done", t)) for t in done.targets)
                    notes.append(f"{fn.label} is done")
            else:
                choice = _choose_branch(fn, critic_rounds)
                if choice is None:
                    notes.append(f"{fn.label}: branch not connected, run ends")
                    continue
                if fn.type == "critic":
                    critic_rounds[fn.id] += 1
                notes.append(f"{fn.label}: {choice.label}")
                nxt.extend((t, edge(fn.id, choice.handle, t)) for t in choice.targets)
        steps.append({"nodes": nodes, "edges": [e for e in edges if e], "note": "; ".join(notes)})
        frontier = nxt
    return steps


def _choose_branch(fn: FlowNode, critic_rounds: dict[str, int]) -> Branch | None:
    connected = [b for b in fn.branches if b.targets]
    if fn.type == "critic":
        revise = next((b for b in fn.branches if b.handle == "revise"), None)
        pass_ = next((b for b in fn.branches if b.handle == "pass"), None)
        if revise and revise.targets and critic_rounds[fn.id] == 0:
            return revise
        return pass_ if pass_ and pass_.targets else None
    preferred = {"approval": "approved", "guardrail": "pass"}.get(fn.type)
    if preferred:
        b = next((b for b in fn.branches if b.handle == preferred), None)
        return b if b and b.targets else None
    return connected[0] if connected else None
