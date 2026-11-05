"""Local/CI gate for the developer workbench; never discovers scientific tests."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    # Parse without creating bytecode files or importing any scientific module.
    for path in sorted((ROOT / "developer").rglob("*.py")):
        if any(part.startswith(".") or part == "__pycache__" for part in path.relative_to(ROOT).parts):
            continue
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for path in sorted((ROOT / ".vscode").glob("*.json")):
        json.loads(path.read_text(encoding="utf-8"))
    commands = [
        [sys.executable, "-m", "unittest", "discover", "-s", "developer/tests", "-v"],
        [sys.executable, "-m", "unittest", "discover", "-s", "developer/labs", "-p", "test_*.py", "-v"],
        [sys.executable, "developer/gnav_dev.py", "config", "--config", "configs/eval.yaml", "backend=cpu", "env.n_envs=2", "--json"],
    ]
    if shutil.which("git"):
        probe = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=ROOT,
                               capture_output=True, text=True, check=False)
        if probe.returncode == 0 and probe.stdout.strip() == "true":
            commands.append(["git", "diff", "--check"])
        else:
            print("SKIP: Git whitespace diff (archive has no Git working tree).")
    else:
        print("SKIP: Git whitespace diff (Git not installed).")
    for command in commands:
        print("\n+ " + " ".join(command), flush=True)
        result = subprocess.run(command, cwd=ROOT, check=False)
        if result.returncode:
            return result.returncode
    print("\nPASS: developer tooling and reference exercise. Simulation/GUI/cloud CI not covered.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
