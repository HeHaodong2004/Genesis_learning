"""Shared fixtures. Genesis can be initialised once per process, so the backend is chosen per pytest run:

    GNAV_BACKEND=cpu pytest            # default
    GNAV_BACKEND=gpu CUDA_VISIBLE_DEVICES=1 pytest
"""

import math
import os

import numpy as np
import pytest

from gnav.runtime import init_genesis

BACKEND = os.environ.get("GNAV_BACKEND", "cpu")


@pytest.fixture(scope="session", autouse=True)
def genesis_device():
    return init_genesis(BACKEND, seed=0)


@pytest.fixture(scope="session")
def backend():
    return BACKEND


# Obstacles parked in the far corner behind the test robot (outside every test FOV), one per obstacle entity.
def parked_obstacles(n, corner=(-3.3, -3.3)):
    return np.array([[corner[0] + 0.0 * i, corner[1] + 1.2 * i] for i in range(n)])


def base_cfg(n_envs, **kw):
    from gnav.config import EnvConfig

    cfg = EnvConfig(n_envs=n_envs, **kw)
    return cfg


TWO_PI = 2 * math.pi
