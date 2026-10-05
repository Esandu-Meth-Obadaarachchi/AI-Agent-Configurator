"""Verify an exported project (section 4.6).

Checks: ruff, mypy and the exported tests for the backend; ESLint and tsc for the
frontend; optionally a Docker Compose boot with a health check.

Where it runs: the brief says verification belongs in containers. `sandbox="docker"`
runs the backend checks inside a throwaway python:3.12-slim container with only the
project folder mounted. `sandbox="local"` runs them on the host (faster, fine for
code you generated yourself from templates). `auto` uses Docker when the daemon is up.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Check:
    name: str
    ok: bool
    output: str = ""
    skipped: bool = False


def docker_available() -> bool:
    if not shutil.which("docker"):
        return False
    try:
        return subprocess.run(["docker", "info"], capture_output=True, timeout=10).returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


def _run(cmd: list[str], cwd: Path, timeout: int = 900, env: dict[str, str] | None = None) -> tuple[bool, str]:
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env={**os.environ, **(env or {})})
    except subprocess.TimeoutExpired:
        return False, f"timed out after {timeout}s: {' '.join(cmd)}"
    except FileNotFoundError as exc:
        return False, str(exc)
    out = (proc.stdout + proc.stderr).strip()
    return proc.returncode == 0, out[-6000:]


def _backend_local(root: Path, log: Callable[[str], None]) -> list[Check]:
    backend = root / "backend"
    venv = backend / ".venv"
    py = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    checks: list[Check] = []
    if not py.exists():
        log("creating backend virtualenv")
        ok, out = _run([sys.executable, "-m", "venv", str(venv)], backend)
        if not ok:
            return [Check("backend: venv", False, out)]
    log("installing backend dependencies (first run takes a minute)")
    installer = [str(py), "-m", "pip", "install", "-q", "-e", ".[dev]"]
    if shutil.which("uv"):
        installer = ["uv", "pip", "install", "-q", "--python", str(py), "-e", ".[dev]"]
    ok, out = _run(installer, backend, timeout=1800)
    checks.append(Check("backend: install", ok, out))
    if not ok:
        return checks
    test_env = {"LLM_PROVIDER": "fake", "HF_HUB_OFFLINE": "1"}
    for name, cmd in [
        ("backend: ruff", [str(py), "-m", "ruff", "check", "."]),
        ("backend: mypy", [str(py), "-m", "mypy", "app"]),
        ("backend: tests", [str(py), "-m", "pytest", "-q", "-p", "no:cacheprovider"]),
    ]:
        log(name)
        ok, out = _run(cmd, backend, env=test_env)
        checks.append(Check(name, ok, out))
    return checks


def _backend_docker(root: Path, log: Callable[[str], None]) -> list[Check]:
    backend = (root / "backend").resolve()
    script = (
        "set -e; pip install -q -r requirements.txt pytest pytest-asyncio ruff mypy >/dev/null; "
        "echo '== ruff'; ruff check .; echo '== mypy'; mypy app; echo '== tests'; LLM_PROVIDER=fake pytest -q -p no:cacheprovider"
    )
    log("running backend checks in a python:3.12-slim container")
    ok, out = _run(
        ["docker", "run", "--rm", "-v", f"{backend}:/work", "-w", "/work", "python:3.12-slim", "sh", "-c", script],
        root,
        timeout=1800,
    )
    return [Check("backend: ruff + mypy + tests (container)", ok, out)]


def _frontend(root: Path, log: Callable[[str], None]) -> list[Check]:
    fe = root / "frontend"
    if not (fe / "package.json").exists():
        return []
    if not shutil.which("npm"):
        return [Check("frontend", False, "npm not found; install Node.js 20+", skipped=True)]
    checks = []
    log("installing frontend dependencies")
    ok, out = _run(["npm", "install", "--no-audit", "--no-fund"], fe, timeout=1800)
    checks.append(Check("frontend: install", ok, out))
    if not ok:
        return checks
    for name, script in [("frontend: eslint", "lint"), ("frontend: tsc", "typecheck")]:
        log(name)
        ok, out = _run(["npm", "run", "-s", script], fe)
        checks.append(Check(name, ok, out))
    return checks


def _boot(root: Path, log: Callable[[str], None], port: int = 8000) -> Check:
    if not (root / "docker-compose.yml").exists():
        return Check("compose boot", True, "no docker-compose.yml", skipped=True)
    env_file = root / ".env"
    created = False
    if not env_file.exists():
        shutil.copy(root / ".env.example", env_file)
        created = True
    try:
        log("docker compose up --build (this builds the images)")
        ok, out = _run(["docker", "compose", "up", "-d", "--build"], root, timeout=2400, env={"LLM_PROVIDER": "fake"})
        if not ok:
            return Check("compose boot", False, out)
        for _ in range(60):
            try:
                with urllib.request.urlopen(f"http://localhost:{port}/api/health", timeout=3) as res:
                    if res.status == 200:
                        return Check("compose boot", True, "API healthy")
            except OSError:
                time.sleep(3)
        _, logs = _run(["docker", "compose", "logs", "--tail", "80"], root)
        return Check("compose boot", False, "API did not become healthy\n" + logs)
    finally:
        _run(["docker", "compose", "down", "-v"], root, timeout=300)
        if created:
            env_file.unlink(missing_ok=True)


def verify(
    path: str | Path,
    *,
    sandbox: str = "auto",
    frontend: bool = True,
    boot: bool = False,
    log: Callable[[str], None] = lambda _m: None,
) -> list[Check]:
    root = Path(path).resolve()
    if not (root / "backend" / "pyproject.toml").exists():
        return [Check("project", False, f"{root} doesn't look like an exported project (no backend/pyproject.toml)")]
    use_docker = sandbox == "docker" or (sandbox == "auto" and docker_available())
    if sandbox == "docker" and not docker_available():
        return [Check("docker", False, "Docker isn't running. Start Docker Desktop or use --local.")]
    checks = _backend_docker(root, log) if use_docker else _backend_local(root, log)
    if frontend:
        checks += _frontend(root, log)
    if boot:
        checks.append(_boot(root, log) if docker_available() else Check("compose boot", False, "Docker isn't running.", skipped=True))
    return checks
