from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from s1_optimizer.compare import compare_inspections
from s1_optimizer.parser import inspect_archive

from tests.helpers import make_3mf


class CompareTests(unittest.TestCase):
    def test_reports_only_changed_and_equal_with_typed_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            left_path = make_3mf(
                root / "left.3mf", {"equal": 1, "changed": 1, "left_only": None}
            )
            right_path = make_3mf(
                root / "right.3mf", {"equal": 1, "changed": "1", "right_only": False}
            )
            result = compare_inspections(
                inspect_archive(str(left_path)), inspect_archive(str(right_path))
            )
            self.assertEqual([item.name for item in result.only_left], ["left_only"])
            self.assertEqual([item.name for item in result.only_right], ["right_only"])
            self.assertEqual(len(result.changed), 1)
            self.assertEqual(result.changed[0].left.value_type, "integer")
            self.assertEqual(result.changed[0].right.value_type, "string")
            self.assertEqual([item.name for item in result.equal], ["equal"])
            self.assertEqual([group.name for group in result.by_name.only_left], ["left_only"])
            self.assertEqual([group.name for group in result.by_name.only_right], ["right_only"])
            self.assertEqual([group.name for group in result.by_name.changed], ["changed"])
            self.assertEqual([left.name for left, _ in result.by_name.equal], ["equal"])

    def test_name_comparison_matches_array_and_scalar_locations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            left_path = make_3mf(root / "left.3mf", {"outer_wall_speed": ["200"]})
            right_path = make_3mf(root / "right.3mf", {"outer_wall_speed": "200"})
            result = compare_inspections(
                inspect_archive(str(left_path)), inspect_archive(str(right_path))
            )
            self.assertEqual(result.by_name.changed, ())
            self.assertEqual(
                [left.name for left, _ in result.by_name.equal],
                ["outer_wall_speed"],
            )
            self.assertNotEqual(result.only_left, ())
            self.assertNotEqual(result.only_right, ())


if __name__ == "__main__":
    unittest.main()
