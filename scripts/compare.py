"""Matched-seed comparison of variants (policies, dynamics profiles, ablations) on identical scenarios.

    scripts/gnav-env.sh python scripts/compare.py --config configs/eval.yaml \
        --variant agile env.dynamics.profiles=[agile] --variant heavy env.dynamics.profiles=[heavy]

The first variant is the reference; results report per-episode paired differences (variant - reference).
Variants must keep env.n_envs and eval.n_episodes equal, so the episode sets coincide.
"""
import argparse
import json
import os

from gnav.config import load_config
from gnav.experiment.evaluate import evaluate, paired_comparison
from gnav.experiment.run import write_json

ap = argparse.ArgumentParser()
ap.add_argument("--config", required=True)
ap.add_argument("--variant", nargs="+", action="append", required=True, metavar=("NAME", "OVERRIDE"))
ap.add_argument("--out", default="runs/compare")
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
results = {}
for name, *ovs in a.variant:
    cfg = load_config(a.config, ovs + [f"name={name}"])
    run_dir, summary, rows = evaluate(cfg, os.path.join(a.out, name))
    results[name] = {"overrides": ovs, "summary": summary, "rows": rows, "run_dir": run_dir}
ref = a.variant[0][0]
report = {
    "reference": ref,
    "variants": {n: {"overrides": r["overrides"], "metrics": r["summary"]["metrics"]} for n, r in results.items()},
    "paired_vs_reference": {n: paired_comparison(results[ref]["rows"], r["rows"]) for n, r in results.items() if n != ref},
}
write_json(os.path.join(a.out, "comparison.json"), report)
print(json.dumps(report["paired_vs_reference"], indent=1))
