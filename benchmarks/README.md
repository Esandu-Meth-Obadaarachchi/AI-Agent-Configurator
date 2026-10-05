# Benchmark: Agent Configurator vs Claude Code alone

Question: for the same app, how do time, tokens, cost and pass rate compare between
asking Claude Code for it from a prompt and generating it here?

## Method

- Apps: the three reference exports (`docs-qa`, `support-bot`, `research-team`).
- Prompts for Claude Code are in `prompts/`, written from each blueprint's description
  with the same feature list (no hints about file layout).
- Pass = the project's own `ruff`, `mypy` and tests pass, and `docker compose up` reaches
  a healthy API. Measured with `configurator verify --boot`.
- 10 runs per app per method. Record wall time, input/output tokens and cost.

## Run

```bash
python benchmarks/run_configurator.py        # times generate + verify for each app
```

The Claude Code side is run by hand with each prompt and timed the same way; record
results in `results.csv`.

## Results

Not run yet.
