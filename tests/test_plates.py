import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest
import zipfile

from s1_optimizer.errors import PlanError
from s1_optimizer.plates import BED_TYPE_ENUM_VALUES, clear_plate_bed_types, patch_plate_bed_types
from s1_optimizer.plate_layout import S1_NATIVE_GRID_PITCH, plan_plate_relocation, relocate_build_items
from s1_optimizer.plan import build_conversion_plan
from s1_optimizer.resolution import resolve_machine_target
from s1_optimizer.targets import discover_targets
from s1_optimizer.writer import write_optimized_archive
from tests.helpers import make_3mf
from tests import test_writer


class PlateTests(unittest.TestCase):
    def test_clear_per_plate_overrides_preserves_object_metadata(self):
        raw = b'''<config><object><metadata key="bed_type" value="untouched"/></object><plate><metadata key="bed_type" value="Cool Plate"/><metadata key="name" value="a &amp; b"/></plate><plate><metadata key="bed_type" value="Textured PEI Plate"/></plate></config>'''
        expected = b'''<config><object><metadata key="bed_type" value="untouched"/></object><plate><metadata key="name" value="a &amp; b"/></plate><plate></plate></config>'''
        self.assertEqual(clear_plate_bed_types(raw), expected)
        self.assertEqual(clear_plate_bed_types(expected), expected)

    def test_multiple_plates_only_change_bed_values(self):
        raw = b'''<config><!-- <plate>fake</plate> --><object id="1"><metadata key="bed_type" value="untouched"/></object><plate><metadata value = 'Cool Plate' key='bed_type'/><metadata key="name" value="a &amp; b"/></plate><plate></plate><plate/></config>'''
        expected = raw.replace(b"value = 'Cool Plate'", b"value = 'Textured PEI Plate'")
        new = b'<metadata key="bed_type" value="Textured PEI Plate"/>'
        expected = expected.replace(b"<plate></plate>", b"<plate>" + new + b"</plate>")
        expected = expected.replace(b"<plate/>", b"<plate>" + new + b"</plate>")
        actual = patch_plate_bed_types(raw, "Textured PEI Plate")
        self.assertEqual(actual, expected)
        self.assertEqual(patch_plate_bed_types(actual, "Textured PEI Plate"), actual)

    def test_no_plates_and_legacy_text_are_preserved(self):
        raw = b'<config><object><slic3rpe:text text="hello"/></object></config>'
        self.assertEqual(patch_plate_bed_types(raw, "Cool Plate"), raw)

    def test_ambiguous_or_malformed_metadata_blocks(self):
        for raw in (
            b'<config><plate><metadata key="bed_type"/></plate></config>',
            b'<config><plate><metadata key="bed_type" value="Cool Plate"/><metadata key="bed_type" value="Cool Plate"/></plate></config>',
            b'<config><plate></config>',
            b'<!DOCTYPE config [<!ENTITY a "x">]><config/>',
        ):
            with self.subTest(raw=raw), self.assertRaises(PlanError):
                patch_plate_bed_types(raw, "Textured PEI Plate")

    def test_default_insertion_override_and_invalid_choice_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, base = test_writer.WriterTests()._plan(root)
            raw = b'<config><plate><metadata key="plater_id" value="1"/></plate></config>'
            source = make_3mf(root / "plate-source.3mf", {"filament_settings_id": ["A"]}, {"Metadata/model_settings.config": raw})
            for index, kwargs in enumerate(({}, {"bed_type": "Cool Plate"}, {"bed_type": "Textured Cool Plate"})):
                bed = kwargs.get("bed_type", "Textured PEI Plate")
                plan = build_conversion_plan(source, base.target, **kwargs)
                self.assertFalse(plan.write_blockers)
                output = root / f"bed-{index}.3mf"
                write_optimized_archive(plan, output)
                with zipfile.ZipFile(output) as archive:
                    project = json.loads(archive.read("Metadata/project_settings.config"))
                    self.assertEqual(project["curr_bed_type"], bed)
                    self.assertEqual(project["default_bed_type"], BED_TYPE_ENUM_VALUES[bed])
                    self.assertIn("default_bed_type", project["different_settings_to_system"][-1].split(";"))
                    self.assertEqual(archive.read("Metadata/model_settings.config"), raw)
            with self.assertRaises(PlanError):
                build_conversion_plan(source, base.target, bed_type="unknown")

    def test_s1_multi_bed_selector_survives_external_project_load(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, base = test_writer.WriterTests()._plan(root)
            target = replace(base.target, effective_values={
                **base.target.effective_values, "support_multi_bed_types": "1",
            })
            plan = build_conversion_plan(source, target)
            output = root / "selectable-plate.3mf"
            write_optimized_archive(plan, output)
            with zipfile.ZipFile(output) as archive:
                settings = json.loads(archive.read("Metadata/project_settings.config"))
            self.assertEqual(settings["curr_bed_type"], "Textured PEI Plate")
            self.assertEqual(settings["default_bed_type"], "4")
            self.assertEqual(settings["support_multi_bed_types"], "1")
            self.assertIn("default_bed_type", settings["different_settings_to_system"][-1].split(";"))

    def test_multi_plate_grid_relocation_preserves_local_positions(self):
        settings = b'''<config><plate><model_instance><metadata key="object_id" value="1"/><metadata key="instance_id" value="0"/></model_instance></plate><plate><model_instance><metadata key="object_id" value="2"/><metadata key="instance_id" value="0"/></model_instance></plate><plate><model_instance><metadata key="object_id" value="3"/><metadata key="instance_id" value="0"/></model_instance></plate><plate><model_instance><metadata key="object_id" value="4"/><metadata key="instance_id" value="0"/></model_instance></plate></config>'''
        model = b'''<model xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><resources/><build><item objectid="1" transform="1 0 0 0 1 0 0 0 1 90 90 0"/><item objectid="2" transform="1 0 0 0 1 0 0 0 1 306 90 0"/><item objectid="3" transform="1 0 0 0 1 0 0 0 1 90 -126 0"/><item objectid="4" transform="1 0 0 0 1 0 0 0 1 306 -126 0"/></build></model>'''
        old = ["0x0", "180x0", "180x180", "0x180"]
        new = ["0x0", "250x0", "250x250", "0x250"]
        changes = plan_plate_relocation(model, settings, old, new)
        self.assertEqual([(x["dx"], x["dy"]) for x in changes],
                         [("35.0", "35.0"), ("119.0", "35.0"),
                          ("35.0", "-49.0"), ("119.0", "-49.0")])
        result = relocate_build_items(model, changes)
        for position in (b"125 125 0", b"425 125 0", b"125 -175 0", b"425 -175 0"):
            self.assertIn(position, result)
        self.assertEqual(relocate_build_items(model, []), model)

    def test_native_s1_pitch_keeps_later_plates_centered(self):
        settings = b'''<config><plate/><plate/><plate/><plate><model_instance><metadata key="object_id" value="1"/><metadata key="instance_id" value="0"/></model_instance></plate></config>'''
        model = b'''<model xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><resources/><build><item objectid="1" transform="1 0 0 0 1 0 0 0 1 306 -126 0"/></build></model>'''
        changes = plan_plate_relocation(
            model, settings, ["0x0", "180x0", "180x180", "0x180"],
            ["0x0", "250x0", "250x250", "0x250"],
            target_grid_pitch=S1_NATIVE_GRID_PITCH,
        )
        self.assertEqual(changes, [{"item_index": 0, "dx": "133.4", "dy": "-77.8"}])
        self.assertIn(b"439.4 -203.8 0", relocate_build_items(model, changes))
        with self.assertRaisesRegex(PlanError, "grid pitch"):
            plan_plate_relocation(model, settings, ["0x0", "180x0", "180x180", "0x180"],
                                  ["0x0", "250x0", "250x250", "0x250"],
                                  target_grid_pitch=(Decimal("249"), Decimal("328.8")))

    def test_multi_plate_unknown_mapping_or_smaller_bed_blocks(self):
        settings = b'''<config><plate/><plate/></config>'''
        model = b'''<model xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><resources/><build><item objectid="1" transform="1 0 0 0 1 0 0 0 1 90 90 0"/></build></model>'''
        old = ["0x0", "180x0", "180x180", "0x180"]
        new = ["0x0", "250x0", "250x250", "0x250"]
        with self.assertRaises(PlanError):
            plan_plate_relocation(model, settings, old, new)
        with self.assertRaises(PlanError):
            plan_plate_relocation(model, settings, new, old)

    def test_smaller_bed_requires_and_checks_mesh_fit(self):
        settings = b'''<config><plate><model_instance><metadata key="object_id" value="1"/><metadata key="instance_id" value="0"/></model_instance></plate><plate><model_instance><metadata key="object_id" value="2"/><metadata key="instance_id" value="0"/></model_instance></plate></config>'''
        model = b'''<model xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><resources><object id="1"><mesh><vertices><vertex x="-10" y="-10" z="0"/><vertex x="10" y="10" z="0"/></vertices><triangles/></mesh></object><object id="2"><mesh><vertices><vertex x="-10" y="-10" z="0"/><vertex x="120" y="10" z="0"/></vertices><triangles/></mesh></object></resources><build><item objectid="1" transform="1 0 0 0 1 0 0 0 1 128 128 0"/><item objectid="2" transform="1 0 0 0 1 0 0 0 1 435.2 128 0"/></build></model>'''
        old = ["0x0", "256x0", "256x256", "0x256"]
        new = ["0x0", "250x0", "250x250", "0x250"]
        with self.assertRaisesRegex(PlanError, "mesh-fit verification"):
            plan_plate_relocation(model, settings, old, new)
        changes = plan_plate_relocation(model, settings, old, new,
                                        read_member=lambda _: self.fail("inline meshes need no external member"))
        self.assertEqual([(x["dx"], x["dy"]) for x in changes],
                         [("-3.0", "-3.0"), ("-10.2", "-3.0")])
        self.assertIn(b"125 125 0", relocate_build_items(model, changes))
        outside = model.replace(b'x="120"', b'x="126"')
        with self.assertRaisesRegex(PlanError, "outside the smaller target bed"):
            plan_plate_relocation(outside, settings, old, new,
                                  read_member=lambda _: b"")

    def test_smaller_bed_external_component_mesh_is_checked(self):
        settings = b'''<config><plate><model_instance><metadata key="object_id" value="2"/><metadata key="instance_id" value="0"/></model_instance></plate><plate><model_instance><metadata key="object_id" value="2"/><metadata key="instance_id" value="1"/></model_instance></plate></config>'''
        model = b'''<model xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06"><resources><object id="2"><components><component p:path="/3D/Objects/a.model" objectid="1" transform="1 0 0 0 1 0 0 0 1 0 0 0"/></components></object></resources><build><item objectid="2" transform="1 0 0 0 1 0 0 0 1 128 128 0"/><item objectid="2" transform="1 0 0 0 1 0 0 0 1 435.2 128 0"/></build></model>'''
        mesh = b'''<model xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><resources><object id="1"><mesh><vertices><vertex x="-1" y="-1" z="0"/><vertex x="1" y="1" z="0"/></vertices><triangles/></mesh></object></resources><build/></model>'''
        seen = []
        def read(name):
            seen.append(name)
            return mesh
        changes = plan_plate_relocation(
            model, settings, ["0x0", "256x0", "256x256", "0x256"],
            ["0x0", "250x0", "250x250", "0x250"], read_member=read,
        )
        self.assertEqual(seen, ["3D/Objects/a.model"])
        self.assertEqual(len(changes), 2)

    def test_explicit_uniform_scale_fits_offset_geometry_with_brim_margin(self):
        settings = b'''<config><plate><model_instance><metadata key="object_id" value="1"/><metadata key="instance_id" value="0"/></model_instance></plate><plate><model_instance><metadata key="object_id" value="2"/><metadata key="instance_id" value="0"/></model_instance></plate></config>'''
        model = b'''<model xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><resources><object id="1"><mesh><vertices><vertex x="-125" y="-105" z="0"/><vertex x="125" y="105" z="0"/></vertices><triangles/></mesh></object><object id="2"><mesh><vertices><vertex x="-20" y="-10" z="0"/><vertex x="20" y="10" z="0"/></vertices><triangles/></mesh></object></resources><build><item objectid="1" transform="1 0 0 0 1 0 0 0 1 129.42013 145.42089 6.65"/><item objectid="2" transform="1 0 0 0 1 0 0 0 1 435.2 128 0"/></build></model>'''
        old = ["0x0", "256x0", "256x256", "0x256"]
        new = ["0x0", "250x0", "250x250", "0x250"]
        with self.assertRaisesRegex(PlanError, "outside the smaller target bed"):
            plan_plate_relocation(model, settings, old, new, read_member=lambda _: b"")
        changes = plan_plate_relocation(
            model, settings, old, new, read_member=lambda _: b"",
            target_grid_pitch=S1_NATIVE_GRID_PITCH,
            scale_percent=Decimal("94"), edge_margin=Decimal("5.6"),
        )
        self.assertEqual(len(changes), 2)
        self.assertEqual([change["scale"] for change in changes], ["0.94", "0.94"])
        scaled = relocate_build_items(model, changes)
        self.assertNotEqual(scaled, model)
        self.assertIn(b'0.94 0 0 0 0.94 0 0 0 0.94', scaled)
        automatic = plan_plate_relocation(
            model, settings, old, new, read_member=lambda _: b"",
            target_grid_pitch=S1_NATIVE_GRID_PITCH,
            scale_to_fit=True, edge_margin=Decimal("5.6"),
        )
        self.assertEqual(
            [(change["plate_index"], change["scale"]) for change in automatic],
            [(0, "0.944"), (1, "1")],
        )
        self.assertIn(b'0.944 0 0 0 0.944 0 0 0 0.944',
                      relocate_build_items(model, automatic))
        with self.assertRaisesRegex(PlanError, "edge clearance"):
            plan_plate_relocation(
                model, settings, old, new, read_member=lambda _: b"",
                target_grid_pitch=S1_NATIVE_GRID_PITCH,
                scale_percent=Decimal("94"), edge_margin=Decimal("6.2"),
            )
        with self.assertRaisesRegex(PlanError, "Scale percent"):
            plan_plate_relocation(model, settings, old, new,
                                  scale_percent=Decimal("101"))

    def test_opt_in_scale_writes_only_build_transforms_and_project(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            machine_dir = root / "machine"
            machine_dir.mkdir()
            label = "Anycubic Kobra S1 0.4 nozzle"
            (machine_dir / f"{label}.json").write_text(json.dumps({
                "name": label, "printer_settings_id": label,
                "printer_model": "Anycubic Kobra S1",
                "nozzle_diameter": ["0.4"],
                "printable_area": ["0x0", "250x0", "250x250", "0x250"],
            }), encoding="utf-8")
            target = resolve_machine_target(
                discover_targets(machine_dir=machine_dir)[0], machine_dir=machine_dir
            )
            settings = b'''<config><plate><model_instance><metadata key="object_id" value="1"/><metadata key="instance_id" value="0"/></model_instance></plate><plate><model_instance><metadata key="object_id" value="2"/><metadata key="instance_id" value="0"/></model_instance></plate></config>'''
            model = b'''<model xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><resources><object id="1"><mesh><vertices><vertex x="-125" y="-105" z="0"/><vertex x="125" y="105" z="0"/></vertices><triangles/></mesh></object><object id="2"><mesh><vertices><vertex x="-20" y="-10" z="0"/><vertex x="20" y="10" z="0"/></vertices><triangles/></mesh></object></resources><build><item objectid="1" transform="1 0 0 0 1 0 0 0 1 129.42013 145.42089 6.65"/><item objectid="2" transform="1 0 0 0 1 0 0 0 1 435.2 128 0"/></build></model>'''
            source = make_3mf(root / "large.3mf", {
                "printer_model": "Bambu Lab P1S", "nozzle_diameter": ["0.4"],
                "printable_area": ["0x0", "256x0", "256x256", "0x256"],
                "brim_type": "auto_brim", "brim_width": "5", "brim_object_gap": "0.1",
                "filament_colour": ["#FFFFFF"], "filament_settings_id": ["Generic PLA"],
            }, {"3D/3dmodel.model": model, "Metadata/model_settings.config": settings})
            blocked = build_conversion_plan(source, target)
            self.assertTrue(any("outside the smaller target bed" in value
                                for value in blocked.write_blockers))
            plan = build_conversion_plan(source, target, scale_percent="94")
            self.assertFalse(plan.write_blockers)
            self.assertEqual(plan.scale_percent, "94")
            self.assertEqual(plan.archive_actions[0].confidence, "REVIEW")
            output = root / "scaled.3mf"
            result = write_optimized_archive(plan, output)
            self.assertEqual(set(result.changed_members), {
                "Metadata/project_settings.config", "3D/3dmodel.model",
            })
            with zipfile.ZipFile(source) as original, zipfile.ZipFile(output) as scaled:
                self.assertEqual(original.read("Metadata/model_settings.config"),
                                 scaled.read("Metadata/model_settings.config"))
                self.assertNotEqual(original.read("3D/3dmodel.model"),
                                    scaled.read("3D/3dmodel.model"))
                self.assertIsNone(scaled.testzip())
            automatic = build_conversion_plan(source, target, scale_to_fit=True)
            self.assertFalse(automatic.write_blockers)
            self.assertEqual(automatic.plate_scale_percentages, ("94.4", "100"))
            self.assertEqual(automatic.archive_actions[0].confidence, "REVIEW")
            auto_output = root / "auto-scaled.3mf"
            auto_result = write_optimized_archive(automatic, auto_output)
            self.assertIn("3D/3dmodel.model", auto_result.changed_members)
            with zipfile.ZipFile(auto_output) as scaled:
                self.assertIsNone(scaled.testzip())
            with self.assertRaisesRegex(PlanError, "not both"):
                build_conversion_plan(source, target, scale_percent="94", scale_to_fit=True)

    def test_auto_fit_does_not_shrink_a_single_plate_that_already_fits(self):
        settings = b'''<config><plate><model_instance><metadata key="object_id" value="1"/><metadata key="instance_id" value="0"/></model_instance></plate></config>'''
        model = b'''<model xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><resources><object id="1"><mesh><vertices><vertex x="-10" y="-10" z="0"/><vertex x="10" y="10" z="0"/></vertices><triangles/></mesh></object></resources><build><item objectid="1" transform="1 0 0 0 1 0 0 0 1 128 128 0"/></build></model>'''
        changes = plan_plate_relocation(
            model, settings, ["0x0", "256x0", "256x256", "0x256"],
            ["0x0", "250x0", "250x250", "0x250"],
            read_member=lambda _: b"", scale_to_fit=True, edge_margin=Decimal("0.5"),
        )
        self.assertEqual(len(changes), 1)
        self.assertEqual((changes[0]["item_index"], changes[0]["plate_index"],
                          changes[0]["scale"]), (0, 0, "1"))
        self.assertEqual((Decimal(changes[0]["dx"]), Decimal(changes[0]["dy"])),
                         (Decimal("-3"), Decimal("-3")))
        self.assertIn(b'1 0 0 0 1 0 0 0 1 125 125 0',
                      relocate_build_items(model, changes))
