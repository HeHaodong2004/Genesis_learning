"""Throughput / memory benchmark. Each batch size runs in a fresh subprocess (clean GPU memory accounting).

    scripts/gnav-env.sh python scripts/benchmark.py --backend gpu --n-envs 16 64 256 1024 4096
    scripts/gnav-env.sh python scripts/benchmark.py --backend cpu --n-envs 1 16 64

Reports, per batch size:
  * physics_only:  step(auto_reset=False) with fixed random actions (physics + sensors + obs)
  * with_resets:   step(auto_reset=True) with uniform random actions (includes host-side scenario sampling)
  * GPU memory used by the process (NVML via nvidia-smi) and peak torch allocations
"""

import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def child(args):
    from gnav.runtime import init_genesis

    t0 = time.time()
    init_genesis(args.backend, seed=0)
    import torch

    from gnav.config import EnvConfig
    from gnav.sim.env import NavEnv

    cfg = EnvConfig(n_envs=args.n)
    cfg.sensors.depth_enabled = not args.no_depth
    tb = time.time()
    env = NavEnv(cfg, seed=0)
    build_s = time.time() - tb
    tr = time.time()
    env.reset()
    reset_all_s = time.time() - tr
    cuda = env.device.type == "cuda"
    sync = torch.cuda.synchronize if cuda else (lambda: None)
    g = torch.Generator(device=env.device).manual_seed(0)
    res = {"n_envs": args.n, "backend": args.backend, "depth": not args.no_depth, "build_s": round(build_s, 2),
           "full_reset_s": round(reset_all_s, 3)}
    for mode in ("physics_only", "with_resets"):
        auto = mode == "with_resets"
        for _ in range(10):
            env.step(torch.rand(args.n, 2, device=env.device, generator=g) * 2 - 1, auto_reset=auto)
        sync()
        n_resets = 0
        t = time.time()
        for _ in range(args.steps):
            a = torch.rand(args.n, 2, device=env.device, generator=g) * 2 - 1
            _, _, term, trunc, _ = env.step(a, auto_reset=auto)
            if auto:
                n_resets += int((term | trunc).sum())
        sync()
        dt = time.time() - t
        res[mode] = {
            "control_steps_per_s": round(args.steps / dt, 1),
            "env_steps_per_s": round(args.steps * args.n / dt, 1),
            "physics_steps_per_s": round(args.steps * args.n * cfg.control_decimation / dt, 1),
            "realtime_factor": round(args.steps * args.n * env.control_dt / dt, 1),
        }
        if auto:
            res[mode]["episode_resets"] = n_resets
    if cuda:
        res["torch_peak_alloc_mb"] = round(torch.cuda.max_memory_allocated() / 2**20, 1)
        try:
            out = subprocess.run(
                ["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=20).stdout
            mem = [int(l.split(",")[1]) for l in out.strip().splitlines() if int(l.split(",")[0]) == os.getpid()]
            res["process_gpu_mem_mb"] = mem[0] if mem else None
        except Exception as e:  # noqa: BLE001
            res["process_gpu_mem_mb"] = f"unavailable: {e}"
    res["total_s"] = round(time.time() - t0, 1)
    print("RESULT " + json.dumps(res))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="gpu", choices=["gpu", "cpu"])
    ap.add_argument("--n-envs", type=int, nargs="+", default=[16, 64, 256, 1024])
    ap.add_argument("--steps", type=int, default=100)
    ap.add_argument("--no-depth", action="store_true")
    ap.add_argument("--out", default="results/benchmark.json")
    ap.add_argument("--child", action="store_true")
    ap.add_argument("--n", type=int)
    args = ap.parse_args()
    if args.child:
        return child(args)
    results = []
    for n in args.n_envs:
        cmd = [sys.executable, __file__, "--child", "--backend", args.backend, "--n", str(n), "--steps", str(args.steps)]
        if args.no_depth:
            cmd.append("--no-depth")
        p = subprocess.run(cmd, capture_output=True, text=True)
        line = [l for l in p.stdout.splitlines() if l.startswith("RESULT ")]
        if not line:
            r = {"n_envs": n, "backend": args.backend, "error": (p.stderr or p.stdout)[-1500:]}
        else:
            r = json.loads(line[0][7:])
        print(json.dumps(r), flush=True)
        results.append(r)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    existing = []
    if os.path.exists(args.out):
        with open(args.out) as f:
            existing = json.load(f)
    key = lambda r: (r["backend"], r["n_envs"], r.get("depth", True))  # noqa: E731
    merged = {key(r): r for r in existing}
    merged.update({key(r): r for r in results})
    with open(args.out, "w") as f:
        json.dump(sorted(merged.values(), key=key), f, indent=1)


if __name__ == "__main__":
    main()
