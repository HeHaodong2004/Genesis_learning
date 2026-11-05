"""Reference GAE with separate bootstrap and trace masks, standard library only."""

from .contract import finite_number, validate


def compute_gae(rewards, values, next_values, terminated, truncated, *, gamma=0.99, lam=0.95, valid=None):
    """Return deltas, advantages, returns as time-major [T, B] float lists.

    next_values[t][b] is V of this transition's TRUE next observation, before
    reset, evaluated with the same frozen critic. It is not generally values[t+1].
    Trailing padding emits zeros and is not a training sample. This function
    neither normalizes advantages nor carries a trace across rollout chunks.
    """
    time_steps, batch_size, valid = validate(
        rewards, values, next_values, terminated, truncated, valid, gamma, lam
    )
    deltas = [[0.0] * batch_size for _ in range(time_steps)]
    advantages = [[0.0] * batch_size for _ in range(time_steps)]
    returns = [[0.0] * batch_size for _ in range(time_steps)]
    for batch in range(batch_size):
        carry = 0.0
        for time in reversed(range(time_steps)):
            if not valid[time][batch]:
                carry = 0.0
                continue
            value = float(values[time][batch])
            bootstrap = 0.0 if terminated[time][batch] else float(next_values[time][batch])
            delta = float(rewards[time][batch]) + gamma * bootstrap - value
            tail = 0.0 if (terminated[time][batch] or truncated[time][batch]) else carry
            carry = delta + gamma * lam * tail
            deltas[time][batch] = finite_number(delta, f"delta[{time}][{batch}]")
            advantages[time][batch] = finite_number(carry, f"advantage[{time}][{batch}]")
            returns[time][batch] = finite_number(carry + value, f"return[{time}][{batch}]")
    return {"deltas": deltas, "advantages": advantages, "returns": returns}
