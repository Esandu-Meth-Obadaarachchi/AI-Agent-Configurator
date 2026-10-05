# Local embeddings (fastembed)

## What
BAAI/bge-small-en-v1.5 (384 dimensions) running on CPU through fastembed's ONNX runtime.

## Why
No API key, no per-call cost, and documents never leave your machine.

## Trade-off
Slightly lower retrieval quality than the best hosted models, a ~130 MB model download on first use, and CPU time during ingestion.
