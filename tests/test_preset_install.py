import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from s1_optimizer.errors import PlanError
from s1_optimizer import preset_install


def candidate(folder: Path, name="Siddament PETG @S1 0.6 REVIEW"):
    data = {"name": name, "type": "filament", "from": "User", "inherits": "",
            "is_custom_defined": "1", "filament_settings_id": [name],
            "compatible_printers": ["Anycubic Kobra S1 0.6 nozzle"], "version": "1.0.0.0"}
    path = folder / "S1_exported.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


class PresetInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_install_keeps_existing_and_rollback_quarantines(self):
        store = self.root / "account" / "filament"
        store.mkdir(parents=True)
        old = store / "My old preset.json"
        old.write_bytes(b"untouched")
        export = self.root / "export"
        export.mkdir()
        candidate(export)
        with patch.object(preset_install, "slicer_running", return_value=False), \
             patch.object(preset_install, "active_filament_store", return_value=store.resolve()):
            manifest = preset_install.install_export(export, self.root, store=store)
            installed = store / "Siddament PETG @S1 0.6 REVIEW.json"
            self.assertTrue(installed.exists())
            self.assertEqual(old.read_bytes(), b"untouched")
            self.assertEqual((manifest.parent / "original-filament" / old.name).read_bytes(), b"untouched")
            quarantine = preset_install.rollback_install(manifest)
        self.assertFalse(installed.exists())
        self.assertTrue((quarantine / installed.name).exists())
        self.assertEqual(old.read_bytes(), b"untouched")

    def test_install_refuses_name_collision_and_running_slicer(self):
        store = self.root / "filament"
        store.mkdir()
        export = self.root / "export"
        export.mkdir()
        candidate(export)
        (store / "Siddament PETG @S1 0.6 REVIEW.info").write_text("existing")
        with patch.object(preset_install, "slicer_running", return_value=False):
            with self.assertRaisesRegex(PlanError, "collision"):
                preset_install.install_export(export, self.root, store=store)
        self.assertFalse(list(self.root.glob("S1-preset-backup-*")))
        with patch.object(preset_install, "slicer_running", return_value=True):
            with self.assertRaisesRegex(PlanError, "Close"):
                preset_install.install_export(export, self.root, store=store)

    def test_install_refuses_name_shadowed_by_base_folder(self):
        store = self.root / "filament"
        (store / "base").mkdir(parents=True)
        export = self.root / "export"
        export.mkdir()
        candidate(export)
        (store / "base" / "Siddament PETG @S1 0.6 REVIEW.json").write_text("existing")
        with patch.object(preset_install, "slicer_running", return_value=False):
            with self.assertRaisesRegex(PlanError, "collision"):
                preset_install.install_export(export, self.root, store=store)
        self.assertFalse(list(self.root.glob("S1-preset-backup-*")))

    def test_rollback_refuses_user_modified_preset(self):
        store = self.root / "filament"
        store.mkdir()
        export = self.root / "export"
        export.mkdir()
        candidate(export)
        with patch.object(preset_install, "slicer_running", return_value=False), \
             patch.object(preset_install, "active_filament_store", return_value=store.resolve()):
            manifest = preset_install.install_export(export, self.root, store=store)
            installed = store / "Siddament PETG @S1 0.6 REVIEW.json"
            installed.write_text(installed.read_text() + " ", encoding="utf-8")
            with self.assertRaisesRegex(PlanError, "changed"):
                preset_install.rollback_install(manifest)
            self.assertTrue(installed.exists())
            quarantine = preset_install.rollback_install(manifest, preserve_modified=True)
        self.assertTrue((quarantine / installed.name).read_text(encoding="utf-8").endswith(" "))

    def test_active_store_uses_configured_account_and_checksum_suffix(self):
        root = self.root / "AnycubicSlicerNext"
        root.mkdir()
        (root / "AnycubicSlicerNext.conf").write_text(
            json.dumps({"app": {"preset_folder": "account123"}})
            + "\n# MD5 checksum " + "A" * 32 + "\n", encoding="utf-8")
        expected = root / "user" / "account123" / "filament"
        expected.mkdir(parents=True)
        (root / "user" / "default" / "filament").mkdir(parents=True)
        self.assertEqual(preset_install.active_filament_store(self.root), expected.resolve())


if __name__ == "__main__":
    unittest.main()
