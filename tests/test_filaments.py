from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from s1_optimizer.filaments import (
    discover_filaments,
    nozzle_meets_hrc,
    resolve_filament_target,
)
from s1_optimizer.resolution import resolve_machine_target
from s1_optimizer.targets import discover_targets
from tests.helpers import make_3mf


class FilamentTests(unittest.TestCase):
    def test_nozzle_hrc_uses_anycubic_thresholds(self) -> None:
        self.assertFalse(nozzle_meets_hrc("brass", "3"))
        self.assertTrue(nozzle_meets_hrc("stainless_steel", "3"))
        self.assertTrue(nozzle_meets_hrc("hardened-steel", "30"))
        self.assertFalse(nozzle_meets_hrc("stainless_steel", "30"))
        self.assertIsNone(nozzle_meets_hrc("bimetal", "3"))
        self.assertIsNone(nozzle_meets_hrc("brass", "not-a-number"))

    def test_explicit_hardness_takes_precedence_over_material_default(self) -> None:
        self.assertTrue(nozzle_meets_hrc("brass", "30", "40"))
        self.assertFalse(nozzle_meets_hrc("hardened-steel", "30", "20"))
        self.assertTrue(nozzle_meets_hrc("hardened-steel", "30", "0"))
        for invalid in (True, "bad", "-1", "501", ["55"]):
            self.assertIsNone(nozzle_meets_hrc("hardened-steel", "30", invalid))

    def test_custom_nozzle_target_exposes_only_matching_stock_filaments(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            machine_dir = root / "machine"
            filament_dir = root / "filament"
            machine_dir.mkdir()
            filament_dir.mkdir()
            for diameter in ("0.4", "0.6"):
                machine_name = f"Anycubic Kobra S1 {diameter} nozzle"
                (machine_dir / f"{machine_name}.json").write_text(json.dumps({
                    "name": machine_name,
                    "printer_settings_id": machine_name,
                    "printer_model": "Anycubic Kobra S1",
                    "nozzle_diameter": [diameter],
                }), encoding="utf-8")
                filament_label = f"Anycubic PLA @{machine_name}"
                (filament_dir / f"{filament_label}.json").write_text(json.dumps({
                    "name": filament_label,
                    "type": "filament",
                    "filament_type": ["PLA"],
                    "filament_settings_id": [filament_label],
                    "compatible_printers": [machine_name],
                }), encoding="utf-8")
            bundle = make_3mf(root / "profiles.3mf", {}, {
                "Metadata/machine_settings_1.config": json.dumps({
                    "inherits": "Anycubic Kobra S1 0.4 nozzle",
                    "name": "Community 0.6 Hardened",
                    "printer_settings_id": "Community 0.6 Hardened",
                    "printer_model": "Anycubic Kobra S1",
                    "nozzle_diameter": ["0.6"],
                    "nozzle_type": "hardened_steel",
                }).encode(),
            })
            target = next(
                item for item in discover_targets(
                    machine_dir=machine_dir, bundles=(bundle,)
                )
                if item.source_kind == "community"
            )
            machine = resolve_machine_target(target, machine_dir=machine_dir)

            options = discover_filaments(
                machine, filament_dir=filament_dir, material="PLA"
            )

            self.assertEqual(
                [item.label for item in options],
                ["Anycubic PLA @Anycubic Kobra S1 0.6 nozzle"],
            )

    def test_filters_material_and_exact_machine_compatibility(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            machine_dir = root / "machine"
            filament_dir = root / "filament"
            machine_dir.mkdir()
            filament_dir.mkdir()
            machine_name = "Anycubic Kobra S1 0.4 nozzle"
            (machine_dir / f"{machine_name}.json").write_text(json.dumps({
                "name": machine_name,
                "printer_settings_id": machine_name,
                "printer_model": "Anycubic Kobra S1",
                "nozzle_diameter": ["0.4"],
                "nozzle_type": "brass",
            }), encoding="utf-8")
            (filament_dir / "Anycubic PETG @acbase.json").write_text(json.dumps({
                "name": "Anycubic PETG @acbase", "type": "filament",
                "filament_type": ["PETG"],
            }), encoding="utf-8")
            label = "Anycubic PETG @Anycubic Kobra S1 0.4 nozzle"
            (filament_dir / f"{label}.json").write_text(json.dumps({
                "name": label, "type": "filament", "inherits": "Anycubic PETG @acbase",
                "filament_settings_id": [label],
                "compatible_printers": [machine_name],
                "filament_max_volumetric_speed": ["12"],
            }), encoding="utf-8")
            wrong = "Anycubic PLA @Other Printer"
            (filament_dir / f"{wrong}.json").write_text(json.dumps({
                "name": wrong, "type": "filament", "filament_type": ["PLA"],
                "compatible_printers": ["Other Printer"],
            }), encoding="utf-8")
            machine = resolve_machine_target(
                discover_targets(machine_dir=machine_dir)[0], machine_dir=machine_dir
            )
            options = discover_filaments(
                machine, filament_dir=filament_dir, material="PETG"
            )
            self.assertEqual([item.label for item in options], [label])
            resolved = resolve_filament_target(options[0], filament_dir=filament_dir)
            self.assertEqual(resolved.effective_values["filament_type"], ["PETG"])


if __name__ == "__main__":
    unittest.main()
