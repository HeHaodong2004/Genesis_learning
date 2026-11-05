"""Data generation and evaluation, kept separate from the learner's estimator."""

import math
import random


def finite_vector(values, name):
    values = list(values)
    if any(type(value) not in (int, float) or not math.isfinite(value) for value in values):
        raise ValueError(f"{name} must contain finite numbers, not booleans")
    return [float(value) for value in values]


def validate_data(states, inputs):
    states = finite_vector(states, "states")
    inputs = finite_vector(inputs, "inputs")
    if not inputs or len(states) != len(inputs) + 1:
        raise ValueError("Need N >= 1 inputs and N+1 states")
    return states, inputs


def mse(predictions, targets):
    predictions = finite_vector(predictions, "predictions")
    targets = finite_vector(targets, "targets")
    if not targets or len(predictions) != len(targets):
        raise ValueError("MSE needs equally sized nonempty sequences")
    return math.fsum((pred - target) ** 2 for pred, target in zip(predictions, targets)) / len(targets)


def rich_inputs(n, seed):
    rng = random.Random(seed)
    return [rng.choice((-1.0, 1.0)) for _ in range(n)]


def simulate(a, b, inputs, *, initial_state=0.0, process_noise_std=0.0,
             measurement_noise_std=0.0, process_seed=0, measurement_seed=1):
    """v[t+1] = a*v[t] + b*u[t] + w[t]; z[t] = v[t] + e[t]."""
    a, b, initial_state, process_noise_std, measurement_noise_std = finite_vector(
        [a, b, initial_state, process_noise_std, measurement_noise_std], "parameters"
    )
    if process_noise_std < 0 or measurement_noise_std < 0:
        raise ValueError("Noise standard deviations must be nonnegative")
    inputs = finite_vector(inputs, "inputs")
    if not inputs:
        raise ValueError("Need at least one input")
    process_rng, measurement_rng = random.Random(process_seed), random.Random(measurement_seed)
    states = [initial_state]
    for action in inputs:
        state = a * states[-1] + b * action + process_rng.gauss(0.0, process_noise_std)
        if not math.isfinite(state):
            raise ValueError("Trajectory overflowed; reduce horizon or parameter magnitude")
        states.append(state)
    observations = [v + measurement_rng.gauss(0.0, measurement_noise_std) for v in states]
    return {"states": states, "observations": observations, "inputs": inputs}


def evaluate(a, b, trajectory):
    """One-step uses each observed state; rollout only uses the first observation."""
    observed, inputs = validate_data(trajectory["observations"], trajectory["inputs"])
    one_step = [a * state + b * action for state, action in zip(observed[:-1], inputs)]
    rollout = [observed[0]]
    for action in inputs:
        rollout.append(a * rollout[-1] + b * action)
    return {
        "one_step_observed_mse": mse(one_step, observed[1:]),
        "rollout_observed_mse": mse(rollout[1:], observed[1:]),
        "rollout_latent_mse": mse(rollout[1:], trajectory["states"][1:]),
    }
