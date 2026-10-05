from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from configurator_cli.main import app

runner = CliRunner()


def test_templates_lists_blueprints() -> None:
    res = runner.invoke(app, ["templates"])
    assert res.exit_code == 0
    assert "support-bot" in res.output


def test_init_validate_generate(tmp_path: Path) -> None:
    spec = tmp_path / "spec.json"
    assert runner.invoke(app, ["init", "--from", "content-studio", "-y", "-o", str(spec)]).exit_code == 0
    assert json.loads(spec.read_text())["project"]["name"] == "content-studio"
    assert runner.invoke(app, ["validate", str(spec)]).exit_code == 0
    out = tmp_path / "out"
    res = runner.invoke(app, ["generate", str(spec), "-o", str(out)])
    assert res.exit_code == 0, res.output
    assert (out / "backend/app/graph.py").exists()
    assert runner.invoke(app, ["generate", str(spec), "-o", str(tmp_path / "p.zip")]).exit_code == 0
    assert (tmp_path / "p.zip").stat().st_size > 1000


def test_validate_reports_errors(tmp_path: Path) -> None:
    spec = tmp_path / "bad.json"
    spec.write_text(json.dumps({"project": {"name": "x"}, "graph": {"nodes": [{"id": "a", "type": "agent"}], "edges": []}}))
    res = runner.invoke(app, ["validate", str(spec)])
    assert res.exit_code == 1
    assert "Chat input" in res.output


def test_bad_json_is_explained(tmp_path: Path) -> None:
    spec = tmp_path / "broken.json"
    spec.write_text("{nope")
    assert runner.invoke(app, ["validate", str(spec)]).exit_code == 2


def test_explain_runs(tmp_path: Path) -> None:
    spec = tmp_path / "spec.json"
    runner.invoke(app, ["init", "--from", "support-bot", "-y", "-o", str(spec)])
    res = runner.invoke(app, ["explain", str(spec)])
    assert res.exit_code == 0
    assert "Dry run" in res.output and "Trade-off" in res.output
