"""Opt-in support overlay derived from a user-supplied, known-good project.

The source project is Bambu/P2S-origin.  This finite list intentionally excludes
machine G-code, filament/AMS choices, purge behavior, raft settings, ironing,
and nozzle-dependent line widths.  Speed values are ceilings, never increases.
"""
from __future__ import annotations


NICE_SUPPORTS_BETA_NAME = "Nice supports - beta"
NICE_SUPPORTS_BETA_VERSION = 1
NICE_SUPPORTS_REFERENCE_FILE = "Amazing_Support_Settings.3mf"
NICE_SUPPORTS_REFERENCE_SHA256 = (
    "8FF01B6DCF49EFD0E0641EE438A7745C0A8B9D79CD9758AD049E490540EB6FB3"
)

# Values are scalar because Anycubic's corresponding process settings are
# scalar.  tree_support_wall_count=0 is an explicit destination adaptation:
# Bambu's -1 means automatic, while Anycubic documents 0 as automatic.
NICE_SUPPORTS_BETA_SETTINGS: dict[str, str] = {
    "avoid_crossing_wall_includes_support": "0",
    "bridge_no_support": "0",
    "detect_overhang_wall": "1",
    "enable_support": "1",
    "enforce_support_layers": "0",
    "independent_support_layer_height": "0",
    "support_angle": "0",
    "support_base_pattern": "default",
    "support_base_pattern_spacing": "2.5",
    "support_bottom_interface_spacing": "0.5",
    "support_bottom_z_distance": "0.2",
    "support_critical_regions_only": "0",
    "support_expansion": "0",
    "support_interface_bottom_layers": "2",
    "support_interface_loop_pattern": "0",
    "support_interface_not_for_body": "1",
    "support_interface_pattern": "rectilinear_interlaced",
    "support_interface_spacing": "0",
    "support_interface_top_layers": "2",
    "support_object_first_layer_gap": "0.2",
    "support_object_xy_distance": "0.35",
    "support_on_build_plate_only": "1",
    "support_remove_small_overhang": "1",
    "support_style": "default",
    "support_threshold_angle": "45",
    "support_top_z_distance": "0.25",
    "support_type": "tree(auto)",
    "tree_support_branch_angle": "45",
    "tree_support_branch_diameter": "2",
    "tree_support_branch_diameter_angle": "5",
    "tree_support_branch_distance": "5",
    "tree_support_wall_count": "0",
}

# Apply as a downward-only ceiling after considering the selected process.
NICE_SUPPORTS_BETA_SPEED_CEILINGS: dict[str, str] = {
    "support_interface_speed": "80",
    "support_speed": "150",
}


def nice_supports_beta_metadata() -> dict[str, object]:
    return {
        "name": NICE_SUPPORTS_BETA_NAME,
        "version": NICE_SUPPORTS_BETA_VERSION,
        "reference_file": NICE_SUPPORTS_REFERENCE_FILE,
        "reference_sha256": NICE_SUPPORTS_REFERENCE_SHA256,
        "setting_count": (
            len(NICE_SUPPORTS_BETA_SETTINGS)
            + len(NICE_SUPPORTS_BETA_SPEED_CEILINGS)
        ),
    }
