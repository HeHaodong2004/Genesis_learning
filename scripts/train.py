"""Train the reference belief agent.

    scripts/gnav-env.sh python scripts/train.py --config configs/train_smoke.yaml [key=value ...]
"""
import argparse

from gnav.config import load_config
from gnav.experiment.train import train

ap = argparse.ArgumentParser()
ap.add_argument("--config", required=True)
ap.add_argument("--run-dir", default=None)
ap.add_argument("overrides", nargs="*", help="dotted overrides, e.g. seed=3 env.n_envs=64")
a = ap.parse_args()
print("run_dir:", train(load_config(a.config, a.overrides), a.run_dir))
