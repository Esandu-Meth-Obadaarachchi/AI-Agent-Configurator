# 0004: Following the current Claude API rules

Checked against the Claude API reference in October 2026.

| Rule | Where it's handled |
| --- | --- |
| Opus 5.5, Sonnet 5.5 and Fable reject sampling parameters (`temperature`) | `llm.py` only sends temperature to models that accept it; the rules engine says so in the inspector |
| Depth is controlled with `effort` | Project and per-agent effort setting, passed as `reasoning_effort` |
| Forced `tool_choice` returns 400 on the newest models | Routers, critics and supervisors use native structured outputs (`with_structured_output(..., method="json_schema")`), never forced tool calls |
| No assistant prefill | `messages.for_node()` (see 0003) |
| Thinking blocks are tied to the conversation | Only plain-text final answers are stored in shared state; edits (approval) never touch thinking blocks |
| Refusal fallbacks recommended by default | Generated apps send `fallbacks: "default"` with the `server-side-fallback-2026-07-01` beta on supported models (`ANTHROPIC_REFUSAL_FALLBACK=off` disables it); the configurator does the same |
| Model ids have no date suffix | Catalog uses `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-4-5`, `claude-fable-5-1` |

The configurator's own calls use `client.messages.parse()` with a Pydantic
`output_format`, `output_config.effort` per task, and log tokens and cost per request.
Default model: `claude-opus-5-5` (`CONFIGURATOR_MODEL` overrides).
