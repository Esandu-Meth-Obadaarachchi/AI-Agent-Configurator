# Anthropic (Claude)

## What
Claude models through langchain-anthropic. Structured decisions (routing, reviews, delegation) use Claude's native structured outputs.

## Why
Strong tool use and long-context reasoning. Claude Opus 5.5 is the default; Sonnet 5.5 suits high-volume workers and Haiku 4.5 suits cheap routing.

## Trade-off
The newest models don't accept temperature; depth is tuned with effort instead. Refusal fallbacks are on by default, so a declined request is retried on another model in the same call and billed at that model's rates.
