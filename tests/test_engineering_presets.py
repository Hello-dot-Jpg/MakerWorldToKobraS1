import json
from pathlib import Path
import tempfile
import unittest

from s1_optimizer.engineering_presets import plan_engineering_preset
from s1_optimizer.errors import PlanError


class EngineeringPresetTests(unittest.TestCase):
    def fixture(self, root):
        base = {"name": "Anycubic PC @Anycubic Kobra S1 0.4 nozzle", "filament_type": ["PC"],
                "compatible_printers": ["Anycubic Kobra S1 0.4 nozzle"],
                "filament_max_volumetric_speed": ["6"], "filament_diameter": ["1.75"],
                "nozzle_temperature": ["260"], "nozzle_temperature_range_low": ["260"],
                "nozzle_temperature_range_high": ["300"], "filament_start_gcode": ["S1"],
                "pressure_advance": ["0.04"], "filament_flow_ratio": ["0.96"]}
        donor = {**base, "name": "Anycubic PC-CF @Anycubic Kobra S1 Max 0.6 nozzle",
                 "compatible_printers": ["Anycubic Kobra S1 Max 0.6 nozzle"],
                 "filament_type": ["PC-CF"], "filament_max_volumetric_speed": ["8"],
                 "nozzle_temperature_HS": ["270"], "nozzle_temperature_initial_layer": ["270"],
                 "textured_plate_temp": ["110"], "chamber_temperature": ["65"],
                 "activate_chamber_temp_control": ["1"], "filament_start_gcode": ["MAX"],
                 "pressure_advance": ["0.01"]}
        for data in (base, donor):
            (root / (data["name"] + ".json")).write_text(json.dumps(data))
        base["nozzle_temperature_range_high_HS"] = ["240"]
        (root / (base["name"] + ".json")).write_text(json.dumps(base))
        return donor

    def test_guide_preserves_chamber_but_not_control_or_macros(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            original = {p: p.read_bytes() for p in root.glob("*.json")}
            plan = plan_engineering_preset(root, "PC-CF", "0.6")
            self.assertFalse(plan.blockers)
            self.assertEqual(plan.values["chamber_temperature"], ["65"])
            self.assertEqual(plan.values["activate_chamber_temp_control"], ["0"])
            self.assertEqual(plan.values["filament_start_gcode"], ["S1"])
            self.assertEqual(plan.values["pressure_advance"], ["0.04"])
            self.assertEqual(plan.values["filament_max_volumetric_speed"], ["6"])
            self.assertEqual(plan.values["nozzle_temperature"], ["270"])
            self.assertEqual(plan.values["filament_type"], ["PC-CF"])
            self.assertEqual(plan.values["inherits"], "")
            self.assertEqual(plan.values["compatible_printers"], ["Anycubic Kobra S1 0.6 nozzle"])
            self.assertEqual(original, {p: p.read_bytes() for p in original})

    def test_limits_and_unsupported_size(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.fixture(root)
            self.assertTrue(plan_engineering_preset(root, "PC-CF", "0.6", max_bed=100).blockers)
            for args in (("PC-CF", "0.25"), ("unknown", "0.6")):
                with self.assertRaises(PlanError):
                    plan_engineering_preset(root, *args)
            with self.assertRaises(PlanError):
                plan_engineering_preset(root, "PC-CF", "0.6", max_nozzle=350)

    def test_range_extension_and_large_conflict(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            donor = self.fixture(root)
            path = root / (donor["name"] + ".json")
            for low, blocked in (("280", False), ("286", True)):
                donor["nozzle_temperature_range_low"] = [low]
                donor["nozzle_temperature_range_low_HS"] = [low]
                path.write_text(json.dumps(donor))
                plan = plan_engineering_preset(root, "PC-CF", "0.6")
                self.assertEqual(bool(plan.blockers), blocked)
                if not blocked:
                    self.assertEqual(plan.values["nozzle_temperature_range_low"], ["270"])
                    self.assertNotIn("nozzle_temperature_range_low_HS", plan.values)
                    self.assertNotIn("nozzle_temperature_range_high_HS", plan.values)
                    self.assertTrue(any("15 C tolerance" in w for w in plan.warnings))


if __name__ == "__main__":
    unittest.main()
