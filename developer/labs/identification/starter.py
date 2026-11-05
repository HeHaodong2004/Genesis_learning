"""Implement the estimator after writing predictions in your learning log.

Use common.validate_data and common.mse; do not import solution. The contract is
defined in test_contract.py and docs/developer/labs/identification.md.
"""

from .common import validate_data


def fit_dynamics(states, inputs, *, rank_tolerance=1e-12):
    states, inputs = validate_data(states, inputs)
    # TODO 1: Build X rows [states[t], inputs[t]], y[t] = states[t+1].
    # TODO 2: Compute the five sums and the numerical rank/condition of X.
    # TODO 3: Return no unique a/b for rank < 2 (do not hide it with epsilon).
    # TODO 4: Solve the 2x2 normal equations and return training one-step MSE.
    raise NotImplementedError("Implement fit_dynamics after recording your predictions")
