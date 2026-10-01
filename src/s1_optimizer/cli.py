from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from . import __version__
from .compare import compare_inspections
from .errors import InspectorError, TargetDiscoveryError
from .filaments import (
    default_filament_profile_dir,
    discover_filaments,
    resolve_filament_target,
    select_filament,
)
from .parser import inspect_archive
from .plan import build_conversion_plan, plan_json
from .profile import inspect_profile
from .processes import (
    default_process_profile_dir,
    discover_processes,
    resolve_process_target,
    select_process,
)
from .resolution import resolve_machine_target
from .report import (
    comparison_json,
    inspection_json,
    profile_json,
    render_comparison,
    render_inspection,
    render_filaments,
    render_profile,
    render_plan,
    render_processes,
    render_targets,
    targets_json,
    filaments_json,
    processes_json,
)
from .rules import load_rules
from .targets import default_machine_profile_dir, discover_targets, select_target
from .writer import write_optimized_archive


def _configure_utf8_output() -> None:
    # Redirected Windows processes can otherwise inherit a legacy code page and
    # fail when a valid archive member contains non-ASCII characters.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="backslashreplace")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="s1optimizer",
        description="Inspect and safely retarget slicer 3MF projects for Kobra S1.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect", help="inspect one 3MF archive")
    inspect_parser.add_argument("file", help="path to the 3MF file")
    inspect_parser.add_argument(
        "--format", choices=("text", "json"), default="text", dest="output_format"
    )
    inspect_parser.add_argument(
        "--verbose", action="store_true", help="show complete long values in text output"
    )

    profile_parser = subparsers.add_parser(
        "inspect-profile", help="inspect one standalone slicer profile JSON"
    )
    profile_parser.add_argument("file", help="path to the slicer profile JSON")
    profile_parser.add_argument(
        "--format", choices=("text", "json"), default="text", dest="output_format"
    )
    profile_parser.add_argument(
        "--verbose", action="store_true", help="show complete long values in text output"
    )

    compare_parser = subparsers.add_parser("compare", help="compare project settings")
    compare_parser.add_argument("left", help="first 3MF file")
    compare_parser.add_argument("right", help="second 3MF file")
    compare_parser.add_argument(
        "--format", choices=("text", "json"), default="text", dest="output_format"
    )
    compare_parser.add_argument(
        "--show-equal", action="store_true", help="include equal settings in text output"
    )
    compare_parser.add_argument(
        "--verbose", action="store_true", help="show complete long values in text output"
    )

    targets_parser = subparsers.add_parser(
        "targets", help="list selectable Kobra S1 machine targets"
    )
    targets_parser.add_argument(
        "--machine-dir", help="directory containing installed Anycubic machine JSONs"
    )

    processes_parser = subparsers.add_parser(
        "processes", help="list process profiles compatible with one machine target"
    )
    processes_parser.add_argument("--target-id", required=True, help="stable ID from targets")
    processes_parser.add_argument("--machine-dir")
    processes_parser.add_argument("--process-dir")
    processes_parser.add_argument("--bundle", action="append", default=[])
    processes_parser.add_argument(
        "--format", choices=("text", "json"), default="text", dest="output_format"
    )

    filaments_parser = subparsers.add_parser(
        "filaments", help="list filament profiles compatible with one machine target"
    )
    filaments_parser.add_argument("--target-id", required=True, help="stable ID from targets")
    filaments_parser.add_argument("--machine-dir")
    filaments_parser.add_argument("--filament-dir")
    filaments_parser.add_argument("--bundle", action="append", default=[])
    filaments_parser.add_argument("--material", help="exact material family, for example PETG")
    filaments_parser.add_argument(
        "--format", choices=("text", "json"), default="text", dest="output_format"
    )

    subparsers.add_parser("gui", help="launch the local desktop interface")
    targets_parser.add_argument(
        "--bundle", action="append", default=[], help="community profile-bundle 3MF"
    )
    targets_parser.add_argument(
        "--nozzle", help="filter by actual nozzle diameter, for example 0.25 or 0.6"
    )
    targets_parser.add_argument(
        "--format", choices=("text", "json"), default="text", dest="output_format"
    )

    plan_parser = subparsers.add_parser(
        "plan", help="produce a no-write machine-retargeting dry run"
    )
    plan_parser.add_argument("file", help="source 3MF project")
    plan_parser.add_argument("--target-id", required=True, help="stable ID from targets")
    plan_parser.add_argument(
        "--machine-dir", help="directory containing installed Anycubic machine JSONs"
    )
    plan_parser.add_argument("--process-id", help="stable ID from processes")
    plan_parser.add_argument("--process-dir", help="installed Anycubic process JSON directory")
    plan_parser.add_argument("--rules", help="optional JSON clamp-rule file")
    plan_parser.add_argument(
        "--filament-id", action="append", default=[],
        help="stable ID from filaments; repeat in source-slot order"
    )
    plan_parser.add_argument("--filament-dir")
    plan_parser.add_argument("--layer-height", help="custom layer height in mm; retains source first layer")
    plan_parser.add_argument("--scale-percent", type=float,
                             help="advanced: uniformly scale all plates to an explicit percent")
    plan_parser.add_argument("--scale-to-fit", action="store_true",
                             help="automatically scale only plates that need it to fit the S1 bed and brim allowance")
    from .plates import SUPPORTED_BED_TYPES
    plan_parser.add_argument("--bed-type", choices=SUPPORTED_BED_TYPES, default="Textured PEI Plate")
    plan_parser.add_argument(
        "--physical-nozzle-type",
        choices=(
            "profile", "brass", "hardened-steel", "stainless-steel",
            "bimetal", "other",
        ),
        default="profile",
        help=(
            "record the installed nozzle material; supported slicer types may "
            "explicitly override the profile with REVIEW confidence"
        ),
    )
    plan_parser.add_argument(
        "--hotend-type",
        choices=("unspecified", "ptfe-lined", "all-metal", "aftermarket-ceramic", "other"),
        default="unspecified",
        help="record the installed hotend/heatbreak construction; no limit is inferred",
    )
    plan_parser.add_argument(
        "--hotend-max-temp", type=float,
        help="optional explicit hotend ceiling in degrees C; values are only reduced"
    )
    plan_parser.add_argument(
        "--nice-supports-beta", action="store_true",
        help="apply the opt-in Nice supports - beta support overlay"
    )
    plan_parser.add_argument(
        "--use-process-layer-height", action="store_true",
        help="replace source layer heights with the selected process values"
    )
    plan_parser.add_argument(
        "--bundle", action="append", default=[], help="community profile-bundle 3MF"
    )
    plan_parser.add_argument(
        "--format", choices=("text", "json"), default="text", dest="output_format"
    )
    plan_parser.add_argument(
        "--verbose", action="store_true", help="show complete long values in text output"
    )

    optimize_parser = subparsers.add_parser(
        "optimize", help="create a validated Kobra S1-retargeted copy"
    )
    optimize_parser.add_argument("file", help="source 3MF project")
    optimize_parser.add_argument("--target-id", required=True, help="stable ID from targets")
    optimize_parser.add_argument("--process-id", required=True, help="stable ID from processes")
    optimize_parser.add_argument("--machine-dir")
    optimize_parser.add_argument("--process-dir")
    optimize_parser.add_argument("--bundle", action="append", default=[])
    optimize_parser.add_argument("--rules", help="optional JSON clamp-rule file")
    optimize_parser.add_argument(
        "--filament-id", action="append", default=[],
        help="stable ID from filaments; repeat in source-slot order"
    )
    optimize_parser.add_argument("--filament-dir")
    optimize_parser.add_argument("--layer-height", help="custom layer height in mm; retains source first layer")
    optimize_parser.add_argument("--scale-percent", type=float,
                                 help="advanced: uniformly scale all plates to an explicit percent")
    optimize_parser.add_argument("--scale-to-fit", action="store_true",
                                 help="automatically scale only plates that need it to fit the S1 bed and brim allowance")
    optimize_parser.add_argument("--bed-type", choices=SUPPORTED_BED_TYPES, default="Textured PEI Plate")
    optimize_parser.add_argument(
        "--physical-nozzle-type",
        choices=(
            "profile", "brass", "hardened-steel", "stainless-steel",
            "bimetal", "other",
        ),
        default="profile",
        help=(
            "record the installed nozzle material; supported slicer types may "
            "explicitly override the profile with REVIEW confidence"
        ),
    )
    optimize_parser.add_argument(
        "--hotend-type",
        choices=("unspecified", "ptfe-lined", "all-metal", "aftermarket-ceramic", "other"),
        default="unspecified",
        help="record the installed hotend/heatbreak construction; no limit is inferred",
    )
    optimize_parser.add_argument(
        "--hotend-max-temp", type=float,
        help="optional explicit hotend ceiling in degrees C; values are only reduced"
    )
    optimize_parser.add_argument(
        "--nice-supports-beta", action="store_true",
        help="apply the opt-in Nice supports - beta support overlay"
    )
    optimize_parser.add_argument(
        "--use-process-layer-height", action="store_true",
        help="replace source layer heights with the selected process values"
    )
    optimize_parser.add_argument("--output", help="new output 3MF path")
    optimize_parser.add_argument(
        "--dry-run", action="store_true", help="report changes without creating output"
    )
    optimize_parser.add_argument("--report", help="optional new report path; never overwritten")
    optimize_parser.add_argument(
        "--format", choices=("text", "json"), default="text", dest="output_format"
    )
    optimize_parser.add_argument("--verbose", action="store_true")
    return parser


def _resolved_machine(args):
    machine_dir = args.machine_dir or default_machine_profile_dir()
    if machine_dir is None:
        raise TargetDiscoveryError(
            "Anycubic machine profiles were not found; pass --machine-dir"
        )
    targets = discover_targets(machine_dir=machine_dir, bundles=args.bundle)
    selected = select_target(targets, args.target_id)
    return machine_dir, resolve_machine_target(selected, machine_dir=machine_dir)


def _resolved_process(args, machine):
    process_dir = args.process_dir or default_process_profile_dir()
    if process_dir is None:
        raise TargetDiscoveryError(
            "Anycubic process profiles were not found; pass --process-dir"
        )
    choices = discover_processes(
        machine, process_dir=process_dir, bundles=args.bundle
    )
    selected = select_process(choices, args.process_id)
    return resolve_process_target(selected, process_dir=process_dir)


def _resolved_filaments(args, machine):
    if not args.filament_id:
        return ()
    filament_dir = args.filament_dir or default_filament_profile_dir()
    if filament_dir is None:
        raise TargetDiscoveryError(
            "Anycubic filament profiles were not found; pass --filament-dir"
        )
    choices = discover_filaments(
        machine, filament_dir=filament_dir, bundles=args.bundle
    )
    return tuple(
        resolve_filament_target(
            select_filament(choices, filament_id), filament_dir=filament_dir
        )
        for filament_id in args.filament_id
    )


def _new_path(path_value: str, *, kind: str) -> Path:
    path = Path(path_value).expanduser().resolve()
    if path.exists():
        raise TargetDiscoveryError(f"Refusing to overwrite existing {kind}: {path}")
    if not path.parent.is_dir():
        raise TargetDiscoveryError(f"{kind.title()} directory does not exist: {path.parent}")
    return path


def _write_new_report(path: Path, content: str) -> None:
    try:
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.write("\n")
    except OSError as exc:
        raise TargetDiscoveryError(f"Cannot write report {path}: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    _configure_utf8_output()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result_code = 0
        if args.command == "inspect":
            inspection = inspect_archive(args.file)
            if not inspection.is_valid_3mf:
                result_code = 1
            output = (
                inspection_json(inspection)
                if args.output_format == "json"
                else render_inspection(inspection, full_values=args.verbose)
            )
        elif args.command == "inspect-profile":
            profile = inspect_profile(args.file)
            output = (
                profile_json(profile)
                if args.output_format == "json"
                else render_profile(profile, full_values=args.verbose)
            )
        elif args.command == "targets":
            targets = discover_targets(
                machine_dir=args.machine_dir,
                bundles=args.bundle,
                nozzle=args.nozzle,
            )
            output = (
                targets_json(targets)
                if args.output_format == "json"
                else render_targets(targets)
            )
        elif args.command == "processes":
            _, machine = _resolved_machine(args)
            process_dir = args.process_dir or default_process_profile_dir()
            processes = discover_processes(
                machine, process_dir=process_dir, bundles=args.bundle
            )
            output = (
                processes_json(processes)
                if args.output_format == "json"
                else render_processes(processes)
            )
        elif args.command == "filaments":
            _, machine = _resolved_machine(args)
            filament_dir = args.filament_dir or default_filament_profile_dir()
            filaments = discover_filaments(
                machine,
                filament_dir=filament_dir,
                bundles=args.bundle,
                material=args.material,
            )
            output = (
                filaments_json(filaments)
                if args.output_format == "json"
                else render_filaments(filaments)
            )
        elif args.command == "gui":
            from .gui import main as gui_main

            return gui_main()
        elif args.command == "plan":
            _, machine = _resolved_machine(args)
            process = _resolved_process(args, machine) if args.process_id else None
            filaments = _resolved_filaments(args, machine)
            plan = build_conversion_plan(
                args.file, machine, process=process, filaments=filaments,
                nozzle_hardware_type=args.physical_nozzle_type,
                hotend_type=args.hotend_type,
                max_nozzle_temperature=args.hotend_max_temp,
                nice_supports_beta=args.nice_supports_beta,
                use_process_layer_height=args.use_process_layer_height,
                layer_height_override=args.layer_height,
                scale_percent=args.scale_percent,
                scale_to_fit=args.scale_to_fit,
                bed_type=args.bed_type,
                rules=load_rules(args.rules)
            )
            output = (
                plan_json(plan)
                if args.output_format == "json"
                else render_plan(plan, full_values=args.verbose)
            )
        elif args.command == "optimize":
            _, machine = _resolved_machine(args)
            process = _resolved_process(args, machine)
            filaments = _resolved_filaments(args, machine)
            plan = build_conversion_plan(
                args.file, machine, process=process, filaments=filaments,
                nozzle_hardware_type=args.physical_nozzle_type,
                hotend_type=args.hotend_type,
                max_nozzle_temperature=args.hotend_max_temp,
                nice_supports_beta=args.nice_supports_beta,
                use_process_layer_height=args.use_process_layer_height,
                layer_height_override=args.layer_height,
                scale_percent=args.scale_percent,
                scale_to_fit=args.scale_to_fit,
                bed_type=args.bed_type,
                rules=load_rules(args.rules)
            )
            if args.dry_run:
                payload = plan.to_dict()
                text_output = render_plan(plan, full_values=args.verbose)
            else:
                source_path = Path(args.file).expanduser().resolve()
                output_value = args.output or str(
                    source_path.with_name(
                        f"{source_path.stem}_KobraS1_{machine.target.nozzle_diameter}mm.3mf"
                    )
                )
                output_path = _new_path(output_value, kind="output")
                report_extension = "json" if args.output_format == "json" else "txt"
                report_value = args.report or str(
                    output_path.with_name(
                        f"{output_path.stem}_changes.{report_extension}"
                    )
                )
                report_path = _new_path(report_value, kind="report")
                result = write_optimized_archive(plan, output_path)
                payload = {"plan": plan.to_dict(), "write": result.to_dict()}
                text_output = render_plan(plan, full_values=args.verbose) + "\n\nOUTPUT VALIDATION\n"
                text_output += f"- output: {result.output_path}\n"
                text_output += f"- output SHA-256: {result.output_sha256}\n"
                text_output += f"- changed members: {', '.join(result.changed_members)}\n"
                text_output += f"- unchanged members verified: {result.unchanged_members_verified}"
            output = (
                json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
                if args.output_format == "json"
                else text_output
            )
            if args.dry_run:
                if args.report:
                    _write_new_report(_new_path(args.report, kind="report"), output)
            else:
                _write_new_report(report_path, output)
        else:
            left = inspect_archive(args.left)
            right = inspect_archive(args.right)
            comparison = compare_inspections(left, right)
            if not left.is_valid_3mf or not right.is_valid_3mf:
                result_code = 1
            output = (
                comparison_json(comparison)
                if args.output_format == "json"
                else render_comparison(
                    comparison,
                    show_equal=args.show_equal,
                    full_values=args.verbose,
                )
            )
    except InspectorError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(output)
    return result_code
