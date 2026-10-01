import json
from pathlib import Path
import tempfile
import unittest

from s1_optimizer.targets import discover_targets
from s1_optimizer.resolution import resolve_machine_target
from s1_optimizer.processes import discover_processes, resolve_process_target
from s1_optimizer.plan import build_conversion_plan, read_project_settings
from s1_optimizer.writer import write_optimized_archive
from s1_optimizer.filaments import discover_filaments, resolve_filament_target
from s1_optimizer.errors import TargetDiscoveryError
from tests.helpers import make_3mf


class ReferenceTests(unittest.TestCase):
    def test_saved_project_supplies_tuning_without_copying_model_intent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            machines, processes = root / "machine", root / "process"
            machines.mkdir()
            processes.mkdir()
            name = "Anycubic Kobra S1 0.4 nozzle"
            (machines / f"{name}.json").write_text(json.dumps({
                "name": name, "printer_settings_id": name,
                "printer_model": "Anycubic Kobra S1", "nozzle_diameter": ["0.4"],
                "nozzle_type": "brass", "gcode_flavor": "klipper",
                "machine_start_gcode": "official start",
            }), encoding="utf-8")
            reference = make_3mf(root / "reference.3mf", {
                "printer_model": "Anycubic Kobra S1", "printer_settings_id": "My tuned S1",
                "gcode_flavor": "klipper", "nozzle_diameter": ["0.4"],
                "nozzle_type": "hardened_steel", "machine_start_gcode": "custom start",
                "print_settings_id": "My tuned process", "inherits": "unavailable preset",
                "layer_height": "0.24", "line_width": "0.45", "outer_wall_speed": "80",
                "wall_loops": "9", "enable_support": "1",
                "filament_settings_id": ["Tuned PLA", "Tuned PLA"],
                "filament_type": ["PLA", "PLA"],
                "nozzle_temperature": ["220", "230"],
                "filament_max_volumetric_speed": ["10", "12"],
                "inherits_group": ["process parent", "PLA parent A", "PLA parent B", "machine parent"],
                "compatible_machine_expression_group": ["process condition", "machine A", "machine B", "printer condition"],
                "compatible_process_expression_group": ["process A", "process B"],
            })
            options = discover_targets(machine_dir=machines, bundles=(reference,))
            target = next(item for item in options if item.source_kind == "reference")
            machine = resolve_machine_target(target, machine_dir=machines)
            choice = next(item for item in discover_processes(machine, process_dir=processes)
                          if item.source_kind == "reference")
            process = resolve_process_target(choice, process_dir=processes)
            source = make_3mf(root / "source.3mf", {
                "printer_model": "Bambu Lab P1S", "printer_settings_id": "Bambu",
                "nozzle_diameter": ["0.4"], "machine_start_gcode": "Bambu start",
                "print_settings_id": "source", "layer_height": "0.2", "line_width": "0.42",
                "outer_wall_speed": "150", "wall_loops": "3", "enable_support": "0",
                "filament_settings_id": ["source PLA", "source PLA"],
                "filament_type": ["PLA", "PLA"],
                "nozzle_temperature": ["210", "210"],
                "filament_max_volumetric_speed": ["8", "20"],
            })
            plan = build_conversion_plan(source, machine, process=process)
            output = root / "result.3mf"
            write_optimized_archive(plan, output)
            _, settings = read_project_settings(output)
            self.assertEqual(settings["machine_start_gcode"], "custom start")
            self.assertEqual(settings["outer_wall_speed"], "80")
            self.assertEqual(settings["line_width"], "0.45")
            self.assertEqual(settings["layer_height"], "0.2")
            self.assertEqual(settings["wall_loops"], "3")
            self.assertEqual(settings["enable_support"], "0")
            self.assertEqual(machine.effective_values["inherits"], name)
            choices = discover_filaments(machine, filament_dir=processes, material="PLA")
            self.assertEqual(len(choices), 2)
            self.assertNotEqual(choices[0].filament_id, choices[1].filament_id)
            filaments = tuple(resolve_filament_target(item, filament_dir=processes)
                              for item in sorted(choices, key=lambda item: item.reference_slot))
            self.assertNotIn("machine_start_gcode", filaments[0].effective_values)
            tuned = build_conversion_plan(source, machine, process=process, filaments=filaments)
            write_optimized_archive(tuned, root / "filaments.3mf")
            _, settings = read_project_settings(root / "filaments.3mf")
            self.assertEqual(settings["nozzle_temperature"], ["220", "230"])
            self.assertEqual(settings["filament_max_volumetric_speed"], ["8", "12"])
            self.assertIn("slot 1", settings["filament_settings_id"][0])
            self.assertEqual(settings["inherits_group"][1:3], ["PLA parent A", "PLA parent B"])
            self.assertEqual(settings["compatible_machine_expression_group"][1:3], ["machine A", "machine B"])
            self.assertEqual(settings["compatible_process_expression_group"], ["process A", "process B"])
            from dataclasses import replace
            broken_layer = replace(machine.layers[-1], values={
                **machine.layers[-1].values, "nozzle_temperature": ["220"],
            })
            from s1_optimizer.filaments import _reference_slot_layer
            with self.assertRaisesRegex(TargetDiscoveryError, "values for 2 slots"):
                _reference_slot_layer(broken_layer, 0)
            for key, bad in (("inherits_group", [""] * 5),
                             ("compatible_machine_expression_group", "bad"),
                             ("compatible_process_expression_group", [None])):
                with self.subTest(key=key), self.assertRaises(TargetDiscoveryError):
                    _reference_slot_layer(replace(machine.layers[-1], values={
                        **machine.layers[-1].values, key: bad,
                    }), 0)
