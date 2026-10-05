# SQL database

## What
Gives the agent a list-tables tool, a describe-table tool and a read-only query tool.

## Why
Most business questions live in a database. Schema exploration plus guarded queries let the agent answer them directly.

## Trade-off
Keep read-only on unless you really need writes. Pair writes with a human approval step.
