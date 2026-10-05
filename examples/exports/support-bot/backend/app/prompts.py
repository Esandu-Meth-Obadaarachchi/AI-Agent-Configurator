"""Instructions for every step, as written on the canvas.

Generated from spec.json. To change a prompt without touching generated code, add
it to OVERRIDES in app/custom/prompts.py; that file survives regeneration.
"""

from __future__ import annotations

from app.custom.prompts import OVERRIDES

PROMPTS: dict[str, str] = {
    "guard": "",
    "triage": "Pick the route that best matches the latest user message.",
    "billing": (
        "You handle billing questions. Look up the order before discussing it. Offer refunds only when the order qualifies, and explain why."
    ),
    "tech": (
        "You solve technical problems. Search the help centre first, then give numbered steps. Ask for the error message if you need it."
    ),
    "smalltalk": "Reply briefly and warmly, then ask how you can help with billing or a technical issue.",
    "approve": "A billing reply is ready. Approve it before it reaches the customer?",
}


def prompt_for(node_id: str) -> str:
    return OVERRIDES.get(node_id) or PROMPTS.get(node_id, "")
