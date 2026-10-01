import unittest
from s1_optimizer.errors import PlanError
from s1_optimizer.filaments import FilamentOption
from s1_optimizer.preset_matching import match_filament_option

def option(label, material="PLA", diameter="0.4"):
    return FilamentOption("id-" + label, label, material, diameter, "official", "x", None, None, None, "SAFE", "hash")

class PresetMatchingTests(unittest.TestCase):
    def test_explicit_selection_beats_canonical_without_cross_material_mapping(self):
        custom = option("Reviewed PLA")
        canonical = option("Anycubic PLA @Anycubic Kobra S1 0.4 nozzle")
        self.assertIs(match_filament_option(iter([custom, canonical]), material="PLA",
                      nozzle_diameter="0.40", selected_id=custom.filament_id), custom)

    def test_explicit_selection_rejects_stale_duplicate_and_mismatched_choices(self):
        chosen = option("chosen")
        for options, material, nozzle, selected_id in (
            ([chosen], "PLA", "0.4", "stale"),
            ([chosen, chosen], "PLA", "0.4", chosen.filament_id),
            ([chosen], "PC-CF", "0.4", chosen.filament_id),
            ([chosen], "PLA", "0.6", chosen.filament_id),
        ):
            with self.subTest(material=material, nozzle=nozzle, selected_id=selected_id):
                with self.assertRaises(PlanError):
                    match_filament_option(options, material=material,
                                          nozzle_diameter=nozzle, selected_id=selected_id)

    def test_canonical_numeric(self):
        canonical = option("Anycubic PLA @Anycubic Kobra S1 0.4 nozzle", diameter="0.40")
        self.assertIs(match_filament_option([option("custom"), canonical], material="PLA", nozzle_diameter="0.40"), canonical)
    def test_single_noncanonical(self):
        candidate = option("Vendor PLA", diameter="0.40")
        self.assertIs(match_filament_option([candidate], material="PLA", nozzle_diameter="0.4"), candidate)
    def test_case_sensitive_and_missing(self):
        for candidate in (option("x", material="pla"), option("x", material="PETG"),
                          option("x", diameter="0.6")):
            with self.assertRaisesRegex(PlanError, "No discovered"):
                match_filament_option([candidate], material="PLA", nozzle_diameter="0.4")
    def test_ambiguous(self):
        with self.assertRaisesRegex(PlanError, "Ambiguous"):
            match_filament_option([option("one"), option("two")], material="PLA", nozzle_diameter="0.4")
    def test_invalid_diameter(self):
        for diameter in ("NaN", "Infinity", "-Infinity", "0", "-0.1"):
            with self.assertRaises(PlanError):
                match_filament_option([], material="PLA", nozzle_diameter=diameter)
