"""Prepare a locally reviewed Siddament batch; never touches installed presets.

Usage: python tools/prepare_siddament_batch.py SOURCE_DIR OUTPUT_PARENT
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

from s1_optimizer.filaments import (default_filament_profile_dir, discover_filaments,
                                    resolve_filament_target, load_standalone_filament_base)
from s1_optimizer.preset_conversion import read_source, scalar, convert_preset, export_presets
from s1_optimizer.preset_matching import match_filament_option
from s1_optimizer.resolution import resolve_machine_target
from s1_optimizer.targets import discover_targets, default_machine_profile_dir


def main() -> int:
    sources = sorted(Path(sys.argv[1]).resolve().glob("*.json"))
    parent = Path(sys.argv[2]).resolve()
    if len(sources) != 17 or not parent.is_dir():
        raise SystemExit("Expected the 17 local Siddament P1S JSON files and an existing output parent")
    plans, skips = [], []
    for target in discover_targets(machine_dir=default_machine_profile_dir()):
        if target.nozzle_diameter not in {"0.25", "0.4", "0.6", "0.8"}:
            continue
        # Existing 0.6 presets are retained. The two previously reviewed
        # explicit-base exports are installed separately, without regeneration.
        if target.nozzle_diameter == "0.6":
            continue
        machine = resolve_machine_target(target, machine_dir=default_machine_profile_dir())
        options = discover_filaments(machine, filament_dir=default_filament_profile_dir())
        for source in sources:
            data, _ = read_source(source)
            material = scalar(data.get("filament_type", ""))
            if source.name.startswith("Siddament_PC_CF"):
                skips.append(f"{source.name} / {target.nozzle_diameter}: source declares PC; explicit PC-CF base required")
                continue
            try:
                choice = match_filament_option(options, material=material,
                                               nozzle_diameter=target.nozzle_diameter)
                base = resolve_filament_target(choice, filament_dir=default_filament_profile_dir())
                plan = convert_preset(source, machine, base, max_nozzle_temp="320", max_bed_temp="110",
                                      nozzle_material="hardened-steel", hotend="ceramic")
                if plan.blockers:
                    skips.append(f"{source.name} / {target.nozzle_diameter}: {'; '.join(plan.blockers)}")
                else:
                    plans.append(plan)
            except Exception as exc:
                skips.append(f"{source.name} / {target.nozzle_diameter}: {exc}")
    folder = export_presets(plans, parent)
    report = {"ready": len(plans), "by_nozzle": {size: sum(f"@S1 {size} " in p.name for p in plans)
                                                for size in ("0.25", "0.4", "0.8")},
              "skipped": skips, "export": str(folder)}
    (folder / "batch-summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
