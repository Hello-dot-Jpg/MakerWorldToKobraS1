import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from tools.audit_corpus import audit


class CorpusAuditTests(unittest.TestCase):
    def test_inventory_is_read_only_and_distinguishes_candidates(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            profiles = root / "profiles"
            profiles.mkdir()
            (profiles / "profile.json").write_text(json.dumps({"enable_overhang_speed": "1"}))
            schema = root / "PrintConfig.cpp"
            schema.write_text('def = this->add("enable_overhang_speed", coBool);\n'
                              'def = this->add("filament_type", coStrings);\n')
            source = root / "example.3MF"
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("Metadata/project_settings.config", json.dumps({
                    "enable_overhang_speed": ["1", "1"],
                    "filament_type": ["PLA", "PETG"],
                    "unknown": ["keep"],
                }))
                archive.writestr("Metadata/model_settings.config", "<config><bad:tag/></config>")
            before = source.read_bytes()
            result = audit(root, schema, profiles)
            self.assertEqual(result["counts"]["files"], 1)
            self.assertEqual(result["counts"]["project_settings_members"], 1)
            self.assertEqual([x["key"] for x in result["findings"]], ["enable_overhang_speed"])
            self.assertEqual(len(result["errors"]), 1)
            self.assertEqual(source.read_bytes(), before)

    def test_missing_modern_config_and_invalid_archives_are_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            schema = root / "schema.cpp"
            schema.write_text("")
            profiles = root / "profiles"
            profiles.mkdir()
            with zipfile.ZipFile(root / "legacy.3mf", "w") as archive:
                archive.writestr("3D/model.model", "<model/>")
            (root / "invalid.3mf").write_bytes(b"not a zip")
            result = audit(root, schema, profiles)
            self.assertEqual(result["counts"]["files_without_modern_project_settings"], 2)
            self.assertEqual(len(result["errors"]), 1)
