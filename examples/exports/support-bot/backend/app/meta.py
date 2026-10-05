"""Facts about this app's graph, shared by the API and the UI."""

from __future__ import annotations

APP_TITLE = "Support Bot"
GREETING = "Hi! How can we help today?"

# Display names for every block on the canvas, keyed by node id.
NODE_LABELS: dict[str, str] = {
    "guard": "Screen message",
    "triage": "Triage",
    "billing": "Billing agent",
    "tech": "Technical agent",
    "smalltalk": "Friendly reply",
    "approve": "Approve refund",
    "orders": "Orders API",
    "helpdocs": "Help centre",
    "memory": "Memory",
}

# What kind of block each step is, so the UI can choose an icon.
NODE_KINDS: dict[str, str] = {
    "guard": "guardrail",
    "triage": "router",
    "billing": "agent",
    "tech": "agent",
    "smalltalk": "prompt",
    "approve": "approval",
}

# Steps whose replies the user sees as chat messages.
SPEAKING_NODES: frozenset[str] = frozenset(["guard", "billing", "tech", "smalltalk", "approve"])

FEATURES = {
    "approval": True,
    "knowledge": [{"id": "helpdocs", "label": "Help centre"}],
    "long_term_memory": False,
    "feedback": True,
    "show_steps": True,
    "streaming": True,
}
