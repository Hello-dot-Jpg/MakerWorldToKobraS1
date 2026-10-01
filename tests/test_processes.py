from __future__ import annotations

from unittest.mock import patch

import json
from pathlib import Path
import tempfile
import unittest

from s1_optimizer.processes import default_process_profile_dir, discover_processes, resolve_process_target
from s1_optimizer.resolution import resolve_machine_target
from s1_optimizer.targets import discover_targets


class ProcessTests(unittest.TestCase):
    def test_active_system_processes_precede_bundled_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            active = root / "appdata" / "AnycubicSlicerNext" / "system" / "Anycubic" / "process"
            bundled = root / "program" / "AnycubicSlicerNext" / "resources" / "profiles" / "Anycubic" / "process"
            active.mkdir(parents=True)
            bundled.mkdir(parents=True)
            with patch.dict("os.environ", {"APPDATA": str(root / "appdata"), "ProgramFiles": str(root / "program")}):
                self.assertEqual(default_process_profile_dir(), active)
                active.rmdir()
                self.assertEqual(default_process_profile_dir(), bundled)

    def test_foreign_inherited_machine_nozzle_does_not_match_process(self) -> None:
        # Multi-nozzle community overlays inherit a 0.4 base; that must not
        # make every 0.4-compatible process eligible for a 0.6 target.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            machine_dir = root / "machine"
            process_dir = root / "process"
            machine_dir.mkdir()
            process_dir.mkdir()
            base = "Anycubic Kobra S1 0.4 nozzle"
            (machine_dir / f"{base}.json").write_text(
                json.dumps({
                    "name": base,
                    "printer_settings_id": base,
                    "printer_model": "Anycubic Kobra S1",
                    "nozzle_diameter": ["0.4"],
                    "nozzle_type": "brass",
                }), encoding="utf-8"
            )
            # Use a standalone target object from a temporary bundle-like overlay.
            from tests.helpers import make_3mf
            bundle = make_3mf(root / "bundle.3mf", {}, {
                "Metadata/machine_settings_1.config": json.dumps({
                    "name": "Community 0.6",
                    "printer_settings_id": "Community 0.6",
                    "printer_model": "Anycubic Kobra S1",
                    "inherits": base,
                    "nozzle_diameter": ["0.6"],
                }).encode("utf-8")
            })
            process = "0.20mm Standard @Anycubic Kobra S1 0.4 nozzle"
            (process_dir / f"{process}.json").write_text(json.dumps({
                "name": process,
                "type": "process",
                "compatible_printers": [base],
            }), encoding="utf-8")
            machine_target = next(
                item for item in discover_targets(machine_dir=machine_dir, bundles=(bundle,))
                if item.source_kind == "community"
            )
            machine = resolve_machine_target(machine_target, machine_dir=machine_dir)
            self.assertEqual(discover_processes(machine, process_dir=process_dir), ())

    def test_discovers_only_exactly_compatible_official_processes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            machine_dir = root / "machine"
            process_dir = root / "process"
            machine_dir.mkdir()
            process_dir.mkdir()
            machine_name = "Anycubic Kobra S1 0.6 nozzle"
            (machine_dir / f"{machine_name}.json").write_text(
                json.dumps(
                    {
                        "name": machine_name,
                        "printer_settings_id": machine_name,
                        "nozzle_diameter": ["0.6"],
                        "nozzle_type": "hardened_steel",
                    }
                ), encoding="utf-8"
            )
            (process_dir / "fdm_process_common.json").write_text(
                json.dumps({"name": "fdm_process_common", "type": "process"}),
                encoding="utf-8",
            )
            good = "0.30mm Standard @Anycubic Kobra S1 0.6 nozzle"
            (process_dir / f"{good}.json").write_text(
                json.dumps(
                    {
                        "name": good,
                        "type": "process",
                        "inherits": "fdm_process_common",
                        "compatible_printers": [machine_name],
                        "layer_height": "0.3",
                        "outer_wall_speed": "180",
                    }
                ), encoding="utf-8"
            )
            wrong = "0.20mm Standard @Anycubic Kobra S1 0.4 nozzle"
            (process_dir / f"{wrong}.json").write_text(
                json.dumps(
                    {
                        "name": wrong,
                        "type": "process",
                        "compatible_printers": ["Anycubic Kobra S1 0.4 nozzle"],
                    }
                ), encoding="utf-8"
            )
            machine = resolve_machine_target(
                discover_targets(machine_dir=machine_dir)[0], machine_dir=machine_dir
            )
            options = discover_processes(machine, process_dir=process_dir)
            self.assertEqual([item.label for item in options], [good])
            self.assertEqual(options[0].nozzle_diameter, "0.6")
            resolved = resolve_process_target(options[0], process_dir=process_dir)
            self.assertEqual(len(resolved.layers), 2)
            self.assertEqual(resolved.effective_values["outer_wall_speed"], "180")


if __name__ == "__main__":
    unittest.main()
