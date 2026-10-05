"""The graph compiles and a full turn runs end to end with the offline demo model."""

from __future__ import annotations

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.graph import build_graph
from app.state import new_turn
from app.tools import build_toolsets


async def _graph():  # type: ignore[no-untyped-def]
    return build_graph(await build_toolsets(), checkpointer=InMemorySaver())


async def test_graph_has_every_step() -> None:
    graph = await _graph()
    names = set(graph.get_graph().nodes)
    for node_id in ["lead", "researcher", "analyst", "writer", "review"]:
        assert node_id in names


async def test_one_turn_reaches_a_reply() -> None:
    graph = await _graph()
    config = {"configurable": {"thread_id": "t1"}, "recursion_limit": 200}
    await graph.ainvoke(new_turn("Hello, can you help me?"), config)
    for _ in range(10):  # approve any pauses until the run finishes
        state = await graph.aget_state(config)
        if not state.interrupts:
            break
        await graph.ainvoke(Command(resume={"approved": True}), config)
    state = await graph.aget_state(config)
    assert not state.next, f"run did not finish: waiting on {state.next}"
    replies = [m for m in state.values["messages"] if isinstance(m, AIMessage)]
    assert replies, "expected at least one reply"
