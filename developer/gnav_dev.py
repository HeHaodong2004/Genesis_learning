#!/usr/bin/env python3
"""Read-only developer tools for gnav; never initialise Genesis or load a checkpoint.

Run through scripts/gnav-env.sh. This entry point pins imports to its own worktree,
so an editable installation of another checkout cannot silently win.
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import types
import typing

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
MAX_BYTES = 16 * 1024 * 1024


class PreflightError(ValueError):
    """An actionable input problem, shown without an implementation traceback."""


def _git(*args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT), *args], capture_output=True, text=True, timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def doctor() -> dict:
    """Inspect package metadata without importing torch/genesis or probing a GPU."""
    dependencies = {}
    for name in ("PyYAML", "numpy", "torch", "genesis-world", "pytest"):
        try:
            dependencies[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            dependencies[name] = None
    spec = importlib.util.find_spec("gnav")
    actual = Path(spec.origin).resolve() if spec and spec.origin else None
    expected = SRC / "gnav" / "__init__.py"
    status = _git("status", "--porcelain")
    checks = {
        "python_supported": (3, 11) <= sys.version_info[:2] < (3, 13),
        "source_is_this_worktree": actual == expected,
        "yaml_available": dependencies["PyYAML"] is not None,
    }
    warnings = []
    if any(dependencies[name] is None for name in ("numpy", "torch", "genesis-world")):
        warnings.append("仿真依赖不完整；轻量开发检查仍可使用，未启动仿真。")
    if os.environ.get("PYTHONPATH"):
        warnings.append("PYTHONPATH 非空；建议经 scripts/gnav-env.sh 运行以隔离 ROS。")
    if status:
        warnings.append("工作区有未提交变更；这是状态提示，不是错误。")
    return {
        "ok": all(checks.values()), "command": "doctor", "root": str(ROOT),
        "python": {"executable": sys.executable, "version": sys.version.split()[0]},
        "gnav_source": str(actual) if actual else None,
        "git": {"branch": _git("branch", "--show-current"),
                "commit": _git("rev-parse", "HEAD"),
                "dirty": bool(status) if status is not None else None},
        "dependencies": dependencies, "checks": checks, "warnings": warnings,
        "scope": "仅检查元数据和导入路径；不代表 CUDA、渲染器或仿真健康检查通过。",
    }


def _read_text(path: Path) -> str:
    try:
        if not path.is_file():
            raise PreflightError(f"找不到普通文件：{path}")
        if path.stat().st_size > MAX_BYTES:
            raise PreflightError(f"文件超过轻量检查上限 16 MiB：{path}")
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise PreflightError(f"无法读取 {path}：{exc}") from exc


def _yaml_module():
    try:
        import yaml
    except ImportError as exc:
        raise PreflightError("缺少 PyYAML；请使用 scripts/gnav-env.sh 及已配置的 Genesis 环境。") from exc
    return yaml


def _yaml_mapping(path: Path) -> dict:
    yaml = _yaml_module()
    try:
        data = yaml.safe_load(_read_text(path))
    except yaml.YAMLError as exc:
        raise PreflightError(f"YAML 无法解析：{path}：{exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise PreflightError(f"配置顶层必须是 mapping（键值表）：{path}")
    return data


def _load_tree(path: Path, stack: tuple[Path, ...] = ()) -> dict:
    """Match gnav inheritance semantics while rejecting cycles and wrong shapes."""
    from gnav.config import _deep_merge

    path = path.resolve()
    if path in stack:
        raise PreflightError("配置继承循环：" + " -> ".join(p.name for p in (*stack, path)))
    if len(stack) >= 32:
        raise PreflightError("配置继承超过 32 层；请简化继承关系。")
    data = _yaml_mapping(path)
    parents = data.pop("inherit", []) or []
    if not isinstance(parents, list) or any(not isinstance(p, str) for p in parents):
        raise PreflightError(f"inherit 必须是相对路径字符串列表：{path}")
    merged = {}
    for parent in parents:
        merged = _deep_merge(merged, _load_tree(path.parent / parent, (*stack, path)))
    return _deep_merge(merged, data)


def _type_errors(value, expected, path: str = "config", depth: int = 0) -> list[str]:
    """Runtime-check dataclass annotations; dataclasses alone do not enforce types."""
    if depth > 40:
        return [f"{path}：嵌套超过 40 层（可能含 YAML alias 循环）"]
    if expected is typing.Any:
        return []
    origin, args = typing.get_origin(expected), typing.get_args(expected)
    if origin in (typing.Union, types.UnionType):
        if any(not _type_errors(value, option, path, depth + 1) for option in args):
            return []
        return [f"{path}：应为 {expected}，实际为 {type(value).__name__}"]
    if dataclasses.is_dataclass(expected):
        if not isinstance(value, dict):
            return [f"{path}：应为键值表，实际为 {type(value).__name__}"]
        hints = typing.get_type_hints(expected)
        errors = []
        for key, item in value.items():
            if key not in hints:
                errors.append(f"{path}.{key}：未知配置字段")
            else:
                errors.extend(_type_errors(item, hints[key], f"{path}.{key}", depth + 1))
        return errors
    if origin in (list, tuple):
        if not isinstance(value, (list, tuple)) or (origin is list and not isinstance(value, list)):
            return [f"{path}：应为 {origin.__name__}"]
        if origin is tuple and len(args) != len(value):
            return [f"{path}：需要 {len(args)} 个元素，实际为 {len(value)}"]
        errors = []
        for index, item in enumerate(value):
            kind = args[0] if origin is list else args[index]
            errors.extend(_type_errors(item, kind, f"{path}[{index}]", depth + 1))
        return errors
    if origin is dict:
        if not isinstance(value, dict):
            return [f"{path}：应为键值表"]
        errors = []
        for key, item in value.items():
            errors.extend(_type_errors(key, args[0], f"{path}.<key>", depth + 1))
            errors.extend(_type_errors(item, args[1], f"{path}.{key}", depth + 1))
        return errors
    valid = isinstance(value, expected)
    if expected is int:
        valid = type(value) is int
    elif expected is float:
        valid = type(value) in (int, float) and math.isfinite(value)
    if valid:
        return []
    return [f"{path}：应为 {getattr(expected, '__name__', expected)}，实际为 {type(value).__name__}"]


def validate_config(cfg) -> list[str]:
    """Conservative preflight rules, separate from the frozen scientific code.

    This catches common invalid inputs. It does not prove geometric feasibility,
    checkpoint compatibility, physics stability, or completeness of custom profiles.
    """
    d = cfg.to_dict()
    errors = []

    def get(path):
        result = d
        for part in path.split("."):
            result = result[part]
        return result

    def require(condition, message):
        if not condition:
            errors.append(message)

    positive = (
        "env.n_envs", "env.sim_dt", "env.control_decimation", "env.max_episode_steps",
        "env.arena_half_size", "env.wall_height", "env.goal_radius", "env.robot_mass",
        "env.robot_max_force", "env.robot_max_torque", "env.sensors.rays_n",
        "env.sensors.max_range", "env.mover.mass", "env.mover.max_force",
        "model.latent_dim", "model.belief_dim", "model.hidden_dim", "train.iterations",
        "train.rollout_len", "train.lr", "train.seq_len", "train.batch_size",
        "train.replay_capacity", "train.checkpoint_every", "eval.n_episodes",
    )
    nonnegative = (
        "seed", "eval_seed", "env.n_pillars", "env.n_occluders", "env.min_start_goal_dist",
        "env.near_collision_clearance", "env.dynamics.delay_jitter", "env.dynamics.max_delay_steps",
        "env.sensors.depth_noise_std", "env.sensors.rays_noise_std",
        "env.sensors.proprio_noise_std", "env.sensors.goal_noise_std",
    )
    for path in positive:
        require(get(path) > 0, f"{path} 必须 > 0")
    for path in nonnegative:
        require(get(path) >= 0, f"{path} 必须 >= 0")
    require(d["backend"] in ("cpu", "gpu"), "backend 必须是 cpu 或 gpu")
    require(bool(d["name"].strip()), "name 不能为空")
    require(bool(d["output_dir"].strip()), "output_dir 不能为空")
    require(0 <= d["train"]["gamma"] <= 1, "train.gamma 必须在 [0, 1] 内")
    require(0 <= d["env"]["dynamics"]["scale_range"] < 1, "env.dynamics.scale_range 必须在 [0, 1) 内")
    require(0 < get("env.sensors.depth_hfov_deg") < 180,
            "env.sensors.depth_hfov_deg 必须在 (0, 180) 内")
    require(0 < get("env.sensors.rays_fov_deg") <= 360,
            "env.sensors.rays_fov_deg 必须在 (0, 360] 内")
    require(all(n > 0 for n in d["env"]["sensors"]["depth_res"]), "env.sensors.depth_res 每个分辨率必须 > 0")
    for path in ("env.mover.speed_range", "env.mover.path_length_range"):
        lo, hi = get(path)
        require(0 <= lo <= hi, f"{path} 需要 0 <= 下界 <= 上界")
    dynamics = d["env"]["dynamics"]
    profiles, probs = dynamics["profiles"], dynamics["profile_probs"]
    require(bool(profiles), "env.dynamics.profiles 不能为空")
    for profile in profiles:
        require(profile in ("agile", "heavy") or profile in dynamics["custom_profiles"],
                f"env.dynamics.profiles：未知动力学 profile {profile!r}")
    if probs is not None:
        require(len(probs) == len(profiles), "env.dynamics.profile_probs 长度必须匹配 profiles")
        require(all(p >= 0 for p in probs), "env.dynamics.profile_probs 概率不能为负")
        require(math.isclose(sum(probs), 1.0, rel_tol=1e-7, abs_tol=1e-7),
                "env.dynamics.profile_probs 总和必须为 1")
    return errors


def _check_json_config(data) -> None:
    """Also check untyped dictionaries before dataclass copying or JSON output."""
    try:
        json.dumps(data, allow_nan=False)
    except (ValueError, TypeError, OverflowError, RecursionError) as exc:
        raise PreflightError(
            f"配置必须是可序列化的 JSON 数据，数值须有限且不能有循环引用：{exc}"
        ) from exc


def resolve_config(path: Path, overrides: list[str] | None = None) -> dict:
    _yaml_module()
    from gnav import config as config_module

    if Path(config_module.__file__).resolve() != SRC / "gnav" / "config.py":
        raise PreflightError("gnav.config 来自其他工作树；请重新启动 Python 并使用本入口。")
    data = _load_tree(path)
    for override in overrides or []:
        if "=" not in override or any(not p for p in override.split("=", 1)[0].split(".")):
            raise PreflightError(f"覆盖参数必须为 section.key=value：{override}")
    try:
        data = config_module.apply_overrides(data, overrides or [])
    except (ValueError, TypeError, AttributeError, _yaml_module().YAMLError) as exc:
        raise PreflightError(f"无法应用覆盖参数：{exc}") from exc
    errors = _type_errors(data, config_module.ExperimentConfig)
    if errors:
        raise PreflightError("配置类型检查失败：\n" + "\n".join(errors[:30]))
    # Bare dict fields can contain values outside their dataclass type annotations.
    # Check before asdict/deepcopy, which would recurse forever on a YAML alias cycle.
    _check_json_config(data)
    cfg = config_module.config_from_dict(data)
    resolved = cfg.to_dict()
    _check_json_config(resolved)
    errors = validate_config(cfg)
    if errors:
        raise PreflightError("配置预检失败：\n" + "\n".join(errors[:30]))
    return {
        "ok": True, "command": "config", "input": str(path.resolve()),
        "source": str(Path(config_module.__file__).resolve()),
        "digest": cfg.digest(), "config": resolved,
        "scope": "类型和常见参数预检通过；未创建环境、运行实验或验证科研结论。",
    }


def _json_loads(text: str):
    def reject_constant(value):
        raise ValueError(f"非标准 JSON 数值 {value}")

    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"JSON 数值超出有限浮点范围：{value}")
        return number

    return json.loads(text, parse_constant=reject_constant, parse_float=finite_float)


def inspect_run(path: Path) -> dict:
    """Inspect ordinary metadata only, never pickle/PT/NPZ or executable code."""
    if not path.is_dir():
        raise PreflightError(f"run 目录不存在：{path}")
    report = {
        "ok": True, "command": "inspect-run", "path": str(path.resolve()),
        "files": {}, "errors": [],
        "scope": "只读元数据检查；文件齐全不等于实验完成、结果可信或可复现。",
    }
    for name in ("config.yaml", "provenance.json", "metrics.json", "metrics.jsonl"):
        file = path / name
        if not file.exists():
            report["files"][name] = {"present": False}
            if name in ("config.yaml", "provenance.json"):
                report["errors"].append(f"缺少 {name}")
            continue
        entry = {"present": True}
        report["files"][name] = entry
        try:
            if name == "config.yaml":
                result = resolve_config(file)
                entry.update({"valid": True, "digest": result["digest"],
                              "experiment_name": result["config"]["name"]})
            elif name == "metrics.jsonl":
                count = 0
                keys = set()
                for line_number, line in enumerate(_read_text(file).splitlines(), 1):
                    if not line.strip():
                        continue
                    try:
                        record = _json_loads(line)
                        if not isinstance(record, dict):
                            raise ValueError("每条记录必须是对象")
                    except (ValueError, TypeError) as exc:
                        raise PreflightError(f"第 {line_number} 行：{exc}") from exc
                    count += 1
                    keys.update(record)
                if count == 0:
                    raise PreflightError("metrics.jsonl 没有记录")
                entry.update({"valid": True, "records": count, "keys": sorted(keys)})
            else:
                data = _json_loads(_read_text(file))
                if not isinstance(data, dict):
                    raise PreflightError("顶层必须是 JSON 对象")
                entry.update({"valid": True, "keys": sorted(data)})
                if name == "provenance.json":
                    entry["summary"] = {key: data[key] for key in (
                        "python", "torch", "torch_cuda", "genesis", "git_commit", "git_dirty", "time", "synthetic"
                    ) if key in data}
                else:
                    entry["summary"] = {key: data[key] for key in (
                        "policy", "n_episodes", "eval_seed", "config_digest", "synthetic"
                    ) if key in data}
        except (PreflightError, ValueError, TypeError, RecursionError) as exc:
            entry.update({"valid": False, "error": str(exc)})
            report["errors"].append(f"{name}：{exc}")
    if not any(report["files"][name]["present"] for name in ("metrics.json", "metrics.jsonl")):
        report["errors"].append("缺少 metrics.json 或 metrics.jsonl；可能尚未开始记录指标")
    metrics = report["files"]["metrics.json"]
    config = report["files"]["config.yaml"]
    stored_digest = metrics.get("summary", {}).get("config_digest")
    if stored_digest is not None and config.get("valid") and stored_digest != config["digest"]:
        report["errors"].append("metrics.json 的 config_digest 与 config.yaml 不匹配")
    report["ok"] = not report["errors"]
    return report


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Genesis 开发工作台：轻量预检，不启动仿真、不修改文件。")
    sub = p.add_subparsers(dest="command", required=True)
    doctor_parser = sub.add_parser("doctor", help="检查解释器、包元数据与真实导入路径")
    doctor_parser.add_argument("--json", action="store_true", help="输出可供脚本读取的 JSON")
    cfg = sub.add_parser("config", help="解析真实配置、覆盖参数并做类型/常见参数预检")
    cfg.add_argument("--config", default="configs/eval.yaml", metavar="PATH")
    cfg.add_argument("--json", action="store_true")
    cfg.add_argument("overrides", nargs="*", metavar="key=value")
    run = sub.add_parser("inspect-run", help="只读检查已有 run 的元数据")
    run.add_argument("path", type=Path)
    run.add_argument("--json", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "doctor":
            report = doctor()
        elif args.command == "config":
            report = resolve_config(Path(args.config), args.overrides)
        else:
            report = inspect_run(args.path)
    except (PreflightError, RecursionError) as exc:
        report = {"ok": False, "command": args.command, "error": str(exc)}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    elif not report["ok"]:
        print("检查未通过：", file=sys.stderr)
        print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), file=sys.stderr)
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
