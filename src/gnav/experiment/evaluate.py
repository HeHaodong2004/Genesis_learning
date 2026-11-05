"""Evaluation on a fixed, policy-independent episode set (matched seeds).

The episode set is ``{(env_id, k) : env_id < B, k < ceil(n_episodes / B)}`` truncated to ``n_episodes``, each
scenario keyed by ``(eval_seed, env_id, k)``. Every policy / dynamics variant evaluated with the same
``eval_seed`` and env settings sees exactly the same scenarios, so per-episode results can be paired."""

from __future__ import annotations

import csv
import math
import os

import numpy as np
import torch

from ..config import ExperimentConfig
from ..learning.diagnostics import linear_probe, privileged_targets
from ..learning.recorder import TrajectoryRecorder
from ..runtime import init_genesis, seed_everything
from .policies import AgentPolicy, make_policy
from .run import make_run_dir, write_json

STAT_KEYS = ("success", "collided", "collisions", "spl", "return", "length", "path_length", "start_goal_dist",
             "final_dist", "min_clearance", "near_collision_steps", "mover_visible_frac", "profile_id")


def evaluate(cfg: ExperimentConfig, run_dir: str | None = None, policy_name: str | None = None, env=None,
             record=None, max_steps_factor: float = 1.05):
    init_genesis(cfg.backend, seed=cfg.eval_seed)
    seed_everything(cfg.eval_seed)
    from ..sim.env import NavEnv

    ec = cfg.eval
    policy_name = policy_name or ec.policy
    run_dir = make_run_dir(cfg, f"eval-{policy_name}", run_dir)
    if env is None:
        env = NavEnv(cfg.env, seed=cfg.eval_seed)
    B = env.B
    per_env = math.ceil(ec.n_episodes / B)
    # Episode j of the set runs in env (j % B) as that env's (j // B)-th episode.
    quota = np.array([ec.n_episodes // B + (1 if e < ec.n_episodes % B else 0) for e in range(B)], dtype=np.int64)
    policy = make_policy(policy_name, env, cfg, ec.checkpoint)
    record = ec.record_trajectories if record is None else record
    rec = TrajectoryRecorder(env, os.path.join(run_dir, "trajectories") if record else None,
                             meta={"policy": policy_name, "config_digest": cfg.digest()})

    obs = env.reset(seed=cfg.eval_seed)
    first = torch.ones(B, dtype=torch.bool, device=env.device)
    rec.start(np.arange(B), obs)
    finished = np.zeros(B, dtype=np.int64)
    rows = []
    probe_x, probe_y = [], {}
    max_steps = int(per_env * cfg.env.max_episode_steps * max_steps_factor) + 10
    for _ in range(max_steps):
        with torch.no_grad():
            a = policy(obs, first)
        obs, r, term, trunc, info = env.step(a, auto_reset=False)
        rec.step(a, obs, r, info)
        if isinstance(policy, AgentPolicy):  # belief-probe data (privileged targets used for diagnostics only)
            probe_x.append(policy.last["belief"].cpu())
            for k, v in privileged_targets(env.privileged_state()).items():
                probe_y.setdefault(k, []).append(v.cpu())
        done = (term | trunc)
        ids = torch.nonzero(done).reshape(-1).cpu().numpy()
        if ids.size:
            ep = {k: v.cpu().numpy() for k, v in info["episode"].items()}
            keep = [i for i in ids if finished[i] < quota[i]]
            for i in keep:
                rows.append({"env_id": int(i), "episode_idx": int(ep["episode_idx"][i]),
                             **{k: float(ep[k][i]) for k in STAT_KEYS}})
                finished[i] += 1
            rec.finish(keep, info["episode"])
            obs = env.reset_done(done, obs)
            restart = [i for i in ids if finished[i] < quota[i]]
            rec.start(restart, obs)
        first = done
        if (finished >= quota).all():
            break
    else:
        raise RuntimeError("evaluation did not finish all episodes")

    rows.sort(key=lambda r: (r["env_id"], r["episode_idx"]))
    with open(os.path.join(run_dir, "episodes.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    summary = {"policy": policy_name, "n_episodes": len(rows), "eval_seed": cfg.eval_seed,
               "config_digest": cfg.digest(), "metrics": aggregate(rows)}
    if probe_x:
        x = torch.cat(probe_x)
        summary["belief_probes"] = {k: linear_probe(x, torch.cat(v)) for k, v in probe_y.items()}
    write_json(os.path.join(run_dir, "metrics.json"), summary)
    return run_dir, summary, rows


def aggregate(rows):
    out = {}
    for k in STAT_KEYS:
        if k == "profile_id":
            continue
        v = np.array([r[k] for r in rows], dtype=np.float64)
        v = v[np.isfinite(v)]
        if v.size == 0:
            continue
        se = v.std(ddof=1) / math.sqrt(v.size) if v.size > 1 else 0.0
        out[k] = {"mean": float(v.mean()), "ci95": float(1.96 * se), "n": int(v.size)}
    return out


def paired_comparison(rows_a, rows_b, keys=("success", "collided", "spl", "length", "min_clearance")):
    """Per-episode paired differences (b - a) over episodes present in both (matched by env_id, episode_idx)."""
    ia = {(r["env_id"], r["episode_idx"]): r for r in rows_a}
    ib = {(r["env_id"], r["episode_idx"]): r for r in rows_b}
    common = sorted(set(ia) & set(ib))
    out = {"n_paired": len(common)}
    for k in keys:
        d = np.array([ib[c][k] - ia[c][k] for c in common], dtype=np.float64)
        d = d[np.isfinite(d)]
        se = d.std(ddof=1) / math.sqrt(d.size) if d.size > 1 else 0.0
        out[k] = {"mean_diff": float(d.mean()) if d.size else float("nan"), "ci95": float(1.96 * se)}
    return out
