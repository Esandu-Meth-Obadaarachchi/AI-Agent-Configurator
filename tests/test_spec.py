import pytest
from pydantic import ValidationError

from configurator_spec import SPEC_VERSION, dump_spec, json_schema, parse_spec
from configurator_spec.catalog import NODE_TYPES, catalog, node_defaults
from configurator_spec.migrate import MigrationError, upgrade

BRIEF_V01 = {
    "spec_version": "0.1",
    "project": {"name": "docs-qa", "description": "Q and A over company PDFs"},
    "llm": {"provider": "anthropic", "model": "claude-sonnet-5-5"},
    "rag": {
        "enabled": True,
        "ingestion": {"sources": ["pdf", "markdown"], "chunker": "recursive", "chunk_size": 800, "overlap": 100},
        "embedding": {"provider": "openai", "model": "text-embedding-3-small"},
        "vector_store": "pgvector",
        "retrieval": {"mode": "hybrid", "top_k": 8, "reranker": "none"},
    },
    "agents": {"pattern": "single", "tools": ["mcp_client", "web_search", "custom"]},
    "memory": {"short_term": True},
    "human_in_loop": {"approval_nodes": []},
    "ui": {"framework": "nextjs", "streaming": True},
    "deploy": {"target": "docker_compose"},
}


def minimal(nodes=None, edges=None):
    return {
        "spec_version": SPEC_VERSION,
        "project": {"name": "demo"},
        "graph": {"nodes": nodes or [], "edges": edges or []},
    }


def test_defaults_are_valid():
    spec = parse_spec({})
    assert spec.spec_version == SPEC_VERSION
    assert spec.llm.provider == "anthropic"


def test_node_data_is_typed_by_discriminator():
    spec = parse_spec(minimal([{"id": "a", "type": "router", "data": {"routes": [{"id": "x"}, {"id": "y"}]}}]))
    router = spec.graph.nodes[0]
    assert router.type == "router"
    assert [r.id for r in router.data.routes] == ["x", "y"]


def test_unknown_node_type_is_rejected():
    with pytest.raises(ValidationError):
        parse_spec(minimal([{"id": "a", "type": "teleporter"}]))


def test_bad_node_id_is_rejected():
    with pytest.raises(ValidationError):
        parse_spec(minimal([{"id": "Bad Id", "type": "agent"}]))


def test_edge_to_unknown_node_is_rejected():
    with pytest.raises(ValidationError, match="unknown node"):
        parse_spec(minimal([{"id": "a", "type": "agent"}], [{"id": "e", "source": "a", "target": "ghost"}]))


def test_duplicate_node_ids_are_rejected():
    with pytest.raises(ValidationError, match="duplicate"):
        parse_spec(minimal([{"id": "a", "type": "agent"}, {"id": "a", "type": "agent"}]))


def test_knowledge_overlap_must_be_smaller_than_chunk():
    with pytest.raises(ValidationError, match="overlap"):
        parse_spec(minimal([{"id": "k", "type": "knowledge", "data": {"chunk_size": 200, "overlap": 200}}]))


def test_duplicate_router_routes_are_rejected():
    with pytest.raises(ValidationError, match="unique"):
        parse_spec(minimal([{"id": "r", "type": "router", "data": {"routes": [{"id": "x"}, {"id": "x"}]}}]))


def test_edges_accept_react_flow_aliases():
    spec = parse_spec(
        minimal(
            [{"id": "a", "type": "agent"}, {"id": "t", "type": "calculator"}],
            [{"id": "e", "source": "t", "target": "a", "sourceHandle": "attach", "targetHandle": "tools"}],
        )
    )
    assert spec.graph.edges[0].target_handle == "tools"


def test_brief_v01_example_upgrades_to_graph():
    spec = parse_spec(BRIEF_V01)
    types = sorted(n.type for n in spec.graph.nodes)
    assert types == sorted(["input", "output", "agent", "mcp_server", "web_search", "custom_tool", "knowledge", "memory"])
    knowledge = next(n for n in spec.graph.nodes if n.type == "knowledge")
    assert knowledge.data.top_k == 8
    assert knowledge.data.vector_store == "pgvector"


def test_v01_orchestrator_with_approval_upgrades():
    raw = dict(BRIEF_V01, agents={"pattern": "orchestrator", "tools": []}, human_in_loop={"approval_nodes": ["x"]})
    spec = parse_spec(raw)
    assert {n.type for n in spec.graph.nodes} >= {"supervisor", "approval"}


def test_upgrade_does_not_mutate_input():
    raw = dict(BRIEF_V01)
    upgrade(raw)
    assert raw["spec_version"] == "0.1"


def test_unknown_version_fails_clearly():
    with pytest.raises(MigrationError):
        upgrade({"spec_version": "9.9"})


def test_dump_is_stable():
    spec = parse_spec(BRIEF_V01)
    assert dump_spec(spec) == dump_spec(parse_spec(__import__("json").loads(dump_spec(spec))))


def test_json_schema_exports():
    schema = json_schema()
    assert schema["title"] == "Agent Configurator spec"
    assert "graph" in schema["properties"]


def test_catalog_covers_every_node_type():
    types = {n["type"] for n in NODE_TYPES}
    assert set(node_defaults()) == types
    c = catalog()
    assert {cat["id"] for cat in c["categories"]} == {n["category"] for n in NODE_TYPES}
