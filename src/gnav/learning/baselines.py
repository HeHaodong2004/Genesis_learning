"""Observation-only scripted policies (reference behaviour for demos and tests; not planners).

They read only agent observations, so they also exercise the information boundary."""

from __future__ import annotations

import math

import torch

from .agent import check_obs


class ReactiveGapPolicy:
    """Follow-the-gap steering on the planar range scan, biased toward the relative goal bearing.

    If the goal lies outside the sensor FOV, the robot rotates toward it (it cannot see what lies there)."""

    def __init__(self, ray_angles: torch.Tensor, max_range: float, clearance_gain=1.0, goal_gain=1.2,
                 safe_dist=0.8, stop_dist=0.35, robot_radius=0.2):
        self.ang = ray_angles  # (N,) robot-frame azimuths, CCW positive
        self.R = max_range
        self.cg, self.gg = clearance_gain, goal_gain
        self.safe, self.stop, self.rr = safe_dist, stop_dist, robot_radius
        self.half_fov = float(ray_angles.abs().max())

    def __call__(self, obs, *_):
        check_obs(obs)
        r = obs["rays"] * self.R  # (B, N) metres
        bearing = torch.atan2(obs["goal"][:, 2], obs["goal"][:, 1])
        # Inflate obstacles by the robot radius: a ray is passable if the clear width around it is wide enough.
        clear = -torch.nn.functional.max_pool1d(-r[:, None], kernel_size=5, stride=1, padding=2)[:, 0]
        score = self.cg * clear.clamp(max=3.0) - self.gg * (self.ang[None] - bearing[:, None]).abs()
        best = self.ang[score.argmax(dim=-1)]
        goal_visible = bearing.abs() < self.half_fov
        heading = torch.where(goal_visible, best, bearing.clamp(-math.pi / 2, math.pi / 2))
        front = r[:, (self.ang.abs() < 0.35)].min(dim=-1).values - self.rr
        w = (2.0 * heading).clamp(-1, 1)
        v = ((front - self.stop) / (self.safe - self.stop)).clamp(0, 1) * (1 - 0.8 * w.abs())
        v = torch.where(goal_visible, v, torch.zeros_like(v))
        return torch.stack([v, w], dim=-1)


class GoalSeekPolicy:
    """Drives straight at the goal, ignoring range data (used to produce collision examples)."""

    def __call__(self, obs, *_):
        check_obs(obs)
        bearing = torch.atan2(obs["goal"][:, 2], obs["goal"][:, 1])
        w = (2.0 * bearing).clamp(-1, 1)
        v = (1 - w.abs()).clamp(0, 1)
        return torch.stack([v, w], dim=-1)


class RandomPolicy:
    def __init__(self, generator: torch.Generator):
        self.g = generator

    def __call__(self, obs, *_):
        b = next(iter(obs.values())).shape[0]
        dev = next(iter(obs.values())).device
        return torch.rand(b, 2, device=dev, generator=self.g) * 2 - 1
