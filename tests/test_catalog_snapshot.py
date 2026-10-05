from __future__ import annotations

import importlib.util

from conftest import ROOT


def test_web_catalog_snapshot_is_current() -> None:
    spec = importlib.util.spec_from_file_location("export_catalog", ROOT / "scripts/export_catalog.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    current = (ROOT / "apps/web/src/lib/catalog.json").read_text(encoding="utf-8")
    assert current == mod.build(), "Run: python scripts/export_catalog.py"
