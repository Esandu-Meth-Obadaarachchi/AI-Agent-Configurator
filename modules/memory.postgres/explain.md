# Postgres conversation memory

## What
LangGraph's Postgres checkpointer saves every step of every conversation.

## Why
Survives restarts, works across several API replicas, and lets paused approvals resume hours later.

## Trade-off
Needs a Postgres server. Docker Compose starts one (the same one pgvector uses, if you have a knowledge base).
