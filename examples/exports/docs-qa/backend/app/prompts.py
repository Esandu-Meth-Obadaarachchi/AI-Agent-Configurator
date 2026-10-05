"""Instructions for every step, as written on the canvas.

Generated from spec.json. To change a prompt without touching generated code, add
it to OVERRIDES in app/custom/prompts.py; that file survives regeneration.
"""

from __future__ import annotations

from app.custom.prompts import OVERRIDES

PROMPTS: dict[str, str] = {
    "assistant": (
        "You answer questions about the company's documents.\n"
        "Always search the knowledge base before answering. Quote the source file for every claim.\n"
        "If the documents don't contain the answer, say so plainly instead of guessing."
    ),
}


def prompt_for(node_id: str) -> str:
    return OVERRIDES.get(node_id) or PROMPTS.get(node_id, "")
