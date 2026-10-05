"""Starter blueprints shipped with the configurator."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from configurator_spec import Spec, load_spec


def blueprints_dir() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "examples" / "specs"
        if (candidate / "index.json").exists():
            return candidate
    bundled = here.parent / "_examples"
    if (bundled / "index.json").exists():
        return bundled
    raise FileNotFoundError("blueprints not found")


@lru_cache
def blueprint_index() -> list[dict[str, Any]]:
    return list(json.loads((blueprints_dir() / "index.json").read_text(encoding="utf-8")))


def load_blueprint(blueprint_id: str) -> Spec:
    entry = next((b for b in blueprint_index() if b["id"] == blueprint_id), None)
    if entry is None:
        raise KeyError(blueprint_id)
    return load_spec(blueprints_dir() / entry["file"])
