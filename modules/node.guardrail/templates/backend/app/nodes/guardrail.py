"""Guardrail step: deterministic screening, no model call.

Checks the latest message (from the user, or a reply if the guardrail sits after an
agent): length, blocked terms and common prompt-injection phrases. Personal data
(emails, phone numbers, card numbers) is redacted in place.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from app.events import step
from app.messages import text_of
from app.nodes import SyncNode
from app.state import AppState

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
CARD = re.compile(r"\b(?:\d[ -]?){13,19}\b")
PHONE = re.compile(r"(?<!\w)(?:\+?\d{1,3}[ .-]?)?(?:\(?\d{2,4}\)?[ .-]?)?\d{3,4}[ .-]?\d{3,4}(?!\w)")
INJECTION = [
    r"ignore (all |any )?(the )?(previous|prior|above) (instructions|prompts?)",
    r"disregard (all |the )?(previous|prior|above)",
    r"you are now (in )?(developer|dan|jailbreak)",
    r"reveal (your|the) (system )?prompt",
    r"pretend (you have|there are) no (rules|restrictions)",
]
INJECTION_RE = re.compile("|".join(INJECTION), re.IGNORECASE)


def redact(text: str) -> str:
    text = EMAIL.sub("[email]", text)
    text = CARD.sub("[card]", text)
    return PHONE.sub(lambda m: "[phone]" if sum(c.isdigit() for c in m.group()) >= 9 else m.group(), text)


def check(text: str, *, block_prompt_injection: bool, max_input_chars: int, blocked_terms: list[str]) -> str | None:
    """Return the reason to block, or None to let the message through."""
    if len(text) > max_input_chars:
        return f"message longer than {max_input_chars} characters"
    lowered = text.lower()
    for term in blocked_terms:
        if term.strip() and term.lower() in lowered:
            return f"blocked term '{term}'"
    if block_prompt_injection and INJECTION_RE.search(text):
        return "possible prompt injection"
    return None


def make_guardrail_node(
    *,
    node_id: str,
    label: str,
    redact_pii: bool = True,
    block_prompt_injection: bool = True,
    max_input_chars: int = 8000,
    blocked_terms: list[str] | None = None,
    blocked_message: str = "Sorry, I can't help with that request.",
) -> SyncNode:
    terms = blocked_terms or []

    def run(state: AppState) -> dict[str, Any]:
        messages: Sequence[BaseMessage] = state["messages"]
        target = next((m for m in reversed(messages) if isinstance(m, HumanMessage | AIMessage) and not (isinstance(m, HumanMessage) and m.name)), None)
        if target is None:
            return {"decisions": {node_id: "pass"}}
        text = text_of(target)
        reason = check(text, block_prompt_injection=block_prompt_injection, max_input_chars=max_input_chars, blocked_terms=terms)
        if reason:
            step(node_id, "end", f"Blocked: {reason}")
            return {"decisions": {node_id: "blocked"}, "messages": [AIMessage(content=blocked_message, name=node_id)]}
        update: dict[str, Any] = {"decisions": {node_id: "pass"}}
        if redact_pii:
            cleaned = redact(text)
            if cleaned != text:
                replacement = type(target)(content=cleaned, id=target.id, name=target.name)
                update["messages"] = [replacement]
                step(node_id, "end", "Passed (personal data redacted)")
                return update
        step(node_id, "end", "Passed")
        return update

    run.__name__ = node_id
    return run
