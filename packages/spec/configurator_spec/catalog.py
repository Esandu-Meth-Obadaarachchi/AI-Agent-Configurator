"""Node catalog: everything the canvas needs to draw a toolkit and an inspector.

The web app renders the toolkit sidebar and every inspector form from this data, so a
new node type is added in one place. Text here is user-facing: plain words, British
English, sentence case.
"""

from __future__ import annotations

from typing import Any

ANTHROPIC_MODELS = [
    {"value": "claude-opus-5-5", "label": "Claude Opus 5.5", "hint": "The default. Strongest all-rounder for agents and supervisors."},
    {"value": "claude-sonnet-5-5", "label": "Claude Sonnet 5.5", "hint": "Faster and cheaper. Good for high-volume workers."},
    {"value": "claude-haiku-4-5", "label": "Claude Haiku 4.5", "hint": "Fastest and cheapest. Good for routers and critics."},
    {"value": "claude-fable-5-1", "label": "Claude Fable 5.1", "hint": "Anthropic's most capable model, priced above Opus. For the hardest long tasks."},
]
OPENAI_MODELS = [
    {"value": "gpt-5", "label": "GPT-5", "hint": "OpenAI flagship."},
    {"value": "gpt-5-mini", "label": "GPT-5 mini", "hint": "Cheaper, faster."},
    {"value": "gpt-4.1", "label": "GPT-4.1", "hint": "Previous generation."},
]
MODELS = {"anthropic": ANTHROPIC_MODELS, "openai": OPENAI_MODELS}
DEFAULT_MODEL = {"anthropic": "claude-opus-5-5", "openai": "gpt-5-mini"}

CATEGORIES = [
    {"id": "flow", "title": "Start and finish", "blurb": "Where a conversation enters and leaves the loop."},
    {"id": "agents", "title": "Agents", "blurb": "Models that think, call tools and hand work to each other."},
    {"id": "logic", "title": "Logic and loops", "blurb": "Branch, review and repeat until the answer is good."},
    {"id": "knowledge", "title": "Knowledge", "blurb": "Ground answers in your own documents (RAG)."},
    {"id": "tools", "title": "Tools", "blurb": "Actions an agent can take. Attach them under an agent."},
    {"id": "memory", "title": "Memory", "blurb": "Remember conversations and facts across sessions."},
    {"id": "safety", "title": "Safety and humans", "blurb": "Guardrails and human sign-off before anything risky."},
]


def _f(key: str, label: str, kind: str, **extra: Any) -> dict[str, Any]:
    return {"key": key, "label": label, "kind": kind, **extra}


LABEL = _f("label", "Name on canvas", "text", placeholder="e.g. Researcher")
NOTES = _f("notes", "Notes", "textarea", rows=2, advanced=True, help="Private notes. Copied into PROMPT_PACK.md.")
MODEL = _f("model", "Model", "model", help="Leave on default to use the project model.")
TEMPERATURE = _f(
    "temperature",
    "Temperature",
    "number",
    min=0,
    max=1,
    step=0.05,
    advanced=True,
    nullable=True,
    help="Only sent to models that accept it. Claude Opus 5.5, Sonnet 5.5 and Fable ignore it; use effort instead.",
)
EFFORT_OPTIONS = [
    {"value": "", "label": "Default"},
    {"value": "low", "label": "Low"},
    {"value": "medium", "label": "Medium"},
    {"value": "high", "label": "High"},
    {"value": "xhigh", "label": "X-high"},
    {"value": "max", "label": "Max"},
]
EFFORT = _f(
    "effort",
    "Reasoning effort",
    "segmented",
    options=EFFORT_OPTIONS,
    advanced=True,
    nullable=True,
    help="Claude only. Higher effort thinks longer and costs more. Low suits routing and chat.",
)

FLOW_IN = [{"id": "in", "kind": "flow"}]
FLOW_OUT = [{"id": "out", "kind": "flow", "label": ""}]
ATTACH_OUT = [{"id": "attach", "kind": "attach"}]

NODE_TYPES: list[dict[str, Any]] = [
    # ------------------------------------------------------------------ flow
    {
        "type": "input",
        "category": "flow",
        "title": "Chat input",
        "icon": "ChatCircleText",
        "blurb": "The user's message enters here.",
        "explain": "Every app has exactly one entry point. It receives the user's message and starts the loop.",
        "role": "flow",
        "max": 1,
        "inputs": [],
        "outputs": FLOW_OUT,
        "fields": [LABEL, _f("greeting", "Greeting shown in the chat UI", "text"), NOTES],
    },
    {
        "type": "output",
        "category": "flow",
        "title": "Reply",
        "icon": "PaperPlaneTilt",
        "blurb": "Send the final answer back.",
        "explain": "Ends the turn and streams the last message to the user. Any branch that stops without a Reply ends here implicitly.",
        "role": "flow",
        "inputs": FLOW_IN,
        "outputs": [],
        "fields": [LABEL, NOTES],
    },
    # ------------------------------------------------------------------ agents
    {
        "type": "agent",
        "category": "agents",
        "title": "Agent",
        "icon": "Robot",
        "blurb": "A model with a job and tools.",
        "explain": "Runs a tool-calling loop: think, call a tool, read the result, repeat, answer. Attach tools, knowledge or memory underneath it.",
        "tradeoff": "More tools give more reach but more chances to pick the wrong one. Keep each agent focused.",
        "role": "flow",
        "inputs": FLOW_IN,
        "outputs": FLOW_OUT,
        "accepts": ["tool", "knowledge", "memory"],
        "fields": [
            LABEL,
            _f("role", "Job in one line", "text", help="Shown to supervisors so they know when to delegate here."),
            _f("system_prompt", "Instructions", "prompt", rows=6, ai="system_prompt"),
            MODEL,
            EFFORT,
            TEMPERATURE,
            _f("max_steps", "Max tool steps", "number", min=1, max=50, step=1, advanced=True),
            NOTES,
        ],
    },
    {
        "type": "supervisor",
        "category": "agents",
        "title": "Supervisor",
        "icon": "UsersThree",
        "blurb": "Delegates to worker agents.",
        "explain": "Reads the conversation, picks the next worker, and repeats until the job is done. Workers you connect from 'Delegate' report back automatically.",
        "tradeoff": "Flexible and good at open-ended tasks, but every round costs a model call. Cap the rounds.",
        "role": "flow",
        "inputs": FLOW_IN,
        "outputs": [
            {"id": "delegate", "kind": "flow", "label": "Delegate"},
            {"id": "done", "kind": "flow", "label": "Done"},
        ],
        "fields": [
            LABEL,
            _f("instructions", "How to delegate", "prompt", rows=5),
            MODEL,
            _f("max_rounds", "Max rounds", "number", min=1, max=30, step=1),
            NOTES,
        ],
    },
    {
        "type": "prompt",
        "category": "agents",
        "title": "LLM step",
        "icon": "Sparkle",
        "blurb": "One model call, no tools.",
        "explain": "A single, predictable model call: summarise, rewrite, translate, extract. Cheaper and faster than an agent.",
        "role": "flow",
        "inputs": FLOW_IN,
        "outputs": FLOW_OUT,
        "fields": [LABEL, _f("instructions", "Instructions", "prompt", rows=5), MODEL, TEMPERATURE, NOTES],
    },
    # ------------------------------------------------------------------ logic
    {
        "type": "router",
        "category": "logic",
        "title": "Router",
        "icon": "GitFork",
        "blurb": "Send each request down one branch.",
        "explain": "Classifies the latest message and follows the matching branch. Use a model for nuance, or keywords for zero cost.",
        "tradeoff": "Model routing handles fuzzy requests; keyword routing is free, instant and predictable.",
        "role": "flow",
        "inputs": FLOW_IN,
        "outputs": "routes",
        "fields": [
            LABEL,
            _f("mode", "Decide with", "segmented", options=[{"value": "llm", "label": "Model"}, {"value": "keywords", "label": "Keywords"}]),
            _f("routes", "Branches", "routes"),
            _f("instructions", "Routing hint", "textarea", rows=2, advanced=True),
            MODEL,
            NOTES,
        ],
    },
    {
        "type": "critic",
        "category": "logic",
        "title": "Review loop",
        "icon": "ArrowsClockwise",
        "blurb": "Check the answer, send it back if weak.",
        "explain": "A reviewer model grades the latest answer against your criteria. 'Revise' loops back with feedback; 'Pass' moves on. The loop stops after the max attempts.",
        "tradeoff": "Raises quality noticeably, at the cost of one extra call per attempt.",
        "role": "flow",
        "inputs": FLOW_IN,
        "outputs": [
            {"id": "pass", "kind": "flow", "label": "Pass"},
            {"id": "revise", "kind": "flow", "label": "Revise"},
        ],
        "fields": [
            LABEL,
            _f("criteria", "A good answer…", "prompt", rows=4),
            _f("max_iterations", "Max attempts", "number", min=1, max=10, step=1),
            MODEL,
            NOTES,
        ],
    },
    {
        "type": "custom_step",
        "category": "logic",
        "title": "Custom step",
        "icon": "Code",
        "blurb": "Your own Python, described in words.",
        "explain": "Anything the toolkit lacks. Describe it and Claude writes the function, or write it yourself. It lands in backend/app/custom/nodes.py.",
        "role": "flow",
        "ai": True,
        "inputs": FLOW_IN,
        "outputs": FLOW_OUT,
        "fields": [
            LABEL,
            _f("description", "What should this step do?", "textarea", rows=4),
            _f("code", "Python", "code", ai="custom_step", language="python"),
            NOTES,
        ],
    },
    # ------------------------------------------------------------------ knowledge
    {
        "type": "knowledge",
        "category": "knowledge",
        "title": "Knowledge base",
        "icon": "Books",
        "blurb": "Your documents, indexed for search.",
        "explain": "Loads, chunks and embeds your files into a vector store. Attach it under an agent (as a search tool) or into a Retrieve step.",
        "tradeoff": "Hybrid search finds exact terms that pure vector search misses. A reranker improves precision but adds latency.",
        "role": "resource",
        "kind": "knowledge",
        "inputs": [],
        "outputs": ATTACH_OUT,
        "fields": [
            LABEL,
            _f("description", "What's inside", "text", help="Agents read this to decide when to search."),
            _f(
                "sources",
                "File types",
                "multiselect",
                options=[
                    {"value": "pdf", "label": "PDF"},
                    {"value": "markdown", "label": "Markdown"},
                    {"value": "text", "label": "Plain text"},
                    {"value": "html", "label": "HTML"},
                ],
            ),
            _f(
                "vector_store",
                "Vector store",
                "select",
                options=[
                    {"value": "pgvector", "label": "pgvector (Postgres)", "hint": "One database for vectors, chat history and app data."},
                    {"value": "chroma", "label": "Chroma", "hint": "Zero setup. Great for prototypes."},
                ],
            ),
            _f(
                "embedding",
                "Embeddings",
                "select",
                options=[
                    {"value": "openai_small", "label": "OpenAI small", "hint": "text-embedding-3-small. Cheap, strong."},
                    {"value": "openai_large", "label": "OpenAI large", "hint": "text-embedding-3-large. Best recall."},
                    {"value": "local_bge_small", "label": "Local (BGE small)", "hint": "Runs on CPU via fastembed. No API key."},
                ],
            ),
            _f(
                "retrieval",
                "Search mode",
                "segmented",
                options=[{"value": "dense", "label": "Vector"}, {"value": "hybrid", "label": "Hybrid"}],
            ),
            _f(
                "reranker",
                "Reranker",
                "select",
                options=[
                    {"value": "none", "label": "None"},
                    {"value": "cross_encoder", "label": "Local cross-encoder", "hint": "Free, runs on CPU."},
                    {"value": "cohere", "label": "Cohere Rerank", "hint": "Hosted, needs COHERE_API_KEY."},
                ],
            ),
            _f("top_k", "Results per search", "number", min=1, max=50, step=1),
            _f(
                "chunker",
                "Chunking",
                "segmented",
                advanced=True,
                options=[{"value": "recursive", "label": "Recursive"}, {"value": "fixed", "label": "Fixed size"}],
            ),
            _f("chunk_size", "Chunk size (characters)", "number", min=100, max=8000, step=50, advanced=True),
            _f("overlap", "Overlap (characters)", "number", min=0, max=2000, step=10, advanced=True),
            NOTES,
        ],
    },
    {
        "type": "retriever",
        "category": "knowledge",
        "title": "Retrieve step",
        "icon": "MagnifyingGlass",
        "blurb": "Always look things up before answering.",
        "explain": "Searches the attached knowledge base with the latest message and hands the results to the next step. Classic RAG: predictable, one search per turn.",
        "tradeoff": "Always searches, even when not needed. Attaching knowledge to an agent instead lets the agent decide.",
        "role": "flow",
        "inputs": FLOW_IN,
        "outputs": FLOW_OUT,
        "accepts": ["knowledge"],
        "fields": [LABEL, _f("top_k", "Results (blank = knowledge base default)", "number", min=1, max=50, step=1, nullable=True), NOTES],
    },
    # ------------------------------------------------------------------ tools
    {
        "type": "web_search",
        "category": "tools",
        "title": "Web search",
        "icon": "Globe",
        "blurb": "Search the live web (Tavily).",
        "explain": "Returns titles, links and snippets for a query. Needs TAVILY_API_KEY.",
        "role": "resource",
        "kind": "tool",
        "inputs": [],
        "outputs": ATTACH_OUT,
        "fields": [LABEL, _f("max_results", "Results per search", "number", min=1, max=20, step=1), NOTES],
    },
    {
        "type": "web_fetch",
        "category": "tools",
        "title": "Read web page",
        "icon": "FileHtml",
        "blurb": "Fetch a URL as clean text.",
        "explain": "Downloads a page and strips it to readable text. Pairs well with web search.",
        "role": "resource",
        "kind": "tool",
        "inputs": [],
        "outputs": ATTACH_OUT,
        "fields": [LABEL, _f("max_chars", "Max characters returned", "number", min=500, max=200000, step=500), NOTES],
    },
    {
        "type": "http_api",
        "category": "tools",
        "title": "HTTP API",
        "icon": "PlugsConnected",
        "blurb": "Call one endpoint of your API.",
        "explain": "Turns a single REST endpoint into a tool. Parameters become tool inputs the model fills in.",
        "role": "resource",
        "kind": "tool",
        "inputs": [],
        "outputs": ATTACH_OUT,
        "fields": [
            LABEL,
            _f("tool_name", "Tool name", "text", mono=True),
            _f("description", "When should the agent call it?", "textarea", rows=2),
            _f("method", "Method", "segmented", options=[{"value": m, "label": m} for m in ["GET", "POST", "PUT", "PATCH", "DELETE"]]),
            _f("base_url", "Base URL", "text", mono=True),
            _f("path", "Path", "text", mono=True, help="Use {name} for path parameters."),
            _f("params", "Parameters", "params"),
            _f("auth_header", "Auth header", "text", mono=True, advanced=True),
            _f("auth_env", "Token env var", "text", mono=True, advanced=True, nullable=True),
            NOTES,
        ],
    },
    {
        "type": "mcp_server",
        "category": "tools",
        "title": "MCP server",
        "icon": "Plug",
        "blurb": "Every tool from an MCP server.",
        "explain": "Connects to a Model Context Protocol server and exposes all of its tools to the agent. Works with local (stdio) and remote (HTTP) servers.",
        "role": "resource",
        "kind": "tool",
        "inputs": [],
        "outputs": ATTACH_OUT,
        "fields": [
            LABEL,
            _f("server_name", "Server name", "text", mono=True),
            _f(
                "transport",
                "Transport",
                "segmented",
                options=[
                    {"value": "stdio", "label": "Local (stdio)"},
                    {"value": "streamable_http", "label": "HTTP"},
                    {"value": "sse", "label": "SSE"},
                ],
            ),
            _f("command", "Command", "text", mono=True, showIf={"transport": "stdio"}),
            _f("args", "Arguments", "tags", mono=True, showIf={"transport": "stdio"}),
            _f("url", "Server URL", "text", mono=True, showIf={"transport": ["streamable_http", "sse"]}),
            NOTES,
        ],
    },
    {
        "type": "calculator",
        "category": "tools",
        "title": "Calculator",
        "icon": "Calculator",
        "blurb": "Exact arithmetic.",
        "explain": "Safely evaluates maths expressions so the model never guesses at numbers.",
        "role": "resource",
        "kind": "tool",
        "inputs": [],
        "outputs": ATTACH_OUT,
        "fields": [LABEL, NOTES],
    },
    {
        "type": "sql_database",
        "category": "tools",
        "title": "SQL database",
        "icon": "Database",
        "blurb": "Query your database.",
        "explain": "Gives the agent a list-tables tool, a describe-table tool and a read-only query tool.",
        "tradeoff": "Keep read-only on unless you really need writes. Pair writes with a human approval step.",
        "role": "resource",
        "kind": "tool",
        "inputs": [],
        "outputs": ATTACH_OUT,
        "fields": [
            LABEL,
            _f("dialect", "Database", "segmented", options=[{"value": "postgres", "label": "Postgres"}, {"value": "mysql", "label": "MySQL"}, {"value": "sqlite", "label": "SQLite"}]),
            _f("url_env", "Connection string env var", "text", mono=True),
            _f("read_only", "Read-only", "toggle"),
            _f("max_rows", "Max rows returned", "number", min=1, max=1000, step=1),
            NOTES,
        ],
    },
    {
        "type": "custom_tool",
        "category": "tools",
        "title": "Custom tool",
        "icon": "Wrench",
        "blurb": "Describe a tool; Claude writes it.",
        "explain": "For anything without a ready-made block. Describe the tool and its inputs, and Claude writes typed Python that passes a contract test. The code is saved into your spec, so exports stay repeatable.",
        "role": "resource",
        "kind": "tool",
        "ai": True,
        "inputs": [],
        "outputs": ATTACH_OUT,
        "fields": [
            LABEL,
            _f("tool_name", "Tool name", "text", mono=True),
            _f("description", "What does it do?", "textarea", rows=3),
            _f("inputs", "Inputs", "toolinputs"),
            _f("env", "Secrets it needs (env vars)", "tags", mono=True, advanced=True),
            _f("python_deps", "Python packages", "tags", mono=True, advanced=True),
            _f("code", "Python", "code", ai="custom_tool", language="python"),
            NOTES,
        ],
    },
    # ------------------------------------------------------------------ memory
    {
        "type": "memory",
        "category": "memory",
        "title": "Memory",
        "icon": "Brain",
        "blurb": "Conversation history and long-term facts.",
        "explain": "Short-term memory keeps each conversation thread (and is what lets approvals pause and resume). Long-term memory gives attached agents remember and recall tools that persist across threads.",
        "tradeoff": "Postgres survives restarts and scales; SQLite is a single file; in-memory resets on restart.",
        "role": "resource",
        "kind": "memory",
        "max": 1,
        "inputs": [],
        "outputs": ATTACH_OUT,
        "fields": [
            LABEL,
            _f(
                "short_term",
                "Conversation store",
                "segmented",
                options=[
                    {"value": "postgres", "label": "Postgres"},
                    {"value": "sqlite", "label": "SQLite"},
                    {"value": "memory", "label": "In-memory"},
                ],
            ),
            _f("long_term", "Long-term memory for attached agents", "toggle"),
            NOTES,
        ],
    },
    # ------------------------------------------------------------------ safety
    {
        "type": "guardrail",
        "category": "safety",
        "title": "Guardrail",
        "icon": "ShieldCheck",
        "blurb": "Screen messages before they go further.",
        "explain": "Deterministic checks, no model call: redact emails, phone and card numbers, block common prompt-injection phrases, cap length, block terms.",
        "role": "flow",
        "inputs": FLOW_IN,
        "outputs": [
            {"id": "pass", "kind": "flow", "label": "Pass"},
            {"id": "blocked", "kind": "flow", "label": "Blocked"},
        ],
        "fields": [
            LABEL,
            _f("redact_pii", "Redact personal data", "toggle"),
            _f("block_prompt_injection", "Block prompt injection", "toggle"),
            _f("max_input_chars", "Max message length", "number", min=100, max=200000, step=100),
            _f("blocked_terms", "Blocked terms", "tags"),
            _f("blocked_message", "Reply when blocked", "text"),
            NOTES,
        ],
    },
    {
        "type": "approval",
        "category": "safety",
        "title": "Human approval",
        "icon": "HandPalm",
        "blurb": "Pause until a person signs off.",
        "explain": "Pauses the run and shows an approval card in the chat UI. The run resumes exactly where it stopped, even after a restart if memory is persistent.",
        "role": "flow",
        "inputs": FLOW_IN,
        "outputs": [
            {"id": "approved", "kind": "flow", "label": "Approved"},
            {"id": "rejected", "kind": "flow", "label": "Rejected"},
        ],
        "fields": [LABEL, _f("prompt", "Question for the reviewer", "text"), _f("allow_edit", "Reviewer can edit the answer", "toggle"), NOTES],
    },
]

NODE_INDEX: dict[str, dict[str, Any]] = {n["type"]: n for n in NODE_TYPES}

PROJECT_FIELDS: list[dict[str, Any]] = [
    _f("project.name", "Project name", "text", mono=True, help="Lower case, numbers and hyphens."),
    _f("project.description", "What does it do?", "textarea", rows=2),
    _f("llm.provider", "Model provider", "segmented", options=[{"value": "anthropic", "label": "Anthropic"}, {"value": "openai", "label": "OpenAI"}]),
    _f("llm.model", "Default model", "model"),
    _f("llm.effort", "Reasoning effort", "segmented", options=EFFORT_OPTIONS, nullable=True, help="Claude only. Default lets the model decide."),
    _f("llm.temperature", "Temperature", "number", min=0, max=1, step=0.05, advanced=True, help="Only sent to models that accept sampling settings."),
    _f(
        "backend.language",
        "Backend",
        "segmented",
        options=[{"value": "python", "label": "Python"}, {"value": "typescript", "label": "TypeScript", "disabled": True, "hint": "Coming soon"}],
    ),
    _f("ui.framework", "Interface", "segmented", options=[{"value": "nextjs", "label": "Next.js chat"}, {"value": "none", "label": "API only"}]),
    _f("ui.title", "Chat title", "text", showIf={"ui.framework": "nextjs"}),
    _f("ui.streaming", "Stream tokens", "toggle", showIf={"ui.framework": "nextjs"}),
    _f("ui.show_steps", "Show agent steps", "toggle", showIf={"ui.framework": "nextjs"}),
    _f("ui.feedback", "Thumbs up / down", "toggle", showIf={"ui.framework": "nextjs"}),
    _f("deploy.target", "Deployment", "segmented", options=[{"value": "docker_compose", "label": "Docker Compose"}, {"value": "none", "label": "None"}]),
    _f("deploy.backend_port", "API port", "number", min=1024, max=65535, step=1, advanced=True),
    _f("deploy.frontend_port", "UI port", "number", min=1024, max=65535, step=1, advanced=True),
    _f("observability.langsmith", "LangSmith tracing", "toggle"),
]


def catalog() -> dict[str, Any]:
    """Everything the web app needs, in one JSON document."""
    from .models import Spec

    return {
        "categories": CATEGORIES,
        "nodes": NODE_TYPES,
        "models": MODELS,
        "default_model": DEFAULT_MODEL,
        "project_fields": PROJECT_FIELDS,
        "defaults": node_defaults(),
        "spec_defaults": Spec().model_dump(mode="json", by_alias=True),
    }


def node_defaults() -> dict[str, dict[str, Any]]:
    """Default ``data`` for every node type, taken from the Pydantic models."""
    from pydantic import TypeAdapter

    from .models import Node

    adapter: TypeAdapter[Any] = TypeAdapter(Node)
    out: dict[str, dict[str, Any]] = {}
    for meta in NODE_TYPES:
        node = adapter.validate_python({"type": meta["type"], "id": "x"})
        data = node.data.model_dump(mode="json")
        data["label"] = meta["title"]
        out[meta["type"]] = data
    return out
