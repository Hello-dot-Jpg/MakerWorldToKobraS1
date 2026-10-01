from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from s1_optimizer.parser import inspect_archive

from tests.helpers import make_3mf


class ParserTests(unittest.TestCase):
    def test_nested_json_is_flattened_with_types_and_categories(self) -> None:
        settings = {
            "layer_height": 0.2,
            "machine": {"printer_model": "P1S", "enabled": True},
            "filament_settings": [{"max_volumetric_speed": 22}, None],
            "empty": [],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = make_3mf(Path(directory) / "sample.3mf", settings)
            inspection = inspect_archive(str(path))
            by_path = {setting.logical_path: setting for setting in inspection.settings}
            self.assertEqual(by_path["layer_height"].value_type, "number")
            self.assertEqual(by_path["machine.enabled"].value_type, "boolean")
            self.assertIn("printer", by_path["machine.printer_model"].categories)
            self.assertIn(
                "speed", by_path["filament_settings[0].max_volumetric_speed"].categories
            )
            self.assertEqual(by_path["filament_settings[1]"].value_type, "null")
            self.assertEqual(by_path["empty"].value_type, "array")

    def test_malformed_project_settings_warns_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = make_3mf(
                Path(directory) / "sample.3mf",
                extra={"Metadata/project_settings.config": b"{broken"},
            )
            inspection = inspect_archive(str(path))
            self.assertEqual(inspection.settings, ())
            self.assertTrue(any("project_settings.config" in item for item in inspection.warnings))

    def test_unusual_keys_have_collision_free_identities(self) -> None:
        settings = {"a.b": 1, "a": {"b": 2}, "items": {"0": "object"}}
        with tempfile.TemporaryDirectory() as directory:
            path = make_3mf(Path(directory) / "sample.3mf", settings)
            inspection = inspect_archive(str(path))
            identities = [setting.identity for setting in inspection.settings]
            self.assertEqual(len(identities), len(set(identities)))
            by_value = {setting.value: setting for setting in inspection.settings}
            self.assertNotEqual(by_value[1].canonical_path, by_value[2].canonical_path)
            self.assertEqual(by_value[1].logical_path, '["a.b"]')

    def test_duplicate_json_key_is_reported_not_silently_collapsed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = make_3mf(
                Path(directory) / "sample.3mf",
                extra={"Metadata/project_settings.config": b'{"speed": 10, "speed": 20}'},
            )
            inspection = inspect_archive(str(path))
            self.assertEqual(inspection.settings, ())
            self.assertTrue(any("duplicate JSON object key" in item for item in inspection.warnings))

    def test_casefold_ties_have_deterministic_setting_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = make_3mf(Path(directory) / "first.3mf", {"speed": 1, "Speed": 2})
            second = make_3mf(Path(directory) / "second.3mf", {"Speed": 2, "speed": 1})
            first_order = [setting.name for setting in inspect_archive(str(first)).settings]
            second_order = [setting.name for setting in inspect_archive(str(second)).settings]
            self.assertEqual(first_order, second_order)

    def test_separate_machine_process_and_filament_configs_are_settings(self) -> None:
        extra = {
            "Metadata/machine_settings_1.config": b'{"max_speed_x": "500"}',
            "Metadata/process_settings_1.config": b'{"wall_loops": "3"}',
            "Metadata/filament_settings_1.config": b'{"type": "PETG"}',
            "Metadata/source_info.config": b'{"type": "metadata"}',
        }
        with tempfile.TemporaryDirectory() as directory:
            path = make_3mf(Path(directory) / "sample.3mf", {"layer_height": 0.2}, extra)
            inspection = inspect_archive(str(path))
            by_member = {
                setting.source_member: setting
                for setting in inspection.settings
                if setting.source_member != "Metadata/project_settings.config"
            }
            self.assertEqual(by_member["Metadata/machine_settings_1.config"].scope, "printer")
            self.assertIn(
                "printer", by_member["Metadata/machine_settings_1.config"].categories
            )
            self.assertEqual(by_member["Metadata/process_settings_1.config"].scope, "process")
            self.assertEqual(by_member["Metadata/filament_settings_1.config"].scope, "filament")
            self.assertNotIn("Metadata/source_info.config", by_member)

    def test_cross_file_identity_conflict_is_reported(self) -> None:
        extra = {
            "Metadata/machine_settings_1.config": b'{"printer_model": "Other"}',
        }
        with tempfile.TemporaryDirectory() as directory:
            path = make_3mf(
                Path(directory) / "sample.3mf",
                {"printer_model": "Kobra S1"},
                extra,
            )
            inspection = inspect_archive(str(path))
            self.assertEqual(
                [conflict.name for conflict in inspection.setting_conflicts],
                ["printer_model"],
            )
            self.assertTrue(
                any("Conflicting high-risk setting" in item for item in inspection.warnings)
            )

    def test_profile_bundle_alternatives_are_not_active_conflicts(self) -> None:
        extra = {
            "Metadata/machine_settings_1.config": (
                b'{"printer_settings_id":"Target A","nozzle_diameter":"0.4"}'
            ),
            "Metadata/machine_settings_2.config": (
                b'{"printer_settings_id":"Target B","nozzle_diameter":"0.8"}'
            ),
        }
        with tempfile.TemporaryDirectory() as directory:
            path = make_3mf(
                Path(directory) / "sample.3mf",
                {"printer_settings_id": "Target A", "nozzle_diameter": "0.4"},
                extra,
            )
            inspection = inspect_archive(str(path))
            variants = {item.member: item.selection for item in inspection.profile_variants}
            self.assertEqual(
                variants["Metadata/machine_settings_1.config"], "selected"
            )
            self.assertEqual(
                variants["Metadata/machine_settings_2.config"], "alternative"
            )
            self.assertEqual(inspection.setting_conflicts, ())
            self.assertFalse(
                any("Conflicting high-risk setting" in item for item in inspection.warnings)
            )

    def test_multiple_selected_filament_slots_are_not_cross_conflicts(self) -> None:
        extra = {
            "Metadata/filament_settings_1.config": (
                b'{"filament_settings_id":"PLA","nozzle_temperature":"220"}'
            ),
            "Metadata/filament_settings_2.config": (
                b'{"filament_settings_id":"PETG","nozzle_temperature":"250"}'
            ),
        }
        with tempfile.TemporaryDirectory() as directory:
            path = make_3mf(
                Path(directory) / "sample.3mf",
                {
                    "filament_settings_id": ["PLA", "PETG"],
                    "nozzle_temperature": ["220", "250"],
                },
                extra,
            )
            inspection = inspect_archive(str(path))
            self.assertEqual(
                [item.selection for item in inspection.profile_variants],
                ["selected", "selected"],
            )
            self.assertEqual(inspection.setting_conflicts, ())

    def test_xml_structure_counts_are_exposed(self) -> None:
        model = b'''<model xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">
          <resources><object id="1"><mesh/></object></resources>
          <build><item objectid="1"/></build>
        </model>'''
        model_settings = b'''<config>
          <object id="1"><part id="1"/></object>
          <plate><model_instance/></plate>
          <assemble><assemble_item/></assemble>
        </config>'''
        with tempfile.TemporaryDirectory() as directory:
            path = make_3mf(
                Path(directory) / "sample.3mf",
                {"layer_height": 0.2},
                {
                    "3D/3dmodel.model": model,
                    "Metadata/model_settings.config": model_settings,
                },
            )
            counts = inspect_archive(str(path)).structure_counts
            self.assertEqual(counts["resource_objects"], 1)
            self.assertEqual(counts["mesh_objects"], 1)
            self.assertEqual(counts["build_items"], 1)
            self.assertEqual(counts["model_settings_objects"], 1)
            self.assertEqual(counts["model_settings_parts"], 1)
            self.assertEqual(counts["model_instances"], 1)
            self.assertEqual(counts["plates"], 1)
            self.assertEqual(counts["assembly_items"], 1)

    def test_three_machine_limit_values_are_preserved_without_schema_warning(self) -> None:
        settings = {"machine_max_speed_x": ["600", "300", "780"]}
        with tempfile.TemporaryDirectory() as directory:
            path = make_3mf(Path(directory) / "sample.3mf", settings)
            inspection = inspect_archive(str(path))
            values = [
                setting.value
                for setting in inspection.settings
                if setting.name == "machine_max_speed_x"
            ]
            self.assertEqual(values, ["600", "300", "780"])
            self.assertEqual(inspection.warnings, ())

    def test_legacy_slic3r_config_is_parsed_as_untyped_strings(self) -> None:
        legacy = (
            b"; generated by AnycubicSlicer 1.4.1\n"
            b"\n"
            b"; printer_model = KOBRA3\n"
            b"; filament_type = ABS;ABS;ABS;ABS\n"
            b"; first_layer_speed = 60\n"
            b"; start_gcode = G28\\nG1 X10 Y10\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = make_3mf(
                Path(directory) / "sample.3mf",
                {},
                {"Metadata/Slic3r_PE.config": legacy},
            )
            inspection = inspect_archive(str(path))
            values = {setting.name: setting for setting in inspection.settings}
            self.assertEqual(values["printer_model"].value, "KOBRA3")
            self.assertEqual(values["filament_type"].value, "ABS;ABS;ABS;ABS")
            self.assertEqual(values["first_layer_speed"].value, "60")
            self.assertEqual(values["start_gcode"].value, r"G28\nG1 X10 Y10")
            self.assertEqual(values["printer_model"].scope, "legacy-project")
            member = next(
                item
                for item in inspection.structured_members
                if item.name == "Metadata/Slic3r_PE.config"
            )
            self.assertEqual(member.detected_type, "legacy-slic3r-config")
            self.assertEqual(member.parse_status, "parsed")

if __name__ == "__main__":
    unittest.main()
