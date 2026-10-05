# 0006: Verification and the sandbox

## Decision
- `configurator verify` runs the export's own ruff, mypy and tests, plus ESLint and tsc
  for the frontend, and optionally boots Docker Compose and waits for the health check.
- `--docker` (or auto when the daemon is up) runs backend checks in a throwaway
  `python:3.12-slim` container. `--local` runs them on the host.
- Claude-written code is only ever **executed** in a container with `--network none`,
  512 MB and one CPU. Without Docker it is checked statically (parse, contract shape,
  no `subprocess`/`eval`/`exec`) and labelled "static check" in the UI and report.

## Why
Template output is code we wrote and test in CI, so running it locally is fine.
Model-written code is untrusted until reviewed, so it never runs on the host.

## Trade-off
Without Docker the contract test is skipped. The UI says so plainly rather than
pretending the code was tested.
