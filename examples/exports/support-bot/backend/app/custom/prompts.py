"""Prompt overrides. This file is yours: regeneration never overwrites it.

Map a node id to new instructions to replace what the canvas says, for example:

    OVERRIDES = {
        "assistant": "You are a concise assistant. Answer in two sentences or fewer.",
    }

Node ids are listed in app/meta.py.
"""

from __future__ import annotations

OVERRIDES: dict[str, str] = {}
