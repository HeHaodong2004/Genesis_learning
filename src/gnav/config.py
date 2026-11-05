"""Typed experiment configuration.

YAML files may inherit from other files via a top-level ``inherit: [relative/path.yaml, ...]`` list (merged in
order, later files win), and any field can be overridden from the command line with ``section.key=value`` (the
value is parsed as YAML). The resolved config is saved verbatim next to every run so the run can be reproduced.
"""

from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
import os
from dataclasses import dataclass, field
from typing import Any

import yaml


@dataclass
class RandomizationConfig:
    # Each source draws from its own seed stream, so disabling one never changes what the others produce.
    robot_init: bool = True
    goal: bool = True
    obstacles: bool = True
    mover: bool = True
    dynamics: bool = False
    obs_noise: bool = False


@dataclass
class SensorConfig:
    depth_enabled: bool = True
    depth_res: tuple[int, int] = (64, 16)  # (width, height)
    depth_hfov_deg: float = 90.0
    rays_enabled: bool = True
    rays_n: int = 31
    rays_fov_deg: float = 90.0
    max_range: float = 6.0
    mount_height: float = 0.20  # above base centre: 0.10 m above hull top, so rays never cross the hull
    depth_noise_std: float = 0.02  # metres, applied when randomization.obs_noise
    rays_noise_std: float = 0.02
    proprio_noise_std: float = 0.02
    goal_noise_std: float = 0.02


@dataclass
class DynamicsConfig:
    profiles: list[str] = field(default_factory=lambda: ["agile"])
    profile_probs: list[float] | None = None  # None -> uniform
    scale_range: float = 0.2  # +-20% multiplicative when randomization.dynamics
    delay_jitter: int = 1  # +-1 control step when randomization.dynamics
    max_delay_steps: int = 4
    custom_profiles: dict[str, dict] = field(default_factory=dict)  # name -> DynamicsProfile fields


@dataclass
class MoverConfig:
    enabled: bool = True
    speed_range: tuple[float, float] = (0.3, 0.9)
    path_length_range: tuple[float, float] = (2.0, 4.0)
    mass: float = 30.0
    max_force: float = 150.0


@dataclass
class EnvConfig:
    n_envs: int = 16
    sim_dt: float = 0.02
    control_decimation: int = 5  # control period = sim_dt * decimation = 0.1 s
    max_episode_steps: int = 300  # control steps (30 s)
    arena_half_size: float = 4.0
    wall_height: float = 2.0
    goal_radius: float = 0.35
    min_start_goal_dist: float = 4.0
    terminate_on_collision: bool = True
    near_collision_clearance: float = 0.15
    robot_mass: float = 10.0
    robot_max_force: float = 150.0  # N; servo force limit (contacts can stop the robot)
    robot_max_torque: float = 20.0
    servo_kv_lin: float = 600.0
    servo_kv_ang: float = 30.0
    n_pillars: int = 3
    n_occluders: int = 2
    reward_progress: float = 1.0
    reward_success: float = 10.0
    reward_collision: float = 5.0
    reward_time: float = 0.01
    sensors: SensorConfig = field(default_factory=SensorConfig)
    dynamics: DynamicsConfig = field(default_factory=DynamicsConfig)
    mover: MoverConfig = field(default_factory=MoverConfig)
    randomization: RandomizationConfig = field(default_factory=RandomizationConfig)


@dataclass
class ModelConfig:
    latent_dim: int = 64
    belief_dim: int = 128
    hidden_dim: int = 128


@dataclass
class TrainConfig:
    iterations: int = 20
    rollout_len: int = 32
    lr: float = 3e-4
    gamma: float = 0.99
    entropy_coef: float = 0.01
    value_coef: float = 0.5
    model_coef: float = 1.0
    seq_len: int = 16
    batch_size: int = 32
    replay_capacity: int = 20000
    checkpoint_every: int = 10


@dataclass
class EvalConfig:
    n_episodes: int = 16
    policy: str = "reactive"  # reactive | random | checkpoint
    checkpoint: str | None = None
    record_trajectories: bool = True
    deterministic: bool = True


@dataclass
class ExperimentConfig:
    name: str = "default"
    seed: int = 0
    eval_seed: int = 10_000  # disjoint seed space from training
    backend: str = "gpu"  # gpu | cpu
    output_dir: str = "runs"
    env: EnvConfig = field(default_factory=EnvConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    train: TrainConfig = field(default_factory=TrainConfig)
    eval: EvalConfig = field(default_factory=EvalConfig)

    def to_dict(self) -> dict:
        return _to_plain(dataclasses.asdict(self))

    def digest(self) -> str:
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True).encode()).hexdigest()[:12]


# ------------------------------------------------------------------------------------------------ loading


def _to_plain(x):
    if isinstance(x, dict):
        return {k: _to_plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_to_plain(v) for v in x]
    return x


def _deep_merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict) and k != "custom_profiles":
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def _load_yaml_tree(path: str) -> dict:
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    parents = data.pop("inherit", []) or []
    merged: dict = {}
    for p in parents:
        merged = _deep_merge(merged, _load_yaml_tree(os.path.join(os.path.dirname(path), p)))
    return _deep_merge(merged, data)


def _build(cls, data: dict):
    if not dataclasses.is_dataclass(cls):
        return data
    kwargs = {}
    known = {f.name: f for f in dataclasses.fields(cls)}
    for k, v in data.items():
        if k not in known:
            raise KeyError(f"Unknown config key '{k}' for {cls.__name__}")
        ftype = known[k].type
        sub = _DATACLASS_FIELDS.get((cls.__name__, k))
        if sub is not None and isinstance(v, dict):
            kwargs[k] = _build(sub, v)
        elif isinstance(v, list) and isinstance(ftype, str) and ftype.startswith("tuple"):
            kwargs[k] = tuple(v)
        else:
            kwargs[k] = v
    return cls(**kwargs)


_DATACLASS_FIELDS = {
    ("ExperimentConfig", "env"): EnvConfig,
    ("ExperimentConfig", "model"): ModelConfig,
    ("ExperimentConfig", "train"): TrainConfig,
    ("ExperimentConfig", "eval"): EvalConfig,
    ("EnvConfig", "sensors"): SensorConfig,
    ("EnvConfig", "dynamics"): DynamicsConfig,
    ("EnvConfig", "mover"): MoverConfig,
    ("EnvConfig", "randomization"): RandomizationConfig,
}


def apply_overrides(data: dict, overrides: list[str]) -> dict:
    data = copy.deepcopy(data)
    for ov in overrides or []:
        if "=" not in ov:
            raise ValueError(f"Override must be key=value, got '{ov}'")
        key, val = ov.split("=", 1)
        node = data
        parts = key.split(".")
        for p in parts[:-1]:
            node = node.setdefault(p, {})
        node[parts[-1]] = yaml.safe_load(val)
    return data


def load_config(path: str | None = None, overrides: list[str] | None = None) -> ExperimentConfig:
    data = _load_yaml_tree(path) if path else {}
    data = apply_overrides(data, overrides or [])
    return _build(ExperimentConfig, data)


def config_from_dict(data: dict) -> ExperimentConfig:
    return _build(ExperimentConfig, data)


def save_config(cfg: ExperimentConfig, path: str):
    with open(path, "w") as f:
        yaml.safe_dump(cfg.to_dict(), f, sort_keys=False)
