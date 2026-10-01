import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

from s1_optimizer.model_xml import parse_model_settings
from s1_optimizer.parser import inspect_archive
from s1_optimizer.validation import validate_filament_assignments
from s1_optimizer.plan import build_machine_plan
from s1_optimizer.resolution import resolve_machine_target
from s1_optimizer.targets import discover_targets
from s1_optimizer.writer import write_optimized_archive
from tests.helpers import make_3mf


LEGACY = b'''<config><object id="1"><metadata key="extruder" value="2"/>
<part id="1"><metadata key="extruder" value="0"/>
<slic3rpe:text text="45%"/><slic3rpe:shape depth="0.4"/></part>
</object><object id="2"><metadata key="extruder" value="0"/></object></config>'''


class ModelXmlTests(unittest.TestCase):
    def test_inherited_assignment_key_case_matches_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            source = make_3mf(Path(directory) / "source.3mf", {}, {
                "Metadata/model_settings.config": LEGACY.replace(b'key="extruder" value="2"', b'key="EXTRUDER" value="2"'),
            })
            result = validate_filament_assignments(source, 2)
            self.assertFalse(result.blockers)
            self.assertTrue(any("inherited/default slot 2" in warning for warning in result.warnings))

    def test_known_legacy_tags_parse_without_removing_text_or_shape(self):
        root = parse_model_settings(LEGACY)
        tags = [item.tag.rsplit("}", 1)[-1] for item in root.iter()]
        self.assertIn("text", tags)
        self.assertIn("shape", tags)
        self.assertEqual(next(item for item in root.iter() if item.tag.endswith("}text")).get("text"), "45%")

    def test_unknown_prefix_malformed_xml_and_entities_still_reject(self):
        for raw in (b"<config><unknown:text/></config>", b"<config><slic3rpe:text></config>",
                    b'<!DOCTYPE config [<!ENTITY x "boom">]><config>&x;</config>'):
            with self.subTest(raw=raw), self.assertRaises(ET.ParseError):
                parse_model_settings(raw)

    def test_zero_assignment_semantics_and_byte_preserving_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = make_3mf(root / "source.3mf", {
                "filament_settings_id": ["A", "B"], "filament_colour": ["red", "blue"],
            }, {"Metadata/model_settings.config": LEGACY})
            before = source.read_bytes()
            validation = validate_filament_assignments(source, 2)
            self.assertEqual(validation.assignments_used, (1, 2))
            self.assertEqual(validation.assignments_checked, 3)
            self.assertFalse(validation.blockers)
            self.assertTrue(any("inherited/default slot 2" in warning for warning in validation.warnings))
            self.assertTrue(validate_filament_assignments(source, 1).blockers)
            machine_dir = root / "machines"
            machine_dir.mkdir()
            label = "Anycubic Kobra S1 0.4 nozzle"
            (machine_dir / f"{label}.json").write_text(json.dumps({
                "name": label, "printer_settings_id": label, "printer_model": "Anycubic Kobra S1",
                "nozzle_diameter": ["0.4"],
            }), encoding="utf-8")
            machine = resolve_machine_target(discover_targets(machine_dir=machine_dir)[0], machine_dir=machine_dir)
            plan = build_machine_plan(source, machine)
            self.assertFalse(plan.write_blockers)
            output = root / "out.3mf"
            write_optimized_archive(plan, output)
            with zipfile.ZipFile(output) as archive:
                self.assertEqual(archive.read("Metadata/model_settings.config"), LEGACY)
            summary = next(item for item in inspect_archive(output).xml_summaries
                           if item.name == "Metadata/model_settings.config")
            self.assertEqual(summary.element_counts["text"], 1)
            self.assertEqual(summary.element_counts["shape"], 1)
            self.assertEqual(source.read_bytes(), before)
