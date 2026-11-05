"""Process-wide Genesis initialisation. ``gs.init`` may only be called once per process."""

from __future__ import annotations

import os
import random

# Silence harmless kernel-compile precision warnings from the Quadrants JIT (must be set before import).
os.environ.setdefault("QD_LOG_LEVEL", "error")

import numpy as np  # noqa: E402
import torch  # noqa: E402

_STATE: dict = {}


def init_genesis(backend: str = "gpu", seed: int = 0, log_level: str = "warning"):
    """Initialise Genesis once. Returns the torch device simulation tensors live on."""
    import genesis as gs

    if _STATE:
        if _STATE["backend"] != backend:
            raise RuntimeError(f"Genesis already initialised with backend={_STATE['backend']}, requested {backend}")
        return gs.device
    be = {"gpu": gs.gpu, "cuda": gs.cuda, "cpu": gs.cpu}[backend]
    gs.init(backend=be, seed=seed, precision="32", logging_level=log_level)
    if backend in ("gpu", "cuda") and gs.backend == gs.cpu:
        raise RuntimeError("GPU backend requested but Genesis fell back to CPU (check driver / CUDA).")
    _STATE["backend"] = backend
    return gs.device


def seed_everything(seed: int):
    random.seed(seed)
    np.random.seed(seed % (2**32))
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
