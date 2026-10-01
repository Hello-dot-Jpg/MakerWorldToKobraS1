"""Regenerate the pinned real INI acceptance preset; never install or overwrite."""
import hashlib
from pathlib import Path

from s1_optimizer.filaments import default_filament_profile_dir, discover_filaments, resolve_filament_target
from s1_optimizer.preset_ini import IniPreset
from s1_optimizer.preset_conversion import convert_preset, export_presets
from s1_optimizer.preset_matching import match_filament_option
from s1_optimizer.resolution import resolve_machine_target
from s1_optimizer.targets import default_machine_profile_dir, discover_targets


def main():
    root = Path(__file__).resolve().parents[1]
    source = root / ".research/BIBO-vendor-2.9.2.ini"
    with source.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != "7251aeec8b2bcaaad092167d40adf83bea28a9e00511e90df0a97d2297ee3a95":
        raise ValueError("Pinned INI source hash mismatch")
    md, fd = default_machine_profile_dir(), default_filament_profile_dir()
    targets = [t for t in discover_targets(machine_dir=md) if t.nozzle_diameter == "0.6"]
    if len(targets) != 1:
        raise ValueError("Expected exactly one official 0.6 target")
    machine = resolve_machine_target(targets[0], machine_dir=md)
    option = match_filament_option(discover_filaments(machine, filament_dir=fd),
                                   material="PETG", nozzle_diameter="0.6")
    base = resolve_filament_target(option, filament_dir=fd)
    plan = convert_preset(IniPreset(source, "filament:Prusament PETG @BIBO2"), machine, base,
                          nozzle_material="hardened-steel", hotend="ceramic", max_bed_temp=110)
    expected = {"nozzle_temperature": ["245"], "nozzle_temperature_initial_layer": ["245"],
                "nozzle_temperature_range_high": ["245"], "textured_plate_temp": ["70"],
                "filament_max_volumetric_speed": ["8"], "inherits": "",
                "is_custom_defined": "1", "nozzle_temperature_HS": ["245"],
                "nozzle_temperature_initial_layer_HS": ["245"]}
    if plan.blockers or any(plan.values.get(key) != value for key, value in expected.items()):
        raise ValueError(f"INI acceptance mismatch: {plan.blockers}")
    if not any("15 C tolerance" in warning for warning in plan.warnings):
        raise ValueError("Missing range-extension warning")
    print(export_presets([plan], root / "reports"))
    print("Verified 245 C print/range, 70 C textured PEI, flow 8; NOT installed.")


if __name__ == "__main__":
    main()
