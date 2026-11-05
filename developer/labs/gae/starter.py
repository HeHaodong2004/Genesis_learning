"""Intentionally wrong masks. Implement compute_gae yourself; checks are provided."""

from .contract import validate


def compute_gae(rewards, values, next_values, terminated, truncated, *, gamma=0.99, lam=0.95, valid=None):
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
            # TODO: Which boundary removes the value bootstrap?
            done = terminated[time][batch] or truncated[time][batch]
            bootstrap = 0.0 if done else float(next_values[time][batch])
            delta = float(rewards[time][batch]) + gamma * bootstrap - value
            # TODO: Which boundary prevents the NEXT episode's advantage leaking?
            tail = 0.0 if terminated[time][batch] else carry
            carry = delta + gamma * lam * tail
            deltas[time][batch] = delta
            advantages[time][batch] = carry
            returns[time][batch] = carry + value
    return {"deltas": deltas, "advantages": advantages, "returns": returns}
