"""Multi-agent message handling: the conversation never ends on an assistant turn."""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage

from app.messages import for_node, text_of
from app.state import RESET, merge


def test_other_agents_become_labelled_notes() -> None:
    history = [HumanMessage(content="Hi"), AIMessage(content="Found it", name="someone_else")]
    seen = for_node(history, "me")
    assert isinstance(seen[-1], HumanMessage)
    assert "Found it" in text_of(seen[-1])


def test_own_replies_stay_assistant_and_get_a_nudge() -> None:
    history = [HumanMessage(content="Hi"), AIMessage(content="Hello", name="me")]
    seen = for_node(history, "me")
    assert isinstance(seen[1], AIMessage)
    assert isinstance(seen[-1], HumanMessage)


def test_text_of_skips_thinking_blocks() -> None:
    msg = AIMessage(content=[{"type": "thinking", "thinking": "hmm"}, {"type": "text", "text": "Answer"}])
    assert text_of(msg) == "Answer"


def test_state_merge_resets_each_turn() -> None:
    assert merge({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}
    assert merge({"a": 1}, {RESET: True}) == {}
