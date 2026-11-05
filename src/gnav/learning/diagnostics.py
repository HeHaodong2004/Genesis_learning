"""Scientific diagnostics that use privileged ground truth. Evaluation-only: nothing here feeds the policy.

``linear_probe`` measures how linearly decodable a privileged quantity (e.g. hidden mover position relative to
the robot, dynamics parameters) is from learned belief states, with a held-out split."""

from __future__ import annotations

import torch


def privileged_targets(priv: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    """Robot-frame targets of scientific interest computed from privileged state."""
    pose = priv["robot_pose"]
    c, s = torch.cos(pose[:, 2]), torch.sin(pose[:, 2])

    def to_robot(xy):
        d = xy - pose[:, :2]
        return torch.stack([c * d[:, 0] + s * d[:, 1], -s * d[:, 0] + c * d[:, 1]], -1)

    return {
        "mover_rel_xy": to_robot(priv["mover_xy"]),
        "mover_visible": priv["mover_visible"].float()[:, None],
        "dyn_params": priv["dyn_params"],
        "clearance": priv["clearance"][:, None],
    }


def linear_probe(x: torch.Tensor, y: torch.Tensor, ridge: float = 1e-2, train_frac: float = 0.7, seed: int = 0):
    """Closed-form ridge regression x -> y; returns held-out R^2 per output dim (mean over dims too)."""
    g = torch.Generator().manual_seed(seed)
    x, y = x.double().cpu(), y.double().cpu()
    n = x.shape[0]
    perm = torch.randperm(n, generator=g)
    k = int(train_frac * n)
    tr, te = perm[:k], perm[k:]
    mu_x, sd_x = x[tr].mean(0), x[tr].std(0).clamp_min(1e-6)
    xs = torch.cat([(x - mu_x) / sd_x, torch.ones(n, 1, dtype=x.dtype)], 1)
    a = xs[tr]
    w = torch.linalg.solve(a.T @ a + ridge * torch.eye(a.shape[1], dtype=x.dtype), a.T @ y[tr])
    pred = xs[te] @ w
    ss_res = ((y[te] - pred) ** 2).sum(0)
    ss_tot = ((y[te] - y[tr].mean(0)) ** 2).sum(0)
    # R^2 is undefined for a (near-)constant target, e.g. dynamics parameters without randomisation -> NaN.
    defined = ss_tot > 1e-9 * max(1, te.numel())
    r2 = torch.where(defined, 1 - ss_res / ss_tot.clamp_min(1e-12), torch.full_like(ss_tot, float("nan")))
    mean = float(r2[defined].mean()) if defined.any() else float("nan")
    return {"r2_per_dim": r2.tolist(), "r2_mean": mean, "n_defined_dims": int(defined.sum()), "n_train": int(k),
            "n_test": int(n - k)}
