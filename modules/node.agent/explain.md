# Agent

## What
Runs a tool-calling loop: think, call a tool, read the result, repeat, answer. Attach tools, knowledge or memory underneath it.

## Why
Most tasks need a model that can look things up and act, not just talk. A tool-calling loop is the standard, well-understood way to do that.

## Trade-off
More tools give more reach but more chances to pick the wrong one. Keep each agent focused.
