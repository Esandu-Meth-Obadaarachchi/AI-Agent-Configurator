# Next.js chat UI

## What
A streaming chat interface with a live activity timeline (which step is running, which tools were called), an approval card for paused runs, thumbs up and down, and document upload when the project has a knowledge base.

## Why
Next.js with the App Router is the most common React stack for production apps. A server-side proxy route keeps the API address out of the browser and works the same locally and in Docker.

## Trade-off
A second runtime (Node.js) to build and deploy. If you only need an API, switch the interface to "API only".
