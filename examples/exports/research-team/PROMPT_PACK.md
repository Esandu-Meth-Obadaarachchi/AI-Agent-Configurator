# Prompt pack: research-team

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
    "name": "research-team",
    "description": "A supervisor runs a researcher, an analyst and a writer, and a reviewer checks the report."
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
          "greeting": "What should the team research?"
        }
      },
      {
        "id": "lead",
        "position": {
          "x": 250.0,
          "y": 0.0
        },
        "type": "supervisor",
        "data": {
          "label": "Research lead",
          "notes": "",
          "instructions": "You lead a small research team. Plan the work, then delegate one step at a time:\n- researcher: finds and reads sources on the web\n- analyst: checks numbers and does calculations\n- writer: drafts the final report\nFinish once the writer has produced a report that answers the question.",
          "model": null,
          "max_rounds": 8
        }
      },
      {
        "id": "researcher",
        "position": {
          "x": 500.0,
          "y": -185.0
        },
        "type": "agent",
        "data": {
          "label": "Researcher",
          "notes": "",
          "role": "Finds and reads sources on the web.",
          "system_prompt": "Search the web, open the most relevant pages and report key facts with their URLs. Prefer primary sources.",
          "model": null,
          "temperature": null,
          "effort": null,
          "max_steps": 8
        }
      },
      {
        "id": "analyst",
        "position": {
          "x": 500.0,
          "y": 0.0
        },
        "type": "agent",
        "data": {
          "label": "Analyst",
          "notes": "",
          "role": "Checks numbers and does calculations.",
          "system_prompt": "Verify every number the team relies on. Use the calculator for arithmetic. Flag anything that doesn't add up.",
          "model": null,
          "temperature": null,
          "effort": null,
          "max_steps": 8
        }
      },
      {
        "id": "writer",
        "position": {
          "x": 500.0,
          "y": 185.0
        },
        "type": "agent",
        "data": {
          "label": "Writer",
          "notes": "",
          "role": "Writes the final report.",
          "system_prompt": "Write a clear, well-structured report from the team's findings. Use headings and cite sources inline.",
          "model": null,
          "temperature": null,
          "effort": null,
          "max_steps": 8
        }
      },
      {
        "id": "review",
        "position": {
          "x": 750.0,
          "y": 0.0
        },
        "type": "critic",
        "data": {
          "label": "Fact check",
          "notes": "",
          "criteria": "Every claim is supported by a cited source, numbers are consistent, and the report answers the original question.",
          "max_iterations": 2,
          "model": null
        }
      },
      {
        "id": "reply",
        "position": {
          "x": 1000.0,
          "y": 0.0
        },
        "type": "output",
        "data": {
          "label": "Reply",
          "notes": ""
        }
      },
      {
        "id": "search",
        "position": {
          "x": 500.0,
          "y": 485.0
        },
        "type": "web_search",
        "data": {
          "label": "Web search",
          "notes": "",
          "provider": "tavily",
          "max_results": 5
        }
      },
      {
        "id": "read",
        "position": {
          "x": 690.0,
          "y": 485.0
        },
        "type": "web_fetch",
        "data": {
          "label": "Read web page",
          "notes": "",
          "max_chars": 12000
        }
      },
      {
        "id": "calc",
        "position": {
          "x": 880.0,
          "y": 485.0
        },
        "type": "calculator",
        "data": {
          "label": "Calculator",
          "notes": ""
        }
      }
    ],
    "edges": [
      {
        "id": "e-start-out-lead",
        "source": "start",
        "target": "lead",
        "sourceHandle": "out",
        "targetHandle": "in"
      },
      {
        "id": "e-lead-delegate-researcher",
        "source": "lead",
        "target": "researcher",
        "sourceHandle": "delegate",
        "targetHandle": "in"
      },
      {
        "id": "e-lead-delegate-analyst",
        "source": "lead",
        "target": "analyst",
        "sourceHandle": "delegate",
        "targetHandle": "in"
      },
      {
        "id": "e-lead-delegate-writer",
        "source": "lead",
        "target": "writer",
        "sourceHandle": "delegate",
        "targetHandle": "in"
      },
      {
        "id": "e-lead-done-review",
        "source": "lead",
        "target": "review",
        "sourceHandle": "done",
        "targetHandle": "in"
      },
      {
        "id": "e-review-pass-reply",
        "source": "review",
        "target": "reply",
        "sourceHandle": "pass",
        "targetHandle": "in"
      },
      {
        "id": "e-review-revise-lead",
        "source": "review",
        "target": "lead",
        "sourceHandle": "revise",
        "targetHandle": "in"
      },
      {
        "id": "a-search-researcher",
        "source": "search",
        "target": "researcher",
        "sourceHandle": "attach",
        "targetHandle": "tools"
      },
      {
        "id": "a-read-researcher",
        "source": "read",
        "target": "researcher",
        "sourceHandle": "attach",
        "targetHandle": "tools"
      },
      {
        "id": "a-calc-analyst",
        "source": "calc",
        "target": "analyst",
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

- `lead` (supervisor) **Research lead**
  - Done → review
  - workers: researcher, analyst, writer
- `researcher` (agent) **Researcher**
  - reports back to `lead`
  - tools from: search, read
- `analyst` (agent) **Analyst**
  - reports back to `lead`
  - tools from: calc
- `writer` (agent) **Writer**
  - reports back to `lead`
- `review` (critic) **Fact check**
  - Pass → reply
  - Revise → lead

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
backend/app/nodes/critic.py
backend/app/nodes/supervisor.py
backend/app/persistence.py
backend/app/prompts.py
backend/app/state.py
backend/app/streaming.py
backend/app/tools/__init__.py
backend/app/tools/calculator.py
backend/app/tools/web_fetch.py
backend/app/tools/web_search.py
backend/data/.gitkeep
backend/pyproject.toml
backend/requirements.txt
backend/tests/conftest.py
backend/tests/test_api.py
backend/tests/test_calculator.py
backend/tests/test_graph.py
backend/tests/test_messages.py
backend/tests/test_web_fetch.py
backend/tests/test_web_search.py
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
