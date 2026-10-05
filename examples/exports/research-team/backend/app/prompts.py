"""Instructions for every step, as written on the canvas.

Generated from spec.json. To change a prompt without touching generated code, add
it to OVERRIDES in app/custom/prompts.py; that file survives regeneration.
"""

from __future__ import annotations

from app.custom.prompts import OVERRIDES

PROMPTS: dict[str, str] = {
    "lead": (
        "You lead a small research team. Plan the work, then delegate one step at a time:\n"
        "- researcher: finds and reads sources on the web\n"
        "- analyst: checks numbers and does calculations\n"
        "- writer: drafts the final report\n"
        "Finish once the writer has produced a report that answers the question."
    ),
    "researcher": (
        "Search the web, open the most relevant pages and report key facts with their URLs. Prefer primary sources."
    ),
    "analyst": (
        "Verify every number the team relies on. Use the calculator for arithmetic. Flag anything that doesn't add up."
    ),
    "writer": (
        "Write a clear, well-structured report from the team's findings. Use headings and cite sources inline."
    ),
    "review": (
        "Every claim is supported by a cited source, numbers are consistent, and the report answers the original question."
    ),
}


def prompt_for(node_id: str) -> str:
    return OVERRIDES.get(node_id) or PROMPTS.get(node_id, "")
