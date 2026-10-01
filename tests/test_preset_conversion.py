import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from s1_optimizer.errors import PlanError
from s1_optimizer.preset_conversion import convert_preset, export_presets, read_source


class PresetConversionTests(unittest.TestCase):
    def test_official_base_detached_for_native_project_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp:
            source, machine, base = self.fixtures(Path(temp))
            base.filament.source_kind = "official"
            base.effective_values.update({
                "nozzle_temperature_HS": ["230"],
                "nozzle_temperature_initial_layer_HS": ["230"],
                "nozzle_temperature_BRASS": ["230"],
                "setting_id": "STOCK", "inherits": "stock parent",
                "activate_chamber_temp_control": ["1"],
            })
            before = json.dumps(base.effective_values, sort_keys=True)
            source_before = source.read_bytes()
            plan = convert_preset(source, machine, base, hotend="ceramic", max_bed_temp=110)
            self.assertFalse(plan.blockers)
            self.assertEqual(plan.values["inherits"], "")
            self.assertEqual(plan.values["is_custom_defined"], "1")
            self.assertNotIn("setting_id", plan.values)
            for key in ("nozzle_temperature_HS", "nozzle_temperature_initial_layer_HS", "nozzle_temperature_BRASS"):
                self.assertEqual(plan.values[key], ["255"])
            self.assertEqual(plan.values["activate_chamber_temp_control"], ["0"])
            self.assertEqual(plan.values["filament_start_gcode"], ["SAFE"])
            self.assertEqual(plan.values["name"], plan.name)
            self.assertTrue(any("project reopen" in w for w in plan.warnings))
            self.assertEqual(json.dumps(base.effective_values, sort_keys=True), before)
            self.assertEqual(source.read_bytes(), source_before)

    def test_material_correction_requires_explicit_opt_in_and_records_source(self):
        with tempfile.TemporaryDirectory() as temp:
            source, machine, base = self.fixtures(Path(temp), filament_type=["PC"])
            before = source.read_bytes()
            base.filament.material = "PC-CF"
            base.effective_values["filament_type"] = ["PC-CF"]
            with self.assertRaises(PlanError):
                convert_preset(source, machine, base, accept_base_material=True)
            base.filament.source_kind = "explicit"
            with self.assertRaises(PlanError):
                convert_preset(source, machine, base)
            plan = convert_preset(source, machine, base, accept_base_material=True,
                                  hotend="ceramic", max_bed_temp=110)
            self.assertFalse(plan.blockers)
            self.assertEqual(plan.values["filament_type"], ["PC-CF"])
            self.assertTrue(any(p.get("material_correction", {}).get("source") == "PC" for p in plan.provenance))
            action = next(d for d in plan.decisions if d["key"] == "filament_type")
            self.assertEqual(action["source"], ["PC"])
            self.assertEqual(action["destination"], ["PC-CF"])
            self.assertEqual(source.read_bytes(), before)

    def test_explicit_base_is_self_contained_and_validated(self):
        from s1_optimizer.filaments import load_standalone_filament_base
        from s1_optimizer.errors import TargetDiscoveryError
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, machine, original = self.fixtures(root)
            path = root / "base.json"
            values = {**original.effective_values, "type": "filament", "inherits": "",
                      "nozzle_temperature_HS": ["290"], "activate_chamber_temp_control": ["1"],
                      "compatible_printers": [machine.target.label], "setting_id": "old"}
            path.write_text(json.dumps(values))
            base = load_standalone_filament_base(path, machine)
            plan = convert_preset(source, machine, base, hotend="ceramic", max_bed_temp=110)
            self.assertFalse(plan.blockers)
            self.assertEqual(plan.values["inherits"], "")
            self.assertEqual(plan.values["nozzle_temperature_HS"], ["255"])
            self.assertEqual(plan.values["activate_chamber_temp_control"], ["0"])
            self.assertEqual(plan.values["filament_start_gcode"], ["SAFE"])
            self.assertEqual(plan.values["pressure_advance"], ["0.03"])
            self.assertEqual(plan.values["filament_max_volumetric_speed"], ["16"])
            self.assertEqual(plan.values["name"], plan.name)
            self.assertNotIn("setting_id", plan.values)
            self.assertEqual(json.loads(path.read_text()), values)
            for invalid in ({"inherits": "foreign"}, {"compatible_printers": []},
                            {"compatible_printers": ["S1 0.4"]}, {"type": "machine"},
                            {"compatible_printers_condition": "true"}):
                path.write_text(json.dumps({**values, **invalid}))
                with self.assertRaises(TargetDiscoveryError):
                    load_standalone_filament_base(path, machine)

    def test_ini_conversion_export_and_plate_warning(self):
        from s1_optimizer.preset_ini import list_ini_presets
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _, machine, base = self.fixtures(root)
            source = root / "materials.ini"
            source.write_text("[filament:Example PETG]\nfilament_type=PETG\ntemperature=250\nfirst_layer_temperature=255\nbed_temperature=75\nfilament_max_volumetric_speed=22\nstart_filament_gcode=FOREIGN MACRO\n", encoding="utf-8")
            before = source.read_bytes()
            for selected in (source, list_ini_presets(source)[0]):
                plan = convert_preset(selected, machine, base, hotend="ceramic", max_bed_temp=110)
                self.assertFalse(plan.blockers)
                self.assertEqual(plan.values["nozzle_temperature"], ["250"])
                self.assertEqual(plan.values["textured_plate_temp"], ["75"])
                self.assertEqual(plan.values["filament_max_volumetric_speed"], ["16"])
                self.assertTrue(any("ONLY to Textured PEI" in w for w in plan.warnings))
                self.assertFalse(any(key.startswith("ini_unmapped_") for key in plan.values))
                self.assertEqual(plan.values["filament_start_gcode"], ["SAFE"])
                folder = export_presets([plan], root)
                self.assertEqual(json.loads((folder / plan.filename).read_text()), plan.values)
            self.assertEqual(source.read_bytes(), before)

    def test_display_identity_is_safe_for_slicer_persistence(self):
        with tempfile.TemporaryDirectory() as temp:
            original = 'Vendor Wood / Marble \\ Test: <>"|?*\x01'
            source, machine, base = self.fixtures(Path(temp), name=original)
            before = source.read_bytes()
            plan = convert_preset(source, machine, base, max_nozzle_temp=320, max_bed_temp=110)
            self.assertFalse(plan.blockers)
            self.assertFalse(any(c in plan.name for c in '<>:"/\\|?*\x01'))
            self.assertEqual(plan.values["name"], plan.name)
            self.assertEqual(plan.values["filament_settings_id"], [plan.name])
            self.assertTrue(any(d["action"] == "TRANSLATE" and d["source"] == original for d in plan.decisions))
            self.assertEqual(source.read_bytes(), before)

    def test_user_reported_hotend_limits_and_firmware_gate(self):
        for hotend, firmware, ceiling in (("ptfe-lined", False, 300),
                                          ("all-metal", False, 320),
                                          ("ceramic", False, 320),
                                          ("ceramic", True, 350)):
            with self.subTest(hotend=hotend, firmware=firmware), tempfile.TemporaryDirectory() as temp:
                source, machine, base = self.fixtures(Path(temp),
                    nozzle_temperature=[str(ceiling)], nozzle_temperature_initial_layer=[str(ceiling)])
                plan = convert_preset(source, machine, base, hotend=hotend,
                    ceramic_firmware_confirmed=firmware, max_bed_temp=100)
                self.assertFalse(plan.blockers)
                self.assertEqual(plan.provenance[-1]["confirmed_nozzle_ceiling"], str(ceiling))
                self.assertEqual(plan.values["nozzle_temperature"], [str(ceiling)])
                self.assertTrue(any("User-reported" in w for w in plan.warnings))
                lower = convert_preset(source, machine, base, hotend=hotend,
                    ceramic_firmware_confirmed=firmware, max_nozzle_temp=ceiling-1, max_bed_temp=100)
                self.assertTrue(lower.blockers)
                higher = convert_preset(source, machine, base, hotend=hotend,
                    ceramic_firmware_confirmed=firmware, max_nozzle_temp=ceiling+1, max_bed_temp=100)
                self.assertTrue(any("Entered nozzle ceiling" in b for b in higher.blockers))
                missing_bed = convert_preset(source, machine, base, hotend=hotend,
                    ceramic_firmware_confirmed=firmware)
                self.assertTrue(any("physical bed" in b for b in missing_bed.blockers))
        with tempfile.TemporaryDirectory() as temp:
            source, machine, base = self.fixtures(Path(temp), nozzle_temperature=["350"])
            self.assertTrue(convert_preset(source, machine, base, hotend="ceramic", max_bed_temp=100).blockers)
            for hotend in ("unspecified", "ptfe-lined", "all-metal", "unknown"):
                with self.assertRaises(PlanError):
                    convert_preset(source, machine, base, hotend=hotend, ceramic_firmware_confirmed=True)

    def test_inherited_plate_temperature_cannot_bypass_physical_limit(self):
        with tempfile.TemporaryDirectory() as temp:
            source, machine, base = self.fixtures(Path(temp))
            base.effective_values["hot_plate_temp"] = ["120"]
            plan = convert_preset(source, machine, base, max_nozzle_temp=300, max_bed_temp=100)
            self.assertTrue(any("Effective hot_plate_temp" in b for b in plan.blockers))

    def test_temperature_range_extensions_and_exact_tolerance(self):
        cases = (
            (240, 280, 290, 280, 240, 290, False),
            (240, 280, 285, 280, 240, 285, False),
            (240, 280, 295, 225, 225, 295, False),
            (240, 280, 295.01, 240, 240, 280, True),
            (240, 280, 280, 224.99, 240, 280, True),
            (240, 280, 280, 240, 240, 280, False),
            (280, 240, 260, 260, 280, 240, True),
        )
        for low, high, normal, first, out_low, out_high, blocked in cases:
            with self.subTest(case=(low, high, normal, first)), tempfile.TemporaryDirectory() as temp:
                source, machine, base = self.fixtures(Path(temp),
                    nozzle_temperature_range_low=[str(low)], nozzle_temperature_range_high=[str(high)],
                    nozzle_temperature=[str(normal)], nozzle_temperature_initial_layer=[str(first)])
                before = source.read_bytes()
                plan = convert_preset(source, machine, base, max_nozzle_temp=320, max_bed_temp=110)
                self.assertEqual(bool(plan.blockers), blocked)
                self.assertEqual(plan.values["nozzle_temperature_range_low"], [str(out_low)])
                self.assertEqual(plan.values["nozzle_temperature_range_high"], [str(out_high)])
                self.assertEqual(plan.values["nozzle_temperature"], [str(normal)])
                self.assertEqual(plan.values["nozzle_temperature_initial_layer"], [str(first)])
                changed = not blocked and (out_low != low or out_high != high)
                self.assertEqual(any("15 C tolerance" in w for w in plan.warnings), changed)
                translations = [d for d in plan.decisions if d["action"] == "TRANSLATE"]
                self.assertEqual(len(translations), int(out_low != low) + int(out_high != high))
                if changed:
                    folder = export_presets([plan], Path(temp))
                    self.assertIn("15 C tolerance", (folder / "conversion-report.txt").read_text())
                    self.assertEqual(json.loads((folder / plan.filename).read_text())["nozzle_temperature_range_high"], [str(out_high)])
                self.assertEqual(source.read_bytes(), before)

    def test_range_extension_never_bypasses_physical_limits(self):
        with tempfile.TemporaryDirectory() as temp:
            source, machine, base = self.fixtures(Path(temp),
                nozzle_temperature_range_low=["240"], nozzle_temperature_range_high=["280"],
                nozzle_temperature=["290"], nozzle_temperature_initial_layer=["280"])
            plan = convert_preset(source, machine, base, max_nozzle_temp=285, max_bed_temp=110)
            self.assertEqual(plan.values["nozzle_temperature_range_high"], ["290"])
            self.assertTrue(any("physical nozzle ceiling" in b for b in plan.blockers))
            with self.assertRaises(PlanError):
                export_presets([plan], Path(temp))
            unconfirmed = convert_preset(source, machine, base)
            self.assertTrue(any("Confirm the physical" in b for b in unconfirmed.blockers))

    def test_inherited_range_is_extended_or_blocked_without_changing_temperatures(self):
        for temperature, blocked in ((245, False), (255, False), (256, True)):
            with self.subTest(temperature=temperature), tempfile.TemporaryDirectory() as temp:
                source, machine, base = self.fixtures(Path(temp),
                    nozzle_temperature=[str(temperature)],
                    nozzle_temperature_initial_layer=[str(temperature)])
                base.effective_values.update(nozzle_temperature_range_low=["190"],
                                             nozzle_temperature_range_high=["240"])
                before = source.read_bytes()
                plan = convert_preset(source, machine, base, max_nozzle_temp=320, max_bed_temp=110)
                self.assertEqual(bool(plan.blockers), blocked)
                self.assertEqual(plan.values["nozzle_temperature"], [str(temperature)])
                self.assertEqual(source.read_bytes(), before)
                self.assertEqual(base.effective_values["nozzle_temperature_range_high"], ["240"])
                if not blocked:
                    self.assertEqual(plan.values["nozzle_temperature_range_high"], [str(temperature)])
                    decision = next(d for d in plan.decisions if d["key"] == "nozzle_temperature_range_high")
                    self.assertEqual(decision["action"], "TRANSLATE")
                    self.assertIsNone(decision["source"])
                    self.assertIn("inherited", decision["reason"])
                    self.assertTrue(any("15 C tolerance" in w for w in plan.warnings))

    def fixtures(self, root, **changes):
        values = {"name": "Vendor PETG @Foreign printer", "filament_type": ["PETG"],
                  "nozzle_temperature": ["255"], "nozzle_temperature_initial_layer": ["255"],
                  "textured_plate_temp": ["70"], "filament_max_volumetric_speed": ["22"],
                  "filament_start_gcode": ["FOREIGN MACRO"], "pressure_advance": ["0.99"],
                  "unknown_vendor_setting": ["1"], "required_nozzle_HRC": ["3"]}
        values.update(changes)
        source = root / "input.json"
        source.write_text(json.dumps(values), encoding="utf-8")
        machine = SimpleNamespace(target=SimpleNamespace(nozzle_diameter="0.6", nozzle_type="hardened_steel", label="S1 0.6"),
                                  effective_values={}, to_dict=lambda: {"machine": "S1 0.6"})
        dest = {**values, "filament_max_volumetric_speed": ["16"], "filament_start_gcode": ["SAFE"], "pressure_advance": ["0.03"]}
        del dest["unknown_vendor_setting"]
        base = SimpleNamespace(filament=SimpleNamespace(material="PETG", nozzle_diameter="0.6", label="Anycubic PETG 0.6"),
                               effective_values=dest, to_dict=lambda: {"base": "PETG"})
        return source, machine, base

    def test_portable_fields_foreign_macros_flow_and_export(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, machine, base = self.fixtures(root)
            original = source.read_bytes()
            plan = convert_preset(source, machine, base, max_nozzle_temp=270, max_bed_temp=100)
            self.assertFalse(plan.blockers)
            self.assertEqual(plan.values["filament_max_volumetric_speed"], ["16"])
            self.assertEqual(plan.values["nozzle_temperature"], ["255"])
            self.assertEqual(plan.values["nozzle_temperature_HS"], ["255"])
            self.assertEqual(plan.values["nozzle_temperature_initial_layer_BRASS"], ["255"])
            self.assertEqual(plan.values["filament_start_gcode"], ["SAFE"])
            self.assertEqual(plan.values["pressure_advance"], ["0.03"])
            self.assertNotIn("unknown_vendor_setting", plan.values)
            self.assertEqual(plan.values["inherits"], "")
            self.assertEqual(plan.values["compatible_printers"], [machine.target.label])
            out = export_presets([plan], root)
            self.assertEqual(json.loads((out / plan.filename).read_text()), plan.values)
            second = export_presets([plan], root)
            self.assertNotEqual(out, second)
            self.assertEqual(source.read_bytes(), original)
            with self.assertRaises(PlanError):
                export_presets([plan, plan], root)

    def test_all_nozzle_variant_fields_follow_explicit_portable_values(self):
        with tempfile.TemporaryDirectory() as temp:
            source, machine, base = self.fixtures(
                Path(temp), fan_max_speed=["100"], slow_down_layer_time=["3"])
            base.effective_values.update({
                "fan_max_speed_HS": ["20"],
                "fan_max_speed_BRASS": ["30"],
                "slow_down_layer_time_HS": ["10"],
                "slow_down_layer_time_BRASS": ["11"],
            })
            plan = convert_preset(source, machine, base,
                                  max_nozzle_temp=270, max_bed_temp=100)
            self.assertFalse(plan.blockers)
            for key in ("fan_max_speed_HS", "fan_max_speed_BRASS",
                        "slow_down_layer_time_HS", "slow_down_layer_time_BRASS"):
                self.assertEqual(plan.values[key], plan.values[key.removesuffix("_HS").removesuffix("_BRASS")])

    def test_missing_or_insufficient_limits_block_without_clamping_temperature(self):
        with tempfile.TemporaryDirectory() as temp:
            source, machine, base = self.fixtures(Path(temp))
            plan = convert_preset(source, machine, base)
            self.assertEqual(len(plan.blockers), 2)
            with self.assertRaises(PlanError):
                export_presets([plan], Path(temp))
            plan = convert_preset(source, machine, base, max_nozzle_temp=240, max_bed_temp=60)
            self.assertTrue(plan.blockers)
            self.assertEqual(plan.values["nozzle_temperature"], ["255"])

    def test_invalid_arrays_nil_and_nonfinite_block(self):
        for value in (["NaN"], ["nil"], ["220", "255"], ["-2"], ["0"]):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as temp:
                source, machine, base = self.fixtures(Path(temp), filament_max_volumetric_speed=value)
                plan = convert_preset(source, machine, base, max_nozzle_temp=300, max_bed_temp=110)
                self.assertTrue(plan.blockers)

    def test_wrong_material_nozzle_and_hardness(self):
        with tempfile.TemporaryDirectory() as temp:
            source, machine, base = self.fixtures(Path(temp))
            machine.target.nozzle_type = "brass"
            self.assertTrue(convert_preset(source, machine, base).blockers)
            base.filament.material = "PLA"
            with self.assertRaises(PlanError):
                convert_preset(source, machine, base)

    def test_all_nozzle_sizes_and_explicit_hardened_steel_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            source, machine, base = self.fixtures(Path(temp))
            identities = set()
            for size in ("0.25", "0.4", "0.6", "0.8"):
                machine.target.nozzle_diameter = size
                machine.target.label = f"S1 {size}"
                machine.target.nozzle_type = "brass"
                base.filament.nozzle_diameter = size
                plan = convert_preset(source, machine, base, max_nozzle_temp=270,
                                      max_bed_temp=100, nozzle_material="hardened-steel")
                self.assertFalse(plan.blockers)
                self.assertEqual(plan.values["compatible_printers"], [f"S1 {size}"])
                self.assertIn("hardened-steel", plan.name)
                self.assertEqual(machine.target.nozzle_type, "brass")
                identities.add(plan.filename)
            self.assertEqual(len(identities), 4)
            base.filament.material = "PETG"
            base.filament.nozzle_diameter = "0.4"
            with self.assertRaises(PlanError):
                convert_preset(source, machine, base)

    def test_inheritance_and_rejection_of_missing_cycle_and_traversal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            parent = root / "parent.json"
            parent.write_text(json.dumps({"filament_type": ["PETG"], "name": "parent"}))
            child = root / "child.json"
            child.write_text(json.dumps({"inherits": "parent", "name": "child"}))
            values, history = read_source(child)
            self.assertEqual(values["filament_type"], ["PETG"])
            self.assertEqual(len(history), 2)
            for name in ("missing", "child", "../parent", "C:\\parent"):
                child.write_text(json.dumps({"inherits": name}))
                with self.assertRaises(PlanError):
                    read_source(child)
