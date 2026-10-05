# Prompt pack: support-bot

Paste this file into Claude Code (or any coding agent) when you want to extend the
project. It explains how the code is laid out, where changes belong, and what is
still open.

## Ground rules for the coding agent

1. This project was generated from `spec.json`. Treat generated files as read-only.
   Put new logic in `backend/app/custom/` (tools.py, nodes.py, prompts.py).
2. Keep the conversation contract: steps append `AIMessage(name=<node id>)` replies;
   internal notes are `HumanMessage(name=<node id>)`. See `backend/app/messages.py`.
3. Never put secrets in code. Add new variables to `.env.example` and `app/config.py`.
4. Run `make test` and `make lint` before you finish. Tests run offline with
   `LLM_PROVIDER=fake`.

## The spec

```json
{
  "spec_version": "0.2",
  "project": {
    "name": "support-bot",
    "description": "Triage support requests to billing or technical agents. Refunds need a human sign-off."
  },
  "llm": {
    "provider": "anthropic",
    "model": "claude-opus-5-5",
    "temperature": 0.2,
    "effort": null,
    "max_tokens": 4096
  },
  "backend": {
    "language": "python"
  },
  "graph": {
    "nodes": [
      {
        "id": "start",
        "position": {
          "x": 0.0,
          "y": 0.0
        },
        "type": "input",
        "data": {
          "label": "Chat input",
          "notes": "",
          "greeting": "Hi! How can we help today?"
        }
      },
      {
        "id": "guard",
        "position": {
          "x": 250.0,
          "y": 0.0
        },
        "type": "guardrail",
        "data": {
          "label": "Screen message",
          "notes": "",
          "redact_pii": true,
          "block_prompt_injection": true,
          "max_input_chars": 8000,
          "blocked_terms": [],
          "blocked_message": "Sorry, I can't help with that request."
        }
      },
      {
        "id": "triage",
        "position": {
          "x": 500.0,
          "y": 0.0
        },
        "type": "router",
        "data": {
          "label": "Triage",
          "notes": "",
          "mode": "llm",
          "instructions": "Pick the route that best matches the latest user message.",
          "routes": [
            {
              "id": "billing",
              "label": "Billing",
              "description": "Payments, invoices, refunds, plans",
              "keywords": [
                "refund",
                "invoice",
                "charge",
                "billing",
                "plan"
              ]
            },
            {
              "id": "technical",
              "label": "Technical",
              "description": "Bugs, errors, how-to questions about the product",
              "keywords": [
                "error",
                "bug",
                "crash",
                "how do i"
              ]
            },
            {
              "id": "other",
              "label": "Other",
              "description": "Greetings and anything else",
              "keywords": []
            }
          ],
          "model": null
        }
      },
      {
        "id": "billing",
        "position": {
          "x": 750.0,
          "y": -185.0
        },
        "type": "agent",
        "data": {
          "label": "Billing agent",
          "notes": "",
          "role": "Handles payments, invoices and refunds.",
          "system_prompt": "You handle billing questions. Look up the order before discussing it. Offer refunds only when the order qualifies, and explain why.",
          "model": null,
          "temperature": null,
          "effort": null,
          "max_steps": 8
        }
      },
      {
        "id": "tech",
        "position": {
          "x": 750.0,
          "y": 0.0
        },
        "type": "agent",
        "data": {
          "label": "Technical agent",
          "notes": "",
          "role": "Solves product problems using the help centre.",
          "system_prompt": "You solve technical problems. Search the help centre first, then give numbered steps. Ask for the error message if you need it.",
          "model": null,
          "temperature": null,
          "effort": null,
          "max_steps": 8
        }
      },
      {
        "id": "smalltalk",
        "position": {
          "x": 750.0,
          "y": 185.0
        },
        "type": "prompt",
        "data": {
          "label": "Friendly reply",
          "notes": "",
          "instructions": "Reply briefly and warmly, then ask how you can help with billing or a technical issue.",
          "model": null,
          "temperature": null
        }
      },
      {
        "id": "approve",
        "position": {
          "x": 1000.0,
          "y": 0.0
        },
        "type": "approval",
        "data": {
          "label": "Approve refund",
          "notes": "",
          "prompt": "A billing reply is ready. Approve it before it reaches the customer?",
          "allow_edit": true
        }
      },
      {
        "id": "reply",
        "position": {
          "x": 1250.0,
          "y": 0.0
        },
        "type": "output",
        "data": {
          "label": "Reply",
          "notes": ""
        }
      },
      {
        "id": "orders",
        "position": {
          "x": 750.0,
          "y": 485.0
        },
        "type": "http_api",
        "data": {
          "label": "Orders API",
          "notes": "",
          "tool_name": "get_order",
          "description": "Look up an order by its id: status, amount and refund eligibility.",
          "method": "GET",
          "base_url": "https://api.example.com",
          "path": "/orders/{order_id}",
          "params": [
            {
              "name": "order_id",
              "description": "The order id, e.g. ORD-1234",
              "location": "path"
            }
          ],
          "auth_header": "Authorization",
          "auth_env": "API_TOKEN"
        }
      },
      {
        "id": "helpdocs",
        "position": {
          "x": 1130.0,
          "y": 485.0
        },
        "type": "knowledge",
        "data": {
          "label": "Help centre",
          "notes": "",
          "description": "Product help-centre articles",
          "sources": [
            "pdf",
            "markdown"
          ],
          "chunker": "recursive",
          "chunk_size": 800,
          "overlap": 100,
          "embedding": "local_bge_small",
          "vector_store": "pgvector",
          "retrieval": "hybrid",
          "top_k": 6,
          "reranker": "none"
        }
      },
      {
        "id": "memory",
        "position": {
          "x": 940.0,
          "y": 485.0
        },
        "type": "memory",
        "data": {
          "label": "Memory",
          "notes": "",
          "short_term": "postgres",
          "long_term": false
        }
      }
    ],
    "edges": [
      {
        "id": "e-start-out-guard",
        "source": "start",
        "target": "guard",
        "sourceHandle": "out",
        "targetHandle": "in"
      },
      {
        "id": "e-guard-pass-triage",
        "source": "guard",
        "target": "triage",
        "sourceHandle": "pass",
        "targetHandle": "in"
      },
      {
        "id": "e-guard-blocked-reply",
        "source": "guard",
        "target": "reply",
        "sourceHandle": "blocked",
        "targetHandle": "in"
      },
      {
        "id": "e-triage-route:billing-billing",
        "source": "triage",
        "target": "billing",
        "sourceHandle": "route:billing",
        "targetHandle": "in"
      },
      {
        "id": "e-triage-route:technical-tech",
        "source": "triage",
        "target": "tech",
        "sourceHandle": "route:technical",
        "targetHandle": "in"
      },
      {
        "id": "e-triage-route:other-smalltalk",
        "source": "triage",
        "target": "smalltalk",
        "sourceHandle": "route:other",
        "targetHandle": "in"
      },
      {
        "id": "e-billing-out-approve",
        "source": "billing",
        "target": "approve",
        "sourceHandle": "out",
        "targetHandle": "in"
      },
      {
        "id": "e-approve-approved-reply",
        "source": "approve",
        "target": "reply",
        "sourceHandle": "approved",
        "targetHandle": "in"
      },
      {
        "id": "e-approve-rejected-billing",
        "source": "approve",
        "target": "billing",
        "sourceHandle": "rejected",
        "targetHandle": "in"
      },
      {
        "id": "e-tech-out-reply",
        "source": "tech",
        "target": "reply",
        "sourceHandle": "out",
        "targetHandle": "in"
      },
      {
        "id": "e-smalltalk-out-reply",
        "source": "smalltalk",
        "target": "reply",
        "sourceHandle": "out",
        "targetHandle": "in"
      },
      {
        "id": "a-orders-billing",
        "source": "orders",
        "target": "billing",
        "sourceHandle": "attach",
        "targetHandle": "tools"
      },
      {
        "id": "a-helpdocs-tech",
        "source": "helpdocs",
        "target": "tech",
        "sourceHandle": "attach",
        "targetHandle": "tools"
      },
      {
        "id": "a-memory-billing",
        "source": "memory",
        "target": "billing",
        "sourceHandle": "attach",
        "targetHandle": "tools"
      }
    ]
  },
  "ui": {
    "framework": "nextjs",
    "streaming": true,
    "feedback": true,
    "show_steps": true,
    "title": ""
  },
  "deploy": {
    "target": "docker_compose",
    "backend_port": 8000,
    "frontend_port": 3000
  },
  "observability": {
    "langsmith": false
  }
}
```

## The graph

- `guard` (guardrail) **Screen message**
  - Pass → triage
  - Blocked → reply
- `triage` (router) **Triage**
  - Billing → billing
  - Technical → tech
  - Other → smalltalk
- `billing` (agent) **Billing agent**
  - then: approve
  - tools from: orders
- `tech` (agent) **Technical agent**
  - then: reply
  - tools from: helpdocs
- `smalltalk` (prompt) **Friendly reply**
  - then: reply
- `approve` (approval) **Approve refund**
  - Approved → reply
  - Rejected → billing

## File map

```
.env.example
.gitignore
DECISIONS.md
Makefile
PROMPT_PACK.md
README.md
backend/.dockerignore
backend/Dockerfile
backend/app/__init__.py
backend/app/config.py
backend/app/custom/__init__.py
backend/app/custom/nodes.py
backend/app/custom/prompts.py
backend/app/custom/tools.py
backend/app/demo.py
backend/app/events.py
backend/app/graph.py
backend/app/llm.py
backend/app/main.py
backend/app/messages.py
backend/app/meta.py
backend/app/nodes/__init__.py
backend/app/nodes/agent.py
backend/app/nodes/approval.py
backend/app/nodes/guardrail.py
backend/app/nodes/prompt_step.py
backend/app/nodes/router.py
backend/app/persistence.py
backend/app/prompts.py
backend/app/rag/__init__.py
backend/app/rag/chunking.py
backend/app/rag/embeddings.py
backend/app/rag/ingest.py
backend/app/rag/loaders.py
backend/app/rag/registry.py
backend/app/rag/retriever.py
backend/app/rag/store_pgvector.py
backend/app/rag/stores.py
backend/app/state.py
backend/app/streaming.py
backend/app/tools/__init__.py
backend/app/tools/http_orders.py
backend/app/tools/knowledge.py
backend/data/.gitkeep
backend/data/docs/getting-started.md
backend/pyproject.toml
backend/requirements.txt
backend/tests/conftest.py
backend/tests/test_api.py
backend/tests/test_graph.py
backend/tests/test_guardrail.py
backend/tests/test_messages.py
backend/tests/test_rag.py
backend/tests/test_router.py
docker-compose.yml
frontend/.dockerignore
frontend/Dockerfile
frontend/eslint.config.mjs
frontend/next-env.d.ts
frontend/next.config.ts
frontend/package.json
frontend/postcss.config.mjs
frontend/public/favicon.svg
frontend/src/app/api/[...path]/route.ts
frontend/src/app/globals.css
frontend/src/app/layout.tsx
frontend/src/app/page.tsx
frontend/src/components/activity.tsx
frontend/src/components/approval-card.tsx
frontend/src/components/chat.tsx
frontend/src/components/composer.tsx
frontend/src/components/reply.tsx
frontend/src/lib/api.ts
frontend/src/lib/turns.ts
frontend/src/lib/types.ts
frontend/tsconfig.json
spec.json
```

Key files:

- `backend/app/graph.py`: the LangGraph wiring (generated).
- `backend/app/nodes/`: one factory per kind of step (generated).
- `backend/app/tools/__init__.py`: which tools each canvas block provides (generated).
- `backend/app/streaming.py`: how runs become Server-Sent Events for the UI.
- `backend/app/custom/`: your code. Never overwritten.

## Extension points

| Task | Where | Contract |
| --- | --- | --- |
| New tool | `backend/app/custom/tools.py` | A function decorated with `@tool`, typed parameters, returns `str`. Add it to a tool set in `app/tools/__init__.py`, or ask for a Custom tool block in the spec. |
| New step | `backend/app/custom/nodes.py` | `def <node_id>(state: dict[str, Any]) -> dict[str, Any]`, returning only the keys to change. |
| Prompt change | `backend/app/custom/prompts.py` | `OVERRIDES[node_id] = "new instructions"` |

## Open items

None. Every block was produced by a template or already has code.
