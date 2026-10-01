from __future__ import annotations

from pathlib import Path
from decimal import Decimal
import tempfile
import unittest
from unittest.mock import patch

from s1_optimizer.validation import validate_filament_assignments, audit_process_overrides

from tests.helpers import make_3mf


MODEL_SETTINGS = b'''<?xml version="1.0" encoding="UTF-8"?>
<config>
  <object id="1"><metadata key="extruder" value="1"/></object>
  <object id="2"><part id="2"><metadata key="extruder" value="4"/></part></object>
</config>'''


class AssignmentValidationTests(unittest.TestCase):
    def test_mesh_scan_is_lazy_without_variable_layer_profile(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = make_3mf(Path(directory) / "ordinary.3mf", {})
            with patch(
                "s1_optimizer.validation._mesh_extents_by_object_id",
                side_effect=AssertionError("ordinary projects must not scan mesh extents"),
            ):
                warnings, blockers = audit_process_overrides(source, set(), None, None)
            self.assertFalse(warnings)
            self.assertFalse(blockers)

    def test_variable_profile_links_to_streamed_mesh_extent(self) -> None:
        model = b'''<model xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">
        <resources><object id="7" type="model"><mesh><vertices>
        <vertex x="0" y="0" z="0"/><vertex x="1" y="0" z="2"/>
        <vertex x="0" y="1" z="1"/></vertices><triangles/></mesh></object></resources>
        <build><item objectid="7"/></build></model>'''
        with tempfile.TemporaryDirectory() as directory:
            source = make_3mf(Path(directory) / "linked.3mf", {}, {
                "3D/3dmodel.model": model,
                "Metadata/layer_heights_profile.txt":
                    b"object_id=7|0;0.12;1;0.20;2;0.28\n",
            })
            warnings, blockers = audit_process_overrides(
                source, set(), Decimal("0.12"), Decimal("0.28")
            )
            self.assertFalse(blockers)
            self.assertTrue(any("linkage" in item and "extent 2" in item for item in warnings))

    def test_local_height_validation_does_not_treat_zero_as_inheritance(self) -> None:
        # Reviewed PrintConfig::validate rejects non-positive actual heights.
        # This is distinct from zero in machine min/max layer-height limits.
        with tempfile.TemporaryDirectory() as directory:
            for value in ("0", "-0.1", "NaN", "Infinity", "20%", "0.12", "0.42"):
                with self.subTest(value=value):
                    xml = ('<config><object id="1"><metadata key="layer_height" '
                           f'value="{value}"/></object></config>').encode()
                    source = make_3mf(Path(directory) / f"case-{value.replace('%', 'pct')}.3mf", {}, {
                        "Metadata/model_settings.config": xml,
                    })
                    before = source.read_bytes()
                    _, blockers = audit_process_overrides(source, set(), Decimal("0.12"), Decimal("0.42"))
                    self.assertEqual(bool(blockers), value not in {"0.12", "0.42"})
                    self.assertEqual(source.read_bytes(), before)

    def test_local_override_conflicts_and_nozzle_bounds(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = make_3mf(Path(directory) / "overrides.3mf", {}, {
                "Metadata/model_settings.config": b'''<config><object id="7">
                <metadata key="support_type" value="normal(auto)"/>
                <part id="9"><metadata key="layer_height" value="0.5"/></part>
                </object></config>''',
                "Metadata/layer_heights_profile.txt": b"preserved",
            })
            before = source.read_bytes()
            warnings, blockers = audit_process_overrides(
                source, {"support_type"}, Decimal("0.12"), Decimal("0.42")
            )
            self.assertTrue(any("object[7]" in text and "support_type" in text for text in warnings))
            self.assertTrue(any("Variable-layer" in text for text in warnings))
            self.assertTrue(any("part[9]" in text and "bounds" in text for text in blockers))
            self.assertEqual(source.read_bytes(), before)

    def test_validates_one_based_object_and_part_assignments(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = make_3mf(
                Path(directory) / "multi.3mf",
                {"filament_settings_id": ["A", "B", "C", "D"]},
                {"Metadata/model_settings.config": MODEL_SETTINGS},
            )
            result = validate_filament_assignments(source, 4)
            self.assertEqual(result.assignments_checked, 2)
            self.assertEqual(result.assignments_used, (1, 4))
            self.assertFalse(result.blockers)

    def test_blocks_assignment_outside_selected_slots(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = make_3mf(
                Path(directory) / "bad.3mf",
                {"filament_settings_id": ["A", "B"]},
                {"Metadata/model_settings.config": MODEL_SETTINGS},
            )
            result = validate_filament_assignments(source, 2)
            self.assertTrue(any("outside" in item for item in result.blockers))


if __name__ == "__main__":
    unittest.main()
