# Local cross-encoder reranker

## What
Re-scores the top candidates with ms-marco-MiniLM-L-6-v2, which reads the query and each passage together.

## Why
Cross-encoders judge relevance far better than embedding similarity alone, so the best passages rise to the top.

## Trade-off
Adds tens of milliseconds per query on CPU and a small model download.
