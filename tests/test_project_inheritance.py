import unittest
from types import SimpleNamespace

from s1_optimizer.errors import PlanError
from s1_optimizer.plan import _machine_inherits_group, _explicit_settings_masks, _retarget_scope_vectors


class ProjectInheritanceTests(unittest.TestCase):
    def test_selected_scopes_replace_stale_metadata_and_preserve_unselected(self):
        source = {
            "compatible_machine_expression_group": ["old process", "old A", "old B", "machine"],
            "compatible_process_expression_group": ["print A", "print B"],
        }
        group = ["source process", "source A", "source B", "S1"]
        option = SimpleNamespace(source_kind="official", label="Stock PETG", inherits="internal")
        filament = SimpleNamespace(filament=option, effective_values={
            "compatible_printers_condition": "target machine", "compatible_prints_condition": "target process",
        })
        result = _retarget_scope_vectors(source, group, None, (filament,))
        self.assertEqual(result["inherits_group"], ["source process", "Stock PETG", "Stock PETG", "S1"])
        self.assertEqual(result["compatible_machine_expression_group"], ["old process", "target machine", "target machine", "machine"])
        self.assertEqual(result["compatible_process_expression_group"], ["target process"] * 2)
        self.assertEqual(source["compatible_process_expression_group"], ["print A", "print B"])
        self.assertEqual(group[1], "source A")

    def test_reference_process_uses_scope_zero_not_machine_inherits(self):
        process = SimpleNamespace(process=SimpleNamespace(source_kind="reference"),
                                  effective_values={"inherits": "WRONG MACHINE", "inherits_group": ["saved process", "filament", "saved machine"]})
        result = _retarget_scope_vectors({}, ["old", "unchanged filament", "S1"], process, ())
        self.assertEqual(result["inherits_group"], ["saved process", "unchanged filament", "S1"])
        self.assertNotIn("compatible_process_expression_group", result)

    def test_scope_vectors_reject_malformed_or_misaligned_values(self):
        for source in ({"compatible_process_expression_group": ["a", "b"]},
                       {"compatible_machine_expression_group": "bad"}):
            with self.subTest(source=source), self.assertRaises(PlanError):
                _retarget_scope_vectors(source, ["", "", "S1"], None, ())

    def test_difference_masks_protect_keep_and_changed_values_from_refresh(self):
        project = {
            "filament_colour": ["red", "blue"],
            "wall_loops": "5",
            "nozzle_type": "hardened_steel",
            "outer_wall_speed": "30",
        }
        names = set(project) | {"nozzle_type", "outer_wall_speed", "different_settings_to_system"}
        process = SimpleNamespace(effective_values={"wall_loops": "2", "outer_wall_speed": "200"})
        masks = _explicit_settings_masks(
            project, names, {"nozzle_type": "brass"}, {"nozzle_type": "brass"}, process, ()
        )
        self.assertEqual(len(masks), 4)
        self.assertTrue({"wall_loops", "outer_wall_speed"} <= set(masks[0].split(";")))
        self.assertEqual(masks[1], "")
        self.assertEqual(masks[2], "")
        self.assertIn("nozzle_type", set(masks[3].split(";")))
        for mask in masks:
            protected = set(mask.split(";")) if mask else set()
            self.assertNotIn("different_settings_to_system", protected)
            self.assertNotIn("unwritten_default", protected)

    def test_mask_rejects_delimiter_injection(self):
        with self.assertRaises(PlanError):
            _explicit_settings_masks({}, {"bad;name"}, {}, {}, None, ())

    def test_gcode_masks_are_scoped_and_equal_parent_values_are_not_modified(self):
        project = {
            "filament_colour": ["red", "blue"],
            "machine_start_gcode": "START",
            "filament_start_gcode": ["LOAD", "CUSTOM"],
        }
        filament = lambda start: SimpleNamespace(
            effective_values={"filament_start_gcode": [start]}
        )
        masks = _explicit_settings_masks(
            project,
            set(project),
            {"machine_start_gcode": "START"},
            {"machine_start_gcode": "START"},
            SimpleNamespace(effective_values={}),
            (filament("LOAD"), filament("LOAD")),
        )
        parsed = [set(mask.split(";")) if mask else set() for mask in masks]
        self.assertNotIn("machine_start_gcode", set().union(*parsed))
        self.assertNotIn("filament_start_gcode", parsed[1])
        self.assertIn("filament_start_gcode", parsed[2])
        self.assertNotIn("filament_start_gcode", parsed[0] | parsed[3])

    def test_masks_include_project_fields_renamed_by_loader(self):
        project = {
            "filament_colour": ["red"],
            "print_compatible_printers": ["S1"],
            "compatible_machine_expression_group": ["process", "machine", "printer"],
            "compatible_process_expression_group": ["print"],
        }
        masks = _explicit_settings_masks(project, set(project), {}, {}, None, ())
        self.assertTrue({"compatible_printers", "compatible_printers_condition"}
                        <= set(masks[0].split(";")))
        self.assertTrue({"compatible_printers_condition", "compatible_prints_condition"}
                        <= set(masks[1].split(";")))
        self.assertIn("compatible_printers_condition", set(masks[2].split(";")))

    def test_machine_override_added_to_target_is_masked_against_real_parent(self):
        project = {"filament_colour": ["#FFFFFF"], "default_bed_type": "4"}
        masks = _explicit_settings_masks(
            project, set(project), {"default_bed_type": "4"},
            {}, None, (),
        )
        self.assertIn("default_bed_type", set(masks[-1].split(";")))

    def test_missing_group_places_parent_after_all_five_slots(self):
        parent = "Anycubic Kobra S1 0.6 nozzle"
        values = {"filament_colour": ["#FFFFFF"] * 5}
        group = _machine_inherits_group(values, parent)
        self.assertEqual(group, [""] * 6 + [parent])
        # PresetBundle indexes the printer at num_filaments + 1, not `inherits`.
        self.assertEqual(group[len(values["filament_colour"]) + 1], parent)
        self.assertNotIn("inherits_group", values)

    def test_preserves_other_scope_parents_without_mutating_source(self):
        old = ["source process", "filament A", "filament B", "Bambu machine"]
        values = {"filament_colour": ["red", "blue"], "inherits_group": old}
        self.assertEqual(_machine_inherits_group(values, "S1"), old[:-1] + ["S1"])
        self.assertEqual(old[-1], "Bambu machine")

    def test_short_group_is_padded_like_loader(self):
        self.assertEqual(_machine_inherits_group({
            "filament_colour": ["red"], "inherits_group": ["process"]
        }, "S1"), ["process", "", "S1"])

    def test_ambiguous_group_is_rejected(self):
        for old in ("not an array", [3], [""] * 4):
            with self.subTest(old=old), self.assertRaises(PlanError):
                _machine_inherits_group({"filament_colour": ["red"], "inherits_group": old}, "S1")
