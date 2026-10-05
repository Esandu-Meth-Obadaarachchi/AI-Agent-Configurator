# SQLite conversation memory

## What
Conversation threads and paused approvals are saved to a single SQLite file.

## Why
Survives restarts with zero infrastructure.

## Trade-off
One file, one writer: fine for a single API instance, not for several replicas.
