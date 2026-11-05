"""Boundary oracles for GAE; select the unfinished exercise explicitly via env."""

import copy
import importlib
import json
import os
import unittest

from .cases import one_step_case, reset_boundary_case

IMPLEMENTATION = os.environ.get("LAB_IMPLEMENTATION", "solution")
if IMPLEMENTATION not in {"starter", "solution"}:
    raise ValueError("LAB_IMPLEMENTATION must be starter or solution")
compute_gae = importlib.import_module(f"developer.labs.gae.{IMPLEMENTATION}").compute_gae


class GAEContract(unittest.TestCase):
    def assertMatrixAlmostEqual(self, actual, expected):
        self.assertEqual(len(actual), len(expected))
        for actual_row, expected_row in zip(actual, expected):
            self.assertEqual(len(actual_row), len(expected_row))
            for a, b in zip(actual_row, expected_row):
                self.assertAlmostEqual(a, b, places=10)

    def test_termination_removes_bootstrap_but_truncation_preserves_it(self):
        # r=2, V=1, gamma=.9, V(next)=10: terminal delta=1, trunc delta=10.
        terminal = compute_gae(**one_step_case(terminated=True))
        truncated = compute_gae(**one_step_case(truncated=True))
        self.assertEqual(terminal["advantages"], [[1.0]])
        self.assertEqual(truncated["advantages"], [[10.0]])
        self.assertEqual(truncated["returns"], [[11.0]])

    def test_truncation_stops_trace_into_next_episode(self):
        # gamma=lambda=1, V=0: no bootstrap contribution, isolating trace masking.
        result = compute_gae([[2], [100]], [[0], [0]], [[0], [None]],
                             [[False], [True]], [[True], [False]], gamma=1, lam=1)
        self.assertEqual(result["advantages"], [[2.0], [100.0]])

    def test_hand_calculated_two_episode_oracle(self):
        # delta=(1+.9*3-2, 2+.9*4-3, 100-50)=(1.7,2.6,50).
        # A1=2.6, A0=1.7+.72*2.6=3.572; A2=50 is a separate episode.
        result = compute_gae(**reset_boundary_case())
        self.assertMatrixAlmostEqual(result["deltas"], [[1.7], [2.6], [50]])
        self.assertMatrixAlmostEqual(result["advantages"], [[3.572], [2.6], [50]])
        self.assertMatrixAlmostEqual(result["returns"], [[5.572], [5.6], [100]])

    def test_new_episode_reward_cannot_change_previous_episode_advantage(self):
        case = reset_boundary_case()
        before = compute_gae(**case)
        case["rewards"][2][0] = 1000000
        after = compute_gae(**case)
        self.assertEqual(before["advantages"][:2], after["advantages"][:2])
        self.assertNotEqual(before["advantages"][2], after["advantages"][2])

    def test_batch_columns_do_not_leak_across_different_boundaries(self):
        # Column 0 terminates at t0; column 1 continues until t1 termination.
        result = compute_gae([[1, 10], [2, 20]], [[0, 0], [0, 0]], [[None, 0], [None, None]],
                             [[True, False], [True, True]], [[False, False], [False, False]],
                             gamma=1, lam=1)
        self.assertEqual(result["advantages"], [[1.0, 30.0], [2.0, 20.0]])

    def test_rollout_end_bootstraps_without_inventing_a_terminal_state(self):
        result = compute_gae(**one_step_case())
        self.assertEqual(result["advantages"], [[10.0]])
        self.assertEqual(result["returns"], [[11.0]])

    def test_lambda_zero_equals_one_step_td_and_gamma_zero_equals_reward_minus_value(self):
        case = reset_boundary_case()
        case["lam"] = 0
        result = compute_gae(**case)
        self.assertMatrixAlmostEqual(result["advantages"], [[1.7], [2.6], [50]])
        case["gamma"] = 0
        result = compute_gae(**case)
        self.assertEqual(result["advantages"], [[-1.0], [-1.0], [50.0]])
        self.assertEqual(result["returns"], case["rewards"])

    def test_gamma_and_lambda_one_match_hand_summed_bootstrapped_return(self):
        result = compute_gae([[2], [3]], [[1], [4]], [[4], [5]],
                             [[False], [False]], [[False], [False]], gamma=1, lam=1)
        # G1=3+5=8, G0=2+3+5=10; subtract V=(1,4) => A=(9,4).
        self.assertEqual(result["advantages"], [[9.0], [4.0]])
        self.assertEqual(result["returns"], [[10.0], [8.0]])

    def test_trailing_padding_is_ignored_and_cannot_contaminate_valid_cells(self):
        result = compute_gae([[2, 10], [float("nan"), 20], [None, None]],
                             [[1, 0], [None, 0], [None, None]],
                             [[4, 0], [None, None], [None, None]],
                             [[False, False], [False, True], [False, False]],
                             [[False, False], [False, False], [False, False]],
                             gamma=1, lam=1, valid=[[True, True], [False, True], [False, False]])
        self.assertEqual(result["advantages"], [[5.0, 30.0], [0.0, 20.0], [0.0, 0.0]])
        self.assertEqual(result["returns"], [[6.0, 30.0], [0.0, 20.0], [0.0, 0.0]])
        json.dumps(result, allow_nan=False)

    def test_interior_padding_is_rejected(self):
        case = reset_boundary_case()
        case["valid"] = [[True], [False], [True]]
        with self.assertRaisesRegex(ValueError, "prefix"):
            compute_gae(**case)

    def test_all_padding_column_emits_only_zeros(self):
        result = compute_gae([[None]], [[None]], [[None]], [[False]], [[False]], valid=[[False]])
        self.assertEqual(result, {"deltas": [[0.0]], "advantages": [[0.0]], "returns": [[0.0]]})

    def test_terminal_next_value_is_unused_even_when_nan_or_flags_both_true(self):
        for value in (None, float("nan")):
            case = one_step_case(terminated=True, truncated=True, next_value=value)
            self.assertEqual(compute_gae(**case)["advantages"], [[1.0]])

    def test_valid_numeric_inputs_must_be_finite(self):
        for field in ("rewards", "values", "next_values"):
            for value in (None, True, "1", float("nan"), float("inf")):
                with self.subTest(field=field, value=repr(value)):
                    case = one_step_case(truncated=True)
                    case[field][0][0] = value
                    with self.assertRaisesRegex(ValueError, "finite"):
                        compute_gae(**case)

    def test_nonfinite_computed_result_is_rejected(self):
        case = one_step_case(next_value=1e308)
        case["rewards"] = [[1e308]]
        case["values"] = [[0.0]]
        case["gamma"] = 1
        with self.assertRaisesRegex(ValueError, "finite"):
            compute_gae(**case)

    def test_rectangular_shape_and_boolean_masks_are_enforced(self):
        for field, bad in (("values", []), ("next_values", [[1, 2]]),
                           ("rewards", [[1], []]), ("terminated", [[1]]), ("valid", [[0]])):
            with self.subTest(field=field):
                case = one_step_case()
                case[field] = bad
                with self.assertRaises(ValueError):
                    compute_gae(**case)
        with self.assertRaises(ValueError):
            compute_gae([], [], [], [], [])
        with self.assertRaises(ValueError):
            compute_gae([[]], [[]], [[]], [[]], [[]])

    def test_gamma_lambda_range_and_input_immutability(self):
        for field in ("gamma", "lam"):
            for value in (-0.1, 1.1, True, float("nan")):
                with self.subTest(field=field, value=repr(value)):
                    case = one_step_case()
                    case[field] = value
                    with self.assertRaises(ValueError):
                        compute_gae(**case)
        case = reset_boundary_case()
        before = copy.deepcopy(case)
        compute_gae(**case)
        self.assertEqual(case, before)

    def test_using_reset_observation_is_a_detectable_collection_error(self):
        actual_next = compute_gae(**one_step_case(truncated=True, next_value=10))
        reset_next = compute_gae(**one_step_case(truncated=True, next_value=100))
        self.assertEqual(actual_next["advantages"], [[10.0]])
        self.assertEqual(reset_next["advantages"], [[91.0]])
        # The GAE function cannot know that the finite value 100 came from reset.
        self.assertEqual(reset_next["advantages"][0][0] - actual_next["advantages"][0][0], 81)


if __name__ == "__main__":
    unittest.main()
