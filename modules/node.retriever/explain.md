# Retrieve step

## What
Searches the attached knowledge base with the latest message and hands the results to the next step. Classic RAG: predictable, one search per turn.

## Why
Searching on every turn makes answers consistently grounded in your documents.

## Trade-off
Always searches, even when not needed. Attaching knowledge to an agent instead lets the agent decide.
