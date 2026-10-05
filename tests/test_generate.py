from __future__ import annotations

import ast
import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest

from configurator_engine.codeparts import split_imports
from configurator_engine.generate import GenerationError, generate, to_zip, write
from conftest import ROOT, build, example_ids

GOLDEN = ROOT / "tests" / "golden"


def digest(files: dict[str, str]) -> dict[str, str]:
    return {path: hashlib.sha256(content.encode()).hexdigest()[:16] for path, content in sorted(files.items())}


@pytest.mark.parametrize("name", example_ids())
def test_matches_golden_files(example, name) -> None:  # type: ignore[no-untyped-def]
    """A fixed spec must render byte-identical output. Run scripts/update_golden.py after intended changes."""
    expected = json.loads((GOLDEN / f"{name}.json").read_text())
    assert digest(generate(example(name)).files) == expected


@pytest.mark.parametrize("name", example_ids())
def test_python_files_parse(example, name) -> None:  # type: ignore[no-untyped-def]
    for path, content in generate(example(name)).files.items():
        if path.endswith(".py"):
            ast.parse(content, filename=path)


def test_rendering_is_deterministic(example) -> None:  # type: ignore[no-untyped-def]
    spec = example("research-team")
    assert generate(spec).files == generate(spec).files
    assert to_zip(generate(spec)) == to_zip(generate(spec))


def test_errors_block_generation() -> None:
    with pytest.raises(GenerationError):
        generate(build([], []))


def test_export_layout(example) -> None:  # type: ignore[no-untyped-def]
    files = generate(example("docs-qa")).files
    for path in [
        "backend/app/main.py",
        "backend/app/graph.py",
        "backend/app/custom/tools.py",
        "backend/app/custom/nodes.py",
        "backend/app/custom/prompts.py",
        "backend/pyproject.toml",
        "backend/Dockerfile",
        "docker-compose.yml",
        ".env.example",
        "spec.json",
        "PROMPT_PACK.md",
        "DECISIONS.md",
        "README.md",
    ]:
        assert path in files, path
    assert "pgvector/pgvector" in files["docker-compose.yml"]
    assert "ANTHROPIC_API_KEY=" in files[".env.example"]
    assert "langgraph==" in files["backend/requirements.txt"]


def test_no_secrets_in_output(example) -> None:  # type: ignore[no-untyped-def]
    for name in example_ids():
        env = generate(example(name)).files[".env.example"]
        for line in env.splitlines():
            if line.endswith("_API_KEY=") or line.startswith("#") or not line:
                continue
            assert "sk-" not in line


def test_custom_tool_code_is_stitched_with_hoisted_imports() -> None:
    code = 'import json\nfrom langchain_core.tools import tool\n\n@tool\ndef lookup(sku: str) -> str:\n    """Find a SKU."""\n    return json.dumps({"sku": sku})\n'
    spec = build(
        [
            ("s", "input"),
            ("a", "agent"),
            {"id": "t", "type": "custom_tool", "data": {"tool_name": "lookup", "inputs": [{"name": "sku"}], "code": code}},
        ],
        [("s", "out", "a", "in"), ("t", "attach", "a", "tools")],
    )
    out = generate(spec).files["backend/app/custom/tools.py"]
    tree = ast.parse(out)
    assert out.index("import json") < out.index("def lookup")
    assert sum(1 for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "lookup") == 1


def test_split_imports() -> None:
    imports, body = split_imports("from __future__ import annotations\nimport os\nx = os.sep\n")
    assert imports == ["import os"]
    assert body == "x = os.sep"


def test_write_preserves_custom_files(tmp_path: Path, example) -> None:  # type: ignore[no-untyped-def]
    out = generate(example("blank"))
    write(out, tmp_path)
    mine = tmp_path / "backend/app/custom/prompts.py"
    mine.write_text("OVERRIDES = {'assistant': 'mine'}\n")
    skipped = write(out, tmp_path)
    assert "backend/app/custom/prompts.py" in skipped
    assert mine.read_text().startswith("OVERRIDES = {'assistant'")


def test_zip_contains_project_folder(example) -> None:  # type: ignore[no-untyped-def]
    data = to_zip(generate(example("blank")))
    names = zipfile.ZipFile(io.BytesIO(data)).namelist()
    assert all(n.startswith("my-agent/") for n in names)


def test_node_files_map_points_at_real_files(example) -> None:  # type: ignore[no-untyped-def]
    out = generate(example("support-bot"))
    assert "backend/app/nodes/router.py" in out.node_files["triage"]
    assert "backend/app/tools/http_orders.py" in out.node_files["orders"]
    for paths in out.node_files.values():
        assert all(p in out.files for p in paths)
