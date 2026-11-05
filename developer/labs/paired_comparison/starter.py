"""Intentionally faulty exercise. Edit this file to satisfy test_contract.py.

This is not copied production code: direction and missing-value bugs are seeded
for practice. The production function already uses B-A and filters non-finite
differences. Its duplicate-ID overwrite is the real motivation for this lab.
"""

import math
import statistics


def paired_comparison(rows_a, rows_b, keys=("success", "collided", "length")):
    # TODO 1: Define and enforce ID validity; reject duplicates before indexing.
    indexed_a = {(row["env_id"], row["episode_idx"]): row for row in rows_a}
    indexed_b = {(row["env_id"], row["episode_idx"]): row for row in rows_b}
    common = sorted(indexed_a.keys() & indexed_b.keys())
    result = {
        "direction": "b - a",
        "n_paired": len(common),
        "unmatched_a": len(indexed_a.keys() - indexed_b.keys()),
        "unmatched_b": len(indexed_b.keys() - indexed_a.keys()),
        "metrics": {},
    }
    for key in keys:
        # TODO 2: Match the declared sign; handle unavailable values per metric.
        differences = [indexed_a[i].get(key, 0) - indexed_b[i].get(key, 0) for i in common]
        n_valid = len(differences)
        # TODO 3: Distinguish unavailable uncertainty from a measured zero width.
        half_width = 0.0
        if n_valid >= 2:
            half_width = 1.96 * statistics.stdev(differences) / math.sqrt(n_valid)
        result["metrics"][key] = {
            "mean_diff": statistics.mean(differences) if n_valid else 0.0,
            "ci95": half_width,
            "n_valid": n_valid,
            "n_dropped": 0,
        }
    return result
