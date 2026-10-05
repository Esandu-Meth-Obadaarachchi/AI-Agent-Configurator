# 0003: LangGraph, create_agent, and one shared conversation

## Decision
- The loop is a LangGraph `StateGraph` built from the canvas. Agents are LangChain
  `create_agent` sub-graphs invoked inside a node.
- Only an agent's final answer is written to the shared conversation, as
  `AIMessage(name=<block id>)`. Internal notes (supervisor tasks, reviewer feedback,
  approval rejections) are `HumanMessage(name=<block id>)`.
- Each step sees the conversation through `messages.for_node()`: its own replies stay
  assistant turns, everyone else's become labelled notes on the user side, and the list
  never ends on an assistant turn.

## Why
- LangGraph gives checkpointing, `interrupt()` for approvals, loops and parallel
  branches. Re-implementing those by hand is where agent apps usually break.
- Keeping tool calls out of the shared history means one agent never sees `tool_use`
  blocks for tools it doesn't have, which Claude rejects.
- Current Claude models reject assistant prefill (a conversation ending on an assistant
  turn), which is exactly what naive multi-agent handoffs produce.

## Trade-off
Agents don't see each other's tool traces, only conclusions. That is usually what you
want; if not, a custom step can add more context.
