# Status: what was verified, and what still needs real keys

Built and checked on 6 October 2026.

## Verified

- Engine: 85 tests pass (schema, migrations, rules, compiler trace, golden files for
  every blueprint, CLI, API, AI router with mocked Claude). ruff and mypy clean.
- All 10 combinations in `ci/matrix.yaml` render a backend that passes its **own** ruff,
  mypy and pytest with pinned dependencies (`make verify-examples`): every blueprint plus
  an OpenAI-provider and an API-only variant. Covers approvals, supervisors, review
  loops, RAG (in-memory store, fake embedder), SQL, MCP (skipped) and memory.
- A generated project was run end to end in demo mode: guardrail redaction, routing,
  streamed tokens through the Next.js proxy, approval interrupt, resume with an edited
  reply, and thread history.
- The generated Next.js UI passes ESLint, tsc and `next build`.
- The canvas passes ESLint and tsc, and a scripted Chrome run covering attach, edit,
  command palette, wiring, refused wiring, checks, trace, code view, undo and zip export,
  with no console errors.

- The canvas's Claude wiring reaches the real API: with a deliberately invalid key,
  "Write with Claude" sent a request to api.anthropic.com, got 401, and showed a clear
  "key rejected" message. Describe-your-app without a key falls back to the closest
  blueprint.

## Not yet verified

- **Real Claude calls.** No API key was available. The Claude paths (text to spec,
  fallback router, prompt help, and the generated apps' `ChatAnthropic` calls with effort
  and refusal fallbacks) are written against the current API and SDK docs, and their
  request payloads were inspected, but no authenticated request has been made. First thing to try
  with a key: `configurator from-text "…"` and a support-bot export with
  `LLM_PROVIDER=anthropic`.
- **Docker.** The Docker daemon wasn't running, so the compose boot test and the
  container sandbox for Claude-written code haven't run locally. CI runs the compose boot.
- **pgvector and Postgres** stores were tested through their interfaces with in-memory
  stand-ins, not against a live Postgres.
- **OpenAI** model names in the catalog are best guesses for October 2026; any model id
  can be typed in.
