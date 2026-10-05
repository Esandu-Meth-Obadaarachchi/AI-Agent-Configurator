# Docker Compose

## What
One command, `docker compose up --build`, starts the API, the chat UI and any database the project needs, with health checks.

## Why
The same setup runs on a laptop and on a small VPS, and a stranger can boot the project without installing Python or Node.

## Trade-off
Compose is single-host. For autoscaling, move the same images to a container platform later.
