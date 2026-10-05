# Architecture

## One spec, three clients

`spec.json` (v0.2) is the single source of truth. The canvas, the CLI and the hosted
API all read and write it. It holds a **graph** (blocks and wires) plus project-wide
settings (model defaults, interface, deployment). See [0001](decisions/0001-graph-spec.md).

## The engine pipeline

1. **Parse** (`configurator_spec`): Pydantic validates the spec. Node data is a
   discriminated union keyed on `type`, so each block is checked by its own model.
   v0.1 specs from the original brief are upgraded on load.
2. **Compile** (`compiler.py`): edges and handles become an IR. Each flow block gets
   its successors, branches (`pass`/`revise`, `approved`/`rejected`, one per router
   route), supervisor workers, attached tools and knowledge. Output blocks become `END`.
   The compiler also produces the **trace**: a deterministic dry run (routers take their
   first branch, review loops revise once, supervisors call each worker once) that the
   canvas animates.
3. **Rules** (`rules.py`): plain if/else. Node-level issues (error / warning / info),
   loops with no exit (strongly connected components without a router, critic,
   supervisor, approval or guardrail), and the list of **modules** this spec needs.
   Custom tools and steps without code are reported as **gaps**.
4. **Render** (`generate.py`): every module's templates are rendered with Jinja2
   (`StrictUndefined`, no autoescape). Static files are copied byte for byte.
5. **Merge** (`merger.py`): `pyproject.toml`, `requirements.txt`, `package.json`,
   `docker-compose.yml` and `.env.example` are assembled from every module's fragment,
   sorted and pinned from `modules/versions.yaml`.
6. **Late files**: `README.md`, `PROMPT_PACK.md` and `DECISIONS.md` are rendered last so
   they can list the final file map and every module's explanation.

The output is a `dict[path, content]`, written to a folder or a deterministic zip
(fixed timestamps, sorted entries). Golden tests hash every file of every blueprint.

## The generated backend

```
backend/app/
  main.py         FastAPI: /api/chat (SSE), /api/chat/resume, /api/threads, /api/feedback, uploads
  graph.py        LangGraph StateGraph wiring, generated and readable
  nodes/          one factory per block kind (agent, supervisor, router, critic, …)
  tools/          tool sets keyed by the canvas block that provides them
  rag/            loaders, chunkers, embeddings, stores, hybrid retrieval, reranking
  llm.py          the model factory (Claude rules live here)
  messages.py     how several agents share one conversation
  streaming.py    LangGraph stream → Server-Sent Events
  custom/         yours: tools.py, nodes.py, prompts.py (never overwritten)
```

Key behaviours:

- **Agents** use LangChain's `create_agent`. Only an agent's final answer enters the
  shared conversation, as `AIMessage(name=<block id>)`; tool chatter streams to the UI
  but stays out of other agents' context.
- **Conversation per node** (`messages.for_node`): each step sees the user's messages,
  its own earlier replies, and other agents' replies as labelled user-side notes. The
  history never ends on an assistant turn (current Claude models reject prefill).
- **Decisions** (router, critic, supervisor, approval, guardrail) write
  `state["decisions"][node_id]`; generated `route()` functions read it. Unknown
  decisions end the run rather than guess.
- **Per-turn bookkeeping** (`decisions`, `counters`, `context`) merges across parallel
  branches and resets at each new user message.
- **Approvals** use `interrupt()`; the checkpointer (memory, SQLite or Postgres) is what
  lets a paused run resume, even after a restart.
- **Streaming** uses `stream_mode=["messages", "updates", "custom"]` with
  `subgraphs=True`, so tokens from agents nested inside nodes reach the UI.
- **Demo mode** (`LLM_PROVIDER=fake`) swaps in an offline model whose structured
  decisions follow the happy path. The generated tests run in this mode.

## The canvas

Next.js 16 app. React Flow renders every block with one component driven by the
catalog (`apps/web/src/lib/catalog.json`, exported from the engine, with a drift test).
State lives in a Zustand store with undo/redo snapshots and localStorage autosave. Every
change is validated by the engine (debounced) and issues come back as badges. The Code
view calls `/api/preview`, which returns the files plus a block-to-files map.

The canvas works offline for editing; preview, export and AI need the engine.
