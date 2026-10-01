from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from s1_optimizer.errors import PlanError
from s1_optimizer.parser import inspect_archive
from s1_optimizer.plan import build_conversion_plan, build_machine_plan
from s1_optimizer.processes import ProcessOption, ResolvedProcessTarget
from s1_optimizer.resolution import resolve_machine_target
from s1_optimizer.targets import discover_targets
from s1_optimizer.writer import write_optimized_archive

from tests.helpers import make_3mf


class WriterTests(unittest.TestCase):
    def test_physical_nozzle_override_round_trip_and_unknown_material(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, base = self._plan(root)
            plan = build_conversion_plan(
                source, base.target, nozzle_hardware_type="hardened-steel"
            )
            output = root / "hardware.3mf"
            write_optimized_archive(plan, output)
            with zipfile.ZipFile(output) as archive:
                config = json.loads(archive.read("Metadata/project_settings.config"))
                self.assertEqual(config["nozzle_type"], "hardened_steel")
                self.assertEqual(config["nozzle_hrc"], "0")
                self.assertEqual(config["inherits"], base.target.target.label)
                self.assertEqual(config["printer_settings_id"], plan.effective_machine_label)
                self.assertIn("hardware override", config["printer_settings_id"])
                self.assertEqual(archive.read("Metadata/paint.bin"), b"paint-data")
            self.assertEqual(plan.nozzle_hardware_source, "user")
            self.assertEqual(base.target.effective_values["nozzle_type"], "brass")
            unknown = build_conversion_plan(source, base.target, nozzle_hardware_type="bimetal")
            self.assertEqual(unknown.effective_machine_label, base.target.target.label)
            self.assertTrue(any("no exact" in warning for warning in unknown.warnings))
            self.assertEqual(
                {a.setting_name: a.new_value for a in unknown.actions},
                {a.setting_name: a.new_value for a in base.actions},
            )

    def _process(self, root: Path) -> ResolvedProcessTarget:
        option = ProcessOption(
            "official:process", "0.20mm test", "0.4", "0.2", "official",
            str(root / "process.json"), None, None, "test", "D" * 64,
        )
        return ResolvedProcessTarget(option, (), {
            "layer_height": "0.2", "wall_loops": "2",
        })

    def test_embedded_official_process_inherits_selected_leaf(self) -> None:
        from dataclasses import replace
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, base = self._plan(root)
            process = self._process(root)
            process = replace(process, process=replace(
                process.process, label="0.18mm selected", inherits="0.30mm base",
            ))
            plan = build_conversion_plan(source, base.target, process=process)
            output = root / "selected-leaf.3mf"
            write_optimized_archive(plan, output)
            with zipfile.ZipFile(output) as archive:
                project = json.loads(archive.read("Metadata/project_settings.config"))
                embedded = json.loads(archive.read("Metadata/process_settings_1.config"))
            self.assertEqual(project["inherits_group"][0], "0.18mm selected")
            self.assertEqual(embedded["inherits"], project["inherits_group"][0])

    def _plan(self, root: Path):
        machine = root / "machine"
        machine.mkdir()
        name = "Anycubic Kobra S1 0.4 nozzle"
        (machine / f"{name}.json").write_text(
            json.dumps(
                {
                    "name": name,
                    "printer_settings_id": name,
                    "printer_model": "Anycubic Kobra S1",
                    "nozzle_diameter": ["0.4"],
                    "nozzle_type": "brass",
                    "gcode_flavor": "klipper",
                    "machine_start_gcode": "G9111",
                }
            ),
            encoding="utf-8",
        )
        source = make_3mf(
            root / "source.3mf",
            {
                "printer_model": "Bambu Lab X1",
                "printer_settings_id": "Bambu Lab X1 0.4 nozzle",
                "nozzle_diameter": ["0.4"],
                "nozzle_type": "hardened_steel",
                "gcode_flavor": "bambu",
                "machine_start_gcode": "M1002",
                "wall_loops": "5",
            },
            {
                "Metadata/paint.bin": b"paint-data",
                "Metadata/plate_1.json": json.dumps(
                    {"nozzle_diameter": 0.6, "paint_marker": "keep"}
                ).encode("utf-8"),
            },
        )
        target = discover_targets(machine_dir=machine)[0]
        return source, build_machine_plan(
            source, resolve_machine_target(target, machine_dir=machine)
        )

    def test_writer_changes_only_project_settings_and_validates_structure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, plan = self._plan(root)
            source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
            output = root / "output.3mf"
            result = write_optimized_archive(plan, output)
            self.assertEqual(
                set(result.changed_members),
                {"Metadata/project_settings.config", "Metadata/plate_1.json"},
            )
            self.assertEqual(result.unchanged_members_verified, 4)
            self.assertTrue(inspect_archive(str(output)).is_valid_3mf)
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), source_hash)
            with zipfile.ZipFile(output) as archive:
                project = json.loads(
                    archive.read("Metadata/project_settings.config").decode("utf-8")
                )
                self.assertEqual(project["printer_model"], "Anycubic Kobra S1")
                self.assertEqual(project["wall_loops"], "5")
                self.assertEqual(archive.read("Metadata/paint.bin"), b"paint-data")
                plate = json.loads(archive.read("Metadata/plate_1.json"))
                self.assertEqual(plate["nozzle_diameter"], 0.4)
                self.assertEqual(plate["paint_marker"], "keep")

    def test_flattened_embedded_profile_is_removed_from_new_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, plan = self._plan(root)
            # Rebuild fixture with an embedded foreign machine profile.
            with zipfile.ZipFile(source, "a") as archive:
                archive.writestr(
                    "Metadata/machine_settings_1.config",
                    json.dumps({"printer_settings_id": "Foreign"}),
                )
            # The source changed, so create a fresh plan against the same resolved target.
            machine_dir = root / "machine"
            target = discover_targets(machine_dir=machine_dir)[0]
            reconciled = build_machine_plan(
                source, resolve_machine_target(target, machine_dir=machine_dir)
            )
            self.assertFalse(reconciled.write_blockers)
            self.assertTrue(
                any(action.action == "REMOVE" for action in reconciled.archive_actions)
            )
            output = root / "reconciled.3mf"
            result = write_optimized_archive(reconciled, output)
            self.assertIn("Metadata/machine_settings_1.config", result.changed_members)
            with zipfile.ZipFile(output) as archive:
                self.assertNotIn(
                    "Metadata/machine_settings_1.config", archive.namelist()
                )

    def test_unflattened_embedded_profile_setting_blocks_export(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, _plan = self._plan(root)
            with zipfile.ZipFile(source, "a") as archive:
                archive.writestr(
                    "Metadata/process_settings_1.config",
                    json.dumps({"print_settings_id": "Foreign", "hidden_tune": "1"}),
                )
            machine_dir = root / "machine"
            target = discover_targets(machine_dir=machine_dir)[0]
            blocked = build_conversion_plan(
                source,
                resolve_machine_target(target, machine_dir=machine_dir),
                process=self._process(root),
            )
            self.assertTrue(blocked.write_blockers)
            with self.assertRaisesRegex(PlanError, "Export blocked"):
                write_optimized_archive(blocked, root / "blocked.3mf")

    def test_unretargeted_embedded_process_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, original_plan = self._plan(root)
            with zipfile.ZipFile(source, "a") as archive:
                archive.writestr(
                    "Metadata/process_settings_1.config",
                    json.dumps({"wall_loops": "2"}),
                )
            plan = build_machine_plan(source, original_plan.target)
            self.assertFalse(plan.write_blockers)
            self.assertFalse(any(action.action == "REMOVE"
                                 for action in plan.archive_actions))
            output = root / "preserved.3mf"
            write_optimized_archive(plan, output)
            with zipfile.ZipFile(output) as archive:
                self.assertIn("Metadata/process_settings_1.config", archive.namelist())

    def test_retargeted_flattened_embedded_conflict_is_removed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, original_plan = self._plan(root)
            with zipfile.ZipFile(source, "a") as archive:
                archive.writestr(
                    "Metadata/process_settings_1.config",
                    json.dumps({"print_settings_id": "Foreign", "wall_loops": "2"}),
                )
            plan = build_conversion_plan(
                source, original_plan.target, process=self._process(root)
            )
            self.assertFalse(plan.write_blockers)
            self.assertTrue(any(
                action.source_member == "Metadata/process_settings_1.config"
                and action.action == "REMOVE"
                for action in plan.archive_actions
            ))
            output = root / "retargeted.3mf"
            write_optimized_archive(plan, output)
            with zipfile.ZipFile(output) as archive:
                embedded = json.loads(archive.read("Metadata/process_settings_1.config"))
                project = json.loads(archive.read("Metadata/project_settings.config"))
                original = json.loads(archive.read(
                    "Metadata/s1optimizer_original_process_reference.json"
                ))
                self.assertEqual(embedded["print_settings_id"], project["print_settings_id"])
                self.assertEqual(embedded["name"], project["print_settings_id"])
                self.assertNotEqual(embedded["print_settings_id"], "Foreign")
                self.assertEqual(embedded["wall_loops"], "5")
                self.assertTrue(original["reference_only"])
                self.assertEqual(original["settings"]["wall_loops"], "5")
                self.assertNotIn("machine_start_gcode", original["settings"])
                self.assertNotIn("gcode_flavor", original["settings"])

    def test_source_layer_height_has_its_own_embedded_process(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, base = self._plan(root)
            with zipfile.ZipFile(source, "r") as archive:
                original = {info.filename: archive.read(info) for info in archive.infolist()}
            project = json.loads(original["Metadata/project_settings.config"])
            project["layer_height"] = "0.16"
            project["ironing_direction"] = "45"
            schema_process_values = {
                "ironing_inset": "0.21", "skeleton_infill_density": "15%",
                "skeleton_infill_line_width": "0.45", "skin_infill_density": "15%",
                "skin_infill_line_width": "0.45", "skin_infill_depth": "2",
                "support_ironing": "0", "support_ironing_pattern": "rectilinear",
                "support_ironing_flow": "10%", "support_ironing_spacing": "0.15",
                "filename_format": "{input_filename_base}_{print_time}.gcode",
            }
            project.update(schema_process_values)
            project["print_settings_id"] = "0.16mm Bambu source"
            project["printhost_apikey"] = "source-secret-not-a-process-setting"
            project["print_host"] = "printer-host-not-a-process-setting"
            project["host_type"] = "source-host-type-not-a-process-setting"
            project["filament_self_index"] = ["0"]
            project["machine_prepare_compensation_time"] = "10"
            project["unknown_vendor_speed"] = "500"
            original["Metadata/project_settings.config"] = json.dumps(project).encode()
            source.unlink()
            with zipfile.ZipFile(source, "w") as archive:
                for name, data in original.items():
                    archive.writestr(name, data)

            plan = build_conversion_plan(source, base.target, process=self._process(root))
            output = root / "source-height.3mf"
            write_optimized_archive(plan, output)
            with zipfile.ZipFile(output) as archive:
                saved = json.loads(archive.read("Metadata/project_settings.config"))
                embedded = json.loads(archive.read("Metadata/process_settings_1.config"))
                self.assertEqual(saved["layer_height"], "0.16")
                self.assertEqual(embedded["layer_height"], "0.16")
                self.assertEqual(embedded["ironing_direction"], "45")
                self.assertIn("filename_format", saved["different_settings_to_system"][0].split(";"))
                for name, value in schema_process_values.items():
                    self.assertEqual(embedded[name], value)
                self.assertEqual(embedded["print_settings_id"], saved["print_settings_id"])
                self.assertTrue(saved["print_settings_id"].startswith("[Optimized] 0.16mm"))
                self.assertEqual(embedded["inherits"], "0.20mm test")
                self.assertNotIn("machine_start_gcode", embedded)
                self.assertNotIn("gcode_flavor", embedded)
                self.assertNotIn("printhost_apikey", embedded)
                self.assertNotIn("print_host", embedded)
                self.assertNotIn("host_type", embedded)
                self.assertNotIn("filament_self_index", embedded)
                self.assertNotIn("machine_prepare_compensation_time", embedded)
                self.assertNotIn("unknown_vendor_speed", embedded)
                original = json.loads(archive.read(
                    "Metadata/s1optimizer_original_process_reference.json"
                ))
                self.assertEqual(original["original_print_settings_id"], "0.16mm Bambu source")
                self.assertEqual(original["settings"]["layer_height"], "0.16")
                self.assertNotIn("printhost_apikey", original["settings"])
                self.assertNotIn("print_host", original["settings"])
                self.assertNotIn("host_type", original["settings"])
                original_bytes = archive.read(
                    "Metadata/s1optimizer_original_process_reference.json"
                )
            second_plan = build_conversion_plan(
                output, base.target, process=self._process(root)
            )
            self.assertFalse(second_plan.write_blockers)
            second_output = root / "source-height-again.3mf"
            write_optimized_archive(second_plan, second_output)
            with zipfile.ZipFile(second_output) as archive:
                self.assertEqual(
                    archive.read("Metadata/s1optimizer_original_process_reference.json"),
                    original_bytes,
                )

    def test_writer_refuses_source_or_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, plan = self._plan(root)
            with self.assertRaisesRegex(PlanError, "must not be the source"):
                write_optimized_archive(plan, source)
            existing = root / "existing.3mf"
            existing.write_bytes(b"keep")
            with self.assertRaisesRegex(PlanError, "overwrite"):
                write_optimized_archive(plan, existing)
            self.assertEqual(existing.read_bytes(), b"keep")


if __name__ == "__main__":
    unittest.main()
