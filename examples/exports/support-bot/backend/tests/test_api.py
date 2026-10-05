"""API smoke tests: the server boots, streams a turn and returns history."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.main import app


def _events(body: str) -> list[tuple[str, dict]]:
    out = []
    for block in body.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        if "event" in lines:
            out.append((lines["event"], json.loads(lines.get("data", "{}"))))
    return out


def test_health_and_info() -> None:
    with TestClient(app) as client:
        assert client.get("/api/health").json() == {"status": "ok"}
        info = client.get("/api/info").json()
        assert info["demo"] is True
        assert info["title"]


def test_chat_streams_a_turn() -> None:
    with TestClient(app) as client:
        res = client.post("/api/chat", json={"message": "Hello there", "thread_id": "api-test"})
        assert res.status_code == 200
        events = _events(res.text)
        kinds = [e for e, _ in events]
        assert "error" not in kinds, events
        assert "done" in kinds or "interrupt" in kinds
        # Approvals pause the run; approve until it finishes.
        for _ in range(10):
            if "interrupt" not in kinds:
                break
            res = client.post("/api/chat/resume", json={"thread_id": "api-test", "approved": True})
            kinds = [e for e, _ in _events(res.text)]
            assert "error" not in kinds
        history = client.get("/api/threads/api-test").json()
        assert history["messages"][0]["role"] == "user"


def test_feedback_is_saved() -> None:
    with TestClient(app) as client:
        res = client.post("/api/feedback", json={"thread_id": "t", "message_id": "m", "score": 1})
        assert res.json() == {"status": "saved"}
