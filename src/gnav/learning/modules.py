"""Minimal reference implementations of the interfaces (test-grade, intentionally simple)."""

from __future__ import annotations

import math

import torch
from torch import nn
from torch.distributions import Independent, Normal

from .interfaces import BeliefModel, LatentDynamics, ObservationEncoder, Policy, ValueFunction


def mlp(i, h, o, n=2):
    layers, d = [], i
    for _ in range(n - 1):
        layers += [nn.Linear(d, h), nn.ELU()]
        d = h
    layers.append(nn.Linear(d, o))
    return nn.Sequential(*layers)


class SimpleEncoder(ObservationEncoder):
    """Small CNN over depth + MLP over the vector channels."""

    def __init__(self, obs_shapes: dict[str, tuple[int, ...]], embed_dim: int = 64):
        super().__init__()
        self.obs_keys = tuple(sorted(obs_shapes))
        self.embed_dim = embed_dim
        self.vec_keys = tuple(k for k in self.obs_keys if k != "depth")
        vec_dim = sum(math.prod(obs_shapes[k]) for k in self.vec_keys)
        self.depth = None
        d_out = 0
        if "depth" in obs_shapes:
            c, h, w = obs_shapes["depth"]
            self.depth = nn.Sequential(
                nn.Conv2d(c, 16, 3, stride=2, padding=1), nn.ELU(),
                nn.Conv2d(16, 32, 3, stride=2, padding=1), nn.ELU(),
                nn.AdaptiveAvgPool2d((2, 4)), nn.Flatten(),
            )
            d_out = 32 * 8
        self.head = mlp(vec_dim + d_out, 128, embed_dim)

    def forward(self, obs):
        parts = [obs[k].flatten(1) for k in self.vec_keys]
        if self.depth is not None:
            parts.append(self.depth(obs["depth"]))
        return self.head(torch.cat(parts, dim=-1))


class GRUBelief(BeliefModel):
    def __init__(self, embed_dim: int, action_dim: int, belief_dim: int = 128):
        super().__init__()
        self.belief_dim = belief_dim
        self.cell = nn.GRUCell(embed_dim + action_dim, belief_dim)

    def initial_state(self, batch_size, device):
        return torch.zeros(batch_size, self.belief_dim, device=device)

    def forward(self, embed, prev_action, state, first):
        keep = (~first).float()[:, None]
        state = state * keep
        prev_action = prev_action * keep
        h = self.cell(torch.cat([embed, prev_action], -1), state)
        return h, h


class MLPLatentDynamics(LatentDynamics):
    """Predicts the next observation embedding e_{t+1} from (b_t, a_t)."""

    def __init__(self, belief_dim: int, action_dim: int, latent_dim: int, hidden: int = 128):
        super().__init__()
        self.latent_dim = latent_dim
        self.net = mlp(belief_dim + action_dim, hidden, latent_dim)

    def forward(self, belief, action):
        return self.net(torch.cat([belief, action], -1))


class TanhGaussianPolicy(Policy):
    """Gaussian in pre-tanh space; actions are squashed to [-1, 1]. ``mode`` = tanh(mean)."""

    def __init__(self, belief_dim: int, action_dim: int = 2, hidden: int = 128):
        super().__init__()
        self.action_dim = action_dim
        self.mu = mlp(belief_dim, hidden, action_dim)
        self.log_std = nn.Parameter(torch.full((action_dim,), -0.5))

    def forward(self, belief):
        return Independent(Normal(self.mu(belief), self.log_std.exp().expand(belief.shape[0], -1)), 1)

    def act(self, belief, deterministic=False):
        d = self(belief)
        u = d.mean if deterministic else d.sample()
        return torch.tanh(u), u


class MLPValue(ValueFunction):
    def __init__(self, belief_dim: int, hidden: int = 128):
        super().__init__()
        self.net = mlp(belief_dim, hidden, 1)

    def forward(self, belief):
        return self.net(belief).squeeze(-1)
