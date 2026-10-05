# Extending the configurator

Target: add a new tool block in under an hour. The same steps work for any block.

## Example: a "Send email" tool

1. **Schema** (`packages/spec/configurator_spec/models.py`): add the data model and node.

   ```python
   class SendEmailData(_Data):
       from_env: str = Field(default="SMTP_URL", pattern=r"^[A-Z][A-Z0-9_]*$")

   class SendEmailNode(_Node):
       type: Literal["send_email"] = "send_email"
       data: SendEmailData = Field(default_factory=SendEmailData)
   ```

   Add `SendEmailNode` to the `Node` union, `"send_email"` to `NodeType` and to
   `TOOL_TYPES`.

2. **Catalog** (`catalog.py`): add an entry to `NODE_TYPES` with category `tools`,
   `role: resource`, `kind: tool`, an icon name from Phosphor, plain-language `blurb`
   and `explain`, and its inspector `fields`.

3. **Module** (`modules/tool.send_email/`):
   - `manifest.yaml`: `id: tool.send_email`, `tree: true`, `python_deps`, `env`.
   - `templates/backend/app/tools/send_email.py`: a factory returning `@tool` functions.
   - `templates/backend/tests/test_send_email.py`: offline tests.
   - `explain.md`: `## What`, `## Why`, `## Trade-off`. This feeds `DECISIONS.md`.

   Pin any new package in `modules/versions.yaml`.

4. **Wire it in** (`modules/core/templates/backend/app/tools/__init__.py.j2`): add an
   `{% elif r.type == "send_email" %}` branch that builds the tool set.

5. **Rules** (`packages/engine/configurator_engine/rules.py`): nothing needed for the
   module to resolve (`tool.<type>` is automatic). Add checks if the block has
   invalid states.

6. **Icon** (`apps/web/src/components/icons.tsx`): import the Phosphor icon and add it
   to the map.

7. **Refresh and test**:

   ```bash
   make catalog          # rebuild the canvas catalog snapshot
   make test             # schema, rules, golden files
   make golden           # only if existing renders changed on purpose
   ```

   Add the block to a blueprint (or a `ci/matrix.yaml` row) so CI renders and tests it.

## Template rules of thumb

- Templates must render lint-clean (ruff with `E,F,I,B,UP`) and type-clean (mypy).
  `make verify-examples` checks every combination with the export's own tools.
- Use the filters `pystr`, `pytext`, `py` and `pytuple` for Python literals; never
  interpolate raw strings into code.
- Files without `.j2` are copied verbatim. `__dot__name` becomes `.name`.
- Nothing in a template may depend on time, randomness or dict ordering you don't
  control: golden tests require byte-identical output.
