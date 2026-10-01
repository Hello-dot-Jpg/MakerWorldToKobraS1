from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from s1_optimizer.errors import ProfileValidationError
from s1_optimizer.profile import inspect_profile


class ProfileTests(unittest.TestCase):
    def test_machine_profile_is_flattened_with_scope_and_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            machine = Path(directory) / "machine"
            machine.mkdir()
            path = machine / "Kobra S1.json"
            path.write_text(
                json.dumps(
                    {
                        "printer_model": "Anycubic Kobra S1",
                        "machine_max_speed_x": ["600", "300", "780"],
                    }
                ),
                encoding="utf-8",
            )
            profile = inspect_profile(path)
            self.assertEqual(profile.profile_kind, "machine")
            self.assertEqual(len(profile.sha256), 64)
            self.assertTrue(all(setting.scope == "printer" for setting in profile.settings))
            values = [
                setting.value
                for setting in profile.settings
                if setting.name == "machine_max_speed_x"
            ]
            self.assertEqual(values, ["600", "300", "780"])

    def test_duplicate_keys_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.json"
            path.write_text('{"name":"one","name":"two"}', encoding="utf-8")
            with self.assertRaisesRegex(ProfileValidationError, "duplicate JSON object key"):
                inspect_profile(path)

    def test_non_object_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.json"
            path.write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(ProfileValidationError, "root must be a JSON object"):
                inspect_profile(path)


if __name__ == "__main__":
    unittest.main()
