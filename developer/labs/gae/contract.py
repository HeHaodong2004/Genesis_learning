"""Input checks shared by the exercise and answer, leaving the GAE work to you."""

import math
from numbers import Real


def finite_number(value, name):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite number")
    try:
        result = float(value)
    except (OverflowError, ValueError) as error:
        raise ValueError(f"{name} must be a finite number") from error
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite number")
    return result


def validate(rewards, values, next_values, terminated, truncated, valid, gamma, lam):
    for name, value in (("gamma", gamma), ("lam", lam)):
        number = finite_number(value, name)
        if not 0 <= number <= 1:
            raise ValueError(f"{name} must lie in [0, 1]")
    if not isinstance(rewards, (list, tuple)) or not rewards:
        raise ValueError("expected nonempty time-major [T, B] rewards")
    if not isinstance(rewards[0], (list, tuple)) or not rewards[0]:
        raise ValueError("expected nonempty batch dimension B")
    time_steps, batch_size = len(rewards), len(rewards[0])
    if valid is None:
        valid = [[True] * batch_size for _ in range(time_steps)]
    matrices = {"rewards": rewards, "values": values, "next_values": next_values,
                "terminated": terminated, "truncated": truncated, "valid": valid}
    for name, matrix in matrices.items():
        if not isinstance(matrix, (list, tuple)) or len(matrix) != time_steps:
            raise ValueError(f"{name}: expected shape [{time_steps}, {batch_size}]")
        if any(not isinstance(row, (list, tuple)) or len(row) != batch_size for row in matrix):
            raise ValueError(f"{name}: expected shape [{time_steps}, {batch_size}]")
    for name, mask in (("terminated", terminated), ("truncated", truncated), ("valid", valid)):
        if any(type(cell) is not bool for row in mask for cell in row):
            raise ValueError(f"{name} must contain bool cells, not 0/1 numbers")
    for batch in range(batch_size):
        padding_seen = False
        for time in range(time_steps):
            if not valid[time][batch]:
                padding_seen = True
                continue
            if padding_seen:
                raise ValueError("valid must be a prefix per environment; interior padding is ambiguous")
            for name, matrix in (("rewards", rewards), ("values", values)):
                finite_number(matrix[time][batch], f"{name}[{time}][{batch}]")
            # True terminal states do not bootstrap. Their unused next value may
            # be None/NaN; never implement this by multiplying NaN by zero.
            if not terminated[time][batch]:
                finite_number(next_values[time][batch], f"next_values[{time}][{batch}]")
    return time_steps, batch_size, valid
