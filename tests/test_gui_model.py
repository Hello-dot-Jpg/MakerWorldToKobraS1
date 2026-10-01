from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from s1_optimizer.errors import PlanError
from s1_optimizer.gui import _target_display
from s1_optimizer.filaments import FilamentOption
from s1_optimizer.gui_model import (
    SourceFilamentSlot,
    SourceSummary,
    closest_supported_nozzle,
    suggest_filament,
    suggest_process,
    suggest_target,
    summarize_source,
)
from s1_optimizer.processes import ProcessOption
from s1_optimizer.targets import TargetOption

from tests.helpers import make_3mf


class GuiModelTests(unittest.TestCase):
    @staticmethod
    def _summary(**overrides) -> SourceSummary:
        values = {
            "path": "source.3mf",
            "printer": "Bambu Lab A1 mini 0.4 nozzle",
            "process": "0.20mm Standard @BBL A1M",
            "nozzle_diameter": "0.4",
            "nozzle_type": "stainless_steel",
            "layer_height": "0.2",
            "initial_layer_height": "0.2",
            "line_width": "0.42",
            "wall_loops": "2",
            "infill_density": "15%",
            "infill_pattern": "grid",
            "support_enabled": "0",
            "support_type": "tree(auto)",
            "bed_type": "Textured PEI Plate",
            "filament_slots": (SourceFilamentSlot(1, "Generic PETG @BBL", "PETG"),),
        }
        values.update(overrides)
        return SourceSummary(**values)

    def test_target_display_shows_effective_nozzle_when_vendor_label_is_stale(self) -> None:
        target = TargetOption(
            target_id="community:example:0.25:brass:stale-label",
            label="AC KS1 0.2 nozzle Brass",
            nozzle_diameter="0.25",
            nozzle_type="brass",
            source_kind="community",
            source_path="bundle.3mf",
            source_member="Metadata/machine_settings_1.config",
            inherits="Anycubic Kobra S1 0.4 nozzle",
            sha256="A" * 64,
        )
        display = _target_display(target)
        self.assertIn("AC KS1 0.2 nozzle Brass", display)
        self.assertIn("effective 0.25 mm / brass", display)

    def test_source_summary_preserves_ordered_filament_slots(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = make_3mf(Path(directory) / "source.3mf", {
                "printer_settings_id": "Bambu X1C 0.4",
                "print_settings_id": "0.20 Standard",
                "nozzle_diameter": ["0.4"],
                "nozzle_type": ["hardened_steel"],
                "layer_height": "0.2",
                "initial_layer_print_height": "0.24",
                "line_width": "0.42",
                "wall_loops": "3",
                "sparse_infill_density": "20%",
                "sparse_infill_pattern": "gyroid",
                "enable_support": "1",
                "support_type": "tree(auto)",
                "curr_bed_type": "Textured PEI Plate",
                "filament_settings_id": ["Red PLA", "Blue PETG"],
                "filament_type": ["PLA", "PETG"],
            })
            summary = summarize_source(source)
            self.assertEqual(summary.nozzle_diameter, "0.4")
            self.assertEqual(summary.nozzle_type, "hardened_steel")
            self.assertEqual(summary.layer_height, "0.2")
            self.assertEqual(summary.initial_layer_height, "0.24")
            self.assertEqual(summary.line_width, "0.42")
            self.assertEqual(summary.infill_pattern, "gyroid")
            self.assertEqual(summary.support_enabled, "1")
            self.assertEqual(summary.bed_type, "Textured PEI Plate")
            self.assertEqual(
                [(item.index, item.material) for item in summary.filament_slots],
                [(1, "PLA"), (2, "PETG")],
            )

    def test_closest_supported_nozzle_uses_nearest_and_stable_lower_tie(self) -> None:
        self.assertEqual(closest_supported_nozzle("0.6"), "0.6")
        self.assertEqual(closest_supported_nozzle("0.5"), "0.4")
        self.assertEqual(closest_supported_nozzle("unknown"), "0.4")

    def test_target_suggestion_prefers_source_nozzle_material_then_official(self) -> None:
        official = TargetOption(
            "official", "Official brass", "0.4", "brass", "official",
            "official.json", None, None, "A" * 64,
        )
        hardened = TargetOption(
            "community", "Community hardened", "0.4", "hardened_steel", "community",
            "bundle.3mf", "Metadata/machine_settings_1.config", "Official brass", "B" * 64,
        )
        summary = self._summary(nozzle_type="hardened_steel")
        self.assertIs(suggest_target(summary, (official, hardened)), hardened)
        self.assertIs(
            suggest_target(self._summary(nozzle_type="stainless_steel"), (hardened, official)),
            official,
        )

    def test_process_suggestion_matches_source_height_width_and_name(self) -> None:
        community = ProcessOption(
            "community", "0.20mm SD @AC KS1", "0.4", "0.2", "community",
            "bundle.3mf", "Metadata/process_settings_1.config", None,
            "compatible_printers", "A" * 64, "0.42",
        )
        official = ProcessOption(
            "official", "0.20mm Standard @Anycubic Kobra S1 0.4 nozzle", "0.4",
            "0.2", "official", "official.json", None, None,
            "compatible_printers", "B" * 64, "0.42",
        )
        self.assertIs(suggest_process(self._summary(), (community, official)), official)

    def test_filament_suggestion_uses_source_profile_name_within_material(self) -> None:
        anycubic = FilamentOption(
            "anycubic", "Anycubic PETG @Anycubic Kobra S1", "PETG", "0.4",
            "official", "anycubic.json", None, None, "3", "SAFE", "A" * 64,
        )
        generic = FilamentOption(
            "generic", "Generic PETG @Anycubic Kobra S1", "PETG", "0.4",
            "official", "generic.json", None, None, "3", "SAFE", "B" * 64,
        )
        slot = SourceFilamentSlot(1, "Generic PETG @BBL A1M", "PETG")
        self.assertIs(suggest_filament(slot, (anycubic, generic)), generic)

    def test_source_summary_refuses_misaligned_slot_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = make_3mf(Path(directory) / "source.3mf", {
                "filament_settings_id": ["A", "B"],
                "filament_type": ["PLA", "PETG", "TPU"],
            })
            with self.assertRaisesRegex(PlanError, "do not align"):
                summarize_source(source)


if __name__ == "__main__":
    unittest.main()
