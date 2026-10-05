# Custom step

## What
Anything the toolkit lacks. Describe it and Claude writes the function, or write it yourself. It lands in backend/app/custom/nodes.py.

## Why
No toolkit covers everything. A typed extension point keeps your logic in a file that regeneration never touches.

## Trade-off
Your code is your responsibility: the generated tests only check it imports and runs.
