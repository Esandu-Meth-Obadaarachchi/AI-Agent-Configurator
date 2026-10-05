"""Deterministic left-to-right layout for graphs that arrive without positions.

Flow steps go in columns by distance from the Chat input (back edges such as review
loops are ignored). Resources sit in a row under the first step they attach to.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from configurator_spec import FLOW_TYPES

COL = 300
ROW = 190
RES_GAP = 210
RES_DROP = 260


def auto_layout(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> None:
    """Set node["position"] in place."""
    types = {n["id"]: n["type"] for n in nodes}
    flow_ids = [n["id"] for n in nodes if n["type"] in FLOW_TYPES]
    out: dict[str, list[str]] = defaultdict(list)
    attach: dict[str, list[str]] = defaultdict(list)
    workers: dict[str, list[str]] = defaultdict(list)
    done: list[tuple[str, str]] = []
    for e in edges:
        s, t = e["source"], e["target"]
        if s not in types or t not in types:
            continue
        handle = e.get("sourceHandle") or e.get("source_handle")
        if types[s] in FLOW_TYPES and types[t] in FLOW_TYPES:
            out[s].append(t)
            if handle == "delegate":
                workers[s].append(t)
            elif handle == "done":
                done.append((s, t))
        elif types[s] not in FLOW_TYPES:
            attach[t].append(s)
    # A supervisor's "done" step comes after its workers, so lay it out to their right.
    for sup, target in done:
        for w in workers[sup]:
            out[w].append(target)

    start = next((i for i in flow_ids if types[i] == "input"), flow_ids[0] if flow_ids else None)
    depth: dict[str, int] = {}
    if start:
        # DFS from the input; an edge to a node still on the stack is a back edge (a loop).
        forward: dict[str, list[str]] = defaultdict(list)
        postorder: list[str] = []
        on_stack: set[str] = set()
        seen: set[str] = set()

        def visit(v: str) -> None:
            seen.add(v)
            on_stack.add(v)
            for w in out[v]:
                if w in on_stack:
                    continue
                forward[v].append(w)
                if w not in seen:
                    visit(w)
            on_stack.discard(v)
            postorder.append(v)

        visit(start)
        for v in reversed(postorder):  # topological order of the forward edges
            depth.setdefault(v, 0)
            for w in forward[v]:
                depth[w] = max(depth.get(w, 0), depth[v] + 1)
    max_depth = max(depth.values(), default=0)
    for i in flow_ids:
        if i not in depth:
            max_depth += 1
            depth[i] = max_depth
    # Outputs go in the last column.
    last = max(depth.values(), default=0)
    for i in flow_ids:
        if types[i] == "output":
            depth[i] = max(depth[i], last)

    columns: dict[int, list[str]] = defaultdict(list)
    for i in flow_ids:
        columns[depth[i]].append(i)
    pos: dict[str, tuple[float, float]] = {}
    for d, ids in columns.items():
        top = -(len(ids) - 1) * ROW / 2
        for k, i in enumerate(ids):
            pos[i] = (d * COL, top + k * ROW)

    # Resources: one row under the flow, each near the first step it serves, never overlapping.
    band = max((y for y in (p[1] for p in pos.values())), default=0) + RES_DROP
    wanted: list[tuple[float, str]] = []
    placed: set[str] = set()
    for flow_id in sorted(flow_ids, key=lambda i: pos[i]):
        for r in attach.get(flow_id, []):
            if r not in placed:
                placed.add(r)
                wanted.append((pos[flow_id][0], r))
    wanted += [(0.0, n["id"]) for n in nodes if n["id"] not in pos and n["id"] not in placed]
    wanted.sort(key=lambda w: w[0])
    last_x = float("-inf")
    for x, r in wanted:
        x = max(x, last_x + RES_GAP)
        pos[r] = (x, band)
        last_x = x

    for n in nodes:
        x, y = pos[n["id"]]
        n["position"] = {"x": round(x), "y": round(y)}
