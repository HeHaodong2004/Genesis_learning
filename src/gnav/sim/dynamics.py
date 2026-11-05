"""Batched actuator / dynamics model for a differential-drive-like base.

A normalised action ``a in [-1, 1]^2`` is mapped to a commanded body twist ``(v, w)``. The command then passes
through, per environment:

1. an actuation delay of ``delay_steps`` control steps (FIFO ring buffer),
2. a first-order lag with time constants ``tau_v`` / ``tau_w`` (actuator inertia),
3. acceleration limits ``a_max`` / ``alpha_max``,

producing the reference twist ``(v_ref, w_ref)``. The reference is converted to a world-frame velocity using the
robot's *measured* heading and handed to the Genesis joint velocity servo, which tracks it through the rigid-body
solver, subject to a finite force limit, so contacts can stop the robot.

All parameters are per-environment tensors, so different envs in one batch can carry different dynamics. The
same action interface serves every profile. Only the parameters change.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, fields

import torch

PARAM_NAMES = ("v_max", "v_min", "w_max", "a_max", "alpha_max", "tau_v", "tau_w", "delay_steps")


@dataclass(frozen=True)
class DynamicsProfile:
    v_max: float  # max forward speed [m/s]
    v_min: float  # max reverse speed magnitude [m/s] (a0 = -1 -> -v_min)
    w_max: float  # max yaw rate [rad/s]
    a_max: float  # max linear acceleration [m/s^2]
    alpha_max: float  # max angular acceleration [rad/s^2]
    tau_v: float  # linear first-order lag time constant [s] (0 = none)
    tau_w: float  # angular first-order lag time constant [s]
    delay_steps: int  # actuation delay in control steps

    def as_dict(self) -> dict:
        return asdict(self)


PROFILES: dict[str, DynamicsProfile] = {
    # Responsive differential-drive base: quick turns, high acceleration, negligible lag.
    "agile": DynamicsProfile(
        v_max=1.2, v_min=0.4, w_max=2.5, a_max=3.0, alpha_max=8.0, tau_v=0.05, tau_w=0.05, delay_steps=0
    ),
    # Heavy, slow-turning platform: low yaw rate, small accelerations, large lag, 0.2 s actuation delay.
    "heavy": DynamicsProfile(
        v_max=1.0, v_min=0.2, w_max=0.6, a_max=0.5, alpha_max=0.6, tau_v=0.6, tau_w=0.8, delay_steps=2
    ),
}


def profile_from_dict(d: dict) -> DynamicsProfile:
    names = {f.name for f in fields(DynamicsProfile)}
    return DynamicsProfile(**{k: d[k] for k in names})


class ActuatorModel:
    """Batched actuator state. Tensors live on ``device``; nothing in ``command``/``substep`` syncs with the host."""

    def __init__(self, n_envs: int, max_delay_steps: int, device: torch.device, dtype=torch.float32):
        self.B = n_envs
        self.device = device
        self.dtype = dtype
        self.max_delay = int(max_delay_steps)
        # Per-env parameters, shape (B,)
        self.params: dict[str, torch.Tensor] = {
            n: torch.zeros(n_envs, device=device, dtype=dtype) for n in PARAM_NAMES if n != "delay_steps"
        }
        self.delay_steps = torch.zeros(n_envs, device=device, dtype=torch.long)
        # State
        self.cmd_buffer = torch.zeros(n_envs, self.max_delay + 1, 2, device=device, dtype=dtype)
        self.buf_head = 0  # global ring head (all envs advance together)
        self.target = torch.zeros(n_envs, 2, device=device, dtype=dtype)  # delayed command (v, w)
        self.ref = torch.zeros(n_envs, 2, device=device, dtype=dtype)  # lagged + rate-limited (v_ref, w_ref)
        self.ref_rate = torch.zeros(n_envs, 2, device=device, dtype=dtype)
        self._ar = torch.arange(n_envs, device=device)

    # ---------------------------------------------------------------- parameters
    def set_params(self, env_ids: torch.Tensor, values: dict[str, torch.Tensor]):
        for n, p in self.params.items():
            p[env_ids] = values[n].to(self.dtype)
        # The env validates max_delay_steps against profiles + jitter at construction, so clamping never binds.
        self.delay_steps[env_ids] = values["delay_steps"].to(torch.long).clamp(0, self.max_delay)

    def reset_state(self, env_ids: torch.Tensor):
        self.cmd_buffer[env_ids] = 0.0
        self.target[env_ids] = 0.0
        self.ref[env_ids] = 0.0
        self.ref_rate[env_ids] = 0.0

    # ---------------------------------------------------------------- control step
    def action_to_twist(self, action: torch.Tensor) -> torch.Tensor:
        a = action.clamp(-1.0, 1.0)
        v = torch.where(a[:, 0] >= 0, a[:, 0] * self.params["v_max"], a[:, 0] * self.params["v_min"])
        w = a[:, 1] * self.params["w_max"]
        return torch.stack([v, w], dim=-1)

    def command(self, action: torch.Tensor):
        """Push a new normalised action (once per control step) and select the per-env delayed command."""
        self.buf_head = (self.buf_head + 1) % (self.max_delay + 1)
        self.cmd_buffer[:, self.buf_head] = self.action_to_twist(action)
        idx = (self.buf_head - self.delay_steps) % (self.max_delay + 1)
        self.target = self.cmd_buffer[self._ar, idx]

    def substep(self, dt: float) -> torch.Tensor:
        """Advance lag + rate limits by one physics step of length dt; returns (v_ref, w_ref)."""
        tau = torch.stack([self.params["tau_v"], self.params["tau_w"]], dim=-1)
        # Exact discretisation of a first-order lag; tau == 0 -> alpha = 1 (pass-through).
        alpha = torch.where(tau > 1e-6, 1.0 - torch.exp(-dt / tau.clamp_min(1e-6)), torch.ones_like(tau))
        delta = alpha * (self.target - self.ref)
        lim = torch.stack([self.params["a_max"], self.params["alpha_max"]], dim=-1) * dt
        delta = torch.maximum(torch.minimum(delta, lim), -lim)
        self.ref = self.ref + delta
        self.ref_rate = delta / dt  # (v_dot_ref, w_dot_ref), used for servo feed-forward
        return self.ref

    def state_dict(self) -> dict[str, torch.Tensor]:
        return {"target": self.target.clone(), "ref": self.ref.clone()}


def sample_dynamics(
    profile_names: list[str],
    profile_probs: list[float],
    randomize: bool,
    scale_range: float,
    delay_jitter: int,
    rng,  # numpy Generator
    profiles: dict[str, DynamicsProfile] | None = None,
) -> tuple[int, dict[str, float]]:
    """Sample (profile_id, params) for one episode. Randomisation is a multiplicative uniform scale per param."""
    profiles = profiles or PROFILES
    pid = int(rng.choice(len(profile_names), p=profile_probs))
    base = profiles[profile_names[pid]].as_dict()
    out = {}
    for k, v in base.items():
        if k == "delay_steps":
            d = int(v)
            if randomize and delay_jitter > 0:
                d = max(0, d + int(rng.integers(-delay_jitter, delay_jitter + 1)))
            out[k] = d
        else:
            s = float(rng.uniform(1.0 - scale_range, 1.0 + scale_range)) if randomize and scale_range > 0 else 1.0
            out[k] = float(v) * s
    return pid, out


def wrap_angle(x: torch.Tensor) -> torch.Tensor:
    return torch.remainder(x + math.pi, 2 * math.pi) - math.pi
