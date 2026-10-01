from io import BytesIO
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import tracemalloc
import unittest
import zipfile

from s1_optimizer.errors import PlanError
from s1_optimizer.plate_layout import plan_plate_relocation, relocate_build_items
from s1_optimizer.stream_geometry import model_skeleton, mesh_vertices
from s1_optimizer.plan import build_conversion_plan
from s1_optimizer.writer import write_optimized_archive
from tests.helpers import make_3mf
from tests import test_writer


MODEL = b'''<model xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><resources><object id="1"><mesh><vertices><vertex x="-100" y="-10" z="0"/><vertex x="100" y="-10" z="0"/><vertex x="0" y="10" z="3"/></vertices><triangles><triangle v1="0" v2="1" v3="2"/></triangles></mesh></object><object id="2"><components><component objectid="1" transform="0 1 0 -1 0 0 0 0 1 0 0 0"/></components></object></resources><build><item objectid="1" transform="1 0 0 0 1 0 0 0 1 128 128 0"/><item objectid="2" transform="1 0 0 0 1 0 0 0 1 435.2 128 0"/></build></model>'''
SETTINGS = b'''<config><plate><model_instance><metadata key="object_id" value="1"/><metadata key="instance_id" value="0"/></model_instance></plate><plate><model_instance><metadata key="object_id" value="2"/><metadata key="instance_id" value="0"/></model_instance></plate></config>'''


class StreamGeometryTests(unittest.TestCase):
    def test_large_multiplate_conversion_preserves_geometry_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, base = test_writer.WriterTests()._plan(root)
            with zipfile.ZipFile(source) as archive:
                project = json.loads(archive.read("Metadata/project_settings.config"))
            project["printable_area"] = ["0x0", "256x0", "256x256", "0x256"]
            padding = b"<!--" + b"x" * (26 * 1024 * 1024) + b"-->"
            raw = MODEL.replace(b"<resources>", b"<resources>" + padding)
            make_3mf(source, project, {"3D/3dmodel.model": raw,
                                       "Metadata/model_settings.config": SETTINGS})
            target = replace(base.target, effective_values={
                **base.target.effective_values,
                "printable_area": ["0x0", "250x0", "250x250", "0x250"],
            })
            plan = build_conversion_plan(source, target, scale_to_fit=True)
            self.assertFalse(plan.write_blockers)
            changes = next(a.new_value for a in plan.archive_actions if a.action == "RELOCATE_PLATES")
            expected = relocate_build_items(MODEL, changes).replace(b"<resources>", b"<resources>" + padding)
            output = root / "converted.3mf"
            write_optimized_archive(plan, output)
            with zipfile.ZipFile(output) as archive:
                self.assertEqual(archive.read("3D/3dmodel.model"), expected)
                self.assertIsNone(archive.testzip())

    def test_streamed_rotated_component_planning_matches_tree(self):
        old = ["0x0", "256x0", "256x256", "0x256"]
        new = ["0x0", "250x0", "250x250", "0x250"]
        expected = plan_plate_relocation(MODEL, SETTINGS, old, new,
                                         read_member=lambda name: MODEL, scale_to_fit=True)
        skeleton = model_skeleton(BytesIO(MODEL))
        actual = plan_plate_relocation(skeleton, SETTINGS, old, new,
                                      read_member=lambda name: skeleton,
                                      read_vertices=lambda name, oid: mesh_vertices(BytesIO(MODEL), oid),
                                      scale_to_fit=True)
        self.assertEqual(actual, expected)
        self.assertNotIn(b"<vertex ", skeleton)

    def test_large_triangle_payload_has_bounded_planning_memory(self):
        triangle = b'<triangle v1="0" v2="1" v3="2"/>'
        raw = MODEL.replace(triangle, triangle * (26 * 1024 * 1024 // len(triangle) + 1))
        self.assertGreater(len(raw), 25 * 1024 * 1024)
        tracemalloc.start()
        try:
            skeleton = model_skeleton(BytesIO(raw))
            vertices = list(mesh_vertices(BytesIO(raw), "1"))
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        self.assertLess(len(skeleton), 4096)
        self.assertEqual(len(vertices), 3)
        self.assertLess(peak, 4 * 1024 * 1024)

    def test_streamed_parser_rejects_entities_and_malformed_xml(self):
        for raw in (b'<!DOCTYPE model><model/>', b'<model>'):
            with self.subTest(raw=raw), self.assertRaises(PlanError):
                model_skeleton(BytesIO(raw))
            with self.subTest(raw=raw), self.assertRaises(PlanError):
                list(mesh_vertices(BytesIO(raw), "1"))
