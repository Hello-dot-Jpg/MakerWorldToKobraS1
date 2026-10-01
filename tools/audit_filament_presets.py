"""Audit a local vendor JSON corpus; optionally export only explicitly ready plans.

Run with PYTHONPATH=src. Never writes to installed slicer configuration.
"""
import argparse
from pathlib import Path

from s1_optimizer.errors import PlanError
from s1_optimizer.filaments import default_filament_profile_dir, discover_filaments, resolve_filament_target
from s1_optimizer.preset_conversion import convert_preset, export_presets, read_source, render_preset_review, scalar
from s1_optimizer.preset_matching import match_filament_option
from s1_optimizer.resolution import resolve_machine_target
from s1_optimizer.targets import default_machine_profile_dir, discover_targets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--nozzle", default="0.6")
    parser.add_argument("--hotend", choices=("unspecified", "ptfe-lined", "all-metal", "ceramic"), default="unspecified")
    parser.add_argument("--nozzle-material", default="hardened-steel")
    parser.add_argument("--max-nozzle-temp", required=True)
    parser.add_argument("--max-bed-temp", required=True)
    parser.add_argument("--export-matched", type=Path, help="Explicitly export only unblocked matches into a fresh directory under this parent")
    args = parser.parse_args()
    sources = sorted(args.source.glob("*.json"))
    if not sources:
        parser.error("Source directory has no JSON presets")
    md, fd = default_machine_profile_dir(), default_filament_profile_dir()
    targets = [t for t in discover_targets(machine_dir=md) if t.nozzle_diameter == args.nozzle]
    if len(targets) != 1:
        parser.error("Select one unambiguous installed nozzle target")
    machine = resolve_machine_target(targets[0], machine_dir=md)
    options = discover_filaments(machine, filament_dir=fd)
    plans, errors = [], []
    for source in sources:
        try:
            data, _ = read_source(source)
            option = match_filament_option(options, material=scalar(data.get("filament_type", "")), nozzle_diameter=args.nozzle)
            base = resolve_filament_target(option, filament_dir=fd)
            plans.append(convert_preset(source, machine, base,
                max_nozzle_temp=args.max_nozzle_temp, max_bed_temp=args.max_bed_temp,
                nozzle_material=args.nozzle_material, hotend=args.hotend))
        except (PlanError, ValueError, OSError) as exc:
            errors.append(f"{source.name}: {exc}")
    ready = [p for p in plans if not p.blockers]
    print(f"Sources: {len(sources)}; plans: {len(plans)}; ready for review export: {len(ready)}; missing/invalid: {len(errors)}")
    for error in errors:
        print(f"SKIPPED: {error}")
    for plan in plans:
        for blocker in plan.blockers:
            print(f"BLOCKED: {plan.name}: {blocker}")
    if args.export_matched:
        folder = export_presets(ready, args.export_matched)
        with (folder / "batch-audit.txt").open("x", encoding="utf-8") as stream:
            stream.write(render_preset_review(plans, errors))
        print(f"EXPORTED: {folder}; not installed. See batch-audit.txt for skipped inputs.")


if __name__ == "__main__":
    main()
