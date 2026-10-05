# Supervisor

## What
Reads the conversation, picks the next worker, and repeats until the job is done. Workers you connect from 'Delegate' report back automatically.

## Why
Splitting work between focused workers keeps each prompt short and each tool list small, which makes every worker more reliable than one agent doing everything.

## Trade-off
Flexible and good at open-ended tasks, but every round costs a model call. Cap the rounds.
