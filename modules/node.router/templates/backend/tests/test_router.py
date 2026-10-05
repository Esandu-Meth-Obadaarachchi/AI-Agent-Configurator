from __future__ import annotations

from app.nodes.router import pick_by_keywords

ROUTES = [
    {"id": "billing", "keywords": ["refund", "invoice"]},
    {"id": "technical", "keywords": ["error", "crash"]},
    {"id": "other", "keywords": []},
]


def test_first_matching_keyword_wins() -> None:
    assert pick_by_keywords("I want a REFUND please", ROUTES) == "billing"
    assert pick_by_keywords("the app shows an error", ROUTES) == "technical"


def test_falls_back_to_last_branch() -> None:
    assert pick_by_keywords("hello", ROUTES) == "other"
