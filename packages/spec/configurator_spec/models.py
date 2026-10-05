"""Spec schema, version 0.2.

The spec is the single source of truth. The CLI, the canvas and the code generator
all read and write this shape. Version 0.1 (the flat format in the original brief)
is upgraded on load by ``configurator_spec.migrate``.

Design choice: the agent loop is a graph (nodes and edges), because that is what the
canvas edits and what LangGraph executes. Flat settings that apply to the whole
project (LLM defaults, UI, deployment) stay outside the graph.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SPEC_VERSION = "0.2"

# Node ids become Python identifiers and file names in the export, so keep them tight.
NODE_ID = r"^[a-z][a-z0-9_]{0,39}$"
PROJECT_NAME = r"^[a-z][a-z0-9-]{0,47}$"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


# --------------------------------------------------------------------------- project


class Project(_Model):
    name: str = Field(default="my-agent", pattern=PROJECT_NAME)
    description: str = Field(default="", max_length=500)


Provider = Literal["anthropic", "openai"]


Effort = Literal["low", "medium", "high", "xhigh", "max"]


class LLMConfig(_Model):
    provider: Provider = "anthropic"
    model: str = "claude-opus-5-5"
    # Claude Opus 5.5, Sonnet 5.5 and Fable reject sampling settings; the generated
    # LLM factory only sends temperature to models that accept it.
    temperature: float = Field(default=0.2, ge=0, le=1)
    # Reasoning effort for Claude models that support it. None = the model's default.
    effort: Effort | None = None
    max_tokens: int = Field(default=4096, ge=256, le=64000)


class Backend(_Model):
    # TypeScript is shown greyed out in the UI. The schema accepts it so specs written
    # today stay valid once the TypeScript templates land; the rules engine blocks it.
    language: Literal["python", "typescript"] = "python"


class UIConfig(_Model):
    framework: Literal["nextjs", "none"] = "nextjs"
    streaming: bool = True
    feedback: bool = True
    show_steps: bool = True
    title: str = Field(default="", max_length=80)


class DeployConfig(_Model):
    target: Literal["docker_compose", "none"] = "docker_compose"
    backend_port: int = Field(default=8000, ge=1024, le=65535)
    frontend_port: int = Field(default=3000, ge=1024, le=65535)


class Observability(_Model):
    langsmith: bool = False


class Position(_Model):
    x: float = 0
    y: float = 0


# --------------------------------------------------------------------------- node data


class _Data(_Model):
    label: str = Field(default="", max_length=60)
    notes: str = Field(default="", max_length=2000)


class InputData(_Data):
    greeting: str = Field(default="Hi! What can I help you with?", max_length=300)


class OutputData(_Data):
    pass


class AgentData(_Data):
    role: str = Field(default="A helpful assistant.", max_length=300)
    system_prompt: str = Field(default="You are a helpful assistant. Use your tools when they help.", max_length=8000)
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=1)
    effort: Effort | None = None
    max_steps: int = Field(default=8, ge=1, le=50)


class SupervisorData(_Data):
    instructions: str = Field(
        default="Break the request into steps. Delegate each step to the best worker. Finish when the answer is complete.",
        max_length=8000,
    )
    model: str | None = None
    max_rounds: int = Field(default=6, ge=1, le=30)


class PromptData(_Data):
    instructions: str = Field(default="Summarise the conversation so far in three bullet points.", max_length=8000)
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=1)


class Route(_Model):
    id: str = Field(pattern=NODE_ID)
    label: str = Field(default="", max_length=40)
    description: str = Field(default="", max_length=300)
    keywords: list[str] = Field(default_factory=list)


class RouterData(_Data):
    mode: Literal["llm", "keywords"] = "llm"
    instructions: str = Field(default="Pick the route that best matches the latest user message.", max_length=2000)
    routes: list[Route] = Field(
        default_factory=lambda: [
            Route(id="a", label="Route A", description="First kind of request"),
            Route(id="b", label="Route B", description="Everything else"),
        ]
    )
    model: str | None = None

    @field_validator("routes")
    @classmethod
    def _unique_routes(cls, routes: list[Route]) -> list[Route]:
        ids = [r.id for r in routes]
        if len(ids) != len(set(ids)):
            raise ValueError("route ids must be unique")
        return routes


class CriticData(_Data):
    criteria: str = Field(
        default="The answer is correct, complete, cites sources where relevant and directly answers the question.",
        max_length=4000,
    )
    max_iterations: int = Field(default=2, ge=1, le=10)
    model: str | None = None


class ApprovalData(_Data):
    prompt: str = Field(default="Review this response before it is sent.", max_length=500)
    allow_edit: bool = True


class GuardrailData(_Data):
    redact_pii: bool = True
    block_prompt_injection: bool = True
    max_input_chars: int = Field(default=8000, ge=100, le=200000)
    blocked_terms: list[str] = Field(default_factory=list)
    blocked_message: str = Field(default="Sorry, I can't help with that request.", max_length=500)


class RetrieverData(_Data):
    top_k: int | None = Field(default=None, ge=1, le=50)


class CustomStepData(_Data):
    description: str = Field(default="Describe what this step does to the conversation state.", max_length=2000)
    code: str | None = Field(default=None, max_length=20000)
    generated_by: Literal["claude", "user"] | None = None


class KnowledgeData(_Data):
    description: str = Field(default="Company documents", max_length=300)
    sources: list[Literal["pdf", "markdown", "text", "html"]] = Field(default_factory=lambda: ["pdf", "markdown"])
    chunker: Literal["recursive", "fixed"] = "recursive"
    chunk_size: int = Field(default=800, ge=100, le=8000)
    overlap: int = Field(default=100, ge=0, le=2000)
    embedding: Literal["openai_small", "openai_large", "local_bge_small"] = "openai_small"
    vector_store: Literal["pgvector", "chroma"] = "pgvector"
    retrieval: Literal["dense", "hybrid"] = "hybrid"
    top_k: int = Field(default=6, ge=1, le=50)
    reranker: Literal["none", "cross_encoder", "cohere"] = "none"

    @model_validator(mode="after")
    def _overlap_lt_size(self) -> KnowledgeData:
        if self.overlap >= self.chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")
        return self


class MemoryData(_Data):
    short_term: Literal["memory", "sqlite", "postgres"] = "postgres"
    long_term: bool = False


class WebSearchData(_Data):
    provider: Literal["tavily"] = "tavily"
    max_results: int = Field(default=5, ge=1, le=20)


class WebFetchData(_Data):
    max_chars: int = Field(default=12000, ge=500, le=200000)


class HttpParam(_Model):
    name: str = Field(pattern=NODE_ID)
    description: str = Field(default="", max_length=200)
    location: Literal["query", "path", "body"] = "query"


class HttpApiData(_Data):
    tool_name: str = Field(default="call_api", pattern=NODE_ID)
    description: str = Field(default="Call the internal API.", max_length=500)
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = "GET"
    base_url: str = Field(default="https://api.example.com", max_length=300)
    path: str = Field(default="/items/{item_id}", max_length=300)
    params: list[HttpParam] = Field(default_factory=lambda: [HttpParam(name="item_id", location="path")])
    auth_header: str = Field(default="Authorization", max_length=60)
    auth_env: str | None = Field(default="API_TOKEN", pattern=r"^[A-Z][A-Z0-9_]*$")


class McpServerData(_Data):
    server_name: str = Field(default="filesystem", pattern=NODE_ID)
    transport: Literal["stdio", "streamable_http", "sse"] = "stdio"
    command: str = Field(default="npx", max_length=200)
    args: list[str] = Field(default_factory=lambda: ["-y", "@modelcontextprotocol/server-filesystem", "/data"])
    url: str = Field(default="", max_length=300)


class CalculatorData(_Data):
    pass


class SqlDatabaseData(_Data):
    dialect: Literal["postgres", "sqlite", "mysql"] = "postgres"
    url_env: str = Field(default="SQL_TOOL_DATABASE_URL", pattern=r"^[A-Z][A-Z0-9_]*$")
    read_only: bool = True
    max_rows: int = Field(default=50, ge=1, le=1000)


class ToolInput(_Model):
    name: str = Field(pattern=NODE_ID)
    type: Literal["str", "int", "float", "bool"] = "str"
    description: str = Field(default="", max_length=200)


class CustomToolData(_Data):
    tool_name: str = Field(default="my_tool", pattern=NODE_ID)
    description: str = Field(default="Describe what the tool does, in plain words.", max_length=2000)
    inputs: list[ToolInput] = Field(default_factory=lambda: [ToolInput(name="query", description="What to look up")])
    env: list[str] = Field(default_factory=list)
    python_deps: list[str] = Field(default_factory=list)
    code: str | None = Field(default=None, max_length=20000)
    generated_by: Literal["claude", "user"] | None = None


# --------------------------------------------------------------------------- nodes


class _Node(_Model):
    id: str = Field(pattern=NODE_ID)
    position: Position = Field(default_factory=Position)


class InputNode(_Node):
    type: Literal["input"] = "input"
    data: InputData = Field(default_factory=InputData)


class OutputNode(_Node):
    type: Literal["output"] = "output"
    data: OutputData = Field(default_factory=OutputData)


class AgentNode(_Node):
    type: Literal["agent"] = "agent"
    data: AgentData = Field(default_factory=AgentData)


class SupervisorNode(_Node):
    type: Literal["supervisor"] = "supervisor"
    data: SupervisorData = Field(default_factory=SupervisorData)


class PromptNode(_Node):
    type: Literal["prompt"] = "prompt"
    data: PromptData = Field(default_factory=PromptData)


class RouterNode(_Node):
    type: Literal["router"] = "router"
    data: RouterData = Field(default_factory=RouterData)


class CriticNode(_Node):
    type: Literal["critic"] = "critic"
    data: CriticData = Field(default_factory=CriticData)


class ApprovalNode(_Node):
    type: Literal["approval"] = "approval"
    data: ApprovalData = Field(default_factory=ApprovalData)


class GuardrailNode(_Node):
    type: Literal["guardrail"] = "guardrail"
    data: GuardrailData = Field(default_factory=GuardrailData)


class RetrieverNode(_Node):
    type: Literal["retriever"] = "retriever"
    data: RetrieverData = Field(default_factory=RetrieverData)


class CustomStepNode(_Node):
    type: Literal["custom_step"] = "custom_step"
    data: CustomStepData = Field(default_factory=CustomStepData)


class KnowledgeNode(_Node):
    type: Literal["knowledge"] = "knowledge"
    data: KnowledgeData = Field(default_factory=KnowledgeData)


class MemoryNode(_Node):
    type: Literal["memory"] = "memory"
    data: MemoryData = Field(default_factory=MemoryData)


class WebSearchNode(_Node):
    type: Literal["web_search"] = "web_search"
    data: WebSearchData = Field(default_factory=WebSearchData)


class WebFetchNode(_Node):
    type: Literal["web_fetch"] = "web_fetch"
    data: WebFetchData = Field(default_factory=WebFetchData)


class HttpApiNode(_Node):
    type: Literal["http_api"] = "http_api"
    data: HttpApiData = Field(default_factory=HttpApiData)


class McpServerNode(_Node):
    type: Literal["mcp_server"] = "mcp_server"
    data: McpServerData = Field(default_factory=McpServerData)


class CalculatorNode(_Node):
    type: Literal["calculator"] = "calculator"
    data: CalculatorData = Field(default_factory=CalculatorData)


class SqlDatabaseNode(_Node):
    type: Literal["sql_database"] = "sql_database"
    data: SqlDatabaseData = Field(default_factory=SqlDatabaseData)


class CustomToolNode(_Node):
    type: Literal["custom_tool"] = "custom_tool"
    data: CustomToolData = Field(default_factory=CustomToolData)


Node = Annotated[
    InputNode
    | OutputNode
    | AgentNode
    | SupervisorNode
    | PromptNode
    | RouterNode
    | CriticNode
    | ApprovalNode
    | GuardrailNode
    | RetrieverNode
    | CustomStepNode
    | KnowledgeNode
    | MemoryNode
    | WebSearchNode
    | WebFetchNode
    | HttpApiNode
    | McpServerNode
    | CalculatorNode
    | SqlDatabaseNode
    | CustomToolNode,
    Field(discriminator="type"),
]

NodeType = Literal[
    "input",
    "output",
    "agent",
    "supervisor",
    "prompt",
    "router",
    "critic",
    "approval",
    "guardrail",
    "retriever",
    "custom_step",
    "knowledge",
    "memory",
    "web_search",
    "web_fetch",
    "http_api",
    "mcp_server",
    "calculator",
    "sql_database",
    "custom_tool",
]

# Flow nodes take part in the control flow. Resource nodes attach to flow nodes.
FLOW_TYPES: frozenset[str] = frozenset(
    {"input", "output", "agent", "supervisor", "prompt", "router", "critic", "approval", "guardrail", "retriever", "custom_step"}
)
TOOL_TYPES: frozenset[str] = frozenset(
    {"web_search", "web_fetch", "http_api", "mcp_server", "calculator", "sql_database", "custom_tool"}
)
RESOURCE_TYPES: frozenset[str] = TOOL_TYPES | {"knowledge", "memory"}


class Edge(_Model):
    id: str = Field(min_length=1, max_length=120)
    source: str
    target: str
    source_handle: str | None = Field(default=None, alias="sourceHandle")
    target_handle: str | None = Field(default=None, alias="targetHandle")


class Graph(_Model):
    nodes: list[Node] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)

    @model_validator(mode="after")
    def _references(self) -> Graph:
        ids = [n.id for n in self.nodes]
        dupes = {i for i in ids if ids.count(i) > 1}
        if dupes:
            raise ValueError(f"duplicate node ids: {', '.join(sorted(dupes))}")
        known = set(ids)
        for e in self.edges:
            for end in (e.source, e.target):
                if end not in known:
                    raise ValueError(f"edge {e.id} points at unknown node '{end}'")
        return self

    def node(self, node_id: str) -> Node:
        for n in self.nodes:
            if n.id == node_id:
                return n
        raise KeyError(node_id)


class Spec(_Model):
    spec_version: Literal["0.2"] = SPEC_VERSION
    project: Project = Field(default_factory=Project)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    backend: Backend = Field(default_factory=Backend)
    graph: Graph = Field(default_factory=Graph)
    ui: UIConfig = Field(default_factory=UIConfig)
    deploy: DeployConfig = Field(default_factory=DeployConfig)
    observability: Observability = Field(default_factory=Observability)
