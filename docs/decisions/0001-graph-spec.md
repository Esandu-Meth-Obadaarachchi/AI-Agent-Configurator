# 0001: The spec is a graph (v0.2)

## Decision
Spec v0.2 stores the agent loop as `graph.nodes` and `graph.edges`, with project-wide
settings (LLM defaults, UI, deployment) outside the graph. v0.1 (the flat format in the
brief) is still accepted and upgraded on load by `configurator_spec.migrate`.

## Why
- The canvas edits nodes and edges, and LangGraph executes nodes and edges. A flat
  `agents.pattern: single | orchestrator` cannot express a router feeding two agents, a
  review loop, or an approval step in the middle of a flow.
- One shape for the CLI, the canvas and the generator means no translation layer to drift.
- Edges accept React Flow's `sourceHandle` / `targetHandle` aliases, so the web app can
  send its state almost unchanged.

## Trade-off
A graph is harder to hand-write than a flat file. The CLI `init` command and the
templates gallery cover that: nobody needs to type node ids by hand.

## Handles carry meaning
| Node | Outputs |
| --- | --- |
| Router | one `route:<id>` per branch |
| Supervisor | `delegate` (workers report back automatically), `done` |
| Review loop | `pass`, `revise` |
| Human approval | `approved`, `rejected` |
| Guardrail | `pass`, `blocked` |
| Resources (tools, knowledge, memory) | `attach`, into an agent's `tools` or a retriever's `knowledge` |

An output with no edge ends the run, so a half-built graph still compiles.
