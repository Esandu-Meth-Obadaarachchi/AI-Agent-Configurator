"""Render every combination in ci/matrix.yaml and verify each export.

Each export is linted, type-checked and tested with its own pinned dependencies
(via `configurator verify --local`). Exit code is non-zero if any export fails.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import yaml

from configurator_engine.generate import generate, write
from configurator_engine.verifier import verify
from configurator_spec import load_spec

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    matrix = yaml.safe_load((ROOT / "ci/matrix.yaml").read_text())
    only = set(sys.argv[1:])
    failed = []
    with tempfile.TemporaryDirectory() as tmp:
        for entry in matrix["combinations"]:
            name = entry["name"]
            if only and name not in only:
                continue
            spec = load_spec(ROOT / entry["spec"])
            for path, value in (entry.get("set") or {}).items():
                obj = spec
                *parents, last = path.split(".")
                for p in parents:
                    obj = getattr(obj, p)
                setattr(obj, last, value)
            out = Path(tmp) / name
            write(generate(spec), out)
            checks = verify(out, sandbox="local", frontend=entry.get("frontend", False), log=lambda m: None)
            ok = all(c.ok or c.skipped for c in checks)
            print(f"{'PASS' if ok else 'FAIL'}  {name}  ({', '.join(c.name.split(': ')[-1] for c in checks)})", flush=True)
            if not ok:
                failed.append(name)
                for c in checks:
                    if not c.ok and not c.skipped:
                        print(f"--- {c.name}\n{c.output}\n")
    print(f"\n{len(failed)} failed" if failed else "\nall combinations passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
