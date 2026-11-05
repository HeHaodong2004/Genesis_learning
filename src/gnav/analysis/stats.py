"""Uncertainty estimates for simulation results."""

from __future__ import annotations

import math

import numpy as np


def wilson(k: float, n: float, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion k/n."""
    if n <= 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (c - h, c + h)


def mean_ci(x, z: float = 1.96) -> tuple[float, float, float]:
    """Mean and normal-approximation CI half-width (returns mean, lo, hi)."""
    x = np.asarray(x, dtype=np.float64)
    mu = float(x.mean())
    se = float(x.std(ddof=1) / math.sqrt(len(x))) if len(x) > 1 else float("nan")
    return mu, mu - z * se, mu + z * se


def paired_diff_ci(a, b, z: float = 1.96) -> tuple[float, float, float]:
    """CI of mean(a - b) for paired samples (same episodes / seeds)."""
    return mean_ci(np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64), z)


def bootstrap_ci(x, stat=np.mean, n_boot: int = 2000, seed: int = 0, alpha: float = 0.05):
    rng = np.random.default_rng(seed)
    x = np.asarray(x)
    vals = np.array([stat(x[rng.integers(0, len(x), len(x))]) for _ in range(n_boot)])
    return float(stat(x)), float(np.quantile(vals, alpha / 2)), float(np.quantile(vals, 1 - alpha / 2))
