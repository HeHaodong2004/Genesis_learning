"""Uniform policy wrappers for evaluation: ``policy(obs, first) -> action`` (recurrent state kept inside)."""

from __future__ import annotations

import torch

from ..learning.agent import BeliefAgent
from ..learning.baselines import GoalSeekPolicy, RandomPolicy, ReactiveGapPolicy


class AgentPolicy:
    def __init__(self, agent: BeliefAgent, n_envs: int, device, deterministic=True):
        self.agent = agent.eval()
        self.state = agent.initial_state(n_envs, device)
        self.det = deterministic
        self.last = {}

    def __call__(self, obs, first):
        a, self.state, self.last = self.agent.act(obs, self.state, first, self.det)
        return a


def build_agent(cfg, obs_shapes) -> BeliefAgent:
    m = cfg.model
    return BeliefAgent(obs_shapes, 2, m.latent_dim, m.belief_dim, m.hidden_dim)


def make_policy(name: str, env, cfg, checkpoint: str | None = None):
    if name == "reactive":
        if env.ray_sensor is None:
            raise ValueError("the reactive baseline needs the planar range scan (env.sensors.rays_enabled=true)")
        p = ReactiveGapPolicy(env.ray_angles(), env.cfg.sensors.max_range)
        return lambda obs, first: p(obs)
    if name == "goalseek":
        p = GoalSeekPolicy()
        return lambda obs, first: p(obs)
    if name == "random":
        p = RandomPolicy(torch.Generator(device=env.device).manual_seed(cfg.eval_seed))
        return lambda obs, first: p(obs)
    if name == "checkpoint":
        from .run import load_checkpoint

        ck = load_checkpoint(checkpoint, map_location=env.device)
        agent = build_agent(ck["config_obj"], env.obs_shapes).to(env.device)
        agent.load_state_dict(ck["agent"])
        return AgentPolicy(agent, env.B, env.device, cfg.eval.deterministic)
    raise ValueError(name)
