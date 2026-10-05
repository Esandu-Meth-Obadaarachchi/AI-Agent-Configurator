from __future__ import annotations

import pytest

from configurator_engine.compiler import compile_graph, find_cycles, simulate
from configurator_engine.rules import resolve
from conftest import build, example_ids


def codes(spec):  # type: ignore[no-untyped-def]
    return {i.code for i in resolve(spec).issues}


@pytest.mark.parametrize("name", example_ids())
def test_every_blueprint_is_valid(example, name) -> None:  # type: ignore[no-untyped-def]
    res = resolve(example(name))
    assert res.ok, [i.message for i in res.errors]


def test_empty_canvas_is_an_error() -> None:
    assert "graph.empty" in codes(build([], []))


def test_missing_input_and_unconnected_input() -> None:
    assert "graph.no_input" in codes(build([("a", "agent")], []))
    assert "graph.input_unconnected" in codes(build([("s", "input"), ("a", "agent")], []))


def test_supervisor_needs_workers() -> None:
    spec = build([("s", "input"), ("boss", "supervisor")], [("s", "out", "boss", "in")])
    assert "supervisor.no_workers" in codes(spec)


def test_tool_must_attach_to_agent() -> None:
    spec = build(
        [("s", "input"), ("p", "prompt"), ("calc", "calculator")],
        [("s", "out", "p", "in"), ("calc", "attach", "p", "tools")],
    )
    assert "edge.tool_target" in codes(spec)


def test_unattached_tool_is_a_warning() -> None:
    spec = build([("s", "input"), ("a", "agent"), ("calc", "calculator")], [("s", "out", "a", "in")])
    res = resolve(spec)
    assert any(i.code == "resource.unattached" and i.level == "warning" for i in res.issues)
    assert res.ok


def test_loop_without_exit_is_blocked() -> None:
    spec = build(
        [("s", "input"), ("a", "agent"), ("b", "agent")],
        [("s", "out", "a", "in"), ("a", "out", "b", "in"), ("b", "out", "a", "in")],
    )
    assert "graph.infinite_loop" in codes(spec)


def test_review_loop_is_a_valid_cycle() -> None:
    spec = build(
        [("s", "input"), ("w", "agent"), ("c", "critic"), ("r", "output")],
        [("s", "out", "w", "in"), ("w", "out", "c", "in"), ("c", "revise", "w", "in"), ("c", "pass", "r", "in")],
    )
    res = resolve(spec)
    assert res.ok
    assert find_cycles(res.graph) == [["c", "w"]]


def test_retriever_without_knowledge() -> None:
    spec = build([("s", "input"), ("ret", "retriever")], [("s", "out", "ret", "in")])
    assert "retriever.no_knowledge" in codes(spec)


def test_typescript_backend_blocked() -> None:
    spec = build([("s", "input"), ("a", "agent")], [("s", "out", "a", "in")])
    spec.backend.language = "typescript"
    assert "backend.typescript" in codes(spec)


def test_custom_tool_without_code_is_a_gap() -> None:
    spec = build(
        [("s", "input"), ("a", "agent"), ("t", "custom_tool")],
        [("s", "out", "a", "in"), ("t", "attach", "a", "tools")],
    )
    res = resolve(spec)
    assert [g.node_id for g in res.gaps] == ["t"]


def test_modules_follow_the_graph(example) -> None:  # type: ignore[no-untyped-def]
    mods = resolve(example("support-bot")).modules
    for m in ["core", "provider.anthropic", "node.router", "node.approval", "tool.http_api", "rag.core", "vector_store.pgvector", "memory.postgres"]:
        assert m in mods
    assert "node.supervisor" not in mods


def test_trace_goes_round_the_review_loop_once(example) -> None:  # type: ignore[no-untyped-def]
    steps = simulate(compile_graph(example("content-studio")))
    visited = [n for s in steps for n in s["nodes"]]
    assert visited.count("writer") == 2
    assert visited[-1] == "reply"
    assert all(e for s in steps for e in s["edges"])


def test_trace_visits_each_supervisor_worker(example) -> None:  # type: ignore[no-untyped-def]
    steps = simulate(compile_graph(example("research-team")))
    visited = [n for s in steps for n in s["nodes"]]
    for worker in ["researcher", "analyst", "writer"]:
        assert worker in visited
