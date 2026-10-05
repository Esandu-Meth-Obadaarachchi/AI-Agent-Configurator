"""Small, deterministic helpers for stitching user or Claude-written Python into files."""

from __future__ import annotations

import ast


def split_imports(code: str) -> tuple[list[str], str]:
    """Separate top-level import statements from the rest of a snippet.

    Snippets from several custom tools end up in one file. Hoisting their imports to
    the top keeps the file lint-clean (no imports after code) and deduplicated.
    Falls back to "no imports" when the snippet doesn't parse; the verifier reports it.
    """
    code = code.strip("\n")
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return [], code
    lines = code.splitlines()
    import_lines: list[str] = []
    drop: set[int] = set()
    for node in tree.body:
        if isinstance(node, ast.Import | ast.ImportFrom):
            start, end = node.lineno - 1, (node.end_lineno or node.lineno) - 1
            stmt = "\n".join(lines[start : end + 1]).strip()
            if stmt != "from __future__ import annotations":
                import_lines.append(stmt)
            drop.update(range(start, end + 1))
    body = "\n".join(line for i, line in enumerate(lines) if i not in drop).strip("\n")
    return import_lines, body


def merge_imports(groups: list[list[str]], always: list[str] | None = None) -> list[str]:
    seen: list[str] = []
    for stmt in (always or []) + [s for g in groups for s in g]:
        if stmt not in seen:
            seen.append(stmt)
    stdlib = []
    third = []
    local = []
    for s in seen:
        mod = s.split()[1]
        root = mod.split(".")[0]
        if root == "app":
            local.append(s)
        elif root in _STDLIB:
            stdlib.append(s)
        else:
            third.append(s)
    return sorted(stdlib) + ([""] if stdlib and (third or local) else []) + sorted(third) + ([""] if third and local else []) + sorted(local)


def defines_function(code: str, name: str) -> bool:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False
    return any(isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef) and n.name == name for n in tree.body)


_STDLIB = {
    "abc", "asyncio", "base64", "collections", "contextlib", "csv", "dataclasses", "datetime", "decimal", "enum",
    "functools", "hashlib", "hmac", "html", "http", "io", "itertools", "json", "logging", "math", "os", "pathlib",
    "random", "re", "statistics", "string", "sys", "textwrap", "time", "typing", "urllib", "uuid", "zoneinfo",
}
