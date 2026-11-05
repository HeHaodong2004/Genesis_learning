"""Default: reference solution. LAB_IMPLEMENTATION=starter opts into the red lab."""

import copy
import importlib
import json
import math
import os
from pathlib import Path
import unittest

IMPLEMENTATION = os.environ.get("LAB_IMPLEMENTATION", "solution")
if IMPLEMENTATION not in {"starter", "solution"}:
    raise ValueError("LAB_IMPLEMENTATION must be starter or solution")
compare = importlib.import_module(f"developer.labs.paired_comparison.{IMPLEMENTATION}").paired_comparison


def row(episode, **metrics):
    return {"env_id": 0, "episode_idx": episode, **metrics}


class PairedComparisonContract(unittest.TestCase):
    def test_direction_is_b_minus_a(self):
        result = compare([row(0, score=10)], [row(0, score=13)], ["score"])
        self.assertEqual(result["direction"], "b - a")
        self.assertEqual(result["metrics"]["score"]["mean_diff"], 3)

    def test_duplicate_id_is_rejected_on_either_side_even_if_unmatched(self):
        duplicate = [row(5, score=1), row(5, score=8)]
        for a, b, label in ((duplicate, [row(0)], "A"), ([row(0)], duplicate, "B")):
            with self.subTest(side=label):
                with self.assertRaisesRegex(ValueError, f"{label}.*duplicate"):
                    compare(a, b, ["score"])

    def test_match_by_id_not_input_position(self):
        a = [row(0, score=10), row(1, score=20), row(2, score=1000)]
        b = [row(1, score=24), row(0, score=12), row(3, score=10000)]
        result = compare(a, b, ["score"])
        self.assertEqual(result["n_paired"], 2)
        self.assertEqual((result["unmatched_a"], result["unmatched_b"]), (1, 1))
        self.assertEqual(result["metrics"]["score"]["mean_diff"], 3)
        self.assertAlmostEqual(result["metrics"]["score"]["ci95"], 1.96)

    def test_metric_specific_valid_counts_and_normal_half_width(self):
        a = [row(0, score=10, length=10), row(1, score=20, length=20), row(2, score=30)]
        b = [row(0, score=12, length=8), row(1, score=24, length=16), row(2, score=36, length=7)]
        result = compare(a, b, ["score", "length"])
        self.assertEqual(result["n_paired"], 3)
        score, length = result["metrics"]["score"], result["metrics"]["length"]
        self.assertEqual((score["n_valid"], length["n_valid"], length["n_dropped"]), (3, 2, 1))
        self.assertEqual((score["mean_diff"], length["mean_diff"]), (4, -3))
        self.assertAlmostEqual(score["ci95"], 1.96 * 2 / math.sqrt(3))
        self.assertAlmostEqual(length["ci95"], 1.96)

    def test_invalid_and_nonfinite_metric_values_are_excluded(self):
        invalid = [None, "3", True, float("nan"), float("inf"), float("-inf")]
        for value in invalid:
            for side in ("A", "B"):
                with self.subTest(value=repr(value), side=side):
                    a = [row(0, score=2), row(1, score=value if side == "A" else 2)]
                    b = [row(0, score=5), row(1, score=value if side == "B" else 5)]
                    metric = compare(a, b, ["score"])["metrics"]["score"]
                    self.assertEqual((metric["mean_diff"], metric["n_valid"], metric["n_dropped"]), (3, 1, 1))
                    self.assertIsNone(metric["ci95"])

    def test_overflowing_difference_is_excluded(self):
        metric = compare([row(0, score=-1e308)], [row(0, score=1e308)], ["score"])["metrics"]["score"]
        self.assertEqual((metric["n_valid"], metric["n_dropped"]), (0, 1))
        self.assertIsNone(metric["mean_diff"])

    def test_no_match_or_no_valid_value_is_json_safe(self):
        for a, b in (([row(0)], [row(1)]), ([row(0)], [row(0)]), ([], [])):
            with self.subTest(a=a, b=b):
                result = compare(a, b, ["score"])
                self.assertIsNone(result["metrics"]["score"]["mean_diff"])
                self.assertIsNone(result["metrics"]["score"]["ci95"])
                json.dumps(result, allow_nan=False)

    def test_single_pair_has_no_estimated_uncertainty(self):
        metric = compare([row(0, score=2)], [row(0, score=5)], ["score"])["metrics"]["score"]
        self.assertEqual(metric["n_valid"], 1)
        self.assertIsNone(metric["ci95"])

    def test_constant_differences_have_zero_width(self):
        metric = compare([row(0, score=2), row(1, score=5)], [row(0, score=5), row(1, score=8)], ["score"])["metrics"]["score"]
        self.assertEqual((metric["mean_diff"], metric["ci95"]), (3, 0))

    def test_input_is_not_modified(self):
        a, b = [row(0, score=2)], [row(0, score=5)]
        before = copy.deepcopy((a, b))
        compare(a, b, ["score"])
        self.assertEqual((a, b), before)

    def test_ids_must_be_nonnegative_integers(self):
        bad_rows = [{"env_id": 0}, {"env_id": True, "episode_idx": 0}, {"env_id": 0, "episode_idx": -1}, {"env_id": 0.0, "episode_idx": 0}]
        for bad in bad_rows:
            with self.subTest(row=bad):
                with self.assertRaises(ValueError):
                    compare([bad], [], ["score"])

    def test_metric_keys_have_an_unambiguous_contract(self):
        for keys in (["score", "score"], [""], [None]):
            with self.subTest(keys=keys):
                with self.assertRaises(ValueError):
                    compare([], [], keys)

    def test_synthetic_fixture_is_explicit_and_reproducible(self):
        fixture = json.loads((Path(__file__).parent / "fixtures" / "synthetic.json").read_text(encoding="utf-8"))
        result = compare(fixture["a"], fixture["b"], fixture["keys"])
        self.assertEqual(result["n_paired"], 3)
        self.assertEqual((result["unmatched_a"], result["unmatched_b"]), (1, 1))
        self.assertAlmostEqual(result["metrics"]["success"]["mean_diff"], 2 / 3)
        self.assertAlmostEqual(result["metrics"]["collided"]["mean_diff"], -1 / 3)
        self.assertEqual(result["metrics"]["length"]["n_valid"], 2)
        self.assertEqual(result["metrics"]["length"]["mean_diff"], -3)
        json.dumps(result, allow_nan=False)


if __name__ == "__main__":
    unittest.main()
