"""Reference: accept only declared sensor fields, return independent immutable values."""
import math

SHAPES = {"rays": 3, "goal": 2, "proprio": 2}


def policy_input(sensor_packet):
    result = {}
    for name, size in SHAPES.items():
        values = sensor_packet.get(name)
        if not isinstance(values, (list, tuple)) or len(values) != size:
            raise ValueError(f"{name}: expected {size} readings")
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
            raise ValueError(f"{name}: expected finite numbers")
        result[name] = tuple(float(v) for v in values)
    if any(v < 0 for v in result["rays"]):
        raise ValueError("rays: range cannot be negative")
    return result
