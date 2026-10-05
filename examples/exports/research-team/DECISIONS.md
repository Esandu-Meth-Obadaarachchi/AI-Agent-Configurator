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

## Review loop

**What.** A reviewer model grades the latest answer against your criteria. 'Revise' loops back with feedback; 'Pass' moves on. The loop stops after the max attempts.

**Why.** A second look catches mistakes the first pass misses. The attempt cap guarantees the loop always ends.

**Trade-off.** Raises quality noticeably, at the cost of one extra call per attempt.

## Supervisor

**What.** Reads the conversation, picks the next worker, and repeats until the job is done. Workers you connect from 'Delegate' report back automatically.

**Why.** Splitting work between focused workers keeps each prompt short and each tool list small, which makes every worker more reliable than one agent doing everything.

**Trade-off.** Flexible and good at open-ended tasks, but every round costs a model call. Cap the rounds.

## Calculator

**What.** Safely evaluates maths expressions so the model never guesses at numbers.

**Why.** Models make arithmetic slips. An exact calculator removes a whole class of wrong answers.

**Trade-off.** Arithmetic only, no symbolic maths.

## Read web page

**What.** Downloads a page and strips it to readable text. Pairs well with web search.

**Why.** Search snippets are short. Reading the full page lets the agent check details and quote accurately.

**Trade-off.** Some sites block bots or need JavaScript; long pages are truncated.

## Web search

**What.** Returns titles, links and snippets for a query. Needs TAVILY_API_KEY.

**Why.** Models don't know recent events. Search gives the agent current information with sources.

**Trade-off.** Needs a Tavily API key, and search results can be wrong or stale.

## In-memory conversation state

**What.** Conversation threads and paused approvals are kept in the API process's memory.

**Why.** Nothing to set up, ideal while you design the loop.

**Trade-off.** Everything is lost when the API restarts. Add a Memory block with SQLite or Postgres before real users arrive.

## Next.js chat UI

**What.** A streaming chat interface with a live activity timeline (which step is running, which tools were called), an approval card for paused runs, thumbs up and down, and document upload when the project has a knowledge base.

**Why.** Next.js with the App Router is the most common React stack for production apps. A server-side proxy route keeps the API address out of the browser and works the same locally and in Docker.

**Trade-off.** A second runtime (Node.js) to build and deploy. If you only need an API, switch the interface to "API only".

## Docker Compose

**What.** One command, `docker compose up --build`, starts the API, the chat UI and any database the project needs, with health checks.

**Why.** The same setup runs on a laptop and on a small VPS, and a stranger can boot the project without installing Python or Node.

**Trade-off.** Compose is single-host. For autoscaling, move the same images to a container platform later.

