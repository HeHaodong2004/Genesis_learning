"""Print a controlled boundary counterexample, without running or training Genesis."""

import argparse
import importlib
import json

from .cases import one_step_case, reset_boundary_case


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--implementation", choices=("starter", "solution"), default="solution")
    args = parser.parse_args()
    compute = importlib.import_module(f"developer.labs.gae.{args.implementation}").compute_gae
    outputs = {
        "label": "Synthetic arithmetic only; no simulation or PPO training",
        "implementation": args.implementation,
        "one_step_continuing": compute(**one_step_case()),
        "one_step_terminated": compute(**one_step_case(terminated=True)),
        "one_step_truncated": compute(**one_step_case(truncated=True)),
        "wrong_reset_obs_value_100": compute(**one_step_case(truncated=True, next_value=100)),
        "two_episodes": compute(**reset_boundary_case()),
    }
    print(json.dumps(outputs, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
