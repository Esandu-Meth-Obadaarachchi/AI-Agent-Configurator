"""Module registry: every feature is a folder under modules/ (section 4.2).

Each module folder holds:
- manifest.yaml: id, deps, env vars, compose services and the files it renders
- templates/: Jinja2 files
- explain.md: plain-language what / why / trade-off, used by DECISIONS.md and the UI

Dependency versions are pinned in one place, modules/versions.yaml, so a library
bump is a one-line change and the nightly job can test the latest versions.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class EnvVar:
    name: str
    value: str = ""
    comment: str = ""
    secret: bool = False


@dataclass(frozen=True)
class FileSpec:
    src: str
    dest: str
    foreach: str | None = None  # name of a context collection; each item is exposed as `item`
    when: str | None = None  # Jinja expression; file is skipped when false


@dataclass
class Module:
    id: str
    title: str
    path: Path
    python_deps: list[str] = field(default_factory=list)
    dev_deps: list[str] = field(default_factory=list)
    node_deps: dict[str, str] = field(default_factory=dict)
    node_dev_deps: dict[str, str] = field(default_factory=dict)
    env: list[EnvVar] = field(default_factory=list)
    compose: dict[str, Any] = field(default_factory=dict)
    files: list[FileSpec] = field(default_factory=list)
    tree: bool = False  # render every file under templates/ to the same relative path
    explain: dict[str, str] = field(default_factory=dict)

    def template_files(self) -> list[FileSpec]:
        out = list(self.files)
        if self.tree:
            root = self.path / "templates"
            explicit = {f.src for f in self.files}
            for p in sorted(root.rglob("*")):
                if p.is_file() and p.name != ".DS_Store":
                    rel = p.relative_to(self.path).as_posix()
                    if rel in explicit:
                        continue
                    dest = p.relative_to(root).as_posix()
                    if dest.endswith(".j2"):
                        dest = dest[:-3]
                    dest = dest.replace("__dot__", ".")
                    out.append(FileSpec(src=rel, dest=dest))
        return out


def modules_dir() -> Path:
    env = os.environ.get("CONFIGURATOR_MODULES_DIR")
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "modules"
        if (candidate / "versions.yaml").exists():
            return candidate
    bundled = here.parent / "_modules"
    if bundled.exists():
        return bundled
    raise FileNotFoundError("Could not find the modules/ directory. Set CONFIGURATOR_MODULES_DIR.")


def _parse_explain(text: str) -> dict[str, str]:
    """Split explain.md into sections keyed by lower-case heading."""
    sections: dict[str, str] = {}
    current = "summary"
    buf: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            sections[current] = "\n".join(buf).strip()
            current = line[3:].strip().lower()
            buf = []
        elif line.startswith("# "):
            sections["title"] = line[2:].strip()
        else:
            buf.append(line)
    sections[current] = "\n".join(buf).strip()
    return {k: v for k, v in sections.items() if v}


def _load_module(path: Path) -> Module:
    raw = yaml.safe_load((path / "manifest.yaml").read_text(encoding="utf-8")) or {}
    explain_path = path / "explain.md"
    return Module(
        id=raw["id"],
        title=raw.get("title", raw["id"]),
        path=path,
        python_deps=list(raw.get("python_deps", [])),
        dev_deps=list(raw.get("dev_deps", [])),
        node_deps=dict(raw.get("node_deps", {})),
        node_dev_deps=dict(raw.get("node_dev_deps", {})),
        env=[EnvVar(**e) for e in raw.get("env", [])],
        compose=dict(raw.get("compose", {})),
        files=[FileSpec(**f) for f in raw.get("files", [])],
        tree=bool(raw.get("tree", False)),
        explain=_parse_explain(explain_path.read_text(encoding="utf-8")) if explain_path.exists() else {},
    )


@lru_cache(maxsize=4)
def load_registry(root: str | None = None) -> dict[str, Module]:
    base = Path(root) if root else modules_dir()
    mods: dict[str, Module] = {}
    for manifest in sorted(base.glob("*/manifest.yaml")):
        m = _load_module(manifest.parent)
        if m.id in mods:
            raise ValueError(f"duplicate module id {m.id}")
        mods[m.id] = m
    return mods


@lru_cache(maxsize=4)
def load_versions(root: str | None = None) -> dict[str, dict[str, str]]:
    base = Path(root) if root else modules_dir()
    data = yaml.safe_load((base / "versions.yaml").read_text(encoding="utf-8"))
    return {"python": dict(data.get("python", {})), "node": dict(data.get("node", {})), "images": dict(data.get("images", {}))}
