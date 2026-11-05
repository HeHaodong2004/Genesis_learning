"""Hand-selected transition data, not simulator output or training evidence."""


def reset_boundary_case():
    """Episode 1 truncates at t=1; t=2 belongs to a new episode and terminates."""
    return {
        "rewards": [[1.0], [2.0], [100.0]],
        "values": [[2.0], [3.0], [50.0]],
        "next_values": [[3.0], [4.0], [None]],
        "terminated": [[False], [False], [True]],
        "truncated": [[False], [True], [False]],
        "gamma": 0.9,
        "lam": 0.8,
    }


def one_step_case(*, terminated=False, truncated=False, next_value=10.0):
    return {
        "rewards": [[2.0]], "values": [[1.0]], "next_values": [[next_value]],
        "terminated": [[terminated]], "truncated": [[truncated]],
        "gamma": 0.9, "lam": 0.8,
    }
