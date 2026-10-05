from __future__ import annotations

import pytest

from configurator_engine import ai
from configurator_engine.ai import Draft, DraftEdge, DraftNode, DraftRoute, GeneratedCode
from configurator_engine.rules import resolve
from conftest import build

GOOD_TOOL = '''import json

from langchain_core.tools import tool


@tool
def lookup_sku(sku: str) -> str:
    """Look up a product by SKU."""
    return json.dumps({"sku": sku, "stock": 3})
'''


@pytest.fixture(autouse=True)
def no_key(monkeypatch):  # type: ignore[no-untyped-def]
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    monkeypatch.setattr(ai, "_ensure_sandbox_image", lambda: False)


def test_without_key_text_to_spec_uses_closest_blueprint() -> None:
    result = ai.text_to_spec("A customer support desk that handles refund tickets")
    assert result.source == "blueprint"
    assert result.spec.project.name == "support-bot"
    assert ai.closest_blueprint("something unrelated entirely") == "blank"


def test_draft_becomes_a_valid_laid_out_spec() -> None:
    draft = Draft(
        project_name="Trip Planner",
        summary="Plans trips.",
        nodes=[
            DraftNode(id="start", type="input", label="Chat", role="", instructions="", routes=[]),
            DraftNode(id="triage", type="router", label="Triage", role="", instructions="Pick one", routes=[
                DraftRoute(id="flights", label="Flights", description="Flight questions"),
                DraftRoute(id="hotels", label="Hotels", description="Hotel questions"),
            ]),
            DraftNode(id="Flight Agent", type="agent", label="Flights", role="Finds flights", instructions="You find flights.", routes=[]),
            DraftNode(id="hotel", type="agent", label="Hotels", role="Finds hotels", instructions="You find hotels.", routes=[]),
            DraftNode(id="search", type="web_search", label="Search", role="", instructions="", routes=[]),
            DraftNode(id="end", type="output", label="Reply", role="", instructions="", routes=[]),
        ],
        edges=[
            DraftEdge(source="start", target="triage", handle="out"),
            DraftEdge(source="triage", target="Flight Agent", handle="route:flights"),
            DraftEdge(source="triage", target="hotel", handle="route:hotels"),
            DraftEdge(source="Flight Agent", target="end", handle="out"),
            DraftEdge(source="hotel", target="end", handle="out"),
            DraftEdge(source="search", target="Flight Agent", handle="whatever"),
        ],
    )
    spec = ai._draft_to_spec(draft)
    assert spec.project.name == "trip-planner"
    res = resolve(spec)
    assert res.ok, res.errors
    agent = res.graph.nodes["flight_agent"]
    assert agent.tools == ["search"]
    xs = {n.id: n.position.x for n in spec.graph.nodes}
    assert xs["start"] < xs["triage"] < xs["flight_agent"] < xs["end"]


def test_static_check_catches_contract_breaks() -> None:
    assert ai.static_check(GOOD_TOOL, "lookup_sku", is_tool=True) == []
    assert ai.static_check("def other(): pass", "lookup_sku", is_tool=True)
    assert any("subprocess" in p for p in ai.static_check("import subprocess\n" + GOOD_TOOL, "lookup_sku", is_tool=True))
    assert any("@tool" in p for p in ai.static_check('def lookup_sku(sku: str) -> str:\n    """x"""\n    return sku\n', "lookup_sku", is_tool=True))


def _custom_tool_spec():  # type: ignore[no-untyped-def]
    return build(
        [("s", "input"), ("a", "agent"), {"id": "t", "type": "custom_tool", "data": {"tool_name": "lookup_sku", "inputs": [{"name": "sku"}]}}],
        [("s", "out", "a", "in"), ("t", "attach", "a", "tools")],
    )


def test_fill_gaps_without_key_leaves_stubs() -> None:
    spec, report = ai.fill_gaps(_custom_tool_spec())
    assert "ANTHROPIC_API_KEY" in report[0]
    assert resolve(spec).gaps


def test_router_retries_then_saves_code(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    answers = [
        GeneratedCode(code="def wrong(): pass", python_deps=[], env=[], notes=""),
        GeneratedCode(code=GOOD_TOOL, python_deps=[], env=["SKU_API_KEY", "bad name"], notes="Uses a stub."),
    ]
    prompts: list[str] = []

    def fake_call(system, user, schema, effort="medium", max_tokens=16000):  # type: ignore[no-untyped-def]
        prompts.append(user)
        return answers.pop(0)

    monkeypatch.setattr(ai, "_call_structured", fake_call)
    spec, result = ai.generate_code(_custom_tool_spec(), "t")
    assert result.ok and result.attempts == 2 and result.verified == "static"
    assert "Static check failed" in prompts[1]
    tool = next(n for n in spec.graph.nodes if n.id == "t")
    assert tool.data.code and tool.data.generated_by == "claude"
    assert tool.data.env == ["SKU_API_KEY"]
    assert not resolve(spec).gaps


def test_router_gives_up_after_three_attempts(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(ai, "_call_structured", lambda *a, **k: GeneratedCode(code="nope(", python_deps=[], env=[], notes=""))
    spec, result = ai.generate_code(_custom_tool_spec(), "t")
    assert not result.ok and result.verified == "failed" and result.attempts == 3
    assert resolve(spec).gaps
