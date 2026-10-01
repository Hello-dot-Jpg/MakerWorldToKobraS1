"""Prepare reviewed Siddament filled-material variants from explicit S1 bases.

The source PC-CF file declares PC. Its correction to PC-CF is deliberately
explicit here, following the user's earlier material decision.
"""
from pathlib import Path

from s1_optimizer.filaments import load_standalone_filament_base
from s1_optimizer.preset_conversion import convert_preset, export_presets
from s1_optimizer.resolution import resolve_machine_target
from s1_optimizer.targets import discover_targets, default_machine_profile_dir


ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / ".research" / "siddament-p1s"
BASES = ROOT / "reports" / "S1-filaments-j7d442cn"


def main():
    target_by_size = {item.nozzle_diameter: item for item in
                      discover_targets(machine_dir=default_machine_profile_dir())}
    pairs = [
        ("0.4", "Siddament_PC_CF__BBL_P1S.json", "S1_PC-CF_0.4_HS_7529c52754_REVIEW.json", True),
        ("0.8", "Siddament_PC_CF__BBL_P1S.json", "S1_PC-CF_0.8_HS_d9bd4d3a47_REVIEW.json", True),
        ("0.8", "Siddament_PLA-CF_Black__BBL_P1S.json", "S1_PLA-CF_0.8_HS_b7c200c7d7_REVIEW.json", False),
    ]
    plans = []
    for size, source_name, base_name, correction in pairs:
        machine = resolve_machine_target(target_by_size[size], machine_dir=default_machine_profile_dir())
        base = load_standalone_filament_base(BASES / base_name, machine)
        plan = convert_preset(SOURCES / source_name, machine, base,
                              max_nozzle_temp="320", max_bed_temp="110",
                              nozzle_material="hardened-steel", hotend="ceramic",
                              accept_base_material=correction)
        if plan.blockers:
            raise SystemExit(f"{plan.name}: {plan.blockers}")
        plans.append(plan)
    folder = export_presets(plans, ROOT / "reports")
    print(folder)
    for plan in plans:
        print(plan.name)


if __name__ == "__main__":
    main()
