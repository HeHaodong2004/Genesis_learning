"""Agent = encoder + belief + latent dynamics + policy + value, with an enforced information boundary."""

from __future__ import annotations

import torch
from torch import nn

from ..sim.env import OBS_KEYS
from .modules import GRUBelief, MLPLatentDynamics, MLPValue, SimpleEncoder, TanhGaussianPolicy


class InformationBoundaryError(KeyError):
    pass


def check_obs(obs: dict) -> dict:
    """Reject anything that is not an agent observation (e.g. a privileged-state dict passed by mistake)."""
    bad = set(obs) - set(OBS_KEYS)
    if bad:
        raise InformationBoundaryError(f"non-observation keys passed to the agent: {sorted(bad)}")
    return obs


class BeliefAgent(nn.Module):
    def __init__(self, obs_shapes, action_dim=2, latent_dim=64, belief_dim=128, hidden_dim=128):
        super().__init__()
        self.encoder = SimpleEncoder(obs_shapes, latent_dim)
        self.belief = GRUBelief(latent_dim, action_dim, belief_dim)
        self.dynamics = MLPLatentDynamics(belief_dim, action_dim, latent_dim, hidden_dim)
        self.policy = TanhGaussianPolicy(belief_dim, action_dim, hidden_dim)
        self.value = MLPValue(belief_dim, hidden_dim)
        self.action_dim = action_dim

    def initial_state(self, batch_size, device):
        return {
            "h": self.belief.initial_state(batch_size, device),
            "prev_action": torch.zeros(batch_size, self.action_dim, device=device),
        }

    def step(self, obs, state, first):
        """One filtering step. Returns (belief, embed, new_state_without_action)."""
        obs = check_obs(obs)
        e = self.encoder(obs)
        b, h = self.belief(e, state["prev_action"], state["h"], first)
        return b, e, h

    @torch.no_grad()
    def act(self, obs, state, first, deterministic=False):
        b, e, h = self.step(obs, state, first)
        a, u = self.policy.act(b, deterministic)
        return a, {"h": h, "prev_action": a}, {"belief": b, "embed": e, "pre_tanh": u, "value": self.value(b)}
