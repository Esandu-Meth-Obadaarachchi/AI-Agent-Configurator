# MCP server

## What
Connects to a Model Context Protocol server and exposes all of its tools to the agent. Works with local (stdio) and remote (HTTP) servers.

## Why
MCP is the open standard for tool servers. One block brings in every tool a server offers, with no glue code.

## Trade-off
You trust the server's tools. Local stdio servers need their runtime (for example Node.js) in the container.
