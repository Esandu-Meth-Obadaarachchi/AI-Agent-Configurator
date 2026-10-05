from __future__ import annotations

import io
import json
import zipfile

import pytest
from fastapi.testclient import TestClient

from configurator_api.main import app
from configurator_engine import ai
from conftest import EXAMPLES

client = TestClient(app)


@pytest.fixture(autouse=True)
def no_key(monkeypatch):  # type: ignore[no-untyped-def]
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def spec(name: str = "support-bot") -> dict:
    return json.loads((EXAMPLES / f"{name}.json").read_text())


def test_catalog_has_nodes_and_blueprints() -> None:
    data = client.get("/api/catalog").json()
    assert {c["id"] for c in data["categories"]} >= {"agents", "tools", "knowledge"}
    assert any(b["id"] == "support-bot" for b in data["blueprints"])
    assert data["defaults"]["agent"]["label"] == "Agent"


def test_validate_returns_issues_and_trace() -> None:
    data = client.post("/api/validate", json={"spec": spec()}).json()
    assert data["ok"] is True
    assert data["trace"][0]["nodes"] == ["start"]


def test_preview_returns_files_and_node_map() -> None:
    data = client.post("/api/preview", json={"spec": spec()}).json()
    paths = {f["path"] for f in data["files"]}
    assert "backend/app/graph.py" in paths
    assert "backend/app/nodes/router.py" in data["node_files"]["triage"]
    assert data["decisions"]


def test_preview_with_errors_has_no_files() -> None:
    broken = spec()
    broken["graph"]["edges"] = []
    data = client.post("/api/preview", json={"spec": broken}).json()
    assert data["ok"] is False and data["files"] == []


def test_schema_errors_are_readable() -> None:
    res = client.post("/api/validate", json={"spec": {"graph": {"nodes": [{"id": "Bad Id", "type": "agent"}]}}})
    assert res.status_code == 422
    assert res.json()["detail"]["problems"]


def test_export_zip() -> None:
    res = client.post("/api/export", json={"spec": spec("blank")})
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/zip"
    names = zipfile.ZipFile(io.BytesIO(res.content)).namelist()
    assert "my-agent/backend/app/main.py" in names


def test_import_upgrades_v01() -> None:
    v01 = {"spec_version": "0.1", "project": {"name": "old"}, "agents": {"pattern": "single", "tools": ["web_search"]}}
    data = client.post("/api/import", json=v01).json()
    assert data["spec_version"] == "0.2"


def test_layout_sets_positions() -> None:
    s = spec("research-team")
    for n in s["graph"]["nodes"]:
        n["position"] = {"x": 0, "y": 0}
    data = client.post("/api/layout", json={"spec": s}).json()
    assert len({(n["position"]["x"], n["position"]["y"]) for n in data["graph"]["nodes"]}) == len(s["graph"]["nodes"])


def test_ai_without_key_falls_back_or_explains() -> None:
    assert client.get("/api/ai/status").json()["available"] is False
    data = client.post("/api/ai/text-to-spec", json={"description": "SQL questions over our warehouse"}).json()
    assert data["source"] == "blueprint" and data["spec"]["project"]["name"] == "data-analyst"
    res = client.post("/api/ai/write-prompt", json={"kind": "agent", "label": "Helper"})
    assert res.status_code == 400


def test_ai_rate_limit(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import configurator_api.main as api

    monkeypatch.setattr(api, "AI_PER_MINUTE", 2)
    api._hits.clear()
    codes = [client.post("/api/ai/text-to-spec", json={"description": "a docs bot"}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
    api._hits.clear()


def test_request_key_is_scoped_to_the_request() -> None:
    assert client.get("/api/ai/status", headers={"X-Anthropic-Key": "sk-test"}).json()["available"] is True
    assert ai.available() is False
