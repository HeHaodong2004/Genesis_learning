"""Evaluate a policy on the matched-seed episode set.

    scripts/gnav-env.sh python scripts/evaluate.py --config configs/eval.yaml eval.policy=reactive
    scripts/gnav-env.sh python scripts/evaluate.py --config configs/eval.yaml eval.policy=checkpoint \
        eval.checkpoint=runs/.../checkpoints/iter_000020.pt
"""
import argparse
import json

from gnav.config import load_config
from gnav.experiment.evaluate import evaluate

ap = argparse.ArgumentParser()
ap.add_argument("--config", required=True)
ap.add_argument("--run-dir", default=None)
ap.add_argument("overrides", nargs="*")
a = ap.parse_args()
run_dir, summary, _ = evaluate(load_config(a.config, a.overrides), a.run_dir)
print(json.dumps({k: round(v["mean"], 4) for k, v in summary["metrics"].items()}, indent=1))
print("run_dir:", run_dir)
