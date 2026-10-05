# In-memory conversation state

## What
Conversation threads and paused approvals are kept in the API process's memory.

## Why
Nothing to set up, ideal while you design the loop.

## Trade-off
Everything is lost when the API restarts. Add a Memory block with SQLite or Postgres before real users arrive.
