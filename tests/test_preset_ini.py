import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from s1_optimizer.errors import PlanError
from s1_optimizer.preset_ini import IniPreset, list_ini_presets, read_ini_source


class PresetIniTests(unittest.TestCase):
    def test_internal_vendor_bases_are_hidden_but_resolvable(self):
        path = self.write("[filament:*common*]\ntemperature=220\n[filament:Visible]\ninherits=*common*\nfilament_type=PLA\n")
        self.assertEqual([p.name for p in list_ini_presets(path)], ["Visible"])
        values, _ = read_ini_source(list_ini_presets(path)[0])
        self.assertEqual(values["nozzle_temperature"], "220")

    def write(self, text):
        folder = tempfile.TemporaryDirectory()
        path = Path(folder.name) / "filament.ini"
        path.write_text(text, encoding="utf-8")
        self.addCleanup(folder.cleanup)
        return path

    def test_standalone_mapping_and_unmapped_audit(self):
        path = self.write("temperature = 220\nfirst_layer_temperature=225\nfilament_type=PLA\ncalibration_gcode = M900 K0\n")
        self.assertEqual(list_ini_presets(path), (IniPreset(path.resolve(), None),))
        values, provenance = read_ini_source(path)
        self.assertEqual(values["nozzle_temperature"], "220")
        self.assertEqual(values["nozzle_temperature_initial_layer"], "225")
        self.assertEqual(values["filament_type"], "PLA")
        self.assertEqual(values["type"], "filament")
        self.assertEqual(values["name"], "filament")
        self.assertEqual(values["ini_unmapped_calibration_gcode"], "M900 K0")
        self.assertEqual(len(provenance[0]["sha256"]), 64)
        self.assertEqual(len(provenance[0]["mapping_sha256"]), 64)

    def test_local_inheritance_and_plate_review(self):
        path = self.write("[filament:Base]\ntemperature=210\n[filament:Child]\ninherits=Base\nfirst_layer_bed_temperature=60\n")
        self.assertEqual([p.section for p in list_ini_presets(path)], ["filament:Base", "filament:Child"])
        values, provenance = read_ini_source(IniPreset(path, "filament:Child"))
        self.assertEqual(IniPreset(path, "filament:Child").name, "Child")
        self.assertEqual(IniPreset(path, "filament:Child").stem, "Child")
        self.assertEqual(values["nozzle_temperature"], "210")
        self.assertEqual(values["textured_plate_temp_initial_layer"], "60")
        self.assertTrue(any(d["review"] for d in provenance[0]["mappings"] if "review" in d))

    def test_ambiguous_and_bad_inheritance_rejected(self):
        path = self.write("[filament:A]\ntemperature=200\n[filament:B]\ntemperature=210\n")
        with self.assertRaises(PlanError):
            read_ini_source(path)
        missing = self.write("[filament:A]\ninherits=Nope\n")
        with self.assertRaises(PlanError):
            read_ini_source(IniPreset(missing, "filament:A"))

    def test_multi_extruder_numeric_value_rejected(self):
        path = self.write("temperature=200;210\n")
        with self.assertRaises(PlanError):
            read_ini_source(path)

    def test_cycle_and_multiple_parents_rejected(self):
        cycle = self.write("[filament:A]\ninherits=B\n[filament:B]\ninherits=A\n")
        with self.assertRaises(PlanError):
            read_ini_source(IniPreset(cycle, "filament:A"))
        parents = self.write("[filament:A]\ninherits=B,C\n[filament:B]\ntemperature=200\n[filament:C]\ntemperature=210\n")
        with self.assertRaises(PlanError):
            read_ini_source(IniPreset(parents, "filament:A"))

    def test_nonfilament_selection_and_unmapped_collision_rejected(self):
        path = self.write("[machine]\ntemperature=200\n[filament:A]\ntemperature=210\n")
        with self.assertRaises(PlanError):
            read_ini_source(IniPreset(path, "machine"))
        collision = self.write("foo/bar=one\nfoo?bar=two\n")
        with self.assertRaises(PlanError):
            read_ini_source(collision)

    def test_uppercase_inherits_is_not_control_directive(self):
        path = self.write("[filament:A]\nInherits=Parent\ntemperature=200\n")
        values, _ = read_ini_source(IniPreset(path, "filament:A"))
        self.assertIn("ini_unmapped_Inherits", values)

    def test_invalid_utf8_duplicate_and_size_rejected(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        bad = Path(folder.name) / "bad.ini"
        bad.write_bytes(b"temperature=\xff")
        with self.assertRaises(PlanError):
            read_ini_source(bad)
        duplicate = Path(folder.name) / "duplicate.ini"
        duplicate.write_text("temperature=200\ntemperature=210\n", encoding="utf-8")
        with self.assertRaises(PlanError):
            read_ini_source(duplicate)
        oversized = Path(folder.name) / "oversized.ini"
        oversized.write_bytes(b"x=" + b"a" * (25 * 1024 * 1024))
        with self.assertRaises(PlanError):
            read_ini_source(oversized)


if __name__ == "__main__":
    unittest.main()
