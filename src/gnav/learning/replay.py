"""Device-resident sequence replay buffer for recurrent / world-model learning."""

from __future__ import annotations

import torch


class SequenceReplay:
    """Ring buffer of shape (T_cap, B, ...). Stores agent observations, actions, rewards and episode-start flags.

    Privileged diagnostics may be stored alongside (``priv_shapes``); they are returned only when
    ``sample(..., include_privileged=True)`` is requested and always under the separate key ``"privileged"``.
    """

    def __init__(self, capacity: int, n_envs: int, obs_shapes: dict, action_dim: int, device, priv_shapes=None):
        self.T = max(2, capacity // n_envs)
        self.B = n_envs
        self.device = device
        f = dict(device=device, dtype=torch.float32)
        self.obs = {k: torch.zeros(self.T, n_envs, *s, **f) for k, s in obs_shapes.items()}
        self.action = torch.zeros(self.T, n_envs, action_dim, **f)
        self.reward = torch.zeros(self.T, n_envs, **f)
        self.first = torch.zeros(self.T, n_envs, device=device, dtype=torch.bool)
        self.priv = {k: torch.zeros(self.T, n_envs, *s, **f) for k, s in (priv_shapes or {}).items()}
        self.ptr = 0
        self.size = 0

    def add(self, obs, action, reward, first, priv=None):
        """obs/first at time t, action taken at t, reward received after it."""
        t = self.ptr
        for k in self.obs:
            self.obs[k][t] = obs[k]
        self.action[t] = action
        self.reward[t] = reward
        self.first[t] = first
        if priv is not None:
            for k in self.priv:
                self.priv[k][t] = priv[k]
        self.ptr = (self.ptr + 1) % self.T
        self.size = min(self.size + 1, self.T)

    def sample(self, batch_size: int, seq_len: int, generator: torch.Generator, include_privileged=False):
        """Sample ``batch_size`` contiguous sequences of length ``seq_len`` -> tensors of shape (L, N, ...).

        Sequences never straddle the ring-buffer write head. Episode boundaries inside a sequence are marked by
        ``first`` (the belief model resets there); the first element of every sequence is also marked."""
        if self.size < seq_len:
            raise ValueError(f"buffer holds {self.size} steps < seq_len {seq_len}")
        n_start = self.size - seq_len + 1
        oldest = (self.ptr - self.size) % self.T
        s = torch.randint(0, n_start, (batch_size,), generator=generator, device=self.device)
        e = torch.randint(0, self.B, (batch_size,), generator=generator, device=self.device)
        t = (oldest + s[None] + torch.arange(seq_len, device=self.device)[:, None]) % self.T  # (L, N)
        out = {
            "obs": {k: v[t, e[None]] for k, v in self.obs.items()},
            "action": self.action[t, e[None]],
            "reward": self.reward[t, e[None]],
            "first": self.first[t, e[None]].clone(),
        }
        out["first"][0] = True
        if include_privileged:
            out["privileged"] = {k: v[t, e[None]] for k, v in self.priv.items()}
        return out
