import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from s1_optimizer.errors import PlanError
from s1_optimizer.preset_sources import list_bundle_presets, read_bundle_source
from s1_optimizer.preset_conversion import convert_preset, export_presets
from tests import test_preset_conversion


class PresetSourceTests(unittest.TestCase):
    def bundle(self, root, members):
        path = root / "bundle.orca_filament"
        with zipfile.ZipFile(path, "w") as archive:
            for name, value in members:
                archive.writestr(name, value if isinstance(value, bytes) else json.dumps(value))
        return path

    def test_nested_bundle_named_inheritance_and_no_extraction(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, machine, base = test_preset_conversion.PresetConversionTests().fixtures(root)
            parent = json.loads(source.read_text())
            parent.update(name="Vendor parent", type="filament")
            path = self.bundle(root, [("base/arbitrary.json", parent),
                                     ("leaves/child.json", {"name": "Child", "type": "filament", "inherits": "Vendor parent"}),
                                     ("manifest.json", {"version": "1"}),
                                     ("machine.json", {"type": "machine", "name": "Machine"})])
            before = path.read_bytes()
            sources = list_bundle_presets(path)
            self.assertEqual(len(sources), 2)
            child = sources[1]
            data, history = read_bundle_source(child)
            self.assertEqual(data["filament_type"], ["PETG"])
            self.assertEqual(len(history), 2)
            plan = convert_preset(child, machine, base, max_nozzle_temp=300, max_bed_temp=110)
            self.assertFalse(plan.blockers)
            output = export_presets([plan], root)
            self.assertTrue((output / plan.filename).is_file())
            self.assertFalse((root / "base").exists())
            self.assertEqual(path.read_bytes(), before)

    def test_unsafe_paths_collisions_symlinks_and_limits_reject(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ("../bad.json", "/bad.json", "C:/bad.json", "dir\\bad.json", "NUL.json", "dir./bad.json"):
                with self.subTest(name=name):
                    info = zipfile.ZipInfo("placeholder")
                    info.filename = name
                    path = self.bundle(root, [(info, {})])
                    with self.assertRaises(PlanError):
                        list_bundle_presets(path)
            path = self.bundle(root, [("A.json", {}), ("a.json", {})])
            with self.assertRaises(PlanError):
                list_bundle_presets(path)
            info = zipfile.ZipInfo("link.json")
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            path = self.bundle(root, [(info, b"target")])
            with self.assertRaises(PlanError):
                list_bundle_presets(path)
            path = self.bundle(root, [("a.json", {"name": "A"})])
            for constant, limit in (("MAX_MEMBERS", 0), ("MAX_TOTAL_BYTES", 1), ("MAX_BUNDLE_BYTES", 1), ("MAX_STRUCTURED_MEMBER_BYTES", 1)):
                with patch(f"s1_optimizer.preset_sources.{constant}", limit), self.assertRaises(PlanError):
                    list_bundle_presets(path)

    def test_missing_ambiguous_cyclic_parent_and_invalid_json_reject(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            child = {"name": "Child", "type": "filament", "inherits": "Parent"}
            parent = {"name": "Parent", "type": "filament"}
            cases = (
                [("child.json", child)],
                [("child.json", child), ("parent.json", parent), ("dup.json", parent)],
                [("child.json", child), ("parent.json", {**parent, "inherits": "Child"})],
            )
            for members in cases:
                path = self.bundle(root, members)
                with self.assertRaises(PlanError):
                    read_bundle_source(list_bundle_presets(path)[0])
            for raw in (b"{invalid", b"[]"):
                path = self.bundle(root, [("bad.json", raw)])
                with self.assertRaises(PlanError):
                    list_bundle_presets(path)
