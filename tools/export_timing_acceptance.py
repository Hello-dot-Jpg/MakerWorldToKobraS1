"""Create a fresh 0.6 HS/PETG review fixture and verify target timing metadata.

Uses the actual converter and writer; no installed presets or originals edited.
"""
import argparse
import json
from pathlib import Path
import tempfile

from s1_optimizer.targets import discover_targets, default_machine_profile_dir
from s1_optimizer.resolution import resolve_machine_target
from s1_optimizer.processes import discover_processes, resolve_process_target, default_process_profile_dir
from s1_optimizer.filaments import discover_filaments, resolve_filament_target, default_filament_profile_dir
from s1_optimizer.plan import build_conversion_plan, read_project_settings, plan_json
from s1_optimizer.writer import write_optimized_archive


def unique(items, label):
    matches = [item for item in items if item.label == label]
    if len(matches) != 1:
        raise ValueError(f"Expected one exact profile: {label}; found {len(matches)}")
    return matches[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output_parent", type=Path)
    args = parser.parse_args()
    md, pd, fd = default_machine_profile_dir(), default_process_profile_dir(), default_filament_profile_dir()
    label = "Anycubic Kobra S1 0.6 nozzle"
    machine = resolve_machine_target(unique(discover_targets(machine_dir=md), label), machine_dir=md)
    process = resolve_process_target(unique(discover_processes(machine, process_dir=pd), f"0.24mm Standard @{label}"), process_dir=pd)
    filament = resolve_filament_target(unique(discover_filaments(machine, filament_dir=fd), f"Anycubic PETG @{label}"), filament_dir=fd)
    _, source = read_project_settings(args.source)
    types = source.get("filament_type")
    if not isinstance(types, list) or len(types) != 1:
        raise ValueError("This focused fixture requires exactly one source filament slot")
    plan = build_conversion_plan(args.source, machine, process=process, filaments=(filament,),
                                 nozzle_hardware_type="hardened_steel", hotend_type="aftermarket-ceramic",
                                 max_nozzle_temperature=320, use_process_layer_height=True)
    if plan.write_blockers:
        raise ValueError(f"Blocked: {plan.write_blockers}")
    folder = Path(tempfile.mkdtemp(prefix="timing-acceptance-", dir=args.output_parent.resolve()))
    result = write_optimized_archive(plan, folder / "tools-06hs-petg-timing-review.3mf")
    _, output = read_project_settings(result.output_path)
    timings = {key: {"source": source.get(key), "target": machine.effective_values.get(key), "output": output.get(key)}
               for key in ("machine_load_filament_time", "machine_unload_filament_time", "machine_tool_change_time")}
    matched = all(value["output"] == value["target"] for value in timings.values() if value["target"] is not None)
    evidence = {"write_result": result.to_dict(), "timings": timings, "target_values_match": matched,
                "native_acceptance": "not_run", "note": "REVIEW only; no print or timing calibration performed"}
    with (folder / "verification.json").open("x", encoding="utf-8") as stream:
        json.dump(evidence, stream, indent=2)
    with (folder / "plan.json").open("x", encoding="utf-8") as stream:
        stream.write(plan_json(plan))
    print(json.dumps({"folder": str(folder), **evidence}, indent=2))
    return int(not matched)


if __name__ == "__main__":
    raise SystemExit(main())
