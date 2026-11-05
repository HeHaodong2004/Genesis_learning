"""Controlled synthetic input-design comparison; no training on holdout data."""

import argparse
import importlib
import json
import math

from .common import evaluate, rich_inputs, simulate


def experiment(implementation="solution", *, horizon=128, process_noise=0.03, measurement_noise=0.0):
    if type(horizon) is not int or not 4 <= horizon <= 10000:
        raise ValueError("horizon must be an integer in [4, 10000]")
    for value in (process_noise, measurement_noise):
        if not math.isfinite(value) or value < 0:
            raise ValueError("noise must be finite and nonnegative")
    if implementation not in ("starter", "solution"):
        raise ValueError("implementation must be starter or solution")
    fit = importlib.import_module(f"developer.labs.identification.{implementation}").fit_dynamics
    a, b, initial_state = 0.75, 0.5, 2.0
    actions = {"constant": [1.0] * horizon, "rich": rich_inputs(horizon, seed=2026)}
    report = {
        "synthetic": True, "purpose": "教学：输入设计与有限数据可辨识；不是新科研成果或自我意识证据",
        "implementation": implementation,
        "controls": {
            "true_a": a, "true_b": b, "horizon": horizon, "train_initial_state": initial_state,
            "input_energy_each": float(horizon), "input_max_abs_each": 1.0,
            "rich_train_input_seed": 2026, "train_process_seed": 101, "train_measurement_seed": 102,
            "holdout_input_seed": 2027, "holdout_process_seed": 201, "holdout_measurement_seed": 202,
            "holdout_initial_state": -0.3,
            "noise_note": "同一噪声级别内两个训练组复用相同噪声draws；holdout独立于训练且两组共享。",
            "measurement_noise_std": measurement_noise,
            "rank_note": "rank来自本次有限设计矩阵的数值阈值；不等于所有实验下的结构可辨识性。",
        },
        "comparisons": [],
    }
    for process_std in dict.fromkeys((0.0, process_noise)):
        holdout = simulate(a, b, rich_inputs(horizon, seed=2027), initial_state=-0.3,
                           process_noise_std=process_std, measurement_noise_std=measurement_noise,
                           process_seed=201, measurement_seed=202)
        comparison = {"process_noise_std": process_std, "fits": {}}
        for label, inputs in actions.items():
            training = simulate(a, b, inputs, initial_state=initial_state,
                                process_noise_std=process_std, measurement_noise_std=measurement_noise,
                                process_seed=101, measurement_seed=102)
            estimate = fit(training["observations"], inputs)
            if estimate["identifiable"]:
                estimate["parameter_l2_error"] = math.hypot(estimate["a"] - a, estimate["b"] - b)
                estimate["holdout"] = evaluate(estimate["a"], estimate["b"], holdout)
            else:
                estimate["parameter_l2_error"] = None
                estimate["holdout"] = None
                estimate["reason"] = "按声明数值阈值不输出唯一稳定估计；condition_x=null表示数值秩不足或未定义，不等于证明精确矩阵无唯一解。"
            comparison["fits"][label] = estimate
        report["comparisons"].append(comparison)
    # Constructive witness: two different models agree on a constant equilibrium
    # trajectory, but disagree under the same independent, noiseless input sequence.
    equilibrium = simulate(a, b, actions["constant"], initial_state=initial_state)
    probe = simulate(a, b, rich_inputs(horizon, seed=2027), initial_state=-0.3)
    report["nonidentifiability_witness"] = [
        {"candidate_a": candidate_a, "candidate_b": candidate_b,
         "train": evaluate(candidate_a, candidate_b, equilibrium),
         "holdout": evaluate(candidate_a, candidate_b, probe)}
        for candidate_a, candidate_b in ((0.75, 0.5), (0.5, 1.0))
    ]
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--implementation", choices=("starter", "solution"), default="solution")
    parser.add_argument("--horizon", type=int, default=128)
    parser.add_argument("--process-noise", type=float, default=0.03)
    parser.add_argument("--measurement-noise", type=float, default=0.0)
    args = parser.parse_args()
    try:
        report = experiment(args.implementation, horizon=args.horizon,
                            process_noise=args.process_noise, measurement_noise=args.measurement_noise)
        print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    except (ValueError, NotImplementedError, OverflowError) as exc:
        parser.exit(2, f"Identification lab failed: {exc}\n")


if __name__ == "__main__":
    main()
