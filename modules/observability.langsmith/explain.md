# LangSmith tracing

## What
Every run is traced to LangSmith: each step, model call, tool call, token count and latency.

## Why
Agent loops are hard to debug from logs. A trace shows exactly which step went wrong and what the model saw.

## Trade-off
Prompts and outputs are sent to a hosted service. Leave it off for sensitive data or self-host.
