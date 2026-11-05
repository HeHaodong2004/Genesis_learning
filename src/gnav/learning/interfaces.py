"""Abstract interfaces for belief-based embodied agents.

Data flow for one control step (B parallel envs):

    obs (dict of OBS_KEYS) --ObservationEncoder--> e_t (B, E)
    (e_t, a_{t-1}, h_{t-1}, first_t) --BeliefModel--> b_t, h_t        (recurrent belief / filtering)
    b_t --Policy--> pi(a_t | b_t)          b_t --ValueFunction--> V(b_t)
    (b_t, a_t) --LatentDynamics--> predicted next latent (model learning, imagination)

Only ``obs`` crosses the information boundary into these modules. Privileged simulator state is consumed only
by diagnostics (e.g. ``gnav.learning.diagnostics``), never by these interfaces.
"""

from __future__ import annotations

import abc

import torch
from torch import nn


class ObservationEncoder(nn.Module, abc.ABC):
    """Maps an observation dict to a flat embedding. ``obs_keys`` declares which observation channels it reads."""

    obs_keys: tuple[str, ...]
    embed_dim: int

    @abc.abstractmethod
    def forward(self, obs: dict[str, torch.Tensor]) -> torch.Tensor:  # (B, E)
        ...


class BeliefModel(nn.Module, abc.ABC):
    """Recurrent belief state over the history of embeddings and actions.

    ``first`` (B,) bool marks the first step of an episode; implementations must reset their state there so
    information never leaks across episode boundaries."""

    belief_dim: int

    @abc.abstractmethod
    def initial_state(self, batch_size: int, device) -> torch.Tensor: ...

    @abc.abstractmethod
    def forward(
        self, embed: torch.Tensor, prev_action: torch.Tensor, state: torch.Tensor, first: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:  # (belief (B, D), new_state)
        ...


class LatentDynamics(nn.Module, abc.ABC):
    """Action-conditioned latent transition model."""

    latent_dim: int

    @abc.abstractmethod
    def forward(self, belief: torch.Tensor, action: torch.Tensor) -> torch.Tensor:
        """Predict the next latent (here: the next observation embedding) from (b_t, a_t)."""

    def imagine(self, belief: torch.Tensor, actions: torch.Tensor) -> torch.Tensor:
        """Open-loop rollout over actions (T, B, A) -> (T, B, latent). Default: 1-step predictions from b_t."""
        return torch.stack([self(belief, a) for a in actions])


class Policy(nn.Module, abc.ABC):
    action_dim: int

    @abc.abstractmethod
    def forward(self, belief: torch.Tensor) -> torch.distributions.Distribution: ...

    def act(self, belief: torch.Tensor, deterministic: bool = False) -> tuple[torch.Tensor, torch.Tensor]:
        """Returns (action in [-1, 1], raw sample whose log-prob ``self(belief).log_prob`` evaluates)."""
        dist = self(belief)
        u = dist.mode if deterministic else dist.sample()
        return u.clamp(-1, 1), u


class ValueFunction(nn.Module, abc.ABC):
    @abc.abstractmethod
    def forward(self, belief: torch.Tensor) -> torch.Tensor:  # (B,)
        ...
