"""Dry-plan a local corpus against one exact target/process; never export files.

This tests planner coverage, not destination slicing or filament retargeting.
The JSON output contains local filenames and should not be published.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

from s1_optimizer.plan import build_conversion_plan
from s1_optimizer.targets import discover_targets, default_machine_profile_dir
from s1_optimizer.resolution import resolve_machine_target
from s1_optimizer.processes import discover_processes, resolve_process_target, default_process_profile_dir
from s1_optimizer.errors import InspectorError, PlanError, TargetDiscoveryError


def audit(root, machine_label, process_label, *, offset=0, limit=None):
    machine_dir = default_machine_profile_dir()
    process_dir = default_process_profile_dir()
    target = next(item for item in discover_targets(machine_dir=machine_dir)
                  if item.label == machine_label)
    machine = resolve_machine_target(target, machine_dir=machine_dir)
    option = next(item for item in discover_processes(machine, process_dir=process_dir)
                  if item.label == process_label)
    process = resolve_process_target(option, process_dir=process_dir)
    counts, blocker_counts = Counter(), Counter()
    findings = []
    files = [path for path in sorted(root.rglob("*"))
             if path.is_file() and path.suffix.lower() == ".3mf"]
    selected = files[offset:] if limit is None else files[offset:offset + limit]
    counts["files_available"] = len(files)
    counts["files_selected"] = len(selected)
    for path in selected:
        counts["files"] += 1
        try:
            plan = build_conversion_plan(path, machine, process=process)
            counts["planned"] += 1
            counts["blocked" if plan.write_blockers else "without_blockers"] += 1
            if plan.write_blockers:
                blocker_counts.update(plan.write_blockers)
                findings.append({"file": str(path), "blockers": plan.write_blockers})
        except (InspectorError, PlanError, TargetDiscoveryError, OSError, ValueError) as error:
            counts["rejected"] += 1
            findings.append({"file": str(path), "error": str(error)})
    return {"machine": target.label, "process": option.label, "counts": dict(counts),
            "blockers": dict(blocker_counts), "findings": findings}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--machine", default="Anycubic Kobra S1 0.4 nozzle")
    parser.add_argument("--process", default="0.20mm Standard @Anycubic Kobra S1 0.4 nozzle")
    parser.add_argument("--offset", type=int, default=0,
                        help="skip this many sorted 3MF files before auditing")
    parser.add_argument("--limit", type=int,
                        help="audit at most this many sorted 3MF files")
    args = parser.parse_args()
    if args.offset < 0 or args.limit is not None and args.limit < 0:
        parser.error("--offset and --limit must be non-negative")
    print(json.dumps(audit(args.root, args.machine, args.process,
                           offset=args.offset, limit=args.limit), indent=2))
