from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from s1_optimizer.errors import PlanError
from s1_optimizer.constants import MAX_STRUCTURED_MEMBER_BYTES
from s1_optimizer.filaments import FilamentOption, ResolvedFilamentTarget
from s1_optimizer.plan import (
    _clamped_value,
    build_conversion_plan,
    build_machine_plan,
    read_project_settings,
)
from s1_optimizer.processes import ProcessOption, ResolvedProcessTarget
from s1_optimizer.resolution import resolve_machine_target
from s1_optimizer.targets import discover_targets, select_target

from tests.helpers import MODEL_XML, make_3mf


class PlanTests(unittest.TestCase):
    def test_plate_preference_warning_names_requested_plate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            name = "Anycubic Kobra S1 0.4 nozzle"
            (root / f"{name}.json").write_text(json.dumps({
                "name": name, "printer_settings_id": name,
                "printer_model": "Anycubic Kobra S1", "nozzle_diameter": ["0.4"],
            }), encoding="utf-8")
            machine = resolve_machine_target(
                discover_targets(machine_dir=root)[0], machine_dir=root
            )
            source = make_3mf(root / "source.3mf", {})
            for plate in ("Textured PEI Plate", "Cool Plate"):
                plan = build_conversion_plan(source, machine, bed_type=plate)
                warnings = [w for w in plan.warnings if w.startswith("Check Plate Type")]
                self.assertEqual(len(warnings), 1)
                self.assertIn(f"requests {plate}", warnings[0])
                self.assertIn("remembered plate preference", warnings[0])
                self.assertIn("editable Plate Type", warnings[0])

    def test_foreign_printer_clearance_uses_selected_s1_machine(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            name = "Anycubic Kobra S1 0.4 nozzle"
            (root / f"{name}.json").write_text(json.dumps({
                "name": name,
                "printer_settings_id": name,
                "printer_model": "Anycubic Kobra S1",
                "nozzle_diameter": ["0.4"],
                "extruder_clearance_height_to_lid": "240",
                "extruder_clearance_height_to_rod": "40",
                "extruder_clearance_radius": "60",
            }), encoding="utf-8")
            machine = resolve_machine_target(
                discover_targets(machine_dir=root)[0], machine_dir=root
            )
            source = make_3mf(root / "foreign.3mf", {
                "printer_model": "Bambu Lab P1S",
                "extruder_clearance_height_to_lid": "90",
                "extruder_clearance_height_to_rod": "36",
                "extruder_clearance_radius": "57",
            })
            plan = build_conversion_plan(source, machine)
            changes = {item.setting_name: item.new_value for item in plan.actions}
            self.assertEqual(changes["extruder_clearance_height_to_lid"], "240")
            self.assertEqual(changes["extruder_clearance_height_to_rod"], "40")
            self.assertEqual(changes["extruder_clearance_radius"], "60")

    def test_foreign_filename_template_uses_selected_process(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            name = "Anycubic Kobra S1 0.4 nozzle"
            (root / f"{name}.json").write_text(json.dumps({
                "name": name, "printer_settings_id": name,
                "printer_model": "Anycubic Kobra S1",
                "nozzle_diameter": ["0.4"],
            }), encoding="utf-8")
            machine = resolve_machine_target(
                discover_targets(machine_dir=root)[0], machine_dir=root
            )
            process = ResolvedProcessTarget(
                ProcessOption("official:test", "0.20mm Standard @S1", "0.4", "0.2",
                              "official", str(root / "process.json"), None, None,
                              "test", "A" * 64),
                (), {"layer_height": "0.2", "filename_format": "s1_{print_time}.gcode"},
            )
            settings = {"printer_model": "Bambu Lab P1S",
                        "filename_format": "bambu_{print_time}.gcode"}
            foreign = build_conversion_plan(
                make_3mf(root / "foreign.3mf", settings), machine, process=process
            )
            changes = {item.setting_name: item.new_value for item in foreign.actions}
            self.assertEqual(changes["filename_format"], "s1_{print_time}.gcode")
            # The projected format equals the resolved parent, but still must
            # be protected from native schema/default parent refresh.
            self.assertIn("filename_format", changes["different_settings_to_system"][0].split(";"))
            settings.update({"printer_model": "Anycubic Kobra S1",
                             "printer_settings_id": name, "nozzle_diameter": ["0.4"]})
            same_s1 = build_conversion_plan(
                make_3mf(root / "same-s1.3mf", settings), machine, process=process
            )
            self.assertEqual(
                {item.setting_name: item.new_value for item in same_s1.actions}["filename_format"],
                "s1_{print_time}.gcode",
            )

    def test_single_plate_skips_large_model_relocation_load(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            machine_name = "Anycubic Kobra S1 0.4 nozzle"
            (root / f"{machine_name}.json").write_text(json.dumps({
                "name": machine_name,
                "printer_settings_id": machine_name,
                "printer_model": "Anycubic Kobra S1",
                "nozzle_diameter": ["0.4"],
            }), encoding="utf-8")
            machine = resolve_machine_target(
                discover_targets(machine_dir=root)[0], machine_dir=root
            )
            large_model = MODEL_XML.replace(
                b"</model>", b" " * (MAX_STRUCTURED_MEMBER_BYTES + 1) + b"</model>"
            )
            source = make_3mf(root / "large-single-plate.3mf", {
                "printer_model": "Bambu Lab A1 mini",
                "printer_settings_id": "Bambu Lab A1 mini 0.4 nozzle",
                "nozzle_diameter": ["0.4"],
            }, {
                "3D/3dmodel.model": large_model,
                "Metadata/model_settings.config": b"<config><plate/></config>",
            })
            plan = build_conversion_plan(source, machine)
            self.assertFalse(plan.write_blockers)
            self.assertFalse(any(
                item.action == "RELOCATE_PLATES" for item in plan.archive_actions
            ))

    def test_same_s1_reoptimization_keeps_unselected_filament_masks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            machine_name = "Anycubic Kobra S1 0.4 nozzle"
            (root / f"{machine_name}.json").write_text(json.dumps({
                "name": machine_name,
                "printer_settings_id": machine_name,
                "printer_model": "Anycubic Kobra S1",
                "nozzle_diameter": ["0.4"],
                "default_filament_profile": ["Anycubic PLA"],
            }), encoding="utf-8")
            machine = resolve_machine_target(
                discover_targets(machine_dir=root)[0], machine_dir=root
            )
            process = ResolvedProcessTarget(
                ProcessOption(
                    "official:test", "0.20mm Standard @S1", "0.4", "0.2",
                    "official", str(root / "process.json"), None, None,
                    "test", "A" * 64,
                ), (), {"layer_height": "0.2"},
            )
            base = {
                "printer_model": "Anycubic Kobra S1",
                "printer_settings_id": machine_name,
                "nozzle_diameter": ["0.4"],
                "print_settings_id": "0.16mm source height",
                "layer_height": "0.16",
                "filament_colour": ["000000", "FFFFFF"],
                "filament_settings_id": ["Anycubic PLA", "Anycubic PETG"],
                "default_filament_profile": ["Anycubic PETG"],
                "filament_start_gcode": ["; start", "; start\n"],
                "filament_end_gcode": ["; end\n", "; end "],
                "filament_flow_ratio": ["0.98", "1"],
                "different_settings_to_system": ["", "filament_flow_ratio", "", ""],
            }
            source = make_3mf(root / "s1.3mf", base)
            plan = build_conversion_plan(source, machine, process=process)
            changes = {item.setting_name: item.new_value for item in plan.actions}
            masks = changes["different_settings_to_system"]
            self.assertEqual(masks[1], "filament_flow_ratio")
            self.assertEqual(masks[2], "")
            self.assertFalse(any("filament_start_gcode" in m for m in masks))
            self.assertFalse(any("filament_end_gcode" in m for m in masks))
            self.assertNotIn("default_filament_profile", changes)

            base["printer_model"] = "Bambu Lab X1"
            foreign = make_3mf(root / "foreign.3mf", base)
            foreign_plan = build_conversion_plan(foreign, machine, process=process)
            foreign_masks = {
                item.setting_name: item.new_value for item in foreign_plan.actions
            }["different_settings_to_system"]
            self.assertIn("filament_start_gcode", foreign_masks[1].split(";"))
            foreign_changes = {
                item.setting_name: item.new_value for item in foreign_plan.actions
            }
            self.assertEqual(foreign_changes["default_filament_profile"], ["Anycubic PLA"])

    def test_machine_change_time_estimates_use_target_even_if_source_omits_them(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            name = "Anycubic Kobra S1 0.6 nozzle"
            (root / f"{name}.json").write_text(json.dumps({
                "name": name, "printer_settings_id": name,
                "printer_model": "Anycubic Kobra S1", "nozzle_diameter": ["0.6"],
                "machine_load_filament_time": "126.423",
                "machine_unload_filament_time": "30", "machine_tool_change_time": "0",
            }))
            target = resolve_machine_target(discover_targets(machine_dir=root)[0], machine_dir=root)
            for values in ({}, {"machine_load_filament_time": "0", "machine_tool_change_time": "99"}):
                source = make_3mf(root / ("empty.3mf" if not values else "source.3mf"), values)
                plan = build_conversion_plan(source, target)
                actions = {a.setting_name: a for a in plan.actions}
                self.assertEqual(actions["machine_load_filament_time"].new_value, "126.423")
                self.assertEqual(actions["machine_load_filament_time"].action, "REPLACE")
                self.assertEqual(actions["machine_unload_filament_time"].new_value, "30")
                self.assertEqual(actions["machine_tool_change_time"].new_value, "0")

    def test_nice_supports_beta_is_opt_in_traceable_and_downward_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            machine_dir = root / "machine"
            machine_dir.mkdir()
            name = "Anycubic Kobra S1 0.6 nozzle"
            (machine_dir / f"{name}.json").write_text(json.dumps({
                "name": name,
                "printer_settings_id": name,
                "printer_model": "Anycubic Kobra S1",
                "nozzle_diameter": ["0.6"],
            }), encoding="utf-8")
            source = make_3mf(root / "source.3mf", {
                "enable_support": "0",
                "support_type": "normal(auto)",
                "support_speed": ["200", "200"],
                "support_interface_speed": ["30", "30"],
                "support_line_width": "0.42",
                "tree_support_wall_count": "-1",
            })
            machine = resolve_machine_target(
                discover_targets(machine_dir=machine_dir)[0], machine_dir=machine_dir
            )
            option = ProcessOption(
                process_id="community:nice:0.6:test",
                label="0.20mm test @ Kobra S1 0.6 nozzle",
                nozzle_diameter="0.6",
                layer_height="0.2",
                source_kind="community",
                source_path=str(root / "bundle.3mf"),
                source_member="Metadata/process_settings_1.config",
                inherits=None,
                association_basis="test",
                sha256="A" * 64,
            )
            process = ResolvedProcessTarget(option, (), {
                "support_speed": "120",
                "support_interface_speed": "60",
                "support_line_width": "0.62",
            })

            plain = build_conversion_plan(source, machine, process=process)
            self.assertFalse(plain.nice_supports_beta)
            self.assertNotIn("support_type", {a.setting_name for a in plain.actions})

            plan = build_conversion_plan(
                source, machine, process=process, nice_supports_beta=True
            )
            actions = {action.setting_name: action for action in plan.actions}
            self.assertTrue(plan.nice_supports_beta)
            self.assertEqual(
                plan.to_dict()["nice_supports_beta_profile"]["reference_file"],
                "Amazing_Support_Settings.3mf",
            )
            self.assertEqual(actions["enable_support"].new_value, "1")
            self.assertEqual(actions["support_type"].new_value, "tree(auto)")
            self.assertEqual(actions["support_speed"].new_value, "120")
            # The beta ceiling never raises the slower source value.
            self.assertEqual(actions["support_interface_speed"].new_value, "30")
            self.assertEqual(actions["support_line_width"].new_value, "0.62")
            self.assertEqual(actions["tree_support_wall_count"].new_value, "0")
            self.assertFalse(actions["support_interface_spacing"].setting_was_present)
            self.assertNotIn(
                "raft_first_layer_expansion",
                actions,
            )
            self.assertTrue(any("Preview" in item for item in plan.warnings))

            from s1_optimizer.writer import write_optimized_archive
            output = root / "output.3mf"
            result = write_optimized_archive(plan, output)
            self.assertEqual(result.output_path, str(output.resolve()))
            _, written = read_project_settings(output)
            self.assertEqual(written["support_interface_spacing"], "0")
            self.assertEqual(written["support_line_width"], "0.62")

            with self.assertRaisesRegex(PlanError, "requires an exact process"):
                build_conversion_plan(source, machine, nice_supports_beta=True)

    def test_process_keeps_layer_height_but_translates_nozzle_widths_and_legacy_enum(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            machine_dir = root / "machine"
            machine_dir.mkdir()
            name = "Anycubic Kobra S1 0.6 nozzle"
            (machine_dir / f"{name}.json").write_text(json.dumps({
                "name": name,
                "printer_settings_id": name,
                "printer_model": "Anycubic Kobra S1",
                "nozzle_diameter": ["0.6"],
            }), encoding="utf-8")
            source = make_3mf(root / "source.3mf", {
                "print_settings_id": "0.20mm source profile",
                "layer_height": "0.2",
                "initial_layer_print_height": "0.2",
                "line_width": "0.42",
                "outer_wall_line_width": "0.42",
                "ensure_vertical_shell_thickness": "enabled",
                "enable_overhang_speed": ["1", "1"],
                "outer_wall_speed": ["200", "500"],
                "top_solid_infill_flow_ratio": ["1", "1"],
                "filament_flow_ratio": ["0.98", "0.98"],
            })
            machine = resolve_machine_target(
                discover_targets(machine_dir=machine_dir)[0], machine_dir=machine_dir
            )
            option = ProcessOption(
                process_id="community:test:0.6:test:030",
                label="0.30mm @AC KS1 0.6 mm Nozzle",
                nozzle_diameter="0.6",
                layer_height="0.3",
                source_kind="community",
                source_path=str(root / "bundle.3mf"),
                source_member="Metadata/process_settings_1.config",
                inherits=None,
                association_basis="single_machine_bundle",
                sha256="A" * 64,
            )
            process = ResolvedProcessTarget(option, (), {
                "layer_height": "0.3",
                "initial_layer_print_height": "0.3",
                "line_width": "0.62",
                "outer_wall_line_width": "0.62",
                "ensure_vertical_shell_thickness": "ensure_all",
                "outer_wall_speed": "60",
            })

            plan = build_conversion_plan(source, machine, process=process)
            actions = {item.setting_name: item for item in plan.actions}

            self.assertIn(
                "[Optimized] 0.2mm source height "
                "(0.30mm @AC KS1 0.6 mm Nozzle settings)",
                actions["print_settings_id"].new_value,
            )
            self.assertEqual(plan.effective_process_label, actions["print_settings_id"].new_value)
            self.assertEqual(actions["line_width"].action, "TRANSLATE")
            self.assertEqual(actions["line_width"].new_value, "0.62")
            self.assertEqual(actions["outer_wall_line_width"].new_value, "0.62")
            self.assertEqual(
                actions["ensure_vertical_shell_thickness"].new_value, "ensure_all"
            )
            self.assertNotIn("layer_height", actions)
            self.assertNotIn("initial_layer_print_height", actions)
            self.assertEqual(actions["enable_overhang_speed"].new_value, "1")
            self.assertEqual(actions["outer_wall_speed"].old_value, ["200", "500"])
            self.assertEqual(actions["outer_wall_speed"].new_value, "60")
            self.assertEqual(actions["outer_wall_speed"].action, "CLAMP")
            self.assertEqual(actions["top_solid_infill_flow_ratio"].new_value, "1")
            self.assertNotIn("filament_flow_ratio", actions)
            self.assertEqual(len(actions), len(plan.actions))

            process_height_plan = build_conversion_plan(
                source, machine, process=process, use_process_layer_height=True
            )
            process_height_actions = {
                item.setting_name: item for item in process_height_plan.actions
            }
            self.assertIn(
                f"[Optimized] {option.label}",
                process_height_actions["print_settings_id"].new_value,
            )
            self.assertEqual(process_height_actions["layer_height"].new_value, "0.3")
            self.assertEqual(
                process_height_actions["initial_layer_print_height"].new_value, "0.3"
            )
            self.assertEqual(
                process_height_actions["layer_height"].confidence, "REVIEW"
            )

            custom = build_conversion_plan(source, machine, process=process, layer_height_override="0.18")
            custom_actions = {item.setting_name: item for item in custom.actions}
            self.assertEqual(custom_actions["layer_height"].new_value, "0.18")
            self.assertEqual(custom_actions["line_width"].new_value, "0.62")
            self.assertNotIn("initial_layer_print_height", custom_actions)
            self.assertIn("0.18mm custom height", custom.effective_process_label)
            self.assertEqual(custom.to_dict()["layer_height_override"], "0.18")
            for invalid in ("nan", "inf", "0", "-0.2", "20%"):
                with self.assertRaises(PlanError):
                    build_conversion_plan(source, machine, process=process, layer_height_override=invalid)
            with self.assertRaises(PlanError):
                build_conversion_plan(source, machine, process=process,
                                      layer_height_override="0.18", use_process_layer_height=True)
            from dataclasses import replace
            bounded = replace(machine, effective_values={**machine.effective_values,
                              "min_layer_height": ["0.12"], "max_layer_height": ["0.42"]})
            blocked = build_conversion_plan(source, bounded, process=process, layer_height_override="0.5")
            self.assertTrue(any("above the selected machine maximum" in value for value in blocked.write_blockers))
            from s1_optimizer.writer import write_optimized_archive
            write_optimized_archive(custom, root / "custom-height.3mf")
            from s1_optimizer.plan import read_project_settings
            _, written = read_project_settings(root / "custom-height.3mf")
            self.assertEqual(written["layer_height"], "0.18")
            self.assertEqual(written["initial_layer_print_height"], "0.2")
            self.assertEqual(written["line_width"], "0.62")

            narrow_process = ResolvedProcessTarget(
                option,
                (),
                {**process.effective_values, "line_width": "0.42"},
            )
            narrow_plan = build_conversion_plan(source, machine, process=narrow_process)
            self.assertTrue(any(
                "0.42 mm is narrower than the 0.6 mm nozzle" in warning
                for warning in narrow_plan.warnings
            ))
            # The writer must still see the original array as its old-value
            # precondition; scalarization and clamping cannot be two actions.
            from s1_optimizer.writer import _apply_plan
            from s1_optimizer.plan import read_project_settings
            written = json.loads(_apply_plan(json.dumps(read_project_settings(source)[1]).encode(), plan))
            self.assertEqual(written["outer_wall_speed"], "60")
            unresolved = make_3mf(root / "unresolved.3mf", {
                "outer_wall_speed": ["20", "40"],
            })
            blocked_speed = build_conversion_plan(unresolved, machine, process=process)
            self.assertTrue(any("outer_wall_speed" in item for item in blocked_speed.write_blockers))
            machine_only = build_machine_plan(source, machine)
            self.assertTrue(any("outer_wall_speed" in item for item in machine_only.write_blockers))
            mixed = make_3mf(root / "mixed.3mf", {
                "enable_overhang_speed": ["1", "0"],
            })
            blocked = build_conversion_plan(mixed, machine, process=process)
            self.assertTrue(any("single overhang-slowdown" in item
                                for item in blocked.write_blockers))

    def test_preserved_layer_height_must_fit_target_machine_limits(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            machine_dir = root / "machine"
            machine_dir.mkdir()
            name = "Anycubic Kobra S1 0.8 nozzle"
            (machine_dir / f"{name}.json").write_text(json.dumps({
                "name": name,
                "printer_settings_id": name,
                "printer_model": "Anycubic Kobra S1",
                "nozzle_diameter": ["0.8"],
                "min_layer_height": ["0.16"],
                "max_layer_height": ["0.56"],
            }), encoding="utf-8")
            source = make_3mf(root / "source.3mf", {
                "layer_height": "0.08",
                "initial_layer_print_height": "0.2",
            })
            machine = resolve_machine_target(
                discover_targets(machine_dir=machine_dir)[0], machine_dir=machine_dir
            )

            plan = build_conversion_plan(source, machine)

            self.assertTrue(any(
                "layer_height 0.08 mm is below" in blocker
                for blocker in plan.write_blockers
            ))

    def test_only_enabled_unconfirmed_vendor_features_warn(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            machine_dir = root / "machine"
            machine_dir.mkdir()
            name = "Anycubic Kobra S1 0.4 nozzle"
            (machine_dir / f"{name}.json").write_text(json.dumps({
                "name": name,
                "printer_settings_id": name,
                "printer_model": "Anycubic Kobra S1",
                "nozzle_diameter": ["0.4"],
            }), encoding="utf-8")
            source = make_3mf(root / "source.3mf", {
                "enable_support_ironing": "1",
                "enable_wrapping_detection": ["0"],
            })
            machine = resolve_machine_target(
                discover_targets(machine_dir=machine_dir)[0], machine_dir=machine_dir
            )

            plan = build_conversion_plan(source, machine)

            warnings = "\n".join(plan.warnings)
            self.assertIn("Bambu support ironing is enabled", warnings)
            self.assertNotIn("Bambu warping detection is enabled", warnings)

    def test_legacy_negative_support_values_are_constrained(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            machine_dir = root / "machine"
            machine_dir.mkdir()
            name = "Anycubic Kobra S1 0.4 nozzle"
            (machine_dir / f"{name}.json").write_text(json.dumps({
                "name": name,
                "printer_settings_id": name,
                "printer_model": "Anycubic Kobra S1",
                "nozzle_diameter": ["0.4"],
            }), encoding="utf-8")
            machine = resolve_machine_target(
                discover_targets(machine_dir=machine_dir)[0], machine_dir=machine_dir
            )
            disabled = make_3mf(root / "disabled.3mf", {
                "tree_support_wall_count": "-1",
                "raft_first_layer_expansion": "-1",
                "raft_layers": "0",
            })

            disabled_plan = build_conversion_plan(disabled, machine)
            disabled_actions = {
                item.setting_name: item for item in disabled_plan.actions
            }
            self.assertEqual(disabled_actions["tree_support_wall_count"].new_value, "0")
            self.assertEqual(
                disabled_actions["raft_first_layer_expansion"].new_value, "0"
            )
            self.assertFalse(disabled_plan.write_blockers)

            active = make_3mf(root / "active.3mf", {
                "raft_first_layer_expansion": "-1",
                "raft_layers": "2",
            })
            option = ProcessOption(
                "official:process", "0.20mm test", "0.4", "0.2", "official",
                str(root / "process.json"), None, None, "test", "C" * 64,
            )
            process = ResolvedProcessTarget(
                option, (), {"raft_first_layer_expansion": "2"}
            )
            active_plan = build_conversion_plan(active, machine, process=process)
            active_action = next(
                item for item in active_plan.actions
                if item.setting_name == "raft_first_layer_expansion"
            )
            self.assertEqual(active_action.new_value, "2")
            self.assertEqual(active_action.confidence, "REVIEW")

            blocked = build_conversion_plan(active, machine)
            self.assertTrue(any(
                "raft_first_layer_expansion is -1" in blocker
                for blocker in blocked.write_blockers
            ))

    def test_filament_identity_and_volumetric_flow_are_safely_adapted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            machine_dir = root / "machine"
            machine_dir.mkdir()
            name = "Anycubic Kobra S1 0.4 nozzle"
            (machine_dir / f"{name}.json").write_text(json.dumps({
                "name": name, "printer_settings_id": name,
                "printer_model": "Anycubic Kobra S1",
                "nozzle_diameter": ["0.4"], "nozzle_type": "brass",
            }), encoding="utf-8")
            source = make_3mf(root / "source.3mf", {
                "filament_settings_id": ["Bambu PETG"],
                "filament_type": ["PETG"],
                "filament_max_volumetric_speed": ["20"],
                "filament_cost": ["35"],
                "nozzle_temperature": ["280"],
                "textured_plate_temp": ["55"],
                "fan_max_speed": ["100"],
                "filament_flow_ratio": ["0.95"],
                "pressure_advance": ["0.02"],
                "filament_retraction_length": ["0.8"],
            })
            machine = resolve_machine_target(
                discover_targets(machine_dir=machine_dir)[0], machine_dir=machine_dir
            )
            option = FilamentOption(
                filament_id="official:test:0.4:petg:test:anycubic-petg",
                label="Anycubic PETG @Anycubic Kobra S1 0.4 nozzle",
                material="PETG", nozzle_diameter="0.4", source_kind="official",
                source_path=str(root / "petg.json"), source_member=None,
                inherits=None, required_nozzle_hrc="3", confidence="SAFE",
                sha256="A" * 64,
            )
            filament = ResolvedFilamentTarget(
                option,
                (),
                {
                    "filament_max_volumetric_speed": ["12"],
                    "filament_cost": ["30"],
                    "nozzle_temperature": ["275"],
                    "textured_plate_temp": ["75"],
                    "fan_max_speed": ["90"],
                    "filament_flow_ratio": ["0.94"],
                    "pressure_advance": ["0.03"],
                    "filament_retraction_length": ["nil"],
                },
            )
            plan = build_conversion_plan(source, machine, filaments=(filament,))
            actions = {item.setting_name: item for item in plan.actions}
            self.assertEqual(actions["filament_settings_id"].action, "TRANSLATE")
            self.assertEqual(actions["required_nozzle_HRC"].new_value, ["3"])
            self.assertFalse(actions["required_nozzle_HRC"].setting_was_present)
            self.assertEqual(actions["filament_max_volumetric_speed"].new_value, ["12"])
            self.assertEqual(actions["filament_cost"].new_value, ["30"])
            self.assertEqual(actions["nozzle_temperature"].new_value, ["275"])
            self.assertEqual(actions["textured_plate_temp"].new_value, ["75"])
            self.assertEqual(actions["fan_max_speed"].new_value, ["90"])
            self.assertEqual(actions["filament_flow_ratio"].new_value, ["0.94"])
            self.assertEqual(actions["pressure_advance"].new_value, ["0.03"])
            self.assertEqual(actions["filament_retraction_length"].new_value, ["nil"])
            limited = build_conversion_plan(
                source,
                machine,
                filaments=(filament,),
                hotend_type="all-metal",
                max_nozzle_temperature=270,
            )
            limited_actions = {item.setting_name: item for item in limited.actions}
            self.assertEqual(limited_actions["nozzle_temperature"].new_value, ["270"])
            self.assertEqual(limited.max_nozzle_temperature, "270")
            self.assertEqual(limited.hotend_type, "all-metal")
            self.assertEqual(limited.to_dict()["hotend_type"], "all-metal")

            with self.assertRaisesRegex(PlanError, "Hotend type must be"):
                build_conversion_plan(source, machine, hotend_type="mystery")

            incompatible = ResolvedFilamentTarget(
                option,
                (),
                {
                    "filament_max_volumetric_speed": ["12"],
                    "nozzle_temperature_range_low": ["275"],
                },
            )
            blocked = build_conversion_plan(
                source,
                machine,
                filaments=(incompatible,),
                max_nozzle_temperature=270,
            )
            self.assertTrue(
                any("below the selected filament minimum" in item for item in blocked.write_blockers)
            )

            wrong = ResolvedFilamentTarget(
                FilamentOption(
                    filament_id="wrong", label="Anycubic PLA", material="PLA",
                    nozzle_diameter="0.4", source_kind="official",
                    source_path=str(root / "pla.json"), source_member=None,
                    inherits=None, required_nozzle_hrc=None, confidence="SAFE",
                    sha256="B" * 64,
                ), (), {"filament_max_volumetric_speed": ["16"]}
            )
            with self.assertRaisesRegex(PlanError, "material mismatch"):
                build_conversion_plan(source, machine, filaments=(wrong,))

    def test_clamp_preserves_array_shape_and_never_increases(self) -> None:
        self.assertEqual(_clamped_value(["250", "40"], "180"), (["180", "40"], None))
        self.assertEqual(_clamped_value("45", "180"), ("45", None))
        self.assertIsNotNone(_clamped_value(["50%"], "100")[1])
        self.assertIsNotNone(_clamped_value(["0"], "100")[1])

    def test_plan_rejects_malformed_project_settings_as_user_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = make_3mf(
                root / "source.3mf",
                None,
                {"Metadata/project_settings.config": b'{"broken":'},
            )
            machine = root / "machine"
            machine.mkdir()
            name = "Anycubic Kobra S1 0.4 nozzle"
            profile_path = machine / f"{name}.json"
            profile_path.write_text(
                json.dumps(
                    {
                        "name": name,
                        "printer_settings_id": name,
                        "nozzle_diameter": ["0.4"],
                        "nozzle_type": "brass",
                    }
                ),
                encoding="utf-8",
            )
            target = discover_targets(machine_dir=machine)[0]
            resolved = resolve_machine_target(target, machine_dir=machine)
            with self.assertRaisesRegex(Exception, "Cannot parse"):
                build_machine_plan(source, resolved)

    def test_machine_plan_replaces_verified_keys_and_keeps_process(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
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
                        "machine_max_speed_x": ["600", "300", "780"],
                        "min_layer_height": ["0.08"],
                        "max_layer_height": ["0.28"],
                        "auxiliary_fan": "1",
                        "retraction_length": ["1"],
                    }
                ),
                encoding="utf-8",
            )
            source = make_3mf(
                root / "source.3mf",
                {
                    "printer_model": "Bambu Lab A1 mini",
                    "printer_settings_id": "Bambu Lab A1 mini 0.4 nozzle",
                    "nozzle_diameter": ["0.4"],
                    "gcode_flavor": "bambu",
                    "machine_start_gcode": "M1002",
                    "machine_max_speed_x": ["500"],
                    "min_layer_height": ["0.04"],
                    "max_layer_height": ["0.2"],
                    "auxiliary_fan": "0",
                    "retraction_length": ["0.8"],
                    "wall_loops": "5",
                },
            )
            before = hashlib.sha256(source.read_bytes()).hexdigest()
            targets = discover_targets(machine_dir=machine)
            selected = select_target(
                targets, "official:anycubic-kobra-s1:0.4:brass"
            )
            resolved = resolve_machine_target(selected, machine_dir=machine)
            plan = build_machine_plan(source, resolved)
            actions = {action.setting_name: action for action in plan.actions}
            self.assertNotIn("print_compatible_printers", actions)
            self.assertEqual(actions["printer_model"].action, "REPLACE")
            self.assertEqual(actions["machine_start_gcode"].new_value, "G9111")
            self.assertEqual(actions["min_layer_height"].new_value, ["0.08"])
            self.assertEqual(actions["max_layer_height"].new_value, ["0.28"])
            self.assertEqual(actions["auxiliary_fan"].new_value, "1")
            self.assertEqual(actions["retraction_length"].new_value, ["1"])
            self.assertNotIn("wall_loops", actions)
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before)
            self.assertEqual(plan.to_dict()["summary"]["writes_performed"], 0)

    def test_community_target_resolves_official_base_then_overlay(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            machine = root / "machine"
            machine.mkdir()
            base_name = "Anycubic Kobra S1 0.4 nozzle"
            (machine / f"{base_name}.json").write_text(
                json.dumps(
                    {
                        "name": base_name,
                        "printer_settings_id": base_name,
                        "nozzle_diameter": ["0.4"],
                        "nozzle_type": "brass",
                        "machine_start_gcode": "G9111",
                    }
                ),
                encoding="utf-8",
            )
            bundle = make_3mf(
                root / "bundle.3mf",
                {"printer_settings_id": "Community Hardened"},
                {
                    "Metadata/machine_settings_1.config": json.dumps(
                        {
                            "inherits": base_name,
                            "name": "Community Hardened",
                            "printer_settings_id": "Community Hardened",
                            "nozzle_type": "hardened_steel",
                        }
                    ).encode("utf-8")
                },
            )
            targets = discover_targets(machine_dir=machine, bundles=(bundle,))
            community = next(item for item in targets if item.source_kind == "community")
            resolved = resolve_machine_target(community, machine_dir=machine)
            self.assertEqual(len(resolved.layers), 2)
            self.assertEqual(resolved.effective_values["machine_start_gcode"], "G9111")
            self.assertEqual(resolved.effective_values["nozzle_type"], "hardened_steel")

    def test_custom_nozzle_rebases_to_matching_official_parent_and_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            machine = root / "machine"
            machine.mkdir()
            for diameter in ("0.4", "0.6"):
                name = f"Anycubic Kobra S1 {diameter} nozzle"
                (machine / f"{name}.json").write_text(json.dumps({
                    "name": name,
                    "printer_settings_id": name,
                    "printer_model": "Anycubic Kobra S1",
                    "nozzle_diameter": [diameter],
                    "nozzle_type": "hardened_steel",
                    "default_filament_profile": [f"Anycubic PLA @{name}"],
                    "default_print_profile": f"0.30mm Standard @{name}",
                    "machine_start_gcode": f"START-{diameter}",
                }), encoding="utf-8")
            bundle = make_3mf(root / "profiles.3mf", {
                "printer_settings_id": "Community 0.6 HS",
            }, {
                "Metadata/machine_settings_1.config": json.dumps({
                    "inherits": "Anycubic Kobra S1 0.4 nozzle",
                    "name": "Community 0.6 HS",
                    "printer_settings_id": "Community 0.6 HS",
                    "nozzle_diameter": ["0.6"],
                    "nozzle_type": "hardened_steel",
                }).encode(),
            })
            selected = next(
                item for item in discover_targets(machine_dir=machine, bundles=(bundle,))
                if item.source_kind == "community"
            )
            resolved = resolve_machine_target(selected, machine_dir=machine)
            self.assertEqual(resolved.declared_parent, "Anycubic Kobra S1 0.4 nozzle")
            self.assertEqual(resolved.compatibility_parent, "Anycubic Kobra S1 0.6 nozzle")
            self.assertEqual(resolved.layers[0].label, "Anycubic Kobra S1 0.6 nozzle")
            self.assertEqual(resolved.effective_values["machine_start_gcode"], "START-0.6")
            self.assertEqual(
                resolved.effective_values["default_filament_profile"],
                ["Anycubic PLA @Anycubic Kobra S1 0.6 nozzle"],
            )
            source = make_3mf(root / "source.3mf", {
                "printer_settings_id": "Bambu A1",
                "default_filament_profile": ["Bambu PLA"],
                "default_print_profile": "Bambu 0.20",
                "nozzle_diameter": ["0.4"],
                "print_settings_id": "0.20mm Standard @BBL A1M",
                "layer_height": "0.2",
                "initial_layer_print_height": "0.2",
                "line_width": "0.42",
                "outer_wall_line_width": "0.42",
            })
            process_option = ProcessOption(
                "official:process", "0.24mm Standard @Anycubic Kobra S1 0.6 nozzle",
                "0.6", "0.24", "official", str(root / "process.json"), None,
                None, "test", "B" * 64,
            )
            process = ResolvedProcessTarget(process_option, (), {
                "layer_height": "0.24",
                "initial_layer_print_height": "0.24",
                "line_width": "0.62",
                "outer_wall_line_width": "0.62",
            })
            plan = build_conversion_plan(source, resolved, process=process)
            actions = {item.setting_name: item for item in plan.actions}
            self.assertEqual(actions["inherits"].new_value, "Anycubic Kobra S1 0.6 nozzle")
            self.assertFalse(actions["inherits"].setting_was_present)
            self.assertEqual(
                actions["default_filament_profile"].new_value,
                ["Anycubic PLA @Anycubic Kobra S1 0.6 nozzle"],
            )
            self.assertIn(
                "[Optimized] 0.2mm source height "
                "(0.24mm Standard @Anycubic Kobra S1 0.6 nozzle settings)",
                actions["default_print_profile"].new_value,
            )
            self.assertEqual(actions["line_width"].new_value, "0.62")
            self.assertEqual(actions["outer_wall_line_width"].new_value, "0.62")
            self.assertNotIn("layer_height", actions)
            self.assertNotIn("initial_layer_print_height", actions)
            self.assertFalse(plan.write_blockers)

            from s1_optimizer.writer import write_optimized_archive
            output = root / "cupholder-regression-output.3mf"
            write_optimized_archive(plan, output)
            _, written = read_project_settings(output)
            self.assertEqual(written["inherits"], "Anycubic Kobra S1 0.6 nozzle")
            self.assertEqual(written["inherits_group"][-1], "Anycubic Kobra S1 0.6 nozzle")
            self.assertEqual(written["print_compatible_printers"], [
                "Community 0.6 HS", "Anycubic Kobra S1 0.6 nozzle",
            ])
            masks = [set(mask.split(";")) if mask else set()
                     for mask in written["different_settings_to_system"]]
            self.assertEqual(len(masks), 2)
            self.assertIn("layer_height", masks[0])
            self.assertNotIn("machine_start_gcode", masks[0])
            self.assertNotIn("machine_start_gcode", masks[1])
            self.assertNotIn("line_width", masks[0])
            self.assertEqual(written["layer_height"], "0.2")
            self.assertEqual(written["line_width"], "0.62")
            self.assertIn(
                "[Optimized] 0.2mm source height "
                "(0.24mm Standard @Anycubic Kobra S1 0.6 nozzle settings)",
                written["print_settings_id"],
            )


if __name__ == "__main__":
    unittest.main()
