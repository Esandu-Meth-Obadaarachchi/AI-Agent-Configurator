# Decisions

Every technology in this project, why it was chosen, and what it costs you.
Generated from each module's explanation, so it always matches the code.

## Core backend

**What.** A FastAPI service that runs your agent loop as a LangGraph state graph and streams every step to the browser over Server-Sent Events.

**Why.** LangGraph gives durable state, interrupts for human approval, loops and parallel branches as first-class ideas. FastAPI is the most familiar Python web framework, with typed request models and async streaming.

**Trade-off.** LangGraph adds a dependency and a learning curve compared with a hand-written loop. In return you get checkpointing, resumable runs and a graph you can inspect, which a hand-written loop has to rebuild.

## Anthropic (Claude)

**What.** Claude models through langchain-anthropic. Structured decisions (routing, reviews, delegation) use Claude's native structured outputs.

**Why.** Strong tool use and long-context reasoning. Claude Opus 5.5 is the default; Sonnet 5.5 suits high-volume workers and Haiku 4.5 suits cheap routing.

**Trade-off.** The newest models don't accept temperature; depth is tuned with effort instead. Refusal fallbacks are on by default, so a declined request is retried on another model in the same call and billed at that model's rates.

## Agent

**What.** Runs a tool-calling loop: think, call a tool, read the result, repeat, answer. Attach tools, knowledge or memory underneath it.

**Why.** Most tasks need a model that can look things up and act, not just talk. A tool-calling loop is the standard, well-understood way to do that.

**Trade-off.** More tools give more reach but more chances to pick the wrong one. Keep each agent focused.

## Knowledge base (RAG)

**What.** Loads PDF, Markdown, text and HTML files, splits them into overlapping chunks, embeds them and stores the vectors. Agents search it as a tool; Retrieve steps search it on every turn.

**Why.** Grounding answers in your own documents cuts made-up answers and lets the model cite sources. Retrieval is cheaper than putting every document in the prompt.

**Trade-off.** Answers are only as good as retrieval. Chunk size is a balance: small chunks match precisely but lose context; large chunks keep context but dilute the match. 800 characters with 100 overlap is a sound default for prose.

## pgvector (Postgres)

**What.** Stores embeddings in Postgres with the pgvector extension, plus a full-text index for keyword search.

**Why.** One database for vectors, conversation history and your app data. Hybrid search uses Postgres's own full-text ranking, so there is nothing extra to run.

**Trade-off.** Needs a Postgres server (Docker Compose starts one). Very large corpora (tens of millions of chunks) may want a dedicated vector database.

## Local embeddings (fastembed)

**What.** BAAI/bge-small-en-v1.5 (384 dimensions) running on CPU through fastembed's ONNX runtime.

**Why.** No API key, no per-call cost, and documents never leave your machine.

**Trade-off.** Slightly lower retrieval quality than the best hosted models, a ~130 MB model download on first use, and CPU time during ingestion.

## Hybrid search

**What.** Runs a vector search and a keyword search, then merges the two rankings with reciprocal rank fusion.

**Why.** Vector search finds paraphrases; keyword search finds exact terms such as product codes, names and error messages. Together they miss less.

**Trade-off.** Two searches per query instead of one. The extra cost is small next to a model call.

## Postgres conversation memory

**What.** LangGraph's Postgres checkpointer saves every step of every conversation.

**Why.** Survives restarts, works across several API replicas, and lets paused approvals resume hours later.

**Trade-off.** Needs a Postgres server. Docker Compose starts one (the same one pgvector uses, if you have a knowledge base).

## Next.js chat UI

**What.** A streaming chat interface with a live activity timeline (which step is running, which tools were called), an approval card for paused runs, thumbs up and down, and document upload when the project has a knowledge base.

**Why.** Next.js with the App Router is the most common React stack for production apps. A server-side proxy route keeps the API address out of the browser and works the same locally and in Docker.

**Trade-off.** A second runtime (Node.js) to build and deploy. If you only need an API, switch the interface to "API only".

## Docker Compose

**What.** One command, `docker compose up --build`, starts the API, the chat UI and any database the project needs, with health checks.

**Why.** The same setup runs on a laptop and on a small VPS, and a stranger can boot the project without installing Python or Node.

**Trade-off.** Compose is single-host. For autoscaling, move the same images to a container platform later.

