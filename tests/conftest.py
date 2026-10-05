from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from configurator_spec import Spec, load_spec, parse_spec

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples" / "specs"


def example_ids() -> list[str]:
    return [e["id"] for e in json.loads((EXAMPLES / "index.json").read_text())]


@pytest.fixture
def example() -> Any:
    def load(name: str) -> Spec:
        return load_spec(EXAMPLES / f"{name}.json")

    return load


def build(nodes: list[tuple[str, str]] | list[dict[str, Any]], edges: list[tuple[str, str, str, str]]) -> Spec:
    """Tiny graph builder for rule tests: nodes as (id, type), edges as (src, handle, dst, target_handle)."""
    node_list = [{"id": n[0], "type": n[1]} if isinstance(n, tuple) else n for n in nodes]
    edge_list = [
        {"id": f"{s}-{h}-{d}", "source": s, "target": d, "sourceHandle": h, "targetHandle": th} for s, h, d, th in edges
    ]
    return parse_spec({"project": {"name": "t"}, "graph": {"nodes": node_list, "edges": edge_list}})
