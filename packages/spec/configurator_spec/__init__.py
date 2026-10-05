"""Agent Configurator spec: Pydantic schema, node catalog and migrations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .migrate import MigrationError, upgrade
from .models import (
    FLOW_TYPES,
    RESOURCE_TYPES,
    SPEC_VERSION,
    TOOL_TYPES,
    Edge,
    Graph,
    Node,
    Spec,
)

__all__ = [
    "FLOW_TYPES",
    "RESOURCE_TYPES",
    "SPEC_VERSION",
    "TOOL_TYPES",
    "Edge",
    "Graph",
    "MigrationError",
    "Node",
    "Spec",
    "dump_spec",
    "json_schema",
    "load_spec",
    "parse_spec",
]


def parse_spec(raw: dict[str, Any]) -> Spec:
    """Validate a spec dict of any supported version and return the current model."""
    return Spec.model_validate(upgrade(raw))


def load_spec(path: str | Path) -> Spec:
    return parse_spec(json.loads(Path(path).read_text(encoding="utf-8")))


def dump_spec(spec: Spec) -> str:
    """Stable JSON: the same spec always serialises to the same bytes."""
    return json.dumps(spec.model_dump(mode="json", by_alias=True), indent=2, ensure_ascii=False) + "\n"


def json_schema() -> dict[str, Any]:
    schema = Spec.model_json_schema(by_alias=True)
    schema["$id"] = f"https://agent-configurator.dev/schema/spec-{SPEC_VERSION}.json"
    schema["title"] = "Agent Configurator spec"
    return schema
