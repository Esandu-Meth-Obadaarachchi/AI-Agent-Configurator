"""HTTP API behind the web canvas (and the hosted version).

Everything here is deterministic except /api/ai/*, which calls Claude. Specs and
uploads are treated as untrusted input: size-limited, schema-validated, never
executed. AI endpoints are rate limited per client and share a daily cost cap.
Keys sent in the X-Anthropic-Key header are used for that request only.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import defaultdict, deque
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field, ValidationError

from configurator_engine import ai
from configurator_engine.catalogue import blueprint_index, load_blueprint
from configurator_engine.compiler import simulate
from configurator_engine.generate import generate, to_zip
from configurator_engine.layout import auto_layout
from configurator_engine.registry import load_registry
from configurator_engine.rules import resolve
from configurator_spec import MigrationError, Spec, json_schema, parse_spec
from configurator_spec.catalog import catalog

log = logging.getLogger("configurator.api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

MAX_SPEC_BYTES = 1_000_000
AI_PER_MINUTE = int(os.environ.get("CONFIGURATOR_AI_PER_MINUTE", "10"))
DAILY_COST_CAP = float(os.environ.get("CONFIGURATOR_DAILY_COST_CAP_USD", "10"))

app = FastAPI(title="Agent Configurator API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CONFIGURATOR_CORS", "http://localhost:3000,http://127.0.0.1:3000").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


# ------------------------------------------------------------------ helpers

_hits: dict[str, deque[float]] = defaultdict(deque)
_cost_day_date = datetime.now(UTC).date()
_cost_day_start = 0.0


def _client_id(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    return (fwd.split(",")[0].strip() if fwd else None) or (request.client.host if request.client else "unknown")


def _guard_ai(request: Request) -> None:
    now = time.monotonic()
    q = _hits[_client_id(request)]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= AI_PER_MINUTE:
        raise HTTPException(429, "Too many AI requests. Wait a minute and try again.")
    q.append(now)
    global _cost_day_date, _cost_day_start
    today = datetime.now(UTC).date()
    if _cost_day_date != today:
        _cost_day_date, _cost_day_start = today, ai.USAGE.cost_usd
    if not request.headers.get("x-anthropic-key") and ai.USAGE.cost_usd - _cost_day_start >= DAILY_COST_CAP:
        raise HTTPException(429, "Today's shared AI budget is used up. Add your own Anthropic key in Settings to continue.")


def _spec_from(raw: Any) -> Spec:
    if not isinstance(raw, dict):
        raise HTTPException(422, "Expected a spec object.")
    try:
        return parse_spec(raw)
    except MigrationError as exc:
        raise HTTPException(422, str(exc)) from exc
    except ValidationError as exc:
        problems = [
            {"path": ".".join(str(p) for p in e["loc"]), "message": e["msg"]} for e in exc.errors(include_url=False)[:20]
        ]
        raise HTTPException(422, {"message": "The spec doesn't match the schema.", "problems": problems}) from exc


async def _spec_body(request: Request) -> Spec:
    body = await request.body()
    if len(body) > MAX_SPEC_BYTES:
        raise HTTPException(413, "Spec is larger than 1 MB.")
    import json

    try:
        raw = json.loads(body or b"{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(400, f"Invalid JSON: {exc}") from exc
    return _spec_from(raw.get("spec", raw) if isinstance(raw, dict) else raw)


def _analysis(spec: Spec) -> dict[str, Any]:
    res = resolve(spec)
    return {
        "ok": res.ok,
        "issues": [i.as_dict() for i in res.issues],
        "modules": res.modules,
        "gaps": [{"node_id": g.node_id, "kind": g.kind} for g in res.gaps],
        "trace": simulate(res.graph),
    }


# ------------------------------------------------------------------ routes


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/catalog")
def get_catalog() -> dict[str, Any]:
    data = catalog()
    data["blueprints"] = blueprint_index()
    data["schema_version"] = Spec().spec_version
    return data


@app.get("/api/schema")
def get_schema() -> dict[str, Any]:
    return json_schema()


@app.get("/api/blueprints")
def blueprints() -> list[dict[str, Any]]:
    return blueprint_index()


@app.get("/api/blueprints/{blueprint_id}")
def blueprint(blueprint_id: str) -> dict[str, Any]:
    try:
        return load_blueprint(blueprint_id).model_dump(mode="json", by_alias=True)
    except KeyError:
        raise HTTPException(404, f"No blueprint called '{blueprint_id}'.") from None


@app.post("/api/import")
async def import_spec(request: Request) -> dict[str, Any]:
    """Accept any supported spec version and return it upgraded to the current one."""
    return (await _spec_body(request)).model_dump(mode="json", by_alias=True)


@app.post("/api/validate")
async def validate(request: Request) -> dict[str, Any]:
    return _analysis(await _spec_body(request))


@app.post("/api/preview")
async def preview(request: Request) -> dict[str, Any]:
    spec = await _spec_body(request)
    result = _analysis(spec)
    files: list[dict[str, Any]] = []
    node_files: dict[str, list[str]] = {}
    if result["ok"]:
        out = await asyncio.to_thread(generate, spec)
        files = [
            {"path": p, "content": c, "module": out.owners.get(p, ["", ""])[0], "size": len(c.encode())}
            for p, c in out.files.items()
        ]
        node_files = out.node_files
    registry = load_registry()
    decisions = [
        {"module": m, "title": registry[m].title, **registry[m].explain} for m in result["modules"] if m in registry and registry[m].explain
    ]
    return {**result, "files": files, "node_files": node_files, "decisions": decisions}


@app.post("/api/export")
async def export(request: Request) -> Response:
    spec = await _spec_body(request)
    res = resolve(spec)
    if not res.ok:
        return JSONResponse(status_code=422, content={"message": "Fix the errors first.", "issues": [i.as_dict() for i in res.errors]})
    out = await asyncio.to_thread(generate, spec)
    data = to_zip(out)
    log.info("export project=%s files=%d bytes=%d", spec.project.name, len(out.files), len(data))
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{spec.project.name}.zip"'},
    )


@app.post("/api/layout")
async def layout(request: Request) -> dict[str, Any]:
    spec = await _spec_body(request)
    raw = spec.model_dump(mode="json", by_alias=True)
    auto_layout(raw["graph"]["nodes"], raw["graph"]["edges"])
    return raw


# ------------------------------------------------------------------ AI


@app.get("/api/ai/status")
def ai_status(request: Request) -> dict[str, Any]:
    token = ai.use_key(request.headers.get("x-anthropic-key"))
    try:
        return {"available": ai.available(), "model": ai.model_name(), "sandbox": _docker()}
    finally:
        ai._request_key.reset(token)


def _docker() -> bool:
    from configurator_engine.verifier import docker_available

    return docker_available()


class TextToSpecBody(BaseModel):
    description: str = Field(min_length=3, max_length=4000)


@app.post("/api/ai/text-to-spec")
async def api_text_to_spec(body: TextToSpecBody, request: Request) -> dict[str, Any]:
    _guard_ai(request)
    token = ai.use_key(request.headers.get("x-anthropic-key"))
    try:
        result = await asyncio.to_thread(ai.text_to_spec, body.description)
    except ai.AIUnavailable as exc:
        raise HTTPException(502, str(exc)) from exc
    finally:
        ai._request_key.reset(token)
    return {
        "spec": result.spec.model_dump(mode="json", by_alias=True),
        "summary": result.summary,
        "source": result.source,
        "notes": result.notes,
    }


class GenerateCodeBody(BaseModel):
    node_id: str = Field(max_length=40)
    spec: dict[str, Any]


@app.post("/api/ai/generate-code")
async def api_generate_code(body: GenerateCodeBody, request: Request) -> dict[str, Any]:
    _guard_ai(request)
    parsed = _spec_from(body.spec)
    node_id = body.node_id
    if not any(n.id == node_id and n.type in {"custom_tool", "custom_step"} for n in parsed.graph.nodes):
        raise HTTPException(404, f"'{node_id}' is not a Custom tool or Custom step block.")
    token = ai.use_key(request.headers.get("x-anthropic-key"))
    try:
        if not ai.available():
            raise HTTPException(400, "Add an Anthropic API key to let Claude write this code.")
        new_spec, result = await asyncio.to_thread(ai.generate_code, parsed, node_id)
    except ai.AIUnavailable as exc:
        raise HTTPException(502, str(exc)) from exc
    finally:
        ai._request_key.reset(token)
    node = next(n for n in new_spec.graph.nodes if n.id == node_id)
    return {
        "ok": result.ok,
        "attempts": result.attempts,
        "verified": result.verified,
        "message": result.message,
        "data": node.data.model_dump(mode="json"),
    }


class PromptBody(BaseModel):
    kind: str = Field(max_length=40)
    label: str = Field(max_length=60)
    role: str = Field(default="", max_length=300)
    context: str = Field(default="", max_length=1000)
    tools: list[str] = Field(default_factory=list, max_length=30)


@app.post("/api/ai/write-prompt")
async def api_write_prompt(body: PromptBody, request: Request) -> dict[str, str]:
    _guard_ai(request)
    token = ai.use_key(request.headers.get("x-anthropic-key"))
    try:
        if not ai.available():
            raise HTTPException(400, "Add an Anthropic API key to let Claude draft prompts.")
        text = await asyncio.to_thread(ai.write_prompt, body.kind, body.label, body.role, body.context, body.tools)
    except ai.AIUnavailable as exc:
        raise HTTPException(502, str(exc)) from exc
    finally:
        ai._request_key.reset(token)
    return {"prompt": text}


@app.get("/api/ai/usage")
def ai_usage() -> dict[str, Any]:
    u = ai.USAGE
    return {"calls": u.calls, "input_tokens": u.input_tokens, "output_tokens": u.output_tokens, "cost_usd": round(u.cost_usd, 4)}
