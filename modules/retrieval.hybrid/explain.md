# Hybrid search

## What
Runs a vector search and a keyword search, then merges the two rankings with reciprocal rank fusion.

## Why
Vector search finds paraphrases; keyword search finds exact terms such as product codes, names and error messages. Together they miss less.

## Trade-off
Two searches per query instead of one. The extra cost is small next to a model call.
