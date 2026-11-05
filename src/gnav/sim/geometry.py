"""Analytic geometry on privileged state (torch, batched). Used for diagnostics and oracles only, never as
agent observations."""

from __future__ import annotations

import torch


def point_box_dist(p: torch.Tensor, c: torch.Tensor, h: torch.Tensor) -> torch.Tensor:
    """p: (B, 2), c: (B, K, 2), h: (K, 2) -> (B, K) distance to AABB surfaces (negative inside)."""
    d = (p[:, None, :] - c).abs() - h[None]
    outside = d.clamp_min(0.0).norm(dim=-1)
    inside = d.max(dim=-1).values.clamp_max(0.0)
    return outside + inside


def clearance(
    robot_xy: torch.Tensor,
    robot_radius: float,
    obstacle_xy: torch.Tensor,
    obstacle_half: torch.Tensor,
    arena_half: float,
    mover_xy: torch.Tensor | None,
    mover_radius: float,
) -> torch.Tensor:
    """Minimum surface-to-surface distance between the robot hull and any obstacle / wall / mover. (B,)"""
    terms = [(arena_half - robot_xy.abs()).min(dim=-1).values - robot_radius]
    if obstacle_xy.shape[1] > 0:
        terms.append(point_box_dist(robot_xy, obstacle_xy, obstacle_half).min(dim=-1).values - robot_radius)
    if mover_xy is not None:
        terms.append((robot_xy - mover_xy).norm(dim=-1) - robot_radius - mover_radius)
    return torch.stack(terms, dim=-1).min(dim=-1).values


def ray_circle_t(origin: torch.Tensor, dirs: torch.Tensor, center: torch.Tensor, radius: float) -> torch.Tensor:
    """origin (B,2), dirs (B,N,2) unit, center (B,2) -> (B,N) first positive hit distance, +inf if none."""
    oc = origin[:, None, :] - center[:, None, :]
    b = (oc * dirs).sum(-1)
    c = (oc * oc).sum(-1) - radius**2
    disc = b * b - c
    sq = disc.clamp_min(0.0).sqrt()
    t0, t1 = -b - sq, -b + sq
    t = torch.where(t0 > 0, t0, t1)
    return torch.where((disc >= 0) & (t > 0), t, torch.full_like(t, float("inf")))
