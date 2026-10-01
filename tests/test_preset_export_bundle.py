import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from s1_optimizer.errors import PlanError
from s1_optimizer.preset_conversion import PresetPlan, export_presets


class PresetExportBundleTests(unittest.TestCase):
    def plan(self, filename="one.json", blockers=()):
        return PresetPlan("One", filename, {"type": "filament", "name": "One"}, [], [], [], list(blockers))

    def test_bundle_contains_exact_json_bytes_only(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = export_presets([self.plan()], Path(temp))
            json_path = folder / "one.json"
            with zipfile.ZipFile(folder / "importable-presets.zip") as bundle:
                self.assertEqual(bundle.namelist(), ["one.json"])
                self.assertEqual(bundle.read("one.json"), json_path.read_bytes())
            self.assertTrue((folder / "conversion-report.txt").exists())

    def test_blocked_plans_create_nothing(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(PlanError):
                export_presets([self.plan(blockers=("blocked",))], Path(temp))
            self.assertEqual(list(Path(temp).iterdir()), [])

    def test_repeated_export_preserves_first_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            first = export_presets([self.plan()], Path(temp))
            before = {p.name: p.read_bytes() for p in first.iterdir()}
            second = export_presets([self.plan()], Path(temp))
            self.assertNotEqual(first, second)
            self.assertEqual(before, {p.name: p.read_bytes() for p in first.iterdir()})

    def test_bundle_failure_cleans_only_fresh_export(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original = root / "keep.json"
            original.write_text("original", encoding="utf-8")
            with patch("s1_optimizer.preset_conversion.zipfile.ZipFile", side_effect=OSError("test failure")):
                with self.assertRaises(OSError):
                    export_presets([self.plan()], root)
            self.assertEqual(list(root.iterdir()), [original])
            self.assertEqual(original.read_text(), "original")


if __name__ == "__main__":
    unittest.main()
