"""HTTP API for support-bot.

POST /api/chat           start a turn, streams Server-Sent Events
POST /api/chat/resume    answer a pending approval, streams the rest of the run
GET  /api/threads/{id}   conversation history (and any pending approval)
POST /api/feedback       thumbs up / down on a reply
GET  /api/info           what this app can do, for the UI
GET  /api/health         liveness check
POST /api/knowledge/{id}/upload   add documents to a knowledge base
GET  /api/knowledge               knowledge bases and their sizes
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command
from pydantic import BaseModel, Field

from app.config import get_settings
from app.graph import build_graph
from app.messages import text_of
from app.meta import APP_TITLE, FEATURES, GREETING, NODE_KINDS, NODE_LABELS
from app.persistence import open_persistence
from app.state import new_turn
from app.streaming import stream_run
from app.tools import build_toolsets

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("support-bot")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    async with open_persistence() as (checkpointer, store):
        toolsets = await build_toolsets()
        app.state.graph = build_graph(toolsets, checkpointer=checkpointer, store=store)
        log.info("ready: provider=%s model=%s checkpointer=%s", settings.llm_provider, settings.llm_model, settings.checkpointer)
        yield


app = FastAPI(title=APP_TITLE, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=100_000)
    thread_id: str | None = None
    user_id: str = "default"


class ResumeRequest(BaseModel):
    thread_id: str
    approved: bool
    edited: str | None = None
    feedback: str | None = None
    user_id: str = "default"


class FeedbackRequest(BaseModel):
    thread_id: str
    message_id: str
    score: int = Field(ge=-1, le=1)
    comment: str | None = None


def _config(thread_id: str, user_id: str) -> dict[str, Any]:
    return {
        "configurable": {"thread_id": thread_id, "user_id": user_id},
        "recursion_limit": get_settings().recursion_limit,
    }


def _sse(gen: AsyncIterator[str]) -> StreamingResponse:
    return StreamingResponse(
        gen,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/info")
async def info() -> dict[str, Any]:
    settings = get_settings()
    return {
        "title": APP_TITLE,
        "greeting": GREETING,
        "nodes": {k: {"label": v, "kind": NODE_KINDS.get(k, "")} for k, v in NODE_LABELS.items()},
        "features": FEATURES,
        "demo": settings.llm_provider == "fake",
        "model": settings.llm_model,
    }


@app.post("/api/chat")
async def chat(body: ChatRequest, request: Request) -> StreamingResponse:
    thread_id = body.thread_id or uuid.uuid4().hex
    graph = request.app.state.graph
    return _sse(stream_run(graph, new_turn(body.message), _config(thread_id, body.user_id)))


@app.post("/api/chat/resume")
async def resume(body: ResumeRequest, request: Request) -> StreamingResponse:
    graph = request.app.state.graph
    config = _config(body.thread_id, body.user_id)
    snapshot = await graph.aget_state(config)
    if not snapshot.interrupts:
        raise HTTPException(status_code=409, detail="This conversation has no pending approval.")
    decision = {"approved": body.approved, "edited": body.edited, "feedback": body.feedback}
    return _sse(stream_run(graph, Command(resume=decision), config))


@app.get("/api/threads/{thread_id}")
async def thread(thread_id: str, request: Request) -> dict[str, Any]:
    graph = request.app.state.graph
    snapshot = await graph.aget_state(_config(thread_id, "default"))
    values = snapshot.values or {}
    messages = []
    for m in values.get("messages", []):
        text = text_of(m)
        if not text.strip():
            continue
        if isinstance(m, HumanMessage):
            role = "note" if m.name else "user"
        elif isinstance(m, AIMessage):
            role = "assistant"
        else:
            continue
        messages.append(
            {"id": m.id, "role": role, "node": m.name, "label": NODE_LABELS.get(m.name or "", ""), "content": text}
        )
    pending = [{"id": i.id, **(i.value or {})} for i in snapshot.interrupts]
    return {"thread_id": thread_id, "messages": messages, "pending": pending}


@app.post("/api/feedback")
async def feedback(body: FeedbackRequest) -> dict[str, str]:
    path = Path(get_settings().data_dir) / "feedback.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {**body.model_dump(), "at": datetime.now(UTC).isoformat()}
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
    return {"status": "saved"}


@app.get("/api/knowledge")
async def knowledge() -> list[dict[str, Any]]:
    from app.rag.registry import KNOWLEDGE_BASES, get_knowledge_base

    out = []
    for kb_id, cfg in KNOWLEDGE_BASES.items():
        kb = get_knowledge_base(kb_id)
        out.append({"id": kb_id, "label": cfg.label, "chunks": await kb.count()})
    return out


@app.post("/api/knowledge/{kb_id}/upload")
async def upload(kb_id: str, files: list[UploadFile] = File(...)) -> dict[str, Any]:  # noqa: B008
    from app.rag.ingest import SUPPORTED, ingest_bytes
    from app.rag.registry import KNOWLEDGE_BASES

    if kb_id not in KNOWLEDGE_BASES:
        raise HTTPException(status_code=404, detail=f"No knowledge base called '{kb_id}'.")
    added = 0
    for f in files:
        name = f.filename or "upload"
        if not name.lower().endswith(SUPPORTED):
            raise HTTPException(status_code=415, detail=f"{name}: supported types are {', '.join(SUPPORTED)}")
        added += await ingest_bytes(kb_id, name, await f.read())
    return {"knowledge_base": kb_id, "chunks_added": added}
