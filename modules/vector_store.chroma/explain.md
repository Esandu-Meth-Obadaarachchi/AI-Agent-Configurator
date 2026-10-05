# Chroma

## What
An embedded vector database that stores its index in a local folder.

## Why
Zero setup: no server, no credentials. Ideal for prototypes and single-instance apps.

## Trade-off
Runs inside the API process, so it does not suit several API replicas sharing one index. Keyword search for hybrid mode is computed in memory with BM25.
