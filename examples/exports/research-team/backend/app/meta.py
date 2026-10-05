"""Facts about this app's graph, shared by the API and the UI."""

from __future__ import annotations

APP_TITLE = "Research Team"
GREETING = "What should the team research?"

# Display names for every block on the canvas, keyed by node id.
NODE_LABELS: dict[str, str] = {
    "lead": "Research lead",
    "researcher": "Researcher",
    "analyst": "Analyst",
    "writer": "Writer",
    "review": "Fact check",
    "search": "Web search",
    "read": "Read web page",
    "calc": "Calculator",
}

# What kind of block each step is, so the UI can choose an icon.
NODE_KINDS: dict[str, str] = {
    "lead": "supervisor",
    "researcher": "agent",
    "analyst": "agent",
    "writer": "agent",
    "review": "critic",
}

# Steps whose replies the user sees as chat messages.
SPEAKING_NODES: frozenset[str] = frozenset(["lead", "researcher", "analyst", "writer"])

FEATURES = {
    "approval": False,
    "knowledge": [],
    "long_term_memory": False,
    "feedback": True,
    "show_steps": True,
    "streaming": True,
}
