"""Where conversation state lives between messages (the LangGraph checkpointer).

Approvals pause a run and resume it later, so the checkpointer is what makes them
work. CHECKPOINTER=memory keeps everything in RAM (lost on restart).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver

from app.config import get_settings


@asynccontextmanager
async def open_persistence() -> AsyncIterator[tuple[Any, Any]]:
    """Yield (checkpointer, store) for the app's lifetime."""
    settings = get_settings()
    kind = settings.checkpointer
    if kind == "postgres":
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        async with AsyncPostgresSaver.from_conn_string(settings.database_url) as saver:
            await saver.setup()
            yield saver, None
        return
    if kind not in {"memory", "postgres", "sqlite"}:
        raise ValueError(f"Unknown CHECKPOINTER '{kind}'. Use memory, sqlite or postgres.")
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    yield InMemorySaver(), None
