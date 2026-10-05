# Knowledge base (RAG)

## What
Loads PDF, Markdown, text and HTML files, splits them into overlapping chunks, embeds them and stores the vectors. Agents search it as a tool; Retrieve steps search it on every turn.

## Why
Grounding answers in your own documents cuts made-up answers and lets the model cite sources. Retrieval is cheaper than putting every document in the prompt.

## Trade-off
Answers are only as good as retrieval. Chunk size is a balance: small chunks match precisely but lose context; large chunks keep context but dilute the match. 800 characters with 100 overlap is a sound default for prose.
