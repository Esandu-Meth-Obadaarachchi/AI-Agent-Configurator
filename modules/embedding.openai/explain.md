# OpenAI embeddings

## What
text-embedding-3-small (1,536 dimensions) or text-embedding-3-large (3,072 dimensions) through the OpenAI API.

## Why
Strong retrieval quality for very little cost, with no model to host.

## Trade-off
A second API key and a network call per ingest batch and per search. Documents leave your infrastructure.
