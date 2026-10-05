from __future__ import annotations

from langgraph.store.memory import InMemoryStore

from app.tools.memory_tools import make_memory_tools, set_store


async def test_remember_then_recall_per_user() -> None:
    set_store(InMemoryStore())
    remember, recall = make_memory_tools()
    alice = {"configurable": {"user_id": "alice"}}
    await remember.ainvoke({"fact": "Prefers replies in French"}, alice)
    assert "French" in await recall.ainvoke({"query": "which language?"}, alice)
    assert await recall.ainvoke({"query": "language"}, {"configurable": {"user_id": "bob"}}) == "Nothing saved yet."
