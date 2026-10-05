# 0002: Templates write the code; Claude fills gaps only

## Decision
All predictable code comes from Jinja2 templates selected by a rules engine. Claude is
called in three places only: text to spec, the fallback router for custom blocks, and
prompt drafting.

## Why
- Repeatable: the same spec renders the same bytes (golden tests enforce it).
- Tested: each module combination in `ci/matrix.yaml` is linted, type-checked and tested.
- Free: a typical export costs zero tokens.
- Reviewable: a template change is a diff, not a new roll of the dice.

## Trade-off
Templates can only express what someone wrote down. New capabilities need a module,
which is why the fallback router exists and why Claude-written code is saved into the
spec instead of being regenerated each time.
