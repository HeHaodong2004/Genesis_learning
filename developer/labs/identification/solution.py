"""Two-parameter OLS reference for teaching, not a production linear solver.

No regularisation or hidden pseudoinverse: rank-deficient data return no unique
parameter estimate. Numerical rank is relative to the largest Gram eigenvalue.
"""

import math

from .common import mse, validate_data


def fit_dynamics(states, inputs, *, rank_tolerance=1e-12):
    states, inputs = validate_data(states, inputs)
    if type(rank_tolerance) not in (float, int) or not 0 < rank_tolerance < 1:
        raise ValueError("rank_tolerance must lie in (0, 1)")
    original_x, original_y, original_inputs = states[:-1], states[1:], inputs
    # A common scale preserves both OLS coefficients and cond(X). Base it on
    # the design, not y: a large target must not make every design entry tiny.
    # This prevents the Gram determinant from overflowing/underflowing when a
    # well-conditioned dataset is merely expressed in very large/small units.
    scale = max(max(map(abs, original_x)), max(map(abs, inputs))) or 1.0
    x = [v / scale for v in original_x]
    inputs = [u / scale for u in inputs]
    y = [target / scale for target in original_y]
    if not all(math.isfinite(target) for target in y):
        raise ValueError("Target/design dynamic range exceeds floating-point limits; check units")
    xx = math.fsum(v * v for v in x)
    uu = math.fsum(u * u for u in inputs)
    xu = math.fsum(v * u for v, u in zip(x, inputs))
    xy = math.fsum(v * target for v, target in zip(x, y))
    uy = math.fsum(u * target for u, target in zip(inputs, y))
    if not all(math.isfinite(number) for number in (xx, uu, xu, xy, uy)):
        raise ValueError("Normal-equation values overflowed; rescale data")
    largest = (xx + uu + math.hypot(xx - uu, 2 * xu)) / 2
    # Equivalent to xx*uu-xu*xu, with less cancellation near collinearity.
    determinant = xx * math.fsum((u - (xu / xx) * v) ** 2 for v, u in zip(x, inputs)) if xx else 0.0
    smallest = determinant / largest if largest else 0.0
    rank = 0 if largest == 0 else (2 if smallest > rank_tolerance * largest else 1)
    result = {
        "n_samples": len(inputs), "rank": rank,
        "rank_tolerance": rank_tolerance,
        "condition_x": math.sqrt(largest / smallest) if rank == 2 else None,
        "identifiable": rank == 2, "a": None, "b": None, "train_one_step_mse": None,
    }
    if rank != 2:
        return result
    a = (xy * uu - uy * xu) / determinant
    b = (uy * xx - xy * xu) / determinant
    if not all(math.isfinite(number) for number in (a, b)):
        raise ValueError("Estimate overflowed; rescale data or improve excitation")
    result.update(a=a, b=b, train_one_step_mse=mse(
        [a * v + b * u for v, u in zip(original_x, original_inputs)], original_y,
    ))
    return result
