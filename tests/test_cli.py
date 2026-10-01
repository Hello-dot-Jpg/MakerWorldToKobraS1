from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile

from s1_optimizer.cli import build_parser, main

from tests.helpers import make_3mf


class CliTests(unittest.TestCase):
    def test_scale_percent_is_opt_in_for_plan_and_export(self) -> None:
        parser = build_parser()
        for command in ("plan", "optimize"):
            base = [command, "input.3mf", "--target-id", "target"]
            if command == "optimize":
                base += ["--process-id", "process"]
            self.assertIsNone(parser.parse_args(base).scale_percent)
            self.assertEqual(parser.parse_args(base + ["--scale-percent", "94"]).scale_percent, 94.0)
            self.assertFalse(parser.parse_args(base).scale_to_fit)
            self.assertTrue(parser.parse_args(base + ["--scale-to-fit"]).scale_to_fit)

    def test_nice_supports_beta_flag_is_opt_in(self) -> None:
        parser = build_parser()
        base = ["plan", "input.3mf", "--target-id", "target"]
        self.assertFalse(parser.parse_args(base).nice_supports_beta)
        self.assertTrue(
            parser.parse_args(base + ["--nice-supports-beta"]).nice_supports_beta
        )

    def test_process_layer_height_flag_is_opt_in(self) -> None:
        parser = build_parser()
        base = ["plan", "input.3mf", "--target-id", "target"]
        self.assertFalse(parser.parse_args(base).use_process_layer_height)
        self.assertTrue(
            parser.parse_args(base + ["--use-process-layer-height"])
            .use_process_layer_height
        )

    def test_inspect_json_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = make_3mf(Path(directory) / "sample.3mf", {"outer_wall_speed": 50})
            output = StringIO()
            with redirect_stdout(output):
                code = main(["inspect", str(path), "--format", "json"])
            self.assertEqual(code, 0)
            payload = json.loads(output.getvalue())
            self.assertEqual(payload["validation"]["zip"], "valid")
            self.assertEqual(payload["validation"]["three_mf"], "valid")
            self.assertEqual(payload["settings"][0]["name"], "outer_wall_speed")

    def test_missing_file_returns_two(self) -> None:
        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(["inspect", "does-not-exist.3mf"])
        self.assertEqual(code, 2)
        self.assertIn("File does not exist", stderr.getvalue())

    def test_inspect_profile_json_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            machine = Path(directory) / "machine"
            machine.mkdir()
            path = machine / "profile.json"
            path.write_text('{"printer_model":"Anycubic Kobra S1"}', encoding="utf-8")
            output = StringIO()
            with redirect_stdout(output):
                code = main(["inspect-profile", str(path), "--format", "json"])
            self.assertEqual(code, 0)
            payload = json.loads(output.getvalue())
            self.assertEqual(payload["profile_kind"], "machine")
            self.assertEqual(payload["settings"][0]["scope"], "printer")

    def test_incomplete_3mf_returns_one_after_reporting(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "incomplete.3mf"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("notes.txt", "not a complete model")
            output = StringIO()
            with redirect_stdout(output):
                code = main(["inspect", str(path)])
            self.assertEqual(code, 1)
            self.assertIn("3MF core structure: invalid or incomplete", output.getvalue())

    def test_module_entrypoint_runs_in_a_subprocess(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = make_3mf(Path(directory) / "sample.3mf", {"wall_loops": 3})
            completed = subprocess.run(
                [sys.executable, "-m", "s1_optimizer", "inspect", str(path)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("wall_loops = 3", completed.stdout)

    def test_long_text_values_are_truncated_unless_verbose(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            long_value = "G1 X1\n" * 100
            path = make_3mf(Path(directory) / "sample.3mf", {"machine_start_gcode": long_value})
            normal = StringIO()
            verbose = StringIO()
            with redirect_stdout(normal):
                self.assertEqual(main(["inspect", str(path)]), 0)
            with redirect_stdout(verbose):
                self.assertEqual(main(["inspect", str(path), "--verbose"]), 0)
            self.assertIn("more chars", normal.getvalue())
            self.assertNotIn("more chars", verbose.getvalue())
            self.assertGreater(len(verbose.getvalue()), len(normal.getvalue()))

    def test_module_entrypoint_emits_unicode_as_utf8(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = make_3mf(
                Path(directory) / "城堡.3mf",
                {"printer_model": "打印机"},
                {"Metadata/城堡.json": b"{}"},
            )
            completed = subprocess.run(
                [sys.executable, "-m", "s1_optimizer", "inspect", str(path)],
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr.decode("utf-8"))
            output = completed.stdout.decode("utf-8")
            self.assertIn("城堡.3mf", output)
            self.assertIn("打印机", output)


if __name__ == "__main__":
    unittest.main()
