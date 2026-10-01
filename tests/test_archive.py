from __future__ import annotations

from pathlib import Path
import hashlib
import tempfile
import unittest
import warnings
import zipfile
from unittest.mock import patch

from s1_optimizer.archive import ThreeMFArchive
from s1_optimizer.errors import ArchiveValidationError
from s1_optimizer.parser import inspect_archive

from tests.helpers import make_3mf


class ArchiveTests(unittest.TestCase):
    def test_valid_archive_is_listed_deterministically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = make_3mf(Path(directory) / "sample.3mf", {"layer_height": 0.2})
            inventory = ThreeMFArchive(path).validate()
            self.assertEqual(
                [member.name for member in inventory.members],
                [
                    "3D/3dmodel.model",
                    "[Content_Types].xml",
                    "_rels/.rels",
                    "Metadata/project_settings.config",
                ],
            )
            self.assertEqual(inventory.warnings, ())

    def test_non_zip_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.3mf"
            path.write_text("not a zip", encoding="utf-8")
            with self.assertRaisesRegex(ArchiveValidationError, "Not a valid ZIP"):
                ThreeMFArchive(path).validate()

    def test_incomplete_3mf_warns(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty.3mf"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("note.txt", "hello")
            inventory = ThreeMFArchive(path).validate()
            self.assertEqual(len(inventory.warnings), 3)
            self.assertFalse(inspect_archive(str(path)).is_valid_3mf)

    def test_input_metadata_is_not_changed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = make_3mf(Path(directory) / "sample.3mf", {"layer_height": 0.2})
            before_hash = hashlib.sha256(path.read_bytes()).digest()
            before = path.stat()
            inspect_archive(str(path))
            after = path.stat()
            after_hash = hashlib.sha256(path.read_bytes()).digest()
            self.assertEqual(before_hash, after_hash)
            self.assertEqual(before.st_size, after.st_size)
            self.assertEqual(before.st_mtime_ns, after.st_mtime_ns)

    def test_malformed_core_model_marks_3mf_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = make_3mf(
                Path(directory) / "bad-model.3mf",
                {"layer_height": 0.2},
                {"3D/3dmodel.model": b"<model>"},
            )
            inspection = inspect_archive(str(path))
            self.assertFalse(inspection.is_valid_3mf)
            self.assertTrue(any("3dmodel.model" in warning for warning in inspection.warnings))

    def test_wrong_case_required_member_is_not_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = make_3mf(Path(directory) / "wrong-case.3mf", {"layer_height": 0.2})
            replacement = Path(directory) / "replacement.3mf"
            with zipfile.ZipFile(path, "r") as source, zipfile.ZipFile(replacement, "w") as target:
                for info in source.infolist():
                    name = "[content_types].xml" if info.filename == "[Content_Types].xml" else info.filename
                    target.writestr(name, source.read(info.filename))
            replacement.replace(path)
            inspection = inspect_archive(str(path))
            self.assertFalse(inspection.is_valid_3mf)
            self.assertTrue(any("[Content_Types].xml" in item for item in inspection.warnings))

    def test_duplicate_core_member_is_not_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = make_3mf(Path(directory) / "duplicate.3mf", {"layer_height": 0.2})
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with zipfile.ZipFile(path, "a") as archive:
                    archive.writestr("3D/3dmodel.model", b"<model />")
            inspection = inspect_archive(str(path))
            self.assertFalse(inspection.is_valid_3mf)
            self.assertIn("3D/3dmodel.model", inspection.inventory.duplicate_names)

    def test_core_xml_skipped_by_bound_is_not_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = make_3mf(Path(directory) / "bounded.3mf", {"layer_height": 0.2})
            with patch("s1_optimizer.parser.MAX_XML_MEMBER_BYTES", 10):
                inspection = inspect_archive(str(path))
            self.assertFalse(inspection.is_valid_3mf)
            self.assertTrue(any("inspection limit" in item for item in inspection.warnings))

    def test_disconnected_model_relationship_is_not_valid_3mf(self) -> None:
        bad_relationships = b'''<Relationships
          xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
          <Relationship Target="/3D/missing.model" Id="rel0"
            Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
        </Relationships>'''
        with tempfile.TemporaryDirectory() as directory:
            path = make_3mf(
                Path(directory) / "disconnected.3mf",
                {"layer_height": 0.2},
                {"_rels/.rels": bad_relationships},
            )
            inspection = inspect_archive(str(path))
            self.assertFalse(inspection.is_valid_3mf)
            self.assertTrue(any("target is missing" in item for item in inspection.warnings))


if __name__ == "__main__":
    unittest.main()
