"""Export an educational snapshot without research outputs or Git history.

Usage: scripts/gnav-env.sh python developer/package.py /absolute/new-directory
The destination must not exist. The original repository is read-only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    target = args.destination.resolve()
    if target.exists() or target == ROOT or ROOT in target.parents:
        parser.error("choose a new destination outside this worktree")
    target.mkdir(parents=True)
    for directory in ("developer", "docs/developer", ".vscode", ".github",
                      "src/gnav/sim", "src/gnav/learning", "src/gnav/experiment",
                      "configs/profiles", "configs/ablations"):
        shutil.copytree(ROOT / directory, target / directory,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".venv*", "my-*"))
    for name in ("Makefile", "START_HERE.md", "src/gnav/__init__.py", "src/gnav/config.py",
                 "src/gnav/runtime.py", "src/gnav/viz/__init__.py", "src/gnav/viz/topdown.py",
                 "src/gnav/analysis/__init__.py", "src/gnav/analysis/stats.py",
                 "configs/base.yaml", "configs/eval.yaml", "configs/train_smoke.yaml",
                 "scripts/gnav-env.sh", "scripts/train.py", "scripts/evaluate.py",
                 "scripts/compare.py", "scripts/smoke_test.py", "scripts/benchmark.py",
                 "environment/requirements.lock.txt", "environment/conda-environment.yml"):
        (target / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target / name)
    # Preserve one real fixture for the reading exercise; do not claim that the
    # original full research suite/results are part of this teaching snapshot.
    (target / "tests").mkdir()
    shutil.copy2(ROOT / "tests/conftest.py", target / "tests/conftest.py")
    (target / "README.md").write_text(
        (ROOT / "START_HERE.md").read_text(encoding="utf-8")
        + "\n## GitHub 教学快照说明\n\n"
        "本仓库是独立训练包：保留跟读所需的原始源码、配置与入口，"
        "不包含原项目Git历史、研究结果、历史诊断模型、完整科研测试/实验目录或个人记忆。"
        "请运行 `make check` 而非把它当成原研究仓库的完整复现。"
        "原研究状态 `STATUS_FOR_CLAUDE.md` 只在原工作区读取。"
        "已有源码来自本机Genesis研究库基线 `181c8f6`，用于本人的学习与开发。\n",
        encoding="utf-8",
    )
    (target / ".gitignore").write_text(
        "__pycache__/\n*.pyc\n.venv*/\n.pytest_cache/\n.ruff_cache/\nruns/\nresults/\n"
        "developer/evidence/my-*\n", encoding="utf-8")
    manifest = []
    for path in sorted(target.rglob("*")):
        if path.is_file():
            data = path.read_bytes()
            manifest.append({"path": str(path.relative_to(target)), "bytes": len(data),
                             "sha256": hashlib.sha256(data).hexdigest()})
    (target / "EXPORT_MANIFEST.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"destination": str(target), "files": len(manifest),
                      "bytes": sum(p["bytes"] for p in manifest)}))


if __name__ == "__main__":
    main()
