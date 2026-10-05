"""Facts about this app's graph, shared by the API and the UI."""

from __future__ import annotations

APP_TITLE = "Docs Qa"
GREETING = "Ask me anything about the docs."

# Display names for every block on the canvas, keyed by node id.
NODE_LABELS: dict[str, str] = {
    "assistant": "Docs assistant",
    "docs": "Company docs",
    "memory": "Memory",
}

# What kind of block each step is, so the UI can choose an icon.
NODE_KINDS: dict[str, str] = {
    "assistant": "agent",
}

# Steps whose replies the user sees as chat messages.
SPEAKING_NODES: frozenset[str] = frozenset(["assistant"])

FEATURES = {
    "approval": False,
    "knowledge": [{"id": "docs", "label": "Company docs"}],
    "long_term_memory": False,
    "feedback": True,
    "show_steps": True,
    "streaming": True,
}
