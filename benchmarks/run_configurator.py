"""Time generate + verify for each reference app (the configurator side of the benchmark)."""

from __future__ import annotations

import csv
import tempfile
import time
from pathlib import Path

from configurator_engine.generate import generate, write
from configurator_engine.verifier import verify
from configurator_spec import load_spec

ROOT = Path(__file__).resolve().parents[1]
APPS = ["docs-qa", "support-bot", "research-team"]


def main() -> None:
    rows = []
    for app in APPS:
        with tempfile.TemporaryDirectory() as tmp:
            start = time.monotonic()
            out = generate(load_spec(ROOT / "examples/specs" / f"{app}.json"))
            write(out, tmp)
            generated = time.monotonic() - start
            checks = verify(tmp, sandbox="local", frontend=False)
            total = time.monotonic() - start
            passed = all(c.ok or c.skipped for c in checks)
        rows.append({"app": app, "method": "configurator", "generate_s": round(generated, 2), "total_s": round(total, 1), "tokens": 0, "cost_usd": 0, "pass": passed})
        print(rows[-1])
    with (ROOT / "benchmarks/results.csv").open("a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        if fh.tell() == 0:
            writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
