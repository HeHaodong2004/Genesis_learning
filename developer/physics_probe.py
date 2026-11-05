"""Bounded Genesis instrument: freefall, discretisation, and subset reset.

Not part of the default lightweight test gate. Run explicitly with --backend.
Writes only the explicitly supplied new report file (exclusive creation).
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=["cpu", "gpu"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists; choose a new path to preserve previous evidence")

    from gnav.runtime import init_genesis
    import genesis as gs
    import torch

    start = time.perf_counter()
    init_genesis(args.backend, seed=0)
    device = gs.device
    results = []
    for dt in (0.02, 0.01):
        scene = gs.Scene(
            sim_options=gs.options.SimOptions(dt=dt, substeps=1, gravity=(0, 0, -9.81)),
            rigid_options=gs.options.RigidOptions(integrator=gs.integrator.Euler),
            show_viewer=False,
        )
        ball = scene.add_entity(gs.morphs.Sphere(radius=0.1, pos=(0, 0, 2.0)))
        scene.build(n_envs=2)
        n = round(0.2 / dt)
        trajectory = []
        for step in range(n):
            scene.step()
            trajectory.append({"t": (step + 1) * dt, "z": ball.get_pos()[:, 2].cpu().tolist(),
                               "vz": ball.get_vel()[:, 2].cpu().tolist()})
        z = ball.get_pos()[:, 2].clone()
        vz = ball.get_vel()[:, 2].clone()
        continuous_z = 2.0 - 0.5 * 9.81 * (n * dt) ** 2
        discrete_z = 2.0 - 9.81 * dt ** 2 * n * (n + 1) / 2
        other_pos = ball.get_pos()[1].clone()
        other_vel = ball.get_vel()[1].clone()
        ball.set_pos(torch.tensor([[0.0, 0.0, 2.0]], device=device), envs_idx=[0])
        ball.set_dofs_velocity(torch.zeros((1, 6), device=device), envs_idx=[0])
        checks = {
            "velocity_matches_analytic": bool(torch.all(torch.abs(vz + 9.81 * n * dt) < 2e-4)),
            "position_matches_discrete_euler": bool(torch.all(torch.abs(z - discrete_z) < 2e-4)),
            "unselected_position_unchanged": bool(torch.equal(other_pos, ball.get_pos()[1])),
            "unselected_velocity_unchanged": bool(torch.equal(other_vel, ball.get_vel()[1])),
            "selected_position_reset": bool(torch.allclose(ball.get_pos()[0], torch.tensor([0., 0., 2.], device=device))),
            "selected_velocity_reset": bool(torch.allclose(ball.get_vel()[0], torch.zeros(3, device=device))),
        }
        results.append({"dt": dt, "steps": n, "trajectory": trajectory,
                        "continuous_z": continuous_z, "discrete_z": discrete_z,
                        "continuous_error": float((z - continuous_z).abs().max()), "checks": checks})
        scene.destroy()

    ratio = results[0]["continuous_error"] / results[1]["continuous_error"]
    passed = all(all(r["checks"].values()) for r in results) and 1.8 < ratio < 2.2
    predictions = ROOT / "developer/labs/physics_predictions.json"
    report = {
        "ok": passed, "kind": "educational_genesis_freefall_probe",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version.split()[0], "genesis": gs.__version__, "torch": torch.__version__,
        "backend": gs.backend.name, "device": str(device),
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "predictions_sha256": hashlib.sha256(predictions.read_bytes()).hexdigest(),
        "results": results, "coarse_to_fine_error_ratio": ratio,
        "elapsed_s_including_init_and_compilation": time.perf_counter() - start,
        "scope": "Freefall and subset reset only; no contacts, sensors, policy, throughput or real-robot claim.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({k: v for k, v in report.items() if k != "results"}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
