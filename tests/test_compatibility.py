import unittest

from s1_optimizer.compatibility import scalarize


class ScalarCompatibilityTests(unittest.TestCase):
    def test_agreeing_numeric_and_boolean_values(self):
        for key, value, expected in (
            ("outer_wall_speed", ["60", "60"], "60"),
            ("enable_overhang_speed", ["1"], "1"),
            ("top_solid_infill_flow_ratio", ["1", "1"], "1"),
            ("overhang_1_4_speed", ["0", "0"], "0"),
            ("small_perimeter_speed", ["50%", "50%"], "50%"),
            ("enable_overhang_speed", "1,1", "1"),
        ):
            with self.subTest(key=key):
                self.assertEqual(scalarize(key, value), (expected, None))

    def test_mixed_empty_and_invalid_values_block(self):
        for key, value in (
            ("outer_wall_speed", ["60", "200"]),
            ("enable_overhang_speed", ["1", "0"]),
            ("outer_wall_speed", []),
            ("outer_wall_speed", ["NaN"]),
            ("outer_wall_speed", ["Infinity"]),
            ("outer_wall_speed", ["-1"]),
            ("outer_wall_speed", ["50%"]),
            ("outer_wall_speed", [True]),
            ("enable_overhang_speed", ["true"]),
        ):
            with self.subTest(key=key, value=value):
                self.assertIsNotNone(scalarize(key, value)[1])

    def test_no_general_array_flattening(self):
        for key in ("filament_flow_ratio", "filament_type", "machine_max_speed_x", "unknown_setting"):
            self.assertEqual(scalarize(key, ["1", "1"]), (["1", "1"], None))
        self.assertEqual(scalarize("outer_wall_speed", "60"), ("60", None))
