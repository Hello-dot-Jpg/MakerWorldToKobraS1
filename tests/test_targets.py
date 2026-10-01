from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from s1_optimizer.errors import TargetDiscoveryError
from s1_optimizer.targets import discover_targets, select_target

from tests.helpers import make_3mf


class TargetTests(unittest.TestCase):
    def test_official_and_inherited_community_targets_are_discovered(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            machine = root / "machine"
            machine.mkdir()
            official = {
                "name": "Anycubic Kobra S1 0.4 nozzle",
                "printer_settings_id": "Anycubic Kobra S1 0.4 nozzle",
                "printer_model": "Anycubic Kobra S1",
                "nozzle_diameter": "0.4",
                "nozzle_type": "brass",
            }
            (machine / "Anycubic Kobra S1 0.4 nozzle.json").write_text(
                json.dumps(official), encoding="utf-8"
            )
            bundle = make_3mf(
                root / "profiles.3mf",
                {"printer_settings_id": "Community 0.6 Brass"},
                {
                    "Metadata/machine_settings_1.config": json.dumps(
                        {
                            "inherits": "Anycubic Kobra S1 0.4 nozzle",
                            "name": "Community 0.6 Brass",
                            "printer_settings_id": "Community 0.6 Brass",
                            "nozzle_diameter": "0.6",
                        }
                    ).encode("utf-8")
                },
            )
            targets = discover_targets(
                machine_dir=machine, bundles=(bundle,), nozzle="0.60"
            )
            self.assertEqual(len(targets), 1)
            target = targets[0]
            self.assertEqual(target.label, "Community 0.6 Brass")
            self.assertEqual(target.nozzle_diameter, "0.6")
            self.assertEqual(target.nozzle_type, "brass")
            self.assertEqual(target.source_kind, "community")
            self.assertEqual(
                target.inherits, "Anycubic Kobra S1 0.4 nozzle"
            )

    def test_nozzle_filter_uses_actual_decimal_value(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            machine = Path(directory) / "machine"
            machine.mkdir()
            for diameter in ("0.25", "0.4"):
                name = f"Anycubic Kobra S1 {diameter} nozzle"
                (machine / f"{name}.json").write_text(
                    json.dumps(
                        {
                            "name": name,
                            "printer_settings_id": name,
                            "nozzle_diameter": [diameter],
                            "nozzle_type": "brass",
                        }
                    ),
                    encoding="utf-8",
                )
            targets = discover_targets(machine_dir=machine, nozzle="0.25")
            self.assertEqual([item.nozzle_diameter for item in targets], ["0.25"])

    def test_selection_requires_an_exact_stable_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            machine = Path(directory) / "machine"
            machine.mkdir()
            name = "Anycubic Kobra S1 0.4 nozzle"
            (machine / f"{name}.json").write_text(
                json.dumps(
                    {
                        "name": name,
                        "printer_settings_id": name,
                        "nozzle_diameter": "0.4",
                        "nozzle_type": "brass",
                    }
                ),
                encoding="utf-8",
            )
            targets = discover_targets(machine_dir=machine)
            selected = select_target(targets, "official:anycubic-kobra-s1:0.4:brass")
            self.assertEqual(selected.nozzle_diameter, "0.4")
            with self.assertRaisesRegex(TargetDiscoveryError, "Unknown conversion target"):
                select_target(targets, "official:anycubic-kobra-s1:0.6:brass")


if __name__ == "__main__":
    unittest.main()
