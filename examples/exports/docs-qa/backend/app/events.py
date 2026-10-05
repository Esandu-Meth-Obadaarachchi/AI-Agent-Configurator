"""Progress events that steps send to the UI while a run is streaming."""

from __future__ import annotations

from typing import Any

from langgraph.config import get_stream_writer


def emit(kind: str, node: str, **data: Any) -> None:
    """Send a progress event. Does nothing outside a streaming run."""
    try:
        writer = get_stream_writer()
    except Exception:
        return
    writer({"kind": kind, "node": node, **data})


def step(node: str, status: str, detail: str = "") -> None:
    emit("step", node, status=status, detail=detail)
