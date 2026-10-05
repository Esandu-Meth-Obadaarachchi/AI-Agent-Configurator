# Core backend

## What
A FastAPI service that runs your agent loop as a LangGraph state graph and streams every step to the browser over Server-Sent Events.

## Why
LangGraph gives durable state, interrupts for human approval, loops and parallel branches as first-class ideas. FastAPI is the most familiar Python web framework, with typed request models and async streaming.

## Trade-off
LangGraph adds a dependency and a learning curve compared with a hand-written loop. In return you get checkpointing, resumable runs and a graph you can inspect, which a hand-written loop has to rebuild.
