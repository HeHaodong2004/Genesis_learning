"""Batched partially observable navigation environment on Genesis.

Information boundary
--------------------
``step``/``reset`` return ``obs``, a dict containing ONLY onboard-sensor quantities (``OBS_KEYS``):

* ``depth``   (B, 1, H, W) forward depth camera (~90 deg HFOV), ray distance / max_range, ray-cast by Genesis
* ``rays``    (B, N)       planar range scan over a configurable FOV, distance / max_range
* ``goal``    (B, 3)       relative goal in the robot frame: [dist / arena_diameter, cos(bearing), sin(bearing)]
* ``proprio`` (B, 5)       measured body-frame [v_fwd, v_lat, yaw_rate] (fixed normalisation) + previous action
* ``bump``    (B, 1)       onboard bumper (hull contact flag; no identity / location of the contacted object)

The complete simulator state (global poses, obstacle layout, mover state and waypoints, dynamics parameters,
actuator internals, analytic clearance, mover visibility) is only available through ``privileged_state()``, for
diagnostics, oracles and evaluation. ``info`` returned by ``step`` carries only outcome flags and per-episode
statistics, which training code may use for logging but must not feed to the policy.
"""

from __future__ import annotations

import math

import numpy as np
import torch

from ..config import EnvConfig
from . import assets
from .dynamics import PROFILES, ActuatorModel, profile_from_dict, sample_dynamics, wrap_angle
from .geometry import clearance, ray_circle_t
from .layout import obstacle_specs, sample_scenario, source_rng

OBS_KEYS = ("depth", "rays", "goal", "proprio", "bump")
PARAM_ORDER = ("v_max", "v_min", "w_max", "a_max", "alpha_max", "tau_v", "tau_w", "delay_steps")
V_NORM, W_NORM = 1.0, 2.5  # fixed proprio normalisation, identical for every profile (no parameter leak)


class NavEnv:
    def __init__(self, cfg: EnvConfig, seed: int, render: bool = False, render_res=(480, 480), camera="overview"):
        import genesis as gs

        self.gs = gs
        self.cfg = cfg
        self.seed = int(seed)
        self.B = int(cfg.n_envs)
        self.device = gs.device
        self.render_enabled = render
        sc = cfg.sensors

        # ---------------- dynamics profiles
        self.profiles = dict(PROFILES)
        self.profiles.update({k: profile_from_dict(v) for k, v in cfg.dynamics.custom_profiles.items()})
        self.profile_names = list(cfg.dynamics.profiles)
        n_p = len(self.profile_names)
        self.profile_probs = list(cfg.dynamics.profile_probs or [1.0 / n_p] * n_p)
        need = max(self.profiles[p].delay_steps for p in self.profile_names)
        need += cfg.dynamics.delay_jitter if cfg.randomization.dynamics else 0
        if need > cfg.dynamics.max_delay_steps:
            raise ValueError(f"dynamics.max_delay_steps={cfg.dynamics.max_delay_steps} < required {need}")

        self.specs = obstacle_specs(cfg.n_pillars, cfg.n_occluders)
        self.K = len(self.specs)
        H = cfg.wall_height
        A = cfg.arena_half_size

        # ---------------- scene
        scene = gs.Scene(
            sim_options=gs.options.SimOptions(dt=cfg.sim_dt),
            rigid_options=gs.options.RigidOptions(enable_self_collision=False),
            vis_options=gs.options.VisOptions(rendered_envs_idx=[0], show_world_frame=False),
            show_viewer=False,
        )
        scene.add_entity(gs.morphs.Plane(), surface=gs.surfaces.Default(color=(0.85, 0.85, 0.82)))
        wall_surf = gs.surfaces.Default(color=(0.55, 0.55, 0.6))
        t = 0.1
        for pos, size in [
            ((A + t / 2, 0, H / 2), (t, 2 * A + 2 * t, H)),
            ((-A - t / 2, 0, H / 2), (t, 2 * A + 2 * t, H)),
            ((0, A + t / 2, H / 2), (2 * A, t, H)),
            ((0, -A - t / 2, H / 2), (2 * A, t, H)),
        ]:
            scene.add_entity(gs.morphs.Box(pos=pos, size=size, fixed=True, batch_fixed_verts=False), surface=wall_surf)
        obs_surf = gs.surfaces.Default(color=(0.35, 0.35, 0.4))
        self.obstacle_ents = []
        for k, s in enumerate(self.specs):
            # Parked outside the arena until the first reset positions it per environment.
            ent = scene.add_entity(
                gs.morphs.Box(pos=(A + 5 + 3 * k, A + 5, H / 2), size=(2 * s.half_x, 2 * s.half_y, H), fixed=True),
                surface=obs_surf,
            )
            self.obstacle_ents.append(ent)
        self.robot = scene.add_entity(
            gs.morphs.MJCF(file=assets.write_asset(assets.robot_mjcf(cfg.robot_mass), f"robot_{cfg.robot_mass}.xml"))
        )
        self.mover = None
        if cfg.mover.enabled:
            self.mover = scene.add_entity(
                gs.morphs.MJCF(file=assets.write_asset(assets.mover_mjcf(cfg.mover.mass), f"mover_{cfg.mover.mass}.xml"))
            )
        self.goal_marker = None
        if render:
            # Visual only (no collision geometry): invisible to the ray-cast sensors.
            self.goal_marker = scene.add_entity(
                gs.morphs.Cylinder(
                    pos=(A + 5, -A - 5, 0.01), radius=cfg.goal_radius, height=0.02, fixed=True, collision=False
                ),
                surface=gs.surfaces.Default(color=(0.106, 0.686, 0.478)),
            )

        base_local = self.robot.get_link("base").idx_local
        mount = (0.0, 0.0, sc.mount_height)
        self.depth_sensor = None
        if sc.depth_enabled:
            self.depth_sensor = scene.add_sensor(
                gs.sensors.DepthCamera(
                    pattern=gs.sensors.DepthCameraPattern(res=tuple(sc.depth_res), fov_horizontal=sc.depth_hfov_deg),
                    entity_idx=self.robot.idx,
                    link_idx_local=base_local,
                    pos_offset=mount,
                    max_range=sc.max_range,
                    return_points=False,
                )
            )
        self.ray_sensor = None
        if sc.rays_enabled:
            self.ray_pattern = gs.sensors.SphericalPattern(fov=(sc.rays_fov_deg, 0.0), n_points=(sc.rays_n, 1))
            self.ray_sensor = scene.add_sensor(
                gs.sensors.Raycaster(
                    pattern=self.ray_pattern,
                    entity_idx=self.robot.idx,
                    link_idx_local=base_local,
                    pos_offset=mount,
                    max_range=sc.max_range,
                    return_points=False,
                )
            )
        self.contact_sensor = scene.add_sensor(gs.sensors.Contact(entity_idx=self.robot.idx, link_idx_local=base_local))

        self.camera = None
        if render:
            if camera == "topdown":
                self.camera = scene.add_camera(
                    res=render_res, pos=(0.0, 0.0, 2.6 * A), lookat=(0, 0, 0), up=(0, 1, 0), fov=46, GUI=False
                )
            else:
                self.camera = scene.add_camera(
                    res=render_res, pos=(0.0, -1.9 * A, 2.1 * A), lookat=(0, -0.1 * A, 0), fov=50, GUI=False
                )

        scene.build(n_envs=self.B)
        self.scene = scene

        # ---------------- actuators (finite force limits: contacts can stall the robot)
        dev = self.device
        self.robot.set_dofs_kv(torch.tensor([cfg.servo_kv_lin, cfg.servo_kv_lin, cfg.servo_kv_ang], device=dev))
        f = torch.tensor([cfg.robot_max_force, cfg.robot_max_force, cfg.robot_max_torque], device=dev)
        self.robot.set_dofs_force_range(-f, f)
        if self.mover is not None:
            self.mover.set_dofs_kv(torch.tensor([1000.0, 1000.0], device=dev))
            fm = torch.full((2,), cfg.mover.max_force, device=dev)
            self.mover.set_dofs_force_range(-fm, fm)

        self.actuator = ActuatorModel(self.B, cfg.dynamics.max_delay_steps, dev)
        # Feed-forward gains: mass / kv and yaw inertia / kv (same inertia as the MJCF hull).
        self._ff_lin = cfg.robot_mass / cfg.servo_kv_lin
        self._ff_ang = 0.5 * cfg.robot_mass * assets.ROBOT_RADIUS**2 / cfg.servo_kv_ang

        # ---------------- state buffers
        B, K = self.B, self.K
        f32 = dict(device=dev, dtype=torch.float32)
        self.obstacle_half = torch.tensor([[s.half_x, s.half_y] for s in self.specs], **f32).reshape(K, 2)
        self.obstacle_xy = torch.zeros(B, K, 2, **f32)
        self.goal_xy = torch.zeros(B, 2, **f32)
        self.mover_a = torch.zeros(B, 2, **f32)
        self.mover_b = torch.zeros(B, 2, **f32)
        self.mover_speed = torch.zeros(B, **f32)
        self.mover_dir = torch.ones(B, **f32)
        self.profile_id = torch.zeros(B, device=dev, dtype=torch.long)
        self.step_count = torch.zeros(B, device=dev, dtype=torch.long)
        self.prev_action = torch.zeros(B, 2, **f32)
        self.prev_xy = torch.zeros(B, 2, **f32)
        self.prev_dist = torch.zeros(B, **f32)
        self.last_contact = torch.zeros(B, device=dev, dtype=torch.bool)
        self.last_clearance = torch.zeros(B, **f32)
        self.last_mover_visible = torch.zeros(B, device=dev, dtype=torch.bool)
        self.episode_idx = np.zeros(B, dtype=np.int64)  # host-side: drives scenario seeds without device syncs
        self.episode_idx_t = torch.zeros(B, device=dev, dtype=torch.long)
        self._stat_names = ("ret", "len", "path", "collisions", "near", "min_clear", "mover_vis", "start_dist")
        self.stats = {n: torch.zeros(B, **f32) for n in self._stat_names}
        self.noise_gen = torch.Generator(device=dev)
        self.noise_gen.manual_seed(int(source_rng(self.seed, "obs_noise", 0, 0, True).integers(2**62)))
        self._all_ids = np.arange(B)
        if self.ray_sensor is not None:
            # Ray directions in the robot frame, read from the sensor's own pattern (no convention assumptions).
            d = self.ray_pattern.ray_dirs.reshape(-1, 3)[:, :2].to(dev)
            self.ray_dirs_local = d / d.norm(dim=-1, keepdim=True)

    # ------------------------------------------------------------------------------------------ spaces
    @property
    def obs_shapes(self) -> dict[str, tuple[int, ...]]:
        sc = self.cfg.sensors
        shapes = {"goal": (3,), "proprio": (5,), "bump": (1,)}
        if self.depth_sensor is not None:
            shapes["depth"] = (1, sc.depth_res[1], sc.depth_res[0])
        if self.ray_sensor is not None:
            shapes["rays"] = (sc.rays_n,)
        return shapes

    action_dim = 2

    # ------------------------------------------------------------------------------------------ reset
    def reset(self, seed: int | None = None) -> dict[str, torch.Tensor]:
        """Reset all envs and restart episode counters (so ``reset(seed)`` replays the same scenario sequence)."""
        if seed is not None:
            self.seed = int(seed)
            self.noise_gen.manual_seed(int(source_rng(self.seed, "obs_noise", 0, 0, True).integers(2**62)))
        self.episode_idx[:] = 0
        self.reset_envs(self._all_ids)
        return self._compute_obs()

    def _sample(self, env_id: int):
        return self.sample_scenario(int(env_id), int(self.episode_idx[env_id]))

    def sample_scenario(self, env_id: int, episode_idx: int, seed: int | None = None):
        """The scenario of episode ``(seed, env_id, episode_idx)`` under this env's config (pure function).

        ``env_id`` is only a seed coordinate, so a scenario screened in a large batch can be replayed in any env
        of another NavEnv (e.g. a single-env render instance) via ``apply_scenarios``."""
        c = self.cfg
        rnd = c.randomization
        return sample_scenario(
            seed=self.seed if seed is None else int(seed),
            env_id=int(env_id),
            episode_idx=int(episode_idx),
            specs=self.specs,
            arena_half=c.arena_half_size,
            goal_radius=c.goal_radius,
            min_start_goal_dist=c.min_start_goal_dist,
            mover_enabled=c.mover.enabled,
            mover_speed_range=tuple(c.mover.speed_range),
            mover_len_range=tuple(c.mover.path_length_range),
            rand={"obstacles": rnd.obstacles, "robot_init": rnd.robot_init, "goal": rnd.goal, "mover": rnd.mover,
                  "dynamics": rnd.dynamics},
            dynamics_sampler=lambda rng: sample_dynamics(
                self.profile_names, self.profile_probs, rnd.dynamics, c.dynamics.scale_range,
                c.dynamics.delay_jitter, rng, self.profiles,
            ),
        )

    def reset_envs(self, env_ids) -> None:
        """Re-sample and re-place the given envs (host-side indices). Does not refresh sensors; see ``_refresh``."""
        env_ids = np.asarray(env_ids, dtype=np.int64).reshape(-1)
        if env_ids.size == 0:
            return
        self.apply_scenarios(env_ids, [self._sample(i) for i in env_ids])

    def apply_scenarios(self, env_ids, scen: list) -> None:
        """Place explicit ``Scenario`` objects into the given envs and start new episodes there.

        Used by ``reset_envs`` and directly by controlled experiments / tests (scripted layouts, counterfactual
        probes). Everything is placed with reset-time setters; nothing is moved during an episode."""
        env_ids = np.asarray(env_ids, dtype=np.int64).reshape(-1)
        dev = self.device
        T = lambda x: torch.as_tensor(np.asarray(x), dtype=torch.float32, device=dev)  # noqa: E731
        ids = torch.as_tensor(env_ids, device=dev, dtype=torch.long)
        n = len(env_ids)
        H = self.cfg.wall_height

        obs_xy = T(np.stack([s.obstacle_xy for s in scen]))  # (n, K, 2)
        self.obstacle_xy[ids] = obs_xy
        for k, ent in enumerate(self.obstacle_ents):
            pos = torch.cat([obs_xy[:, k], torch.full((n, 1), H / 2, device=dev)], dim=-1)
            ent.set_pos(pos, envs_idx=ids)

        q0 = T([[s.robot_xy[0], s.robot_xy[1], s.robot_yaw] for s in scen])
        self.robot.set_dofs_position(q0, envs_idx=ids, zero_velocity=True)
        self.goal_xy[ids] = T(np.stack([s.goal_xy for s in scen]))
        if self.goal_marker is not None:
            gpos = torch.cat([self.goal_xy[ids], torch.full((n, 1), 0.01, device=dev)], dim=-1)
            self.goal_marker.set_pos(gpos, envs_idx=ids)

        a, b = T(np.stack([s.mover_a for s in scen])), T(np.stack([s.mover_b for s in scen]))
        self.mover_a[ids], self.mover_b[ids] = a, b
        self.mover_speed[ids] = T([s.mover_speed for s in scen])
        self.mover_dir[ids] = T([float(s.mover_dir) for s in scen])
        if self.mover is not None:
            ph = T([s.mover_phase for s in scen])[:, None]
            self.mover.set_dofs_position(a + ph * (b - a), envs_idx=ids, zero_velocity=True)

        self.profile_id[ids] = torch.as_tensor([s.profile_id for s in scen], device=dev)
        self.actuator.set_params(ids, {p: T([s.dynamics[p] for s in scen]) for p in PARAM_ORDER})
        self.actuator.reset_state(ids)

        self.step_count[ids] = 0
        self.prev_action[ids] = 0.0
        self.prev_xy[ids] = q0[:, :2]
        d0 = (self.goal_xy[ids] - q0[:, :2]).norm(dim=-1)
        self.prev_dist[ids] = d0
        self.last_contact[ids] = False
        for k in self._stat_names:
            self.stats[k][ids] = 0.0
        self.stats["min_clear"][ids] = float("inf")
        self.stats["start_dist"][ids] = d0
        self.episode_idx_t[ids] = torch.as_tensor(self.episode_idx[env_ids], device=dev)
        self.episode_idx[env_ids] += 1
        self._refresh()

    def _refresh(self):
        """Recompute sensor readings for the current state without advancing physics (used after resets).

        Uses Genesis's sensor manager directly (private API, Genesis 1.4.5): ``scene.step()`` would also advance
        the physics of every other environment."""
        self.scene._sim._sensor_manager.step()
        self._update_privileged_diagnostics()

    # ------------------------------------------------------------------------------------------ step
    def _mover_control(self):
        if self.mover is None:
            return
        p = self.mover.get_dofs_position()
        tgt = torch.where(self.mover_dir[:, None] > 0, self.mover_b, self.mover_a)
        arrived = (tgt - p).norm(dim=-1) < 0.15
        self.mover_dir = torch.where(arrived, -self.mover_dir, self.mover_dir)
        tgt = torch.where(self.mover_dir[:, None] > 0, self.mover_b, self.mover_a)
        d = tgt - p
        v = d / d.norm(dim=-1, keepdim=True).clamp_min(1e-6) * self.mover_speed[:, None]
        self.mover.control_dofs_velocity(v)

    def step(self, action: torch.Tensor, auto_reset: bool = True):
        c = self.cfg
        action = action.to(self.device, torch.float32).clamp(-1.0, 1.0)
        self.actuator.command(action)
        self._mover_control()
        contact = torch.zeros(self.B, device=self.device, dtype=torch.bool)
        for _ in range(c.control_decimation):
            ref = self.actuator.substep(c.sim_dt)
            # Command along the predicted mid-substep heading (removes the half-step lag of a turning base), plus
            # an acceleration feed-forward: the P velocity servo (force = kv * err) then supplies m * a_ref, incl.
            # the centripetal term v * w, without a steady-state tracking error (i.e. without lateral slip).
            th = self.robot.get_dofs_position()[:, 2] + 0.5 * c.sim_dt * ref[:, 1]
            ct, st = torch.cos(th), torch.sin(th)
            v, w = ref[:, 0], ref[:, 1]
            v_dot, w_dot = self.actuator.ref_rate[:, 0], self.actuator.ref_rate[:, 1]
            ax, ay = v_dot * ct - v * w * st, v_dot * st + v * w * ct
            vel = torch.stack(
                [v * ct + self._ff_lin * ax, v * st + self._ff_lin * ay, w + self._ff_ang * w_dot], dim=-1
            )
            self.robot.control_dofs_velocity(vel)
            self.scene.step()
            # OR over substeps so transient contacts are not missed.
            contact |= self.contact_sensor.read().reshape(self.B, -1).any(dim=-1)
        self.prev_action = action
        self.last_contact = contact
        self._update_privileged_diagnostics()

        xy = self.robot.get_dofs_position()[:, :2]
        dist = (self.goal_xy - xy).norm(dim=-1)
        success = dist < c.goal_radius
        self.step_count += 1
        truncated = (self.step_count >= c.max_episode_steps) & ~success
        terminated = success | (contact & c.terminate_on_collision)
        truncated &= ~terminated
        reward = (
            c.reward_progress * (self.prev_dist - dist)
            + c.reward_success * success.float()
            - c.reward_collision * contact.float()
            - c.reward_time
        )
        self.prev_dist = dist
        s = self.stats
        s["ret"] += reward
        s["len"] += 1
        s["path"] += (xy - self.prev_xy).norm(dim=-1)
        self.prev_xy = xy
        s["collisions"] += contact.float()
        near = self.last_clearance < c.near_collision_clearance
        s["near"] += near.float()
        s["min_clear"] = torch.minimum(s["min_clear"], self.last_clearance)
        s["mover_vis"] += self.last_mover_visible.float()
        done = terminated | truncated

        info = {
            "success": success,
            "collision": contact,
            "near_collision": near,
            "terminated": terminated,
            "truncated": truncated,
            "episode": self._episode_stats(success, dist),  # valid where done
        }
        obs = self._compute_obs()
        if auto_reset:
            obs = self.reset_done(done, obs)
        return obs, reward, terminated, truncated, info

    def reset_done(self, done: torch.Tensor, obs: dict | None = None) -> dict[str, torch.Tensor]:
        """Reset finished envs and return fresh observations. One device->host sync (the done mask)."""
        ids = torch.nonzero(done).reshape(-1).cpu().numpy()
        if ids.size:
            self.reset_envs(ids)
            return self._compute_obs()
        return obs if obs is not None else self._compute_obs()

    def _episode_stats(self, success, dist):
        s = self.stats
        path = s["path"]
        sd = s["start_dist"]
        return {
            "success": success.float(),
            "collisions": s["collisions"].clone(),
            "collided": (s["collisions"] > 0).float(),
            "return": s["ret"].clone(),
            "length": s["len"].clone(),
            "path_length": path.clone(),
            "start_goal_dist": sd.clone(),
            # SPL with the straight-line distance to the goal *region* as the (lower-bound) shortest path.
            "spl": success.float() * (sd - self.cfg.goal_radius) / torch.maximum(path, sd - self.cfg.goal_radius).clamp_min(1e-6),
            "final_dist": dist.clone(),
            "min_clearance": s["min_clear"].clone(),
            "near_collision_steps": s["near"].clone(),
            "mover_visible_frac": s["mover_vis"] / s["len"].clamp_min(1),
            "profile_id": self.profile_id.float(),
            "episode_idx": self.episode_idx_t.float(),
        }

    # ------------------------------------------------------------------------------------------ observations
    def _compute_obs(self) -> dict[str, torch.Tensor]:
        c, sc = self.cfg, self.cfg.sensors
        noisy = c.randomization.obs_noise
        g = self.noise_gen
        B = self.B
        obs: dict[str, torch.Tensor] = {}

        def nz(x, std):
            if not noisy or std <= 0:
                return x
            return x + std * torch.randn(x.shape, device=x.device, generator=g)

        if self.depth_sensor is not None:
            d = self.depth_sensor.read_image().reshape(B, 1, sc.depth_res[1], sc.depth_res[0])
            obs["depth"] = (nz(d, sc.depth_noise_std).clamp(0.0, sc.max_range) / sc.max_range).float()
        if self.ray_sensor is not None:
            r = self.ray_sensor.read().distances.reshape(B, -1)
            obs["rays"] = (nz(r, sc.rays_noise_std).clamp(0.0, sc.max_range) / sc.max_range).float()

        q = self.robot.get_dofs_position()
        qd = self.robot.get_dofs_velocity()
        th = q[:, 2]
        ct, st = torch.cos(th), torch.sin(th)
        dx, dy = (self.goal_xy - q[:, :2]).unbind(-1)
        gx, gy = ct * dx + st * dy, -st * dx + ct * dy
        dist = nz(torch.sqrt(gx * gx + gy * gy), sc.goal_noise_std).clamp_min(0.0)
        bearing = nz(torch.atan2(gy, gx), sc.goal_noise_std)
        obs["goal"] = torch.stack([dist / (2 * c.arena_half_size), torch.cos(bearing), torch.sin(bearing)], -1)

        v_f = ct * qd[:, 0] + st * qd[:, 1]
        v_l = -st * qd[:, 0] + ct * qd[:, 1]
        pro = torch.stack([v_f / V_NORM, v_l / V_NORM, qd[:, 2] / W_NORM], dim=-1)
        obs["proprio"] = torch.cat([nz(pro, sc.proprio_noise_std), self.prev_action], dim=-1).float()
        obs["bump"] = self.last_contact.float()[:, None]
        return obs

    # ------------------------------------------------------------------------------------------ privileged
    def _update_privileged_diagnostics(self):
        q = self.robot.get_dofs_position()
        xy = q[:, :2]
        mxy = self.mover.get_dofs_position() if self.mover is not None else None
        self.last_clearance = clearance(
            xy, assets.ROBOT_RADIUS, self.obstacle_xy, self.obstacle_half, self.cfg.arena_half_size, mxy,
            assets.MOVER_RADIUS,
        )
        vis = torch.zeros(self.B, device=self.device, dtype=torch.bool)
        if mxy is not None and self.ray_sensor is not None:
            th = q[:, 2]
            ct, st = torch.cos(th)[:, None], torch.sin(th)[:, None]
            lx, ly = self.ray_dirs_local[None, :, 0], self.ray_dirs_local[None, :, 1]
            dirs = torch.stack([ct * lx - st * ly, st * lx + ct * ly], dim=-1)
            t = ray_circle_t(xy, dirs, mxy, assets.MOVER_RADIUS)
            measured = self.ray_sensor.read().distances.reshape(self.B, -1)
            # Mover visible iff some ray's actual return is the analytic mover hit (i.e. not occluded).
            vis = ((t - measured).abs() < 0.05).any(dim=-1)
        self.last_mover_visible = vis

    def privileged_state(self) -> dict[str, torch.Tensor]:
        """Full simulator state. For diagnostics / oracles / evaluation only. Never pass to the policy."""
        q = self.robot.get_dofs_position()
        qd = self.robot.get_dofs_velocity()
        out = {
            "robot_pose": torch.cat([q[:, :2], wrap_angle(q[:, 2:3])], dim=-1),
            "robot_vel_world": qd.clone(),
            "goal_xy": self.goal_xy.clone(),
            "obstacle_xy": self.obstacle_xy.clone(),
            "obstacle_half": self.obstacle_half.expand(self.B, -1, -1).clone(),
            "mover_xy": self.mover.get_dofs_position() if self.mover is not None else self.mover_a.clone(),
            "mover_vel": self.mover.get_dofs_velocity() if self.mover is not None else torch.zeros_like(self.mover_a),
            "mover_a": self.mover_a.clone(),
            "mover_b": self.mover_b.clone(),
            "mover_speed": self.mover_speed.clone(),
            "profile_id": self.profile_id.clone(),
            "dyn_params": torch.stack(
                [self.actuator.params[p] for p in PARAM_ORDER if p != "delay_steps"]
                + [self.actuator.delay_steps.float()], dim=-1),
            "actuator_target": self.actuator.target.clone(),
            "actuator_ref": self.actuator.ref.clone(),
            "contact": self.last_contact.clone(),
            "clearance": self.last_clearance.clone(),
            "mover_visible": self.last_mover_visible.clone(),
            "step": self.step_count.clone(),
            "episode_idx": self.episode_idx_t.clone(),
        }
        return out

    # ------------------------------------------------------------------------------------------ rendering
    def render(self) -> np.ndarray:
        """RGB frame (H, W, 3) uint8 of env 0 from the Genesis rasterizer."""
        if self.camera is None:
            raise RuntimeError("Env built without render=True")
        rgb = self.camera.render(rgb=True)[0]
        rgb = np.asarray(rgb.cpu() if torch.is_tensor(rgb) else rgb)
        if rgb.ndim == 4:
            rgb = rgb[0]
        return rgb.astype(np.uint8)

    @property
    def control_dt(self) -> float:
        return self.cfg.sim_dt * self.cfg.control_decimation

    def ray_angles(self) -> torch.Tensor:
        """Robot-frame azimuth of each planar ray (for visualisation)."""
        return torch.atan2(self.ray_dirs_local[:, 1], self.ray_dirs_local[:, 0])


def angle_diff(a, b):
    return (a - b + math.pi) % (2 * math.pi) - math.pi
