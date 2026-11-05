"""Smoke test: Genesis init + build the navigation env + step it. Usage:

    python scripts/smoke_test.py --backend cpu
    CUDA_VISIBLE_DEVICES=1 python scripts/smoke_test.py --backend gpu
"""

import argparse
import json
import time

from gnav.runtime import init_genesis

ap = argparse.ArgumentParser()
ap.add_argument("--backend", default="gpu", choices=["gpu", "cpu"])
ap.add_argument("--n-envs", type=int, default=4)
ap.add_argument("--steps", type=int, default=50)
ap.add_argument("--render", action="store_true")
args = ap.parse_args()

t0 = time.time()
device = init_genesis(args.backend, seed=0)
import genesis as gs  # noqa: E402
import torch  # noqa: E402

from gnav.config import EnvConfig  # noqa: E402
from gnav.sim.env import OBS_KEYS, NavEnv  # noqa: E402

t_init = time.time() - t0
cfg = EnvConfig(n_envs=args.n_envs)
t0 = time.time()
env = NavEnv(cfg, seed=0, render=args.render)
t_build = time.time() - t0
obs = env.reset()
assert set(obs) <= set(OBS_KEYS), obs.keys()
for k, v in obs.items():
    assert v.shape[0] == args.n_envs and torch.isfinite(v).all(), k
    assert v.device.type == torch.device(device).type, (k, v.device, device)
g = torch.Generator(device=env.device).manual_seed(0)
t0 = time.time()
n_done = 0
for _ in range(args.steps):
    a = torch.rand(args.n_envs, 2, device=env.device, generator=g) * 2 - 1
    obs, r, term, trunc, info = env.step(a)
    n_done += int((term | trunc).sum())
if env.device.type == "cuda":
    torch.cuda.synchronize()
t_step = time.time() - t0
ps = env.privileged_state()
if args.render:
    frame = env.render()
    assert frame.ndim == 3 and frame.shape[2] == 3 and frame.std() > 1.0, frame.shape
report = {
    "genesis": gs.__version__,
    "torch": torch.__version__,
    "backend": gs.backend.name,
    "device": str(env.device),
    "init_s": round(t_init, 2),
    "build_s": round(t_build, 2),
    "control_steps": args.steps,
    "n_envs": args.n_envs,
    "step_loop_s": round(t_step, 3),
    "env_steps_per_s": round(args.steps * args.n_envs / t_step, 1),
    "episodes_finished": n_done,
    "obs_shapes": {k: list(v.shape) for k, v in obs.items()},
    "robot_pose_env0": [round(x, 3) for x in ps["robot_pose"][0].tolist()],
}
print(json.dumps(report, indent=1))
print("SMOKE TEST PASSED")
