"""Run directories, provenance capture, structured metrics and reproducible checkpoints."""

from __future__ import annotations

import json
import os
import platform
import random
import subprocess
import sys
import time

import numpy as np
import torch

from ..config import ExperimentConfig, config_from_dict, save_config

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def _cmd(args):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=20, cwd=REPO_ROOT).stdout.strip()
    except Exception:  # noqa: BLE001
        return None


def provenance() -> dict:
    import genesis as gs

    info = {
        "python": sys.version.split()[0],
        "torch": torch.__version__,
        "torch_cuda": torch.version.cuda,
        "genesis": gs.__version__,
        "numpy": np.__version__,
        "platform": platform.platform(),
        "hostname": platform.node(),
        "git_commit": _cmd(["git", "rev-parse", "HEAD"]),
        "git_dirty": bool(_cmd(["git", "status", "--porcelain", "--untracked-files=no"])),
        "argv": sys.argv,
        "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    if torch.cuda.is_available():
        info["gpu"] = torch.cuda.get_device_name(0)
        info["cuda_visible_devices"] = os.environ.get("CUDA_VISIBLE_DEVICES")
        info["nvidia_driver"] = _cmd(["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"])
    return info


def make_run_dir(cfg: ExperimentConfig, kind: str, run_dir: str | None = None) -> str:
    if run_dir is None:
        run_dir = os.path.join(cfg.output_dir, f"{cfg.name}_{kind}_{cfg.digest()}_s{cfg.seed}")
    os.makedirs(run_dir, exist_ok=True)
    save_config(cfg, os.path.join(run_dir, "config.yaml"))
    write_json(os.path.join(run_dir, "provenance.json"), provenance())
    return run_dir


def write_json(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, default=_json_default)


def _json_default(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if torch.is_tensor(o):
        return o.tolist()
    raise TypeError(type(o))


class MetricsLogger:
    """Append-only JSON-lines metrics (one record per call)."""

    def __init__(self, path):
        self.path = path
        self.f = open(path, "a")

    def log(self, **record):
        self.f.write(json.dumps(record, default=_json_default) + "\n")
        self.f.flush()

    def close(self):
        self.f.close()


def rng_state() -> dict:
    st = {"python": random.getstate(), "numpy": np.random.get_state(), "torch": torch.get_rng_state()}
    if torch.cuda.is_available():
        st["cuda"] = torch.cuda.get_rng_state_all()
    return st


def set_rng_state(st: dict):
    random.setstate(st["python"])
    np.random.set_state(st["numpy"])
    torch.set_rng_state(st["torch"])
    if "cuda" in st and torch.cuda.is_available():
        torch.cuda.set_rng_state_all(st["cuda"])


def save_checkpoint(path, *, cfg: ExperimentConfig, agent, optimizer, iteration: int, extra: dict | None = None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    torch.save(
        {
            "config": cfg.to_dict(),
            "config_digest": cfg.digest(),
            "iteration": iteration,
            "agent": agent.state_dict(),
            "optimizer": optimizer.state_dict() if optimizer is not None else None,
            "rng": rng_state(),
            "provenance": provenance(),
            "extra": extra or {},
        },
        path,
    )


def load_checkpoint(path, map_location="cpu"):
    ck = torch.load(path, map_location=map_location, weights_only=False)
    ck["config_obj"] = config_from_dict(ck["config"])
    return ck
