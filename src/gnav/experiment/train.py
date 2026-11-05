"""Reference training loop: recurrent A2C (GAE) + latent-dynamics auxiliary loss from sequence replay.

Test-grade by design. Its job is to exercise the full data flow (env -> encoder -> belief -> policy/value,
replay -> latent dynamics, checkpoints, metrics) reproducibly, not to be a strong learner. Truncated episodes are
treated as terminal; a stronger learner should bootstrap them."""

from __future__ import annotations

import os
import time

import torch

from ..config import ExperimentConfig
from ..learning.replay import SequenceReplay
from ..runtime import init_genesis, seed_everything
from .policies import build_agent
from .run import MetricsLogger, make_run_dir, save_checkpoint

EP_KEYS = ("success", "collided", "spl", "return", "length", "min_clearance", "mover_visible_frac")


def train(cfg: ExperimentConfig, run_dir: str | None = None) -> str:
    init_genesis(cfg.backend, seed=cfg.seed)
    seed_everything(cfg.seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    from ..sim.env import NavEnv

    run_dir = make_run_dir(cfg, "train", run_dir)
    log = MetricsLogger(os.path.join(run_dir, "metrics.jsonl"))
    env = NavEnv(cfg.env, seed=cfg.seed)
    dev = env.device
    tc = cfg.train
    agent = build_agent(cfg, env.obs_shapes).to(dev)
    opt = torch.optim.Adam(agent.parameters(), lr=tc.lr)
    replay = SequenceReplay(tc.replay_capacity, env.B, env.obs_shapes, 2, dev)
    gen = torch.Generator(device=dev).manual_seed(cfg.seed)

    obs = env.reset()
    state = agent.initial_state(env.B, dev)
    first = torch.ones(env.B, dtype=torch.bool, device=dev)
    env_steps = 0
    for it in range(1, tc.iterations + 1):
        t0 = time.time()
        h0 = {k: v.detach() for k, v in state.items()}
        roll = {"obs": [], "first": [], "u": [], "r": [], "done": []}
        ep_acc = {k: torch.zeros((), device=dev) for k in EP_KEYS}
        n_ep = torch.zeros((), device=dev)
        for _ in range(tc.rollout_len):
            with torch.no_grad():
                b, _, h = agent.step(obs, state, first)
                dist = agent.policy(b)
                u = _sample(dist, gen)
                a = torch.tanh(u)
            obs2, r, term, trunc, info = env.step(a)
            done = term | trunc
            roll["obs"].append(obs)
            roll["first"].append(first)
            roll["u"].append(u)
            roll["r"].append(r)
            roll["done"].append(done)
            replay.add(obs, a, r, first)
            ep = info["episode"]
            n_ep += done.sum()
            for k in EP_KEYS:
                ep_acc[k] += (ep[k] * done).sum()
            state = {"h": h, "prev_action": a}
            first = done
            obs = obs2
        env_steps += tc.rollout_len * env.B

        # ---- actor-critic update (BPTT over the rollout from the detached initial state)
        st = h0
        logps, ents, vals = [], [], []
        for t in range(tc.rollout_len):
            b, _, h = agent.step(roll["obs"][t], st, roll["first"][t])
            d = agent.policy(b)
            logps.append(d.log_prob(roll["u"][t]))
            ents.append(d.entropy())
            vals.append(agent.value(b))
            st = {"h": h, "prev_action": torch.tanh(roll["u"][t])}
        with torch.no_grad():
            b_last, _, _ = agent.step(obs, st, first)
            v_last = agent.value(b_last)
        vals_t = torch.stack(vals)
        adv = torch.zeros_like(vals_t)
        gae = torch.zeros(env.B, device=dev)
        lam = 0.95
        for t in reversed(range(tc.rollout_len)):
            nd = (~roll["done"][t]).float()
            v_next = v_last if t == tc.rollout_len - 1 else vals_t[t + 1].detach()
            delta = roll["r"][t] + tc.gamma * v_next * nd - vals_t[t].detach()
            gae = delta + tc.gamma * lam * nd * gae
            adv[t] = gae
        ret = adv + vals_t.detach()
        adv_n = (adv - adv.mean()) / (adv.std() + 1e-8)
        pi_loss = -(torch.stack(logps) * adv_n).mean()
        v_loss = 0.5 * ((vals_t - ret) ** 2).mean()
        ent = torch.stack(ents).mean()

        # ---- latent dynamics loss: predict e_{t+1} from (b_t, a_t) on replayed sequences
        m_loss = torch.zeros((), device=dev)
        if replay.size >= tc.seq_len:
            seq = replay.sample(tc.batch_size, tc.seq_len, gen)
            L = tc.seq_len
            hs = agent.belief.initial_state(tc.batch_size, dev)
            pa = torch.zeros(tc.batch_size, 2, device=dev)
            preds, targets, masks = [], [], []
            embeds = [agent.encoder({k: v[t] for k, v in seq["obs"].items()}) for t in range(L)]
            for t in range(L - 1):
                bt, hs = agent.belief(embeds[t], pa, hs, seq["first"][t])
                preds.append(agent.dynamics(bt, seq["action"][t]))
                targets.append(embeds[t + 1].detach())
                masks.append((~seq["first"][t + 1]).float())
                pa = seq["action"][t]
            mk = torch.stack(masks)
            m_loss = (((torch.stack(preds) - torch.stack(targets)) ** 2).mean(-1) * mk).sum() / mk.sum().clamp_min(1)

        loss = pi_loss + tc.value_coef * v_loss - tc.entropy_coef * ent + tc.model_coef * m_loss
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(agent.parameters(), 1.0)
        opt.step()
        state = {k: v.detach() for k, v in state.items()}

        n = max(int(n_ep.item()), 1)  # one sync per iteration (logging)
        log.log(
            iteration=it, env_steps=env_steps, loss=loss.item(), pi_loss=pi_loss.item(), v_loss=v_loss.item(),
            entropy=ent.item(), model_loss=m_loss.item(), episodes=int(n_ep.item()),
            **{f"ep_{k}": float(ep_acc[k]) / n for k in EP_KEYS},
            sps=round(tc.rollout_len * env.B / (time.time() - t0), 1),
        )
        if it % tc.checkpoint_every == 0 or it == tc.iterations:
            save_checkpoint(os.path.join(run_dir, "checkpoints", f"iter_{it:06d}.pt"), cfg=cfg, agent=agent,
                            optimizer=opt, iteration=it, extra={"env_steps": env_steps})
    log.close()
    return run_dir


def _sample(dist, gen):
    """Sample a (diagonal) Normal with an explicit generator for reproducibility."""
    base = dist.base_dist
    eps = torch.randn(base.loc.shape, device=base.loc.device, generator=gen)
    return base.loc + base.scale * eps
