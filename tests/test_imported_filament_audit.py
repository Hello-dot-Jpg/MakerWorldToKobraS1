import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "tools" / "check_imported_filaments.py"


class ImportedFilamentAuditTests(unittest.TestCase):
    def test_standalone_base_folder_identity(self):
        with tempfile.TemporaryDirectory() as root:
            export, installed = Path(root) / "e", Path(root) / "i"
            export.mkdir(); (installed / "base").mkdir(parents=True)
            values = {"name": "PC guide", "chamber_temperature": ["65"], "activate_chamber_temp_control": ["0"]}
            plan = {"name": values["name"], "values": values,
                    "provenance": [{"destination_base": {"effective_values": {}}}]}
            (export / "conversion-report.txt").write_text("DETAILED FIELD AUDIT\n" + json.dumps([plan]))
            (export / "installed-before-batch.json").write_text("{}")
            (installed / "base" / "pc.json").write_text(json.dumps(values))
            result = self.run_audit(export, installed)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            evidence = json.loads(result.stdout)
            self.assertEqual(evidence["expected_added_presets"], ["base/pc.json"])
            self.assertEqual(evidence["results"][0]["compared_keys"], 2)

    def test_windows_report_expected_display_name_passes(self):
        with tempfile.TemporaryDirectory() as root:
            export, installed = Path(root) / "e", Path(root) / "i"
            export.mkdir(); installed.mkdir()
            values = {"name": "Vendor PETG REVIEW", "nozzle_temperature": ["255"]}
            plan = {"name": values["name"], "values": values,
                    "provenance": [{"destination_base": {"effective_values": {}}}]}
            (export / "conversion-report.txt").write_bytes(
                ("DETAILED FIELD AUDIT\r\n" + json.dumps([plan])).encode())
            (export / "installed-before-batch.json").write_text("{}")
            (installed / "different-filename.json").write_text(json.dumps(values))
            result = self.run_audit(export, installed)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            evidence = json.loads(result.stdout)
            self.assertEqual(evidence["expected_added_presets"], ["different-filename.json"])
            self.assertEqual(evidence["results"][0]["compared_keys"], 1)
            self.assertEqual(evidence["results"][0]["differences"], {})

    def test_user_root_resolves_unique_matching_account_store(self):
        with tempfile.TemporaryDirectory() as root:
            export = Path(root) / "e"
            user_root = Path(root) / "user"
            installed = user_root / "789721" / "filament"
            export.mkdir(); installed.mkdir(parents=True)
            values = {"name": "Expected", "nozzle_temperature": ["250"]}
            plan = {"name": values["name"], "values": values,
                    "provenance": [{"destination_base": {"effective_values": {}}}]}
            (export / "conversion-report.txt").write_text(
                "DETAILED FIELD AUDIT\n" + json.dumps([plan]), encoding="utf-8")
            (installed / "expected.json").write_text(json.dumps(values), encoding="utf-8")
            result = self.run_audit(export, user_root)
            evidence = json.loads(result.stdout)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            # Windows runners may expose TEMP through an 8.3 path alias.
            # The auditor deliberately reports the resolved long path.
            self.assertEqual(Path(evidence["resolved_installed_folder"]), installed.resolve())

    def test_user_root_with_ambiguous_matching_stores_fails(self):
        with tempfile.TemporaryDirectory() as root:
            export = Path(root) / "e"
            user_root = Path(root) / "user"
            export.mkdir(); user_root.mkdir()
            values = {"name": "Expected"}
            plan = {"name": values["name"], "values": values,
                    "provenance": [{"destination_base": {"effective_values": {}}}]}
            (export / "conversion-report.txt").write_text(
                "DETAILED FIELD AUDIT\n" + json.dumps([plan]), encoding="utf-8")
            for account in ("one", "two"):
                installed = user_root / account / "filament"
                installed.mkdir(parents=True)
                (installed / "expected.json").write_text(json.dumps(values), encoding="utf-8")
            result = self.run_audit(export, user_root)
            evidence = json.loads(result.stdout)
            self.assertEqual(result.returncode, 1)
            self.assertIn("Could not resolve one active", evidence["audit_error"])

    def run_audit(self, export, installed, *extra):
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(export), str(installed), *extra],
            text=True, capture_output=True, check=False,
        )

    def test_empty_report_is_structured_failure(self):
        with tempfile.TemporaryDirectory() as root:
            root, export, installed = Path(root), Path(root) / "e", Path(root) / "i"
            export.mkdir(); installed.mkdir()
            (export / "conversion-report.txt").write_text("REVIEW ONLY\n", encoding="utf-8")
            result = self.run_audit(export, installed)
            self.assertEqual(result.returncode, 1)
            self.assertIn("audit_error", json.loads(result.stdout))

    def test_added_unexpected_preset_fails(self):
        with tempfile.TemporaryDirectory() as root:
            root, export, installed = Path(root), Path(root) / "e", Path(root) / "i"
            export.mkdir(); installed.mkdir()
            plan = {"name": "Expected", "values": {}, "provenance": [{"destination_base": {"effective_values": {}}}]}
            (export / "conversion-report.txt").write_text(
                "DETAILED FIELD AUDIT\r\n" + json.dumps([plan]), encoding="utf-8")
            (export / "installed-before-batch.json").write_text("{}", encoding="utf-8")
            (installed / "unexpected.json").write_text(json.dumps({"name": "Unexpected"}), encoding="utf-8")
            result = self.run_audit(export, installed)
            evidence = json.loads(result.stdout)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(evidence["unexpected_added_presets"], ["unexpected.json"])

    def test_explicit_missing_snapshot_fails(self):
        with tempfile.TemporaryDirectory() as root:
            root, export, installed = Path(root), Path(root) / "e", Path(root) / "i"
            export.mkdir(); installed.mkdir()
            plan = {"name": "Expected", "values": {}, "provenance": [{"destination_base": {"effective_values": {}}}]}
            (export / "conversion-report.txt").write_text("DETAILED FIELD AUDIT\n" + json.dumps([plan]), encoding="utf-8")
            (installed / "expected.json").write_text(
                json.dumps({"name": "Expected"}), encoding="utf-8"
            )
            result = self.run_audit(export, installed, "--before", str(export / "missing.json"))
            self.assertEqual(result.returncode, 1)
            self.assertIn("snapshot_error", json.loads(result.stdout))

    def test_malformed_nested_plan_fails(self):
        with tempfile.TemporaryDirectory() as root:
            root, export, installed = Path(root), Path(root) / "e", Path(root) / "i"
            export.mkdir(); installed.mkdir()
            (export / "conversion-report.txt").write_text("DETAILED FIELD AUDIT\n" + json.dumps([{"name": "x", "values": {}, "provenance": [{}]}]), encoding="utf-8")
            result = self.run_audit(export, installed)
            self.assertEqual(result.returncode, 1)
            self.assertIn("audit_error", json.loads(result.stdout))

    def test_standalone_empty_inherits_does_not_fill_missing_supported_field_from_base(self):
        with tempfile.TemporaryDirectory() as root:
            root, export, installed = Path(root), Path(root) / "e", Path(root) / "i"
            export.mkdir(); installed.mkdir()
            plan = {"name": "Standalone", "values": {"inherits": ""},
                    "provenance": [{"destination_base": {
                        "effective_values": {"nozzle_temperature": ["250"]}}}]}
            (export / "conversion-report.txt").write_text(
                "DETAILED FIELD AUDIT\n" + json.dumps([plan]), encoding="utf-8")
            (installed / "standalone.json").write_text(
                json.dumps({"name": "Standalone", "inherits": ""}), encoding="utf-8")
            result = self.run_audit(export, installed)
            evidence = json.loads(result.stdout)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(evidence["results"][0]["differences"], {})

    def test_standalone_missing_field_is_not_masked_by_matching_base_value(self):
        with tempfile.TemporaryDirectory() as root:
            root, export, installed = Path(root), Path(root) / "e", Path(root) / "i"
            export.mkdir(); installed.mkdir()
            plan = {"name": "Standalone", "values": {"inherits": "", "nozzle_temperature": ["260"]},
                    "provenance": [{"destination_base": {
                        "effective_values": {"nozzle_temperature": ["260"]}}}]}
            (export / "conversion-report.txt").write_text(
                "DETAILED FIELD AUDIT\n" + json.dumps([plan]), encoding="utf-8")
            (installed / "standalone.json").write_text(
                json.dumps({"name": "Standalone", "inherits": ""}), encoding="utf-8")
            result = self.run_audit(export, installed)
            evidence = json.loads(result.stdout)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("nozzle_temperature", evidence["results"][0]["differences"])

    def test_inherited_preset_overlays_destination_base(self):
        with tempfile.TemporaryDirectory() as root:
            root, export, installed = Path(root), Path(root) / "e", Path(root) / "i"
            export.mkdir(); installed.mkdir()
            plan = {"name": "Inherited", "values": {"inherits": "base"},
                    "provenance": [{"destination_base": {
                        "effective_values": {"nozzle_temperature": ["250"]}}}]}
            (export / "conversion-report.txt").write_text(
                "DETAILED FIELD AUDIT\n" + json.dumps([plan]), encoding="utf-8")
            (installed / "inherited.json").write_text(
                json.dumps({"name": "Inherited", "inherits": "base"}), encoding="utf-8")
            result = self.run_audit(export, installed)
            evidence = json.loads(result.stdout)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(evidence["results"][0]["differences"], {})


if __name__ == "__main__":
    unittest.main()
