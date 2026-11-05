"""Per-episode trajectory recording (observations, actions and privileged ground truth) to .npz files."""

from __future__ import annotations

import json
import os

import numpy as np
import torch

from ..sim import assets

PRIV_KEYS = ("robot_pose", "robot_vel_world", "mover_xy", "mover_vel", "contact", "clearance", "mover_visible",
             "actuator_ref")
STATIC_KEYS = ("goal_xy", "obstacle_xy", "obstacle_half", "mover_a", "mover_b", "mover_speed", "profile_id",
               "dyn_params")


class TrajectoryRecorder:
    """Records whole episodes for a subset of envs. Usage per control step (with ``auto_reset=False``)::

        rec.start(all_ids, obs)                       # after env.reset()
        obs, r, term, trunc, info = env.step(a, auto_reset=False)
        rec.step(a, obs, r, info)
        done_ids = ...; rec.finish(done_ids, info["episode"])
        obs = env.reset_done(done); rec.start(done_ids, obs)
    """

    def __init__(self, env, out_dir: str | None, env_ids=None, obs_keys=("rays", "goal", "proprio", "bump"),
                 record_depth=False, meta=None, max_episodes=None):
        self.env = env
        self.out_dir = out_dir
        self.env_ids = list(range(env.B)) if env_ids is None else list(env_ids)
        self.obs_keys = [k for k in obs_keys if k in env.obs_shapes]
        if record_depth and "depth" in env.obs_shapes:
            self.obs_keys.append("depth")
        self.meta = dict(meta or {})
        self.max_episodes = max_episodes
        self.buf: dict[int, dict] = {}
        self.episodes: list[dict] = []
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

    def _snapshot(self, obs, ids):
        ps = self.env.privileged_state()
        idx = torch.as_tensor(ids, device=self.env.device)
        priv = {k: ps[k][idx].float().cpu().numpy() for k in PRIV_KEYS}
        static = {k: ps[k][idx].float().cpu().numpy() for k in STATIC_KEYS}
        o = {k: obs[k][idx].float().cpu().numpy() for k in self.obs_keys}
        return priv, static, o

    def start(self, ids, obs):
        ids = [i for i in np.asarray(ids).reshape(-1).tolist() if i in self.env_ids]
        if not ids or self.full:
            return
        priv, static, o = self._snapshot(obs, ids)
        ep = self.env.episode_idx_t[torch.as_tensor(ids, device=self.env.device)].cpu().numpy()
        for j, i in enumerate(ids):
            self.buf[i] = {
                "env_id": i, "episode_idx": int(ep[j]),
                "priv": {k: [v[j]] for k, v in priv.items()},
                "static": {k: v[j] for k, v in static.items()},
                "obs": {k: [v[j]] for k, v in o.items()},
                "action": [], "reward": [],
            }

    def step(self, action, obs, reward, info):
        ids = list(self.buf)
        if not ids:
            return
        priv, _, o = self._snapshot(obs, ids)
        idx = torch.as_tensor(ids, device=self.env.device)
        a = action[idx].float().cpu().numpy()
        r = reward[idx].float().cpu().numpy()
        for j, i in enumerate(ids):
            b = self.buf[i]
            for k in priv:
                b["priv"][k].append(priv[k][j])
            for k in o:
                b["obs"][k].append(o[k][j])
            b["action"].append(a[j])
            b["reward"].append(r[j])

    @property
    def full(self):
        return self.max_episodes is not None and len(self.episodes) >= self.max_episodes

    def finish(self, ids, episode_stats: dict):
        ids = [i for i in np.asarray(ids).reshape(-1).tolist() if i in self.buf]
        if not ids:
            return []
        idx = torch.as_tensor(ids, device=self.env.device)
        stats = {k: v[idx].float().cpu().numpy() for k, v in episode_stats.items()}
        done = []
        for j, i in enumerate(ids):
            b = self.buf.pop(i)
            if self.full:
                continue
            ep = {
                "env_id": i, "episode_idx": b["episode_idx"],
                "stats": {k: float(v[j]) for k, v in stats.items()},
                **{k: np.stack(v) for k, v in b["priv"].items()},
                **{k: np.asarray(v) for k, v in b["static"].items()},
                **{"obs_" + k: np.stack(v) for k, v in b["obs"].items()},
                "action": np.stack(b["action"]), "reward": np.asarray(b["reward"]),
            }
            self.episodes.append(ep)
            done.append(ep)
            if self.out_dir:
                self.save(ep)
        return done

    def episode_meta(self, ep):
        env = self.env
        meta = {
            **self.meta,
            "env_id": ep["env_id"], "episode_idx": ep["episode_idx"], "seed": env.seed, "stats": ep["stats"],
            "control_dt": env.control_dt, "arena_half": env.cfg.arena_half_size, "goal_radius": env.cfg.goal_radius,
            "robot_radius": assets.ROBOT_RADIUS, "mover_radius": assets.MOVER_RADIUS,
            "max_range": env.cfg.sensors.max_range, "profile": env.profile_names[int(ep["profile_id"])],
        }
        if env.ray_sensor is not None:
            meta["ray_angles"] = env.ray_angles().cpu().tolist()
        return meta

    def save(self, ep):
        name = f"seed{self.env.seed}_env{ep['env_id']:04d}_ep{ep['episode_idx']:04d}"
        arrays = {k: v for k, v in ep.items() if isinstance(v, np.ndarray)}
        np.savez_compressed(os.path.join(self.out_dir, name + ".npz"), **arrays)
        with open(os.path.join(self.out_dir, name + ".json"), "w") as f:
            json.dump(self.episode_meta(ep), f, indent=1)


def load_episode(path_npz: str):
    data = dict(np.load(path_npz))
    with open(path_npz[:-4] + ".json") as f:
        meta = json.load(f)
    return data, meta
