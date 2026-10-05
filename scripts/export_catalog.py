"""Write apps/web/src/lib/catalog.json: node catalog plus starter blueprints.

The web canvas imports this snapshot so it loads instantly and still works for
editing when the API is offline. tests/test_catalog_snapshot.py fails if it drifts.
"""

from __future__ import annotations

import json
from pathlib import Path

from configurator_engine.catalogue import blueprint_index, load_blueprint
from configurator_spec.catalog import catalog

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "apps/web/src/lib/catalog.json"


def build() -> str:
    data = catalog()
    data["blueprints"] = [
        {**b, "spec": load_blueprint(b["id"]).model_dump(mode="json", by_alias=True)} for b in blueprint_index()
    ]
    return json.dumps(data, indent=1, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    TARGET.write_text(build(), encoding="utf-8")
    print(f"wrote {TARGET.relative_to(ROOT)}")
