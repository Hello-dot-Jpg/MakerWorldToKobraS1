from __future__ import annotations

import json
from typing import Iterable

from .compare import Comparison, SettingGroup
from .parser import Inspection
from .plan import ConversionPlan
from .processes import ProcessOption
from .filaments import FilamentOption
from .profile import ProfileInspection
from .settings import Setting
from .targets import TargetOption


MAX_TEXT_VALUE_CHARS = 180


def _render_value(value: object, *, full: bool = False) -> str:
    rendered = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if not full and len(rendered) > MAX_TEXT_VALUE_CHARS:
        omitted = len(rendered) - MAX_TEXT_VALUE_CHARS
        return f"{rendered[:MAX_TEXT_VALUE_CHARS]}… <{omitted} more chars>"
    return rendered


def _tags(setting: Setting) -> str:
    return ", ".join(setting.categories) if setting.categories else "uncategorized"


def inspection_json(inspection: Inspection) -> str:
    return json.dumps(inspection.to_dict(), indent=2, ensure_ascii=False, sort_keys=True)


def profile_json(inspection: ProfileInspection) -> str:
    return json.dumps(inspection.to_dict(), indent=2, ensure_ascii=False, sort_keys=True)


def render_profile(
    inspection: ProfileInspection, *, full_values: bool = False
) -> str:
    lines = [
        "SLICER PROFILE INSPECTION",
        f"Path: {inspection.path}",
        f"SHA-256: {inspection.sha256}",
        f"Profile kind: {inspection.profile_kind}",
        f"Parsed settings: {len(inspection.settings)}",
        "",
        "SETTINGS (ALPHABETICAL)",
    ]
    for setting in inspection.settings:
        lines.append(
            f"- {setting.name} = {_render_value(setting.value, full=full_values)} "
            f"<{setting.value_type}; scope={setting.scope}; {_tags(setting)}> @ "
            f"{setting.logical_path}"
        )
    lines.extend(["", "CATEGORY COUNTS"])
    for category in ("printer", "process", "filament", "speed", "acceleration"):
        count = sum(category in setting.categories for setting in inspection.settings)
        lines.append(f"- {category}: {count}")
    return "\n".join(lines)


def targets_json(targets: tuple[TargetOption, ...]) -> str:
    return json.dumps(
        {"count": len(targets), "targets": [target.to_dict() for target in targets]},
        indent=2,
        ensure_ascii=False,
        sort_keys=True,
    )


def render_targets(targets: tuple[TargetOption, ...]) -> str:
    lines = ["CONVERSION TARGETS", f"Count: {len(targets)}"]
    for target in targets:
        lines.extend(
            [
                "",
                f"- {target.target_id}",
                f"  label: {target.label}",
                f"  nozzle: {target.nozzle_diameter} mm ({target.nozzle_type})",
                f"  source: {target.source_kind} @ {target.source_path}",
                f"  member: {target.source_member or '(standalone JSON)'}",
                f"  inherits: {target.inherits or '(none)'}",
                f"  SHA-256: {target.sha256}",
            ]
        )
    return "\n".join(lines)


def processes_json(processes: tuple[ProcessOption, ...]) -> str:
    return json.dumps(
        {"count": len(processes), "processes": [item.to_dict() for item in processes]},
        indent=2,
        ensure_ascii=False,
        sort_keys=True,
    )


def render_processes(processes: tuple[ProcessOption, ...]) -> str:
    lines = ["COMPATIBLE PROCESS PROFILES", f"Count: {len(processes)}"]
    for item in processes:
        lines.extend(
            [
                "",
                f"- {item.process_id}",
                f"  label: {item.label}",
                f"  nozzle: {item.nozzle_diameter} mm",
                f"  layer height: {item.layer_height or '(inherited/unspecified)'} mm",
                f"  nominal line width: {item.line_width or '(inherited/unspecified)'} mm",
                f"  source: {item.source_kind} @ {item.source_path}",
                f"  member: {item.source_member or '(standalone JSON)'}",
                f"  association: {item.association_basis}",
                f"  SHA-256: {item.sha256}",
            ]
        )
    return "\n".join(lines)


def filaments_json(filaments: tuple[FilamentOption, ...]) -> str:
    return json.dumps(
        {"count": len(filaments), "filaments": [item.to_dict() for item in filaments]},
        indent=2,
        ensure_ascii=False,
        sort_keys=True,
    )


def render_filaments(filaments: tuple[FilamentOption, ...]) -> str:
    lines = ["COMPATIBLE FILAMENT PROFILES", f"Count: {len(filaments)}"]
    for item in filaments:
        lines.extend([
            "",
            f"- {item.filament_id}",
            f"  label: {item.label}",
            f"  material: {item.material}",
            f"  nozzle: {item.nozzle_diameter} mm",
            f"  source: {item.source_kind} @ {item.source_path}",
            f"  member: {item.source_member or '(standalone JSON)'}",
            f"  required nozzle HRC: {item.required_nozzle_hrc or '(not specified)'}",
            f"  confidence: {item.confidence}",
            f"  SHA-256: {item.sha256}",
        ])
    return "\n".join(lines)


def render_plan(plan: ConversionPlan, *, full_values: bool = False) -> str:
    lines = [
        "KOBRA S1 CONVERSION PLAN",
        f"Source: {plan.source_path}",
        f"Source SHA-256: {plan.source_sha256}",
        f"Target: {plan.target.target.target_id}",
        f"Target label: {plan.target.target.label}",
        "Profile nozzle: "
        f"{plan.target.target.nozzle_diameter} mm "
        f"({plan.target.target.nozzle_type.replace('_', ' ')})",
        f"Physical nozzle: {plan.nozzle_hardware_type} ({plan.nozzle_hardware_source})",
        f"Output machine label: {plan.effective_machine_label}",
        f"Machine profile layers: {len(plan.target.layers)}",
        f"Process: {plan.process.process.process_id if plan.process else '(not selected)'}",
        f"Output process label: {plan.effective_process_label or '(not selected)'}",
        f"Layer-height policy: "
        f"{('custom ' + plan.layer_height_override + ' mm; source first layer retained') if plan.layer_height_override else ('selected process values' if plan.use_process_layer_height else 'preserve source values')}",
        f"Filament profiles: {len(plan.filaments)}",
        f"Filament slots: {plan.assignment_validation.filament_slots}",
        f"Object/part extruder assignments checked: "
        f"{plan.assignment_validation.assignments_checked}",
        f"Extruder slots used: "
        f"{', '.join(str(value) for value in plan.assignment_validation.assignments_used) or '(none found)'}",
        f"Hotend / heatbreak type: {plan.hotend_type}",
        f"Hotend maximum nozzle temperature: "
        f"{plan.max_nozzle_temperature + ' C' if plan.max_nozzle_temperature else '(not supplied)' }",
        f"Nice supports - beta: {'enabled' if plan.nice_supports_beta else 'disabled'}",
        f"Geometry scale: "
        f"{('automatic S1 fit (' + ', '.join(f'plate {i + 1}: {value}%' for i, value in enumerate(plan.plate_scale_percentages)) + ')') if plan.scale_to_fit else (plan.scale_percent + '%' if plan.scale_percent else 'unchanged')}",
        "Writes performed by planning: 0",
        "",
        "SUMMARY",
        f"- REPLACE: {sum(action.action == 'REPLACE' for action in plan.actions)}",
        f"- CLAMP: {sum(action.action == 'CLAMP' for action in plan.actions)}",
        f"- TRANSLATE: {sum(action.action == 'TRANSLATE' for action in plan.actions)}",
        f"- archive metadata changes: {len(plan.archive_actions)}",
        f"- KEEP top-level settings: {plan.kept_top_level_settings}",
        f"- warnings: {len(plan.warnings)}",
        f"- write blockers: {len(plan.write_blockers)}",
        "",
        "PROFILE INHERITANCE",
    ]
    for layer in plan.target.layers:
        location = layer.source_path
        if layer.source_member:
            location += f"::{layer.source_member}"
        lines.append(f"- {layer.label} @ {location} [{layer.sha256}]")
    if plan.process:
        lines.append("Process:")
        for layer in plan.process.layers:
            location = layer.source_path
            if layer.source_member:
                location += f"::{layer.source_member}"
            lines.append(f"- {layer.label} @ {location} [{layer.sha256}]")
    for index, filament in enumerate(plan.filaments, start=1):
        lines.append(f"Filament selection {index}:")
        for layer in filament.layers:
            location = layer.source_path
            if layer.source_member:
                location += f"::{layer.source_member}"
            lines.append(f"- {layer.label} @ {location} [{layer.sha256}]")
    lines.extend(["", "PROPOSED CHANGES"])
    if not plan.actions:
        lines.append("(none)")
    for action in plan.actions:
        lines.append(
            f"- {action.action} {action.setting_name}: "
            f"{_render_value(action.old_value, full=full_values)} -> "
            f"{_render_value(action.new_value, full=full_values)} "
            f"[{action.confidence}]"
        )
    for action in plan.archive_actions:
        lines.append(
            f"- {action.action} {action.source_member}::{action.setting_name}: "
            f"{_render_value(action.old_value, full=full_values)} -> "
            f"{_render_value(action.new_value, full=full_values)} "
            f"[{action.confidence}]"
        )
    lines.extend(["", "WARNINGS"])
    lines.extend(f"- {warning}" for warning in plan.warnings)
    if not plan.warnings:
        lines.append("(none)")
    return "\n".join(lines)


def render_inspection(inspection: Inspection, *, full_values: bool = False) -> str:
    lines = [
        "3MF INSPECTION",
        f"Path: {inspection.inventory.path}",
        "ZIP: valid",
        f"3MF core structure: {'valid' if inspection.is_valid_3mf else 'invalid or incomplete'}",
        f"Members: {len(inspection.inventory.members)}",
        f"Parsed settings: {len(inspection.settings)}",
        "",
        "ARCHIVE MEMBERS",
    ]
    for member in inspection.inventory.members:
        flags: list[str] = []
        if member.encrypted:
            flags.append("encrypted")
        if member.suspicious_path:
            flags.append("suspicious-path")
        suffix = f" [{', '.join(flags)}]" if flags else ""
        lines.append(
            f"- {member.name} ({member.size} bytes, {member.compressed_size} compressed){suffix}"
        )

    lines.extend(["", "STRUCTURED FILES"])
    if inspection.structured_members:
        for member in inspection.structured_members:
            message = f": {member.message}" if member.message else ""
            lines.append(
                f"- {member.name} [{member.detected_type}; {member.parse_status}]{message}"
            )
    else:
        lines.append("(none detected)")

    lines.extend(["", "MODEL AND PLATE STRUCTURE"])
    structure_labels = {
        "resource_objects": "3MF resource objects",
        "mesh_objects": "3MF mesh objects",
        "build_items": "3MF build items",
        "model_settings_objects": "model-settings objects",
        "model_settings_parts": "model-settings parts",
        "model_instances": "model instances",
        "plates": "plates",
        "assembly_items": "assembly items",
    }
    for key, label in structure_labels.items():
        lines.append(f"- {label}: {inspection.structure_counts[key]}")

    lines.extend(["", "SETTINGS (ALPHABETICAL)"])
    if inspection.settings:
        for setting in inspection.settings:
            lines.append(
                f"- {setting.name} = {_render_value(setting.value, full=full_values)} "
                f"<{setting.value_type}; scope={setting.scope}; {_tags(setting)}> @ "
                f"{setting.source_member}::{setting.logical_path}"
            )
    else:
        lines.append("(no recognized JSON settings config parsed)")

    lines.extend(["", "CATEGORY COUNTS"])
    for category in ("printer", "process", "filament", "speed", "acceleration"):
        count = sum(category in setting.categories for setting in inspection.settings)
        lines.append(f"- {category}: {count}")

    lines.extend(["", f"BUNDLED PROFILE VARIANTS ({len(inspection.profile_variants)})"])
    if inspection.profile_variants:
        for variant in inspection.profile_variants:
            identifiers = ", ".join(variant.identifiers) or "(no identifier)"
            lines.append(
                f"- {variant.member} [{variant.scope}; {variant.selection}]: {identifiers}"
            )
    else:
        lines.append("(none)")

    lines.extend(["", f"CROSS-FILE VALUE CONFLICTS ({len(inspection.setting_conflicts)})"])
    if inspection.setting_conflicts:
        for conflict in inspection.setting_conflicts:
            lines.append(f"- {conflict.name}")
            for setting in conflict.occurrences:
                lines.append(
                    f"  - {_render_value(setting.value, full=full_values)} @ "
                    f"{setting.source_member}::{setting.logical_path}"
                )
    else:
        lines.append("(none)")

    lines.extend(["", "WARNINGS"])
    if inspection.warnings:
        lines.extend(f"- {warning}" for warning in inspection.warnings)
    else:
        lines.append("(none)")
    return "\n".join(lines)


def comparison_json(comparison: Comparison) -> str:
    return json.dumps(comparison.to_dict(), indent=2, ensure_ascii=False, sort_keys=True)


def _render_settings(
    lines: list[str],
    title: str,
    settings: Iterable[Setting],
    *,
    full_values: bool,
) -> None:
    values = tuple(settings)
    lines.extend(["", title])
    if not values:
        lines.append("(none)")
        return
    for setting in values:
        lines.append(
            f"- {setting.identity} = {_render_value(setting.value, full=full_values)} "
            f"<{setting.value_type}; scope={setting.scope}; {_tags(setting)}>"
        )


def _render_group(
    lines: list[str],
    group: SettingGroup,
    *,
    prefix: str = "",
    full_values: bool,
) -> None:
    lines.append(f"{prefix}- {group.name}")
    for setting in group.occurrences:
        lines.append(
            f"{prefix}  - {_render_value(setting.value, full=full_values)} "
            f"<{setting.value_type}; scope={setting.scope}> @ "
            f"{setting.source_member}::{setting.logical_path}"
        )


def render_comparison(
    comparison: Comparison,
    *,
    show_equal: bool = False,
    full_values: bool = False,
) -> str:
    lines = [
        "3MF SETTINGS COMPARISON",
        f"Left:  {comparison.left_path}",
        f"Right: {comparison.right_path}",
        "",
        "SETTING-NAME SUMMARY",
        f"- only left: {len(comparison.by_name.only_left)}",
        f"- only right: {len(comparison.by_name.only_right)}",
        f"- changed values: {len(comparison.by_name.changed)}",
        f"- equal values: {len(comparison.by_name.equal)}",
        f"- warnings: {len(comparison.warnings)}",
    ]
    lines.extend(["", "ONLY LEFT"])
    if comparison.by_name.only_left:
        for group in comparison.by_name.only_left:
            _render_group(lines, group, full_values=full_values)
    else:
        lines.append("(none)")

    lines.extend(["", "ONLY RIGHT"])
    if comparison.by_name.only_right:
        for group in comparison.by_name.only_right:
            _render_group(lines, group, full_values=full_values)
    else:
        lines.append("(none)")

    lines.extend(["", "CHANGED"])
    if comparison.by_name.changed:
        for change in comparison.by_name.changed:
            lines.append(f"- {change.name}")
            lines.append("  LEFT")
            _render_group(lines, change.left, prefix="    ", full_values=full_values)
            lines.append("  RIGHT")
            _render_group(lines, change.right, prefix="    ", full_values=full_values)
    else:
        lines.append("(none)")

    if show_equal:
        lines.extend(["", "EQUAL"])
        for left, right in comparison.by_name.equal:
            lines.append(f"- {left.name}")
            lines.append("  LEFT")
            _render_group(lines, left, prefix="    ", full_values=full_values)
            lines.append("  RIGHT")
            _render_group(lines, right, prefix="    ", full_values=full_values)

    lines.extend(
        [
            "",
            "EXACT MEMBER/PATH SUMMARY",
            f"- only left: {len(comparison.only_left)}",
            f"- only right: {len(comparison.only_right)}",
            f"- changed: {len(comparison.changed)}",
            f"- equal: {len(comparison.equal)}",
            "- full exact-location records are included in JSON output",
        ]
    )

    lines.extend(["", "WARNINGS"])
    if comparison.warnings:
        lines.extend(f"- {warning}" for warning in comparison.warnings)
    else:
        lines.append("(none)")
    return "\n".join(lines)
