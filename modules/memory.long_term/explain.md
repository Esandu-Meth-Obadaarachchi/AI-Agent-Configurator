# Long-term memory

## What
Attached agents get two tools, remember and recall, backed by LangGraph's store. Memories are kept per user and outlive any one conversation.

## Why
The assistant can learn stable facts (names, preferences, ongoing projects) without stuffing every past conversation into the prompt.

## Trade-off
The model decides what to remember, so it can miss things or store noise. Recall ranks by keyword overlap, which is simple and predictable but not semantic.
