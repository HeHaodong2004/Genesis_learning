"""Default solution is green; LAB_IMPLEMENTATION=starter selects the exercise."""

import copy
import importlib
import json
import math
import os
import unittest

from .common import evaluate, rich_inputs, simulate
from .run import experiment

IMPLEMENTATION = os.environ.get("LAB_IMPLEMENTATION", "solution")
if IMPLEMENTATION not in ("starter", "solution"):
    raise ValueError("LAB_IMPLEMENTATION must be starter or solution")
fit = importlib.import_module(f"developer.labs.identification.{IMPLEMENTATION}").fit_dynamics


class IdentificationContract(unittest.TestCase):
    def test_hand_calculation_with_orthogonal_rows(self):
        # Rows [0,1], [1,0], targets [1,0.5]: a=0.5, b=1.
        result = fit([0, 1, 0.5], [1, 0])
        self.assertTrue(result["identifiable"])
        self.assertEqual(result["rank"], 2)
        self.assertAlmostEqual(result["a"], 0.5)
        self.assertAlmostEqual(result["b"], 1)
        self.assertAlmostEqual(result["condition_x"], 1)
        self.assertAlmostEqual(result["train_one_step_mse"], 0)

    def test_hand_calculation_with_nonorthogonal_rows(self):
        # 2=a+b, 0=2a-b; catches swapped targets and wrong determinant.
        result = fit([1, 2, 0], [1, -1])
        self.assertAlmostEqual(result["a"], 2 / 3)
        self.assertAlmostEqual(result["b"], 4 / 3)

    def test_no_motion_and_no_input_gives_rank_zero(self):
        result = fit([0] * 9, [0] * 8)
        self.assertEqual(result["rank"], 0)
        self.assertFalse(result["identifiable"])
        for key in ("a", "b", "condition_x", "train_one_step_mse"):
            self.assertIsNone(result[key])
        json.dumps(result, allow_nan=False)

    def test_free_decay_cannot_identify_input_gain(self):
        data = simulate(0.75, 0.5, [0] * 16, initial_state=1)
        result = fit(data["states"], data["inputs"])
        self.assertEqual(result["rank"], 1)
        self.assertFalse(result["identifiable"])

    def test_nonzero_collinear_columns_cannot_identify_two_parameters(self):
        states, inputs = [1.0], []
        for _ in range(8):
            inputs.append(2 * states[-1])
            states.append(0.75 * states[-1] + 0.5 * inputs[-1])
        result = fit(states, inputs)
        self.assertEqual(result["rank"], 1)
        self.assertIsNone(result["a"])
        self.assertIsNone(result["b"])

    def test_constant_equilibrium_data_are_rank_deficient(self):
        result = fit([2] * 129, [1] * 128)
        self.assertEqual(result["rank"], 1)
        self.assertFalse(result["identifiable"])

    def test_constant_input_with_transient_can_have_full_rank(self):
        data = simulate(0.75, 0.5, [1] * 128, initial_state=0)
        result = fit(data["states"], data["inputs"])
        self.assertEqual(result["rank"], 2)
        self.assertAlmostEqual(result["a"], 0.75, places=10)
        self.assertAlmostEqual(result["b"], 0.5, places=10)

    def test_rich_noiseless_trajectory_recovers_parameters(self):
        for a, b in ((0.75, 0.5), (0.2, 1.2), (-0.3, 0.4)):
            with self.subTest(a=a, b=b):
                data = simulate(a, b, rich_inputs(128, 2026), initial_state=2)
                result = fit(data["states"], data["inputs"])
                self.assertEqual(result["rank"], 2)
                self.assertAlmostEqual(result["a"], a, places=11)
                self.assertAlmostEqual(result["b"], b, places=11)
                self.assertLess(result["train_one_step_mse"], 1e-24)

    def test_process_noise_recovery_on_prespecified_seed(self):
        data = simulate(0.75, 0.5, rich_inputs(512, 2026), initial_state=2,
                        process_noise_std=0.03, process_seed=101)
        result = fit(data["states"], data["inputs"])
        self.assertLess(abs(result["a"] - 0.75), 0.02)
        self.assertLess(abs(result["b"] - 0.5), 0.02)
        self.assertGreater(result["train_one_step_mse"], 0)

    def test_unexcited_models_can_fit_training_and_disagree_on_holdout(self):
        training = simulate(0.75, 0.5, [1] * 64, initial_state=2)
        holdout = simulate(0.75, 0.5, rich_inputs(64, 2027), initial_state=-0.3)
        self.assertEqual(evaluate(0.5, 1.0, training)["one_step_observed_mse"], 0)
        self.assertEqual(evaluate(0.75, 0.5, training)["one_step_observed_mse"], 0)
        self.assertGreater(evaluate(0.5, 1.0, holdout)["rollout_observed_mse"], 0.01)
        self.assertEqual(evaluate(0.75, 0.5, holdout)["rollout_observed_mse"], 0)
        self.assertFalse(fit(training["states"], training["inputs"])["identifiable"])

    def test_holdout_rollout_does_not_use_later_observed_states(self):
        # True y=[1,2,3], a=1,b=1, initial=0, u=1. Replace middle observation
        # with 20: one-step feedback changes, free-running predictions remain 1,2,3.
        original = {"states": [0, 1, 2, 3], "observations": [0, 1, 2, 3], "inputs": [1, 1, 1]}
        changed = copy.deepcopy(original)
        changed["observations"][2] = 20
        self.assertEqual(evaluate(1, 1, changed)["rollout_latent_mse"], 0)
        self.assertGreater(evaluate(1, 1, changed)["one_step_observed_mse"], 0)

    def test_condition_number_is_of_design_not_gram(self):
        # X=[0,2; 1,0] => singular values 2,1. States need not follow model.
        result = fit([0, 1, 1], [2, 0])
        self.assertAlmostEqual(result["condition_x"], 2)

    def test_uniform_extreme_scales_preserve_orthogonal_oracle(self):
        # X = scale * I with the two rows reversed: cond(X)=1, a=.5,b=1.
        # The unscaled determinant is scale**4 and exceeds float range at
        # either end, although the regression itself is perfectly conditioned.
        for scale in (1e-100, 1e154):
            with self.subTest(scale=scale):
                result = fit([0, scale, 0.5 * scale], [scale, 0])
                self.assertEqual(result["rank"], 2)
                self.assertTrue(result["identifiable"])
                self.assertAlmostEqual(result["condition_x"], 1)
                self.assertAlmostEqual(result["a"], 0.5)
                self.assertAlmostEqual(result["b"], 1)
                self.assertEqual(result["train_one_step_mse"], 0)

    def test_reported_mse_keeps_original_units_after_scaling(self):
        # X=[[0,1],[1,0],[1,1]], y=[1,1,0] gives a=b=1/3 and MSE=4/9.
        # Multiplying all data by 10 preserves a,b and multiplies MSE by 100.
        result = fit([0, 10, 10, 0], [10, 0, 10])
        self.assertAlmostEqual(result["a"], 1 / 3)
        self.assertAlmostEqual(result["b"], 1 / 3)
        self.assertAlmostEqual(result["train_one_step_mse"], 400 / 9)

    def test_nearly_collinear_data_respect_declared_rank_tolerance(self):
        result = fit([2, 2 + 1e-10, 2 - 1e-10], [1, 1])
        self.assertEqual(result["rank"], 1)

    def test_invalid_data_are_rejected(self):
        for states, inputs in (([], []), ([0, 1], [1, 2]), ([0, True], [1]),
                               ([0, float("nan")], [1]), ([0, 1], [float("inf")])):
            with self.subTest(states=states, inputs=inputs), self.assertRaises(ValueError):
                fit(states, inputs)

    def test_input_sequences_are_unchanged(self):
        states, inputs = [0, 1, 0.5], [1, 0]
        before = copy.deepcopy((states, inputs))
        fit(states, inputs)
        self.assertEqual((states, inputs), before)

    def test_reference_experiment_is_reproducible_and_json_safe(self):
        first = experiment(IMPLEMENTATION)
        second = experiment(IMPLEMENTATION)
        self.assertEqual(first, second)
        self.assertTrue(first["synthetic"])
        self.assertEqual(first["controls"]["input_energy_each"], 128)
        self.assertEqual(first["comparisons"][0]["fits"]["constant"]["rank"], 1)
        self.assertEqual(first["comparisons"][0]["fits"]["rich"]["rank"], 2)
        json.dumps(first, allow_nan=False)

    def test_measurement_noise_is_explicitly_separate(self):
        clean = simulate(0.75, 0.5, rich_inputs(16, 2026), process_noise_std=0)
        noisy = simulate(0.75, 0.5, clean["inputs"], process_noise_std=0, measurement_noise_std=0.2)
        self.assertEqual(clean["states"], noisy["states"])
        self.assertNotEqual(clean["observations"], noisy["observations"])
        self.assertEqual(fit(noisy["observations"], noisy["inputs"])["rank"], 2)


if __name__ == "__main__":
    unittest.main()
