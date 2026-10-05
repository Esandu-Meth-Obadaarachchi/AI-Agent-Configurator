"""Test settings: offline demo model, in-memory state, no external services."""

from __future__ import annotations

import os

os.environ["LLM_PROVIDER"] = "fake"
os.environ["CHECKPOINTER"] = "memory"
os.environ["DATA_DIR"] = os.environ.get("PYTEST_DATA_DIR", "/tmp/research-team-test-data")
