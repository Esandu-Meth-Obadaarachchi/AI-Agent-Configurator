# HTTP API

## What
Turns a single REST endpoint into a tool. Parameters become tool inputs the model fills in.

## Why
Most real agents need your own systems. One endpoint per tool keeps each tool's purpose obvious to the model.

## Trade-off
The model fills parameters from the conversation, so validate inputs on the API side too.
