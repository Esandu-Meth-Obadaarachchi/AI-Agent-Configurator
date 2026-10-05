# Status: what was verified, and what still needs real keys

Built and checked on 6 October 2026.

## Verified

- Engine: 85+ tests pass (schema, migrations, rules, compiler trace, golden files for
  every blueprint, CLI, API, AI router with mocked Claude). ruff and mypy clean.
- Every blueprint renders a backend that passes its **own** ruff, mypy and pytest with
  pinned dependencies (`make verify-examples`), including approvals, supervisors,
  review loops, RAG (in-memory store, fake embedder), SQL, MCP (skipped) and memory.
- A generated project was run end to end in demo mode: guardrail redaction, routing,
  streamed tokens through the Next.js proxy, approval interrupt, resume with an edited
  reply, and thread history.
- The generated Next.js UI passes ESLint, tsc and `next build`.
- The canvas passes ESLint and tsc, and a scripted Chrome run covering attach, edit,
  command palette, wiring, refused wiring, checks, trace, code view, undo and zip export,
  with no console errors.

## Not yet verified

- **Real Claude calls.** No API key was available. The Claude paths (text to spec,
  fallback router, prompt help, and the generated apps' `ChatAnthropic` calls with effort
  and refusal fallbacks) are written against the current API and SDK docs, and their
  request payloads were inspected, but no live request has been made. First thing to try
  with a key: `configurator from-text "…"` and a support-bot export with
  `LLM_PROVIDER=anthropic`.
- **Docker.** The Docker daemon wasn't running, so the compose boot test and the
  container sandbox for Claude-written code haven't run locally. CI runs the compose boot.
- **pgvector and Postgres** stores were tested through their interfaces with in-memory
  stand-ins, not against a live Postgres.
- **OpenAI** model names in the catalog are best guesses for October 2026; any model id
  can be typed in.
