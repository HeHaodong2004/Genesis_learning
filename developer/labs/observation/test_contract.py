import copy
import importlib
import os
import unittest

implementation = os.environ.get("LAB_IMPLEMENTATION", "solution")
if implementation not in {"solution", "starter"}:
    raise ValueError("LAB_IMPLEMENTATION must be solution or starter")
policy_input = importlib.import_module(f"developer.labs.observation.{implementation}").policy_input


def packet():
    return {"rays": [1., 2., 3.], "goal": [4., 0.5], "proprio": [0.2, 0.1],
            "privileged_obstacle_xy": [100., 200.], "episode_seed": 42}


class ObservationContract(unittest.TestCase):
    def test_allowlist(self):
        self.assertEqual(set(policy_input(packet())), {"rays", "goal", "proprio"})

    def test_hidden_world_changes_do_not_change_input(self):
        a, b = packet(), packet()
        b["privileged_obstacle_xy"] = [-999., 999.]
        b["episode_seed"] = 999
        self.assertEqual(policy_input(a), policy_input(b))

    def test_sensor_change_is_not_erased(self):
        a, b = packet(), packet()
        b["rays"][0] = 0.2
        self.assertNotEqual(policy_input(a), policy_input(b))

    def test_no_buffer_alias_to_future_observation(self):
        data = packet()
        output = policy_input(data)
        data["rays"][0] = 900.
        self.assertEqual(output["rays"][0], 1.)

    def test_bad_shape_or_missing_sensor(self):
        for value in (None, [], [1., 2.], "123"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                policy_input({**packet(), "rays": value})

    def test_nonfinite_boolean_and_negative_range(self):
        for value in (float("nan"), float("inf"), True, -1.):
            with self.subTest(value=value), self.assertRaises(ValueError):
                policy_input({**packet(), "rays": [value, 2., 3.]})

    def test_does_not_mutate_sensor_input(self):
        data = packet()
        before = copy.deepcopy(data)
        policy_input(data)
        self.assertEqual(data, before)
