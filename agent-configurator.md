# Agent Configurator: Build Spec

Read this file fully before writing code. Follow the working agreements at the end.

## 1. What this is

A tool that turns a configuration into a complete, working agentic application. The user picks options (RAG, agents, tools, memory, UI, deployment). The tool outputs a full project: FastAPI backend, Next.js chat UI, Docker Compose, tests and docs. It also outputs a prompt pack the user pastes into Claude Code for anything the templates do not cover.

This is a portfolio piece. A hosted version will run as a live demo. The repo will be open source.

## 2. The gap it covers

A developer can ask Claude Code for an agent app. This tool adds:

- Options the developer does not know exist (reranking, hybrid search, chunking strategies).
- Repeatable output. The same spec gives the same code every time.
- Tested combinations. Every supported combination boots in CI.
- Zero token cost for the predictable parts.
- A spec file a team reviews and diffs.
- A decision log that explains why each option was chosen.

## 3. Decisions already made

- Primary users: developers. The tool also stays approachable for beginners through plain-language explanations.
- Build order: CLI first, step-by-step wizard second, drag-and-drop canvas last.
- Output language: Python backend for v1. The user can see TypeScript output as a greyed-out option. The spec must not block adding it later.
- Output includes backend and frontend.
- LLM providers: Anthropic and OpenAI, selectable per project.
- A hosted version will exist.
- Deterministic templates produce code. An LLM only fills gaps.

## 4. Architecture

Seven parts. Build them in this order.

### 4.1 Spec

One JSON file holds every choice. Pydantic v2 validates it. The CLI, wizard and canvas all read and write this file. Version the schema with a `spec_version` field.

Example:

```json
{
  "spec_version": "0.1",
  "project": { "name": "docs-qa", "description": "Q and A over company PDFs" },
  "llm": { "provider": "anthropic", "model": "claude-sonnet-5-5" },
  "rag": {
    "enabled": true,
    "ingestion": { "sources": ["pdf", "markdown"], "chunker": "recursive", "chunk_size": 800, "overlap": 100 },
    "embedding": { "provider": "openai", "model": "text-embedding-3-small" },
    "vector_store": "pgvector",
    "retrieval": { "mode": "hybrid", "top_k": 8, "reranker": "none" }
  },
  "agents": {
    "pattern": "single",
    "tools": ["mcp_client", "web_search", "custom"]
  },
  "memory": { "short_term": true },
  "human_in_loop": { "approval_nodes": [] },
  "ui": { "framework": "nextjs", "streaming": true },
  "deploy": { "target": "docker_compose" }
}
```

### 4.2 Module registry

Each feature is a folder under `modules/`. Each folder holds:

- `manifest.yaml`: id, options, requires, conflicts, env vars, dependencies, files to render.
- `templates/`: Jinja2 files.
- `tests/`: tests copied into the export.
- `explain.md`: plain-language description and trade-offs for the UI and decision log.

Manifest example:

```yaml
id: retrieval.hybrid
requires: [vector_store.sparse_capable]
conflicts: []
python_deps: [rank-bm25]
env: []
files:
  - src: templates/retriever.py.j2
    dest: backend/app/rag/retriever.py
```

### 4.3 Rules engine

Plain if and else logic in Python. No LLM. It:

- Resolves required modules.
- Blocks conflicts with a clear error message.
- Picks which templates apply to which spec.
- Reports unsupported requests so the router can pick them up.

### 4.4 Renderer and merger

Jinja2 renders the project tree. A merger combines `pyproject.toml`, `package.json`, `docker-compose.yml` and `.env.example` from all chosen modules. Output goes to a target folder or a zip.

### 4.5 Fallback router (the only code-writing LLM use)

When a requirement matches no module, call the Claude API. Rules:

- Send a strict contract: target interface, target file path, one example, the test it must pass.
- Use structured output. Receive code as a field, never as free text.
- Write the result to `backend/app/custom/` only. Never edit template files.
- Run the verifier. On failure, send the error back. Retry up to three times.
- After three failures, mark the item as open and add it to the prompt pack.

### 4.6 Verifier

Run on every export, in CI and in the hosted app:

- Ruff lint and mypy type check on the backend.
- ESLint and tsc on the frontend.
- Exported unit tests.
- Docker Compose boot test with a health check.

### 4.7 Prompt pack

Generate `PROMPT_PACK.md` in each export. It holds the spec, the file map, the extension points and a list of open items. The user pastes it into Claude Code.

## 5. Where an LLM is allowed

Three places only:

1. Text to spec: the user types a wish, the model proposes a spec, the user confirms.
2. Fallback router code stubs.
3. Prompt pack wording.

Everything else is deterministic. State this boundary in the README.

## 6. Extension points in exported code

Templates expose files meant for user changes:

- `backend/app/custom/tools.py`
- `backend/app/custom/nodes.py`
- `backend/app/custom/prompts.py`

Core files stay untouched. A template upgrade does not overwrite custom work.

## 7. v1 module scope

- RAG ingestion: PDF and Markdown loaders. Chunkers: recursive and fixed size.
- Embeddings: one OpenAI option plus one local option.
- Vector stores: pgvector and Chroma.
- Retrieval: dense, hybrid, optional reranker.
- Agent patterns: single agent with tools. Orchestrator with workers using LangGraph.
- Tools: MCP client, web search, custom tool slot.
- Memory: short term (conversation) with a LangGraph Postgres checkpointer.
- Human in the loop: one approval node with interrupt and resume.
- UI: Next.js chat with streaming, approval screen and feedback buttons.
- Deployment: Docker Compose.
- Not in v1: TypeScript backend, long term memory, evaluation sets, canvas, extra clouds.

## 8. Exported project structure

```
exported-project/
  backend/
    app/
      main.py
      config.py
      rag/
      agents/
      tools/
      custom/
    tests/
    pyproject.toml
    Dockerfile
  frontend/
    src/
    package.json
    Dockerfile
  docker-compose.yml
  .env.example
  spec.json
  PROMPT_PACK.md
  DECISIONS.md
  README.md
```

`DECISIONS.md` lists each chosen option with the reason and the trade-off, taken from each module's `explain.md`.

## 9. Repository layout for the configurator itself

```
agent-configurator/
  packages/
    spec/            Pydantic schema and JSON Schema export
    engine/          registry, rules, renderer, merger, router, verifier
    cli/             Typer CLI
  modules/           feature modules
  apps/
    web/             Next.js wizard (phase 2)
    api/             FastAPI service for the hosted version
  examples/          three reference specs and their exports
  benchmarks/        Claude Code comparison scripts
  docs/
  .github/workflows/
```

## 10. CLI commands (phase 1)

- `configurator init`: interactive prompts, writes `spec.json`.
- `configurator validate spec.json`: schema and rules check.
- `configurator explain spec.json`: prints each choice and trade-off.
- `configurator generate spec.json -o ./out`: renders the project.
- `configurator verify ./out`: runs the verifier.
- `configurator from-text "describe your app"`: text to spec through the Claude API.

## 11. Testing and CI

- Unit tests for the schema, rules engine and renderer.
- Golden file tests: a fixed spec must render byte-identical output.
- Matrix job: render and boot every supported combination in `ci/matrix.yaml`. Keep the matrix small in v1.
- Nightly job: render with the latest LangGraph, FastAPI and MCP library versions. Report failures.
- Pin all versions in exported projects.

## 12. Security rules

- Run router-generated code and verification only inside containers. Never on the host.
- Never put API keys in templates or specs. Use `.env`.
- Hosted version: per-user rate limits, a cost cap per day, no storage of user keys beyond the session.
- Treat user uploads and spec text as untrusted input.

## 13. Hosted version

- Web wizard that edits the spec and shows a live preview of the file tree.
- Generate and download as a zip.
- Sandboxed verifier job in a container with no outbound network except the package registries.
- Free tier with a daily generation cap. Log cost per request.
- Suggested hosting: a small VPS or container service. Decide after phase 2.

## 14. Four week plan

Week 1 (5 to 11 October): spec schema, module registry, rules engine, renderer, CLI `init` `validate` `generate`. One module set: single agent with pgvector RAG. Exit test: generated project boots with `docker compose up`.

Week 2 (12 to 18 October): add chunker, retriever and embedding options, MCP client tool, web search tool, memory, Next.js chat UI, verifier. Exit test: golden file tests and a matrix of four combinations pass in CI.

Week 3 (19 to 25 October): orchestrator with workers, human in the loop approval node, fallback router with retries, prompt pack, `from-text`, `DECISIONS.md` generation. Exit test: a multi-agent example boots and the router fixes one deliberate gap.

Week 4 (26 October to 1 November): benchmark against Claude Code, three example exports, README, architecture diagram, two minute demo video, first hosted deploy of the wizard shell. Exit test: a stranger follows the README and gets a running app in 15 minutes.

## 15. Portfolio proof to produce

- Benchmark table: same app built by Claude Code from a prompt and by this tool. Measure time, tokens, cost and pass rate over 10 runs each.
- CI badge for the supported matrix.
- Three example exports: document Q and A, support bot, multi-agent research app.
- One decision record per technology choice with the trade-off in plain words.
- Architecture diagram and demo video.

## 16. Definition of done for v1

- All CLI commands work.
- The supported matrix passes CI.
- The router runs with retries and a visible failure path.
- Docs let a new developer extend a module in under an hour.
- Hosted wizard generates a zip.

## 17. Risks

- Combination growth. Keep the matrix small and tested.
- Template rot from fast library changes. Nightly CI and pinned versions.
- Weak differentiation against plain Claude Code. The benchmark and the tested matrix answer this.
- Scope creep into a canvas. Do not start the canvas before the wizard is done.

## 18. Working agreements for Claude Code

- Plan before coding. Show the plan for each week and wait for approval.
- Small commits. One feature per commit with a clear message.
- Write tests before or with each module.
- Explain each technology choice in a short comment or in `docs/decisions/`. The owner must be able to explain every choice in a job interview.
- Ask before adding a dependency. State why it is needed and what the alternative is.
- Use Python 3.12, Pydantic v2, Typer, Jinja2, FastAPI, LangGraph, Next.js with TypeScript.
- Use British English in docs and comments.
- Stop and ask when a requirement is unclear. Do not guess.
