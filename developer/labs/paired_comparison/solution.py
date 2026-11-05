"""Reference implementation for the lab, not a replacement for gnav statistics.

The difference is always B minus A. Every metric independently excludes missing,
non-numeric, non-finite, or overflowing differences. ``ci95`` is the half-width
1.96 * sample standard deviation / sqrt(n), or None when fewer than two valid
pairs exist. It is a normal approximation, not a coverage guarantee.
"""

from collections.abc import Mapping, Sequence
import math
from numbers import Real
import statistics
from typing import Any


def _index(rows: Sequence[Mapping[str, Any]], label: str) -> dict:
    indexed = {}
    for position, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"{label} row {position}: expected an object")
        try:
            identity = (row["env_id"], row["episode_idx"])
        except KeyError as error:
            raise ValueError(f"{label} row {position}: missing episode ID") from error
        if any(type(value) is not int or value < 0 for value in identity):
            raise ValueError(f"{label} row {position}: episode IDs must be nonnegative integers")
        if identity in indexed:
            raise ValueError(f"{label}: duplicate episode ID {identity}")
        indexed[identity] = row
    return indexed


def _finite_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, Real):
        return False
    try:
        return math.isfinite(value)
    except (OverflowError, TypeError, ValueError):
        return False


def paired_comparison(rows_a, rows_b, keys=("success", "collided", "length")):
    """Compare unique episodes by ID, reporting metric-specific valid pair counts."""
    keys = tuple(keys)
    if any(not isinstance(key, str) or not key for key in keys):
        raise ValueError("metric keys must be nonempty strings")
    if len(set(keys)) != len(keys):
        raise ValueError("metric keys must be unique")
    indexed_a, indexed_b = _index(rows_a, "A"), _index(rows_b, "B")
    common = sorted(indexed_a.keys() & indexed_b.keys())
    result = {
        "direction": "b - a",
        "n_paired": len(common),
        "unmatched_a": len(indexed_a.keys() - indexed_b.keys()),
        "unmatched_b": len(indexed_b.keys() - indexed_a.keys()),
        "metrics": {},
    }
    for key in keys:
        differences = []
        for identity in common:
            a, b = indexed_a[identity].get(key), indexed_b[identity].get(key)
            if not (_finite_number(a) and _finite_number(b)):
                continue
            difference = float(b) - float(a)
            if math.isfinite(difference):
                differences.append(difference)
        n_valid = len(differences)
        ci95 = None
        if n_valid >= 2:
            ci95 = 1.96 * (statistics.stdev(differences) / math.sqrt(n_valid))
            if not math.isfinite(ci95):
                raise ValueError(f"{key}: confidence half-width exceeds finite numeric range")
        result["metrics"][key] = {
            "mean_diff": statistics.mean(differences) if n_valid else None,
            "ci95": ci95,
            "n_valid": n_valid,
            "n_dropped": len(common) - n_valid,
        }
    return result
