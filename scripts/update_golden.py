"""Rewrite tests/golden/*.json after an intended template change.

Golden files hold a short hash per rendered file, so a diff shows exactly which
files changed without committing whole exported projects.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from configurator_engine.generate import generate
from configurator_spec import load_spec

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    golden = ROOT / "tests" / "golden"
    golden.mkdir(parents=True, exist_ok=True)
    for entry in json.loads((ROOT / "examples/specs/index.json").read_text()):
        files = generate(load_spec(ROOT / "examples/specs" / entry["file"])).files
        digest = {p: hashlib.sha256(c.encode()).hexdigest()[:16] for p, c in sorted(files.items())}
        (golden / f"{entry['id']}.json").write_text(json.dumps(digest, indent=2) + "\n")
        print(f"{entry['id']}: {len(digest)} files")


if __name__ == "__main__":
    main()
