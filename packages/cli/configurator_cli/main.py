"""configurator: the command-line interface.

    configurator init                     pick a blueprint and options, write spec.json
    configurator templates                list the starter blueprints
    configurator validate spec.json       schema and rules check
    configurator explain spec.json        each choice and its trade-off
    configurator generate spec.json -o ./out
    configurator verify ./out             lint, type-check, test (and optionally boot)
    configurator from-text "describe your app" -o spec.json
    configurator serve                    run the web canvas API
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from configurator_engine.catalogue import blueprint_index, load_blueprint
from configurator_engine.compiler import simulate
from configurator_engine.generate import GenerationError, generate, to_zip, write
from configurator_engine.registry import load_registry
from configurator_engine.rules import Resolution, resolve
from configurator_spec import MigrationError, Spec, dump_spec, json_schema, load_spec
from configurator_spec.catalog import DEFAULT_MODEL, MODELS, NODE_INDEX

app = typer.Typer(no_args_is_help=True, add_completion=False, help="Turn an agent design into a working project.")
console = Console()
err = Console(stderr=True)

LEVEL_STYLE = {"error": "bold red", "warning": "yellow", "info": "cyan"}


def _load(path: Path) -> Spec:
    try:
        return load_spec(path)
    except FileNotFoundError:
        err.print(f"[red]No such file:[/] {path}")
    except json.JSONDecodeError as exc:
        err.print(f"[red]{path} is not valid JSON:[/] {exc}")
    except (ValidationError, MigrationError) as exc:
        err.print(f"[red]{path} doesn't match the spec schema:[/]\n{exc}")
    raise typer.Exit(2)


def _print_issues(res: Resolution) -> None:
    if not res.issues:
        console.print("[green]No issues.[/]")
        return
    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    table.add_column("Level")
    table.add_column("Block")
    table.add_column("Issue")
    for i in res.issues:
        table.add_row(f"[{LEVEL_STYLE[i.level]}]{i.level}[/]", i.node_id or "-", i.message)
    console.print(table)


@app.command()
def templates() -> None:
    """List the starter blueprints."""
    table = Table(box=None, header_style="bold")
    for col in ("Id", "Name", "Level", "What it does"):
        table.add_column(col)
    for b in blueprint_index():
        table.add_row(b["id"], b["title"], b["level"], b["blurb"])
    console.print(table)
    console.print("\nStart one with: [bold]configurator init --from support-bot[/]")


@app.command()
def init(
    output: Annotated[Path, typer.Option("--output", "-o", help="Where to write the spec.")] = Path("spec.json"),
    blueprint: Annotated[str | None, typer.Option("--from", help="Blueprint id (see `configurator templates`).")] = None,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Accept defaults without asking.")] = False,
) -> None:
    """Create spec.json from a blueprint, asking a few questions."""
    index = blueprint_index()
    ids = [b["id"] for b in index]
    if blueprint is None:
        if yes:
            blueprint = "blank"
        else:
            console.print(Panel.fit("Pick a starting point. You can change everything later on the canvas.", title="Agent Configurator"))
            for n, b in enumerate(index, start=1):
                console.print(f"  [bold]{n}[/]. {b['title']} [dim]({b['id']})[/]  {b['blurb']}")
            choice = typer.prompt("Blueprint number", default="1")
            blueprint = ids[int(choice) - 1] if choice.isdigit() and 0 < int(choice) <= len(ids) else choice
    if blueprint not in ids:
        err.print(f"[red]Unknown blueprint '{blueprint}'.[/] Choose from: {', '.join(ids)}")
        raise typer.Exit(2)
    spec = load_blueprint(blueprint)
    if not yes:
        spec.project.name = typer.prompt("Project name (lower case, hyphens)", default=spec.project.name)
        provider = typer.prompt("Model provider [anthropic/openai]", default=spec.llm.provider)
        if provider in MODELS:
            spec.llm.provider = provider  # type: ignore[assignment]
            options = ", ".join(m["value"] for m in MODELS[provider])
            default = spec.llm.model if spec.llm.model.startswith("claude-") == (provider == "anthropic") else DEFAULT_MODEL[provider]
            spec.llm.model = typer.prompt(f"Default model ({options})", default=default)
        spec.ui.framework = "nextjs" if typer.confirm("Include the Next.js chat UI?", default=True) else "none"
        spec.deploy.target = "docker_compose" if typer.confirm("Include Docker Compose?", default=True) else "none"
    spec = Spec.model_validate(spec.model_dump())
    output.write_text(dump_spec(spec), encoding="utf-8")
    console.print(f"[green]Wrote {output}[/]. Next: [bold]configurator generate {output} -o ./{spec.project.name}[/]")


@app.command()
def validate(spec_path: Annotated[Path, typer.Argument(help="Path to spec.json")]) -> None:
    """Check the spec against the schema and the rules."""
    res = resolve(_load(spec_path))
    _print_issues(res)
    if not res.ok:
        raise typer.Exit(1)
    console.print(f"[green]Valid.[/] Modules: {', '.join(res.modules)}")


@app.command()
def explain(spec_path: Annotated[Path, typer.Argument(help="Path to spec.json")]) -> None:
    """Print the loop, each technology choice and its trade-off."""
    spec = _load(spec_path)
    res = resolve(spec)
    tree = Tree(f"[bold]{spec.project.name}[/]  [dim]{spec.llm.provider} / {spec.llm.model}[/]")
    for n in res.graph.nodes.values():
        meta = NODE_INDEX[n.type]
        branch = tree.add(f"[bold]{n.label}[/] [dim]({meta['title']})[/]")
        for t in n.tools + n.knowledge:
            r = res.graph.resources[t]
            branch.add(f"[cyan]{r.label}[/] [dim]({NODE_INDEX[r.type]['title']})[/]")
    console.print(tree)
    console.print("\n[bold]Dry run[/] (happy path, loops go round once):")
    for i, s in enumerate(simulate(res.graph), start=1):
        console.print(f"  {i:>2}. {', '.join(s['nodes'])}  [dim]{s['note']}[/]")
    registry = load_registry()
    console.print()
    for mod_id in res.modules:
        m = registry.get(mod_id)
        if not m or not m.explain:
            continue
        body = "\n".join(f"[bold]{k.capitalize()}.[/] {m.explain[k]}" for k in ("what", "why", "trade-off") if k in m.explain)
        console.print(Panel(body, title=m.title, title_align="left", border_style="dim"))
    if res.issues:
        console.print()
        _print_issues(res)


@app.command("generate")
def generate_cmd(
    spec_path: Annotated[Path, typer.Argument(help="Path to spec.json")],
    output: Annotated[Path, typer.Option("--output", "-o", help="Folder (or .zip file) to write.")] = Path("out"),
    force: Annotated[bool, typer.Option(help="Also overwrite backend/app/custom/ files.")] = False,
    fill_gaps: Annotated[bool, typer.Option("--fill-gaps", help="Ask Claude to write custom tools and steps that have no code yet.")] = False,
) -> None:
    """Render the full project."""
    spec = _load(spec_path)
    if fill_gaps:
        from configurator_engine.ai import fill_gaps as run_fill

        spec, report = run_fill(spec, log=lambda m: console.print(f"[dim]{m}[/]"))
        for line in report:
            console.print(line)
        spec_path.write_text(dump_spec(spec), encoding="utf-8")
    try:
        out = generate(spec)
    except GenerationError as exc:
        _print_issues(exc.resolution)
        err.print("[red]Fix the errors above, then generate again.[/]")
        raise typer.Exit(1) from None
    if output.suffix == ".zip":
        output.write_bytes(to_zip(out))
        console.print(f"[green]Wrote {output}[/] ({len(out.files)} files)")
    else:
        skipped = write(out, output, overwrite_custom=force)
        console.print(f"[green]Generated {len(out.files)} files in {output}/[/]")
        if skipped:
            console.print(f"[dim]Kept your edits in: {', '.join(skipped)} (use --force to overwrite)[/]")
    if out.resolution.gaps:
        console.print(
            f"[yellow]{len(out.resolution.gaps)} custom block(s) have no code yet.[/] "
            "They were exported as typed stubs and listed in PROMPT_PACK.md. "
            "Run again with --fill-gaps to have Claude write them."
        )
    console.print(
        f"\nNext:\n  cd {output}\n  cp .env.example .env   # add your API key\n  make setup && make test && make dev"
    )


@app.command("verify")
def verify_cmd(
    path: Annotated[Path, typer.Argument(help="Exported project folder")],
    local: Annotated[bool, typer.Option("--local", help="Run backend checks on this machine instead of a container.")] = False,
    docker: Annotated[bool, typer.Option("--docker", help="Require a container for backend checks.")] = False,
    skip_frontend: Annotated[bool, typer.Option("--skip-frontend", help="Skip ESLint and tsc.")] = False,
    boot: Annotated[bool, typer.Option("--boot", help="Also `docker compose up` and wait for the health check.")] = False,
) -> None:
    """Lint, type-check and test an exported project."""
    from configurator_engine.verifier import verify

    sandbox = "local" if local else "docker" if docker else "auto"
    checks = verify(path, sandbox=sandbox, frontend=not skip_frontend, boot=boot, log=lambda m: console.print(f"[dim]… {m}[/]"))
    failed = False
    for c in checks:
        mark = "[yellow]skip[/]" if c.skipped else ("[green]pass[/]" if c.ok else "[red]fail[/]")
        console.print(f"{mark}  {c.name}")
        if not c.ok and not c.skipped:
            failed = True
            console.print(Panel(c.output or "(no output)", border_style="red", title=c.name, title_align="left"))
    raise typer.Exit(1 if failed else 0)


@app.command("from-text")
def from_text(
    description: Annotated[str, typer.Argument(help="Describe the app in a sentence or two.")],
    output: Annotated[Path, typer.Option("--output", "-o")] = Path("spec.json"),
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Write without asking for confirmation.")] = False,
) -> None:
    """Draft a spec from a description, using Claude (falls back to the closest blueprint)."""
    from configurator_engine.ai import text_to_spec

    result = text_to_spec(description)
    spec = result.spec
    console.print(Panel(result.summary, title=f"Proposed: {spec.project.name}", subtitle=f"via {result.source}", title_align="left"))
    res = resolve(spec)
    for n in res.graph.nodes.values():
        console.print(f"  • {n.label} [dim]({NODE_INDEX[n.type]['title']})[/]")
    for r in res.graph.resources.values():
        console.print(f"    + {r.label} [dim]({NODE_INDEX[r.type]['title']})[/]")
    if not yes and not typer.confirm(f"Write this to {output}?", default=True):
        raise typer.Exit(0)
    output.write_text(dump_spec(spec), encoding="utf-8")
    console.print(f"[green]Wrote {output}[/]. Open it on the canvas or run: configurator generate {output} -o ./out")


@app.command()
def schema() -> None:
    """Print the spec's JSON Schema."""
    console.print_json(json.dumps(json_schema()))


@app.command()
def serve(
    host: Annotated[str, typer.Option()] = "127.0.0.1",
    port: Annotated[int, typer.Option()] = 8787,
    reload: Annotated[bool, typer.Option()] = False,
) -> None:
    """Run the configurator API that the web canvas talks to."""
    import uvicorn

    uvicorn.run("configurator_api.main:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    app()
