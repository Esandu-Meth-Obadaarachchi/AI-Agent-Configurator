# pgvector (Postgres)

## What
Stores embeddings in Postgres with the pgvector extension, plus a full-text index for keyword search.

## Why
One database for vectors, conversation history and your app data. Hybrid search uses Postgres's own full-text ranking, so there is nothing extra to run.

## Trade-off
Needs a Postgres server (Docker Compose starts one). Very large corpora (tens of millions of chunks) may want a dedicated vector database.
