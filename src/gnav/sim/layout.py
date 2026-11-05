"""Reproducible per-episode scenario sampling.

Every episode is identified by ``(seed, env_id, episode_idx)``. Each randomisation *source* (obstacles, robot
init, goal, mover, dynamics) draws from its own ``numpy`` stream keyed by
``SeedSequence([seed, source_id, env_id, episode_idx])``. Consequences:

* An episode's scenario does not depend on which policy runs or on when other envs finish, so two policies (or
  two dynamics profiles) evaluated with the same seed face identical scenarios: *matched-seed comparisons*.
* Disabling a source replaces its key with a fixed nominal key ``[NOMINAL, source_id, 0, 0]``: that source then
  draws the same values in every episode and env, and the other sources' streams are unchanged.
  (Rejection sampling means a fixed source is exactly constant only when the sources it is conditioned on,
  i.e. sampled before it, are also fixed. Order: obstacles -> robot_init -> goal -> mover -> dynamics.)
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .assets import MOVER_RADIUS, ROBOT_RADIUS

SOURCE_IDS = {"obstacles": 1, "robot_init": 2, "goal": 3, "mover": 4, "dynamics": 5, "obs_noise": 6}
NOMINAL = 0x5EED


def source_rng(seed: int, source: str, env_id: int, episode_idx: int, enabled: bool) -> np.random.Generator:
    key = [seed, SOURCE_IDS[source], env_id, episode_idx] if enabled else [NOMINAL, SOURCE_IDS[source], 0, 0]
    return np.random.default_rng(np.random.SeedSequence(key))


@dataclass(frozen=True)
class ObstacleSpec:
    name: str
    half_x: float
    half_y: float


PILLAR_SIZES = [(0.25, 0.25), (0.35, 0.20), (0.20, 0.40), (0.30, 0.30)]
OCCLUDER_SIZES = [(1.20, 0.08), (0.08, 1.20)]


def obstacle_specs(n_pillars: int, n_occluders: int) -> list[ObstacleSpec]:
    specs = [ObstacleSpec(f"occluder{i}", *OCCLUDER_SIZES[i % len(OCCLUDER_SIZES)]) for i in range(n_occluders)]
    specs += [ObstacleSpec(f"pillar{i}", *PILLAR_SIZES[i % len(PILLAR_SIZES)]) for i in range(n_pillars)]
    return specs


@dataclass
class Scenario:
    obstacle_xy: np.ndarray  # (K, 2)
    robot_xy: np.ndarray  # (2,)
    robot_yaw: float
    goal_xy: np.ndarray  # (2,)
    mover_a: np.ndarray  # (2,) patrol endpoint A
    mover_b: np.ndarray  # (2,) patrol endpoint B
    mover_speed: float
    mover_phase: float  # in [0, 1): initial fraction along A->B
    mover_dir: int  # +1 heading to B, -1 heading to A
    profile_id: int
    dynamics: dict


def point_box_dist(p: np.ndarray, c: np.ndarray, h: np.ndarray) -> np.ndarray:
    """Distance from points p (..., 2) to axis-aligned boxes (centre c, half extents h); 0 inside."""
    d = np.abs(p - c) - h
    return np.linalg.norm(np.maximum(d, 0.0), axis=-1) + np.minimum(np.max(d, axis=-1), 0.0)


def _clear(p, centers, halves, margin) -> bool:
    if len(centers) == 0:
        return True
    return bool(np.all(point_box_dist(p[None], np.asarray(centers), np.asarray(halves)) > margin))


def sample_scenario(
    *,
    seed: int,
    env_id: int,
    episode_idx: int,
    specs: list[ObstacleSpec],
    arena_half: float,
    goal_radius: float,
    min_start_goal_dist: float,
    mover_enabled: bool,
    mover_speed_range: tuple[float, float],
    mover_len_range: tuple[float, float],
    rand: dict[str, bool],
    dynamics_sampler,  # callable(rng) -> (profile_id, params)
    max_tries: int = 500,
) -> Scenario:
    halves = np.array([[s.half_x, s.half_y] for s in specs], dtype=np.float64).reshape(-1, 2)

    # --- obstacles: inside arena, pairwise gap >= 0.8 m so the robot can pass between them
    rng = source_rng(seed, "obstacles", env_id, episode_idx, rand["obstacles"])
    centers: list[np.ndarray] = []
    for k in range(len(specs)):
        for _ in range(max_tries):
            lim = arena_half - halves[k] - 0.6
            c = rng.uniform(-lim, lim)
            # Gap between two AABBs == distance from c to box j inflated by box k's half extents (Minkowski sum).
            ok = all(
                point_box_dist(c[None], centers[j], halves[j] + halves[k]).item() > 0.8 for j in range(len(centers))
            )
            if ok:
                centers.append(c)
                break
        else:
            raise RuntimeError("obstacle placement failed")
    obstacle_xy = np.array(centers).reshape(-1, 2)

    def free(p, margin):
        return np.all(np.abs(p) < arena_half - margin) and _clear(p, obstacle_xy, halves, margin)

    def all_free(pts, margin):  # vectorised free() over (P, 2) points
        if not np.all(np.abs(pts) < arena_half - margin):
            return False
        if len(obstacle_xy) == 0:
            return True
        return bool(np.all(point_box_dist(pts[:, None], obstacle_xy[None], halves[None]) > margin))

    # --- robot start
    rng = source_rng(seed, "robot_init", env_id, episode_idx, rand["robot_init"])
    for _ in range(max_tries):
        robot_xy = rng.uniform(-arena_half + 0.6, arena_half - 0.6, size=2)
        if free(robot_xy, ROBOT_RADIUS + 0.3):
            break
    else:
        raise RuntimeError("robot placement failed")
    robot_yaw = float(rng.uniform(-math.pi, math.pi))

    # --- goal
    rng = source_rng(seed, "goal", env_id, episode_idx, rand["goal"])
    for _ in range(max_tries):
        goal_xy = rng.uniform(-arena_half + 0.6, arena_half - 0.6, size=2)
        if free(goal_xy, goal_radius + 0.2) and np.linalg.norm(goal_xy - robot_xy) >= min_start_goal_dist:
            break
    else:
        raise RuntimeError("goal placement failed")

    # --- mover: patrol segment that crosses the start->goal line, kept clear of obstacles, start and goal
    rng = source_rng(seed, "mover", env_id, episode_idx, rand["mover"])
    mover_a = mover_b = np.array([arena_half + 5.0, arena_half + 5.0])
    mover_speed, mover_phase, mover_dir = 0.0, 0.0, 1
    if mover_enabled:
        sg = goal_xy - robot_xy
        perp = np.array([-sg[1], sg[0]]) / (np.linalg.norm(sg) + 1e-9)
        for _ in range(max_tries):
            p = robot_xy + rng.uniform(0.35, 0.75) * sg
            ang = rng.uniform(-0.5, 0.5)
            d = np.array([math.cos(ang) * perp[0] - math.sin(ang) * perp[1], math.sin(ang) * perp[0] + math.cos(ang) * perp[1]])
            L = rng.uniform(*mover_len_range)
            off = rng.uniform(-0.3, 0.3) * L
            a, b = p + d * (off - L / 2), p + d * (off + L / 2)
            pts = a[None] + np.linspace(0, 1, 25)[:, None] * (b - a)[None]
            if not all_free(pts, MOVER_RADIUS + 0.15):
                continue
            if np.min(np.linalg.norm(pts - robot_xy, axis=-1)) < 1.0 or np.min(np.linalg.norm(pts - goal_xy, axis=-1)) < 0.7:
                continue
            mover_a, mover_b = a, b
            mover_speed = float(rng.uniform(*mover_speed_range))
            mover_phase = float(rng.uniform(0, 1))
            mover_dir = int(rng.choice([-1, 1]))
            break
        # If no valid segment exists (rare, e.g. cluttered corridor), the mover idles out of the arena.

    rng = source_rng(seed, "dynamics", env_id, episode_idx, rand["dynamics"])
    profile_id, dyn = dynamics_sampler(rng)

    return Scenario(
        obstacle_xy=obstacle_xy,
        robot_xy=robot_xy,
        robot_yaw=robot_yaw,
        goal_xy=goal_xy,
        mover_a=mover_a,
        mover_b=mover_b,
        mover_speed=mover_speed,
        mover_phase=mover_phase,
        mover_dir=mover_dir,
        profile_id=profile_id,
        dynamics=dyn,
    )


def make_scenario(
    *,
    robot_xy,
    robot_yaw: float,
    goal_xy,
    obstacle_xy,
    mover_a=None,
    mover_b=None,
    mover_speed: float = 0.0,
    mover_phase: float = 0.0,
    mover_dir: int = 1,
    dynamics: dict,
    profile_id: int = 0,
) -> Scenario:
    """Explicit scenario for controlled experiments and tests (mover parked outside the arena by default)."""
    park = np.array([20.0, 20.0])
    return Scenario(
        obstacle_xy=np.asarray(obstacle_xy, dtype=np.float64).reshape(-1, 2),
        robot_xy=np.asarray(robot_xy, dtype=np.float64),
        robot_yaw=float(robot_yaw),
        goal_xy=np.asarray(goal_xy, dtype=np.float64),
        mover_a=park if mover_a is None else np.asarray(mover_a, dtype=np.float64),
        mover_b=park if mover_b is None else np.asarray(mover_b, dtype=np.float64),
        mover_speed=float(mover_speed),
        mover_phase=float(mover_phase),
        mover_dir=int(mover_dir),
        profile_id=int(profile_id),
        dynamics=dict(dynamics),
    )
