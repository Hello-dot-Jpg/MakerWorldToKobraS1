from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

from .archive import ThreeMFArchive
from .constants import MAX_STRUCTURED_MEMBER_BYTES, MAX_XML_MEMBER_BYTES, PROJECT_SETTINGS_BASENAME
from .errors import PlanError
from .parser import decode_json
from .resolution import ResolvedMachineTarget
from .processes import ResolvedProcessTarget
from .filaments import (
    ResolvedFilamentTarget,
    nozzle_hrc_for_type,
    nozzle_meets_hrc,
    required_nozzle_hrc,
)
from .rules import RuleSet, load_rules

from .plates import BED_TYPE_ENUM_VALUES, SUPPORTED_BED_TYPES, clear_plate_bed_types
from .plate_layout import S1_NATIVE_GRID_PITCH, plan_plate_relocation
from .stream_geometry import model_skeleton, mesh_vertices
from .model_xml import parse_model_settings
from .validation import AssignmentValidation, validate_filament_assignments, audit_process_overrides
from .compatibility import SCALAR_KEYS, scalarize
from .nice_supports import (
    NICE_SUPPORTS_BETA_SETTINGS,
    NICE_SUPPORTS_BETA_SPEED_CEILINGS,
    nice_supports_beta_metadata,
)


_MACHINE_REPLACE_KEYS = frozenset(
    {
        "bed_exclude_area",
        "before_layer_change_gcode",
        "change_filament_gcode",
        "auxiliary_fan",
        "deretraction_speed",
        "default_filament_profile",
        "default_bed_type",
        "default_print_profile",
        "emit_machine_limits_to_gcode",
        "extruder_clearance_height_to_lid",
        "extruder_clearance_height_to_rod",
        "extruder_clearance_radius",
        "extruder_offset",
        "gcode_flavor",
        "inherits",
        "layer_change_gcode",
        "max_layer_height",
        "machine_end_gcode",
        "machine_pause_gcode",
        "machine_start_gcode",
        "machine_load_filament_time",
        "machine_unload_filament_time",
        "machine_tool_change_time",
        "min_layer_height",
        "nozzle_diameter",
        "nozzle_type",
        "nozzle_hrc",
        "nozzle_volume",
        "pause_print_gcode",
        "printable_area",
        "printable_height",
        "printer_model",
        "printer_settings_id",
        "printer_structure",
        "printer_technology",
        "printer_variant",
        "retract_before_wipe",
        "retract_length_toolchange",
        "retract_lift_above",
        "retract_lift_below",
        "retract_lift_enforce",
        "retract_on_top_layer",
        "retract_restart_extra",
        "retract_restart_extra_toolchange",
        "retract_when_changing_layer",
        "retraction_distances_when_cut",
        "retraction_length",
        "retraction_minimum_travel",
        "retraction_speed",
        "silent_mode",
        "support_multi_bed_types",
        "template_custom_gcode",
        "time_lapse_gcode",
        "use_firmware_retraction",
        "wipe",
        "wipe_distance",
        "z_hop",
        "z_hop_types",
    }
)
_MACHINE_REPLACE_PREFIXES = (
    "machine_max_acceleration_",
    "machine_max_jerk_",
    "machine_max_speed_",
    "machine_min_extruding_rate",
    "machine_min_travel_rate",
)
_SEPARATE_PROFILE_MEMBER = re.compile(
    r"(?:machine|process|filament)_settings(?:_\d+)?\.config", re.IGNORECASE
)
_PLATE_JSON_MEMBER = re.compile(r"plate_\d+\.json", re.IGNORECASE)
_PROFILE_METADATA_KEYS = frozenset(
    {
        "compatible_printers",
        "compatible_printers_condition",
        "compatible_prints",
        "compatible_prints_condition",
        "filament_settings_id",
        "from",
        "inherits",
        "instantiation",
        "name",
        "print_host",
        "print_host_webui",
        "print_settings_id",
        "printer_settings_id",
        "printhost_apikey",
        "printhost_cafile",
        "printhost_password",
        "printhost_port",
        "printhost_user",
        "setting_id",
        "type",
        "version",
    }
)
_NOZZLE_TEMPERATURE_CEILING_KEYS = frozenset(
    {
        "nozzle_temperature",
        "nozzle_temperature_initial_layer",
        "nozzle_temperature_HS",
        "nozzle_temperature_initial_layer_HS",
        "nozzle_temperature_range_high",
    }
)
_LEGACY_PROCESS_VALUE_TRANSLATIONS = {
    "ensure_vertical_shell_thickness": {"enabled": "ensure_all"},
}
_UNCONFIRMED_ACTIVE_FEATURES = {
    "apply_top_surface_compensation": "Bambu top-surface compensation",
    "detect_floating_vertical_shell": "Bambu floating-shell detection",
    "embedding_wall_into_infill": "Bambu wall-into-infill embedding",
    "enable_circle_compensation": "Bambu circle compensation",
    "enable_height_slowdown": "Bambu height-based slowdown",
    "enable_order_independent_overlap_carving": "Bambu overlap carving",
    "enable_support_ironing": "Bambu support ironing",
    "enable_wrapping_detection": "Bambu warping detection",
    "filament_adaptive_volumetric_speed": "Bambu filament adaptive volumetric speed",
    "override_filament_scarf_seam_setting": "Bambu filament scarf-seam override",
    "override_process_overhang_speed": "Bambu per-filament overhang-speed override",
    "prime_tower_enable_framework": "Bambu prime-tower framework",
    "seam_placement_away_from_overhangs": "Bambu seam placement away from overhangs",
}
_FILAMENT_TRANSLATE_KEYS = frozenset(
    {
        "activate_air_filtration",
        "activate_chamber_temp_control",
        "adaptive_pressure_advance",
        "adaptive_pressure_advance_bridges",
        "adaptive_pressure_advance_model",
        "adaptive_pressure_advance_overhangs",
        "additional_cooling_fan_speed",
        "chamber_temperature",
        "close_fan_the_first_x_layers",
        "complete_print_exhaust_fan_speed",
        "during_print_exhaust_fan_speed",
        "enable_overhang_bridge_fan",
        "enable_pressure_advance",
        "fan_cooling_layer_time",
        "fan_max_speed",
        "fan_min_speed",
        "filament_cooling_final_speed",
        "filament_cooling_initial_speed",
        "filament_cooling_moves",
        "filament_deretraction_speed",
        "filament_end_gcode",
        "filament_flow_ratio",
        "filament_cost",
        "filament_id",
        "filament_loading_speed",
        "filament_loading_speed_start",
        "filament_long_retractions_when_cut",
        "filament_minimal_purge_on_wipe_tower",
        "filament_multitool_ramming",
        "filament_multitool_ramming_flow",
        "filament_multitool_ramming_volume",
        "filament_ramming_parameters",
        "filament_stamping_distance",
        "filament_stamping_loading_speed",
        "filament_start_gcode",
        "filament_toolchange_delay",
        "filament_unloading_speed",
        "filament_unloading_speed_start",
        "filament_vendor",
        "full_fan_speed_layer",
        "idle_temperature",
        "internal_bridge_fan_speed",
        "overhang_fan_speed",
        "overhang_fan_threshold",
        "pressure_advance",
        "reduce_fan_stop_start_freq",
        "slow_down_for_layer_cooling",
        "slow_down_layer_time",
        "slow_down_layer_time_HS",
        "slow_down_min_speed",
        "support_material_interface_fan_speed",
        "temperature_vitrification",
    }
)
_FILAMENT_TRANSLATE_PREFIXES = (
    "filament_retract",
    "filament_retraction",
    "filament_wipe",
    "filament_z_hop",
    "nozzle_temperature",
)


@dataclass(frozen=True, slots=True)
class PlanAction:
    action: str
    setting_name: str
    old_value: object
    new_value: object
    confidence: str
    rationale: str
    setting_was_present: bool = True

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ArchiveAction:
    action: str
    source_member: str
    setting_name: str
    old_value: object
    new_value: object
    confidence: str
    rationale: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ConversionPlan:
    source_path: str
    source_sha256: str
    project_member: str
    target: ResolvedMachineTarget
    process: ResolvedProcessTarget | None
    filaments: tuple[ResolvedFilamentTarget, ...]
    nozzle_hardware_type: str
    nozzle_hardware_source: str
    effective_machine_label: str
    hotend_type: str
    max_nozzle_temperature: str | None
    nice_supports_beta: bool
    use_process_layer_height: bool
    layer_height_override: str | None
    scale_percent: str | None
    scale_to_fit: bool
    plate_scale_percentages: tuple[str, ...]
    effective_process_label: str | None
    assignment_validation: AssignmentValidation
    rules: RuleSet
    actions: tuple[PlanAction, ...]
    archive_actions: tuple[ArchiveAction, ...]
    kept_top_level_settings: int
    warnings: tuple[str, ...]
    write_blockers: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "source_path": self.source_path,
            "source_sha256": self.source_sha256,
            "project_member": self.project_member,
            "target": self.target.to_dict(),
            "process": self.process.to_dict() if self.process else None,
            "filaments": [item.to_dict() for item in self.filaments],
            "nozzle_hardware_type": self.nozzle_hardware_type,
            "nozzle_hardware_source": self.nozzle_hardware_source,
            "effective_machine_label": self.effective_machine_label,
            "hotend_type": self.hotend_type,
            "max_nozzle_temperature": self.max_nozzle_temperature,
            "nice_supports_beta": self.nice_supports_beta,
            "nice_supports_beta_profile": (
                nice_supports_beta_metadata() if self.nice_supports_beta else None
            ),
            "use_process_layer_height": self.use_process_layer_height,
            "layer_height_override": self.layer_height_override,
            "scale_percent": self.scale_percent,
            "scale_to_fit": self.scale_to_fit,
            "plate_scale_percentages": list(self.plate_scale_percentages),
            "effective_process_label": self.effective_process_label,
            "assignment_validation": self.assignment_validation.to_dict(),
            "rules": self.rules.to_dict(),
            "summary": {
                "replace": sum(action.action == "REPLACE" for action in self.actions),
                "clamp": sum(action.action == "CLAMP" for action in self.actions),
                "translate": sum(action.action == "TRANSLATE" for action in self.actions),
                "keep": self.kept_top_level_settings,
                "warnings": len(self.warnings),
                "archive_changes": len(self.archive_actions),
                "write_blockers": len(self.write_blockers),
                "writes_performed": 0,
            },
            "actions": [action.to_dict() for action in self.actions],
            "archive_actions": [action.to_dict() for action in self.archive_actions],
            "warnings": list(self.warnings),
            "write_blockers": list(self.write_blockers),
        }


def read_project_settings(path: str | Path) -> tuple[str, dict[str, object]]:
    path = Path(path).expanduser().resolve()
    archive = ThreeMFArchive(path)
    inventory = archive.validate()
    matches = [
        member.name
        for member in inventory.members
        if PurePosixPath(member.name).name.casefold()
        == PROJECT_SETTINGS_BASENAME.casefold()
    ]
    if len(matches) != 1:
        raise PlanError(
            "Exactly one project_settings.config is required for conversion planning; "
            f"found {len(matches)}"
        )
    raw = archive.read_member(matches[0], max_bytes=MAX_STRUCTURED_MEMBER_BYTES)
    try:
        value = decode_json(raw)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise PlanError(f"Cannot parse {matches[0]} as strict JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise PlanError("project_settings.config root must be a JSON object")
    return matches[0], value


def _is_machine_replace_key(name: str) -> bool:
    return name in _MACHINE_REPLACE_KEYS or name.startswith(_MACHINE_REPLACE_PREFIXES)


def _same_target_s1_machine(project: dict[str, object], target: ResolvedMachineTarget) -> bool:
    source_nozzles, _ = _as_values(project.get("nozzle_diameter"))
    return (
        project.get("printer_model") == "Anycubic Kobra S1"
        and project.get("printer_settings_id") == target.target.label
        and len(source_nozzles) == 1
        and _positive_decimal(source_nozzles[0])
        == _positive_decimal(target.target.nozzle_diameter)
    )


def _is_nozzle_width_key(name: str) -> bool:
    return name == "line_width" or name.endswith("_line_width")


def _is_filament_translate_key(name: str) -> bool:
    return (
        name in _FILAMENT_TRANSLATE_KEYS
        or name.startswith(_FILAMENT_TRANSLATE_PREFIXES)
        or "plate_temp" in name
    )


def _translated_filament_value(
    source_value: object,
    selected_filaments: tuple[ResolvedFilamentTarget, ...],
    setting_name: str,
) -> tuple[object | None, str | None]:
    target_values: list[object] = []
    for filament in selected_filaments:
        if setting_name not in filament.effective_values:
            return None, f"missing from {filament.filament.label}"
        values, _ = _as_values(filament.effective_values[setting_name])
        if len(values) != 1:
            return None, f"has a non-slot-shaped value in {filament.filament.label}"
        target_values.append(values[0])
    if isinstance(source_value, list):
        if len(source_value) != len(selected_filaments):
            return None, "source array does not align with filament slots"
        return target_values, None
    if len(selected_filaments) != 1:
        return None, "source scalar cannot represent multiple filament slots"
    return target_values[0], None


def build_machine_plan(
    source_path: str | Path, target: ResolvedMachineTarget
) -> ConversionPlan:
    return build_conversion_plan(source_path, target)


def _positive_decimal(value: object) -> Decimal | None:
    if isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return number if number.is_finite() and number > 0 else None


def _nonnegative_decimal(value: object) -> Decimal | None:
    if isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return number if number.is_finite() and number >= 0 else None


def _scale_edge_margin(project: dict[str, object]) -> Decimal:
    """Reserve an extra half-millimetre beyond any requested brim."""
    margin = Decimal("0.5")
    brim_type = str(project.get("brim_type", "no_brim")).casefold()
    if brim_type not in {"no_brim", "none", "0"}:
        width = _nonnegative_decimal(project.get("brim_width"))
        gap = _nonnegative_decimal(project.get("brim_object_gap", "0"))
        if width is None or gap is None:
            raise PlanError("Cannot verify brim clearance for scaled geometry")
        margin += width + gap
    return margin


def _as_values(value: object) -> tuple[list[object], bool]:
    return (list(value), True) if isinstance(value, list) else ([value], False)


def _is_enabled(value: object) -> bool:
    enabled_values = {"1", "true", "yes", "enabled", "on"}
    return any(str(item).strip().casefold() in enabled_values for item in _as_values(value)[0])


def _from_decimal(number: Decimal, template: object) -> object:
    if isinstance(template, str):
        return format(number.normalize(), "f")
    if isinstance(template, int) and number == number.to_integral_value():
        return int(number)
    if isinstance(template, (int, float)):
        return float(number)
    return format(number.normalize(), "f")


def _layer_height_bounds(
    target_values: dict[str, object],
) -> tuple[Decimal | None, Decimal | None]:
    # Slicing.cpp: zero machine limits select automatic bounds, not infinity.
    keys = ("min_layer_height", "max_layer_height", "nozzle_diameter")
    arrays = {key: _as_values(target_values.get(key))[0] for key in keys}
    count = max(len(values) for values in arrays.values())
    if any(len(values) not in {1, count} for values in arrays.values()):
        raise PlanError("Cannot align machine layer-height limits with nozzle diameters")
    minimums, maximums = [], []
    for index in range(count):
        raw_min, raw_max, raw_nozzle = (
            arrays[key][0 if len(arrays[key]) == 1 else index] for key in keys
        )
        lower = _nonnegative_decimal(raw_min)
        upper = _nonnegative_decimal(raw_max)
        if ((raw_min is not None and lower is None)
                or (raw_max is not None and upper is None)):
            raise PlanError("Machine layer-height limits must be finite nonnegative numbers")
        if lower is not None:
            lower = Decimal("0.07") if lower == 0 else max(Decimal("0.01"), lower)
            minimums.append(lower)
        if upper == 0:
            nozzle = _positive_decimal(raw_nozzle)
            if nozzle is None:
                raise PlanError("Automatic maximum layer height requires a valid nozzle diameter")
            upper = Decimal("0.75") * nozzle
        if upper is not None:
            maximums.append(max(lower, upper) if lower is not None else upper)
    return (max(minimums) if minimums else None, min(maximums) if maximums else None)


def _clamped_value(source: object, ceiling: object) -> tuple[object | None, str | None]:
    source_values, source_is_list = _as_values(source)
    ceiling_values, _ = _as_values(ceiling)
    if not source_values or not ceiling_values:
        return None, "empty array"
    if len(ceiling_values) == 1:
        ceiling_values *= len(source_values)
    elif len(ceiling_values) != len(source_values):
        return None, "incompatible array lengths"
    result: list[object] = []
    for source_item, ceiling_item in zip(source_values, ceiling_values, strict=True):
        source_number = _positive_decimal(source_item)
        ceiling_number = _positive_decimal(ceiling_item)
        if source_number is None or ceiling_number is None:
            return None, "non-numeric, percentage-based, or zero sentinel value"
        selected = min(source_number, ceiling_number)
        result.append(_from_decimal(selected, source_item))
    converted: object = result if source_is_list else result[0]
    return converted, None


def _archive_review(
    source: Path,
    target: ResolvedMachineTarget,
    process: ResolvedProcessTarget | None,
    filaments: tuple[ResolvedFilamentTarget, ...],
    project: dict[str, object],
    filament_slots: int,
) -> tuple[list[ArchiveAction], list[str]]:
    archive = ThreeMFArchive(source)
    inventory = archive.validate()
    plate_actions: list[ArchiveAction] = []
    blockers: list[str] = []
    embedded_members: list[tuple[str, str]] = []
    for member in inventory.members:
        basename = PurePosixPath(member.name).name
        if _SEPARATE_PROFILE_MEMBER.fullmatch(basename):
            scope = basename.split("_settings", 1)[0].casefold()
            embedded_members.append((member.name, scope))
            continue
        if not _PLATE_JSON_MEMBER.fullmatch(basename):
            continue
        try:
            value = decode_json(
                archive.read_member(member.name, max_bytes=MAX_STRUCTURED_MEMBER_BYTES)
            )
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            blockers.append(f"Cannot validate plate metadata {member.name}: {exc}")
            continue
        if not isinstance(value, dict) or "nozzle_diameter" not in value:
            continue
        old_number = _positive_decimal(value["nozzle_diameter"])
        target_number = _positive_decimal(target.target.nozzle_diameter)
        if old_number is None or target_number is None:
            blockers.append(f"Invalid nozzle_diameter in plate metadata: {member.name}")
            continue
        if abs(old_number - target_number) <= Decimal("0.0001"):
            continue
        plate_actions.append(
            ArchiveAction(
                action="REPLACE",
                source_member=member.name,
                setting_name="nozzle_diameter",
                old_value=value["nozzle_diameter"],
                new_value=float(target_number),
                confidence="SAFE",
                rationale="Plate metadata must match the explicitly selected nozzle diameter",
            )
        )

    retargeted_scopes = {"machine"}
    if process is not None:
        retargeted_scopes.add("process")
    if filaments:
        retargeted_scopes.add("filament")

    for scope in ("machine", "process"):
        if scope not in retargeted_scopes:
            continue
        count = sum(member_scope == scope for _, member_scope in embedded_members)
        if count > 1:
            blockers.append(
                f"Multiple embedded {scope} profiles are ambiguous and cannot be "
                f"reconciled automatically: {count} members"
            )
    filament_profile_count = sum(
        member_scope == "filament" for _, member_scope in embedded_members
    )
    if "filament" in retargeted_scopes and filament_profile_count > max(1, filament_slots):
        blockers.append(
            "Embedded filament profiles exceed the available source filament slots: "
            f"{filament_profile_count} profiles for {filament_slots} slots"
        )

    if not blockers:
        for member_name, scope in embedded_members:
            if scope not in retargeted_scopes:
                continue
            try:
                value = decode_json(
                    archive.read_member(
                        member_name, max_bytes=MAX_STRUCTURED_MEMBER_BYTES
                    )
                )
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                blockers.append(f"Cannot reconcile embedded profile {member_name}: {exc}")
                continue
            if not isinstance(value, dict):
                blockers.append(f"Embedded profile root is not an object: {member_name}")
                continue
            missing = sorted(
                (
                    name
                    for name in value
                    if name not in _PROFILE_METADATA_KEYS and name not in project
                ),
                key=lambda name: (name.casefold(), name),
            )
            if missing:
                blockers.append(
                    f"Embedded profile {member_name} has settings not flattened into "
                    f"project_settings.config: {', '.join(missing)}"
                )
                continue
            identity = (
                value.get(f"{scope}_settings_id")
                or value.get("name")
                or f"embedded {scope} profile"
            )
            plate_actions.append(
                ArchiveAction(
                    action="REMOVE",
                    source_member=member_name,
                    setting_name="embedded_profile",
                    old_value=identity,
                    new_value=None,
                    confidence="SAFE",
                    rationale=(
                        "Retargeted embedded preset removed after every substantive key "
                        "was confirmed flattened into authoritative project settings; "
                        "Anycubic loads project settings after registering embedded presets"
                    ),
                )
            )
    return plate_actions, blockers


def _machine_inherits_group(project: dict[str, object], parent: str) -> list[str]:
    """Mirror Anycubic's print / filament slots / printer project layout.

    PresetBundle::load_config overwrites plain `inherits` from this vector.
    Preserve other scopes; only the machine is unconditionally retargeted.
    """
    slots = project.get("filament_colour", project.get("filament_settings_id", []))
    count = len(slots) if isinstance(slots, list) else 1
    old = project.get("inherits_group", [])
    if (not isinstance(old, list) or not all(isinstance(v, str) for v in old)
            or len(old) > count + 2):
        raise PlanError("Cannot safely align inherits_group with source filament slots")
    result = old + [""] * (count + 2 - len(old))
    result[count + 1] = parent
    return result


def _explicit_settings_masks(
    project: dict[str, object],
    names: set[str],
    target_values: dict[str, object],
    parent_machine_values: dict[str, object],
    process: ResolvedProcessTarget | None,
    filaments: tuple[ResolvedFilamentTarget, ...],
) -> list[str]:
    """Protect only values that differ from the selected parent in each scope.

    Anycubic orders this vector as process, filament slots, then printer.  A key
    in a mask is treated as an intentional project override; putting the same
    superset in every slot both defeats parent refresh and makes unrelated
    machine/process G-code look like modified filament G-code.
    """
    if any(not name or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for c in name)
           for name in names):
        raise PlanError("Cannot safely encode a project setting name in the preset difference mask")
    slots = project.get("filament_colour", project.get("filament_settings_id", []))
    count = len(slots) if isinstance(slots, list) else 1
    protected = names - {"different_settings_to_system"}

    machine_keys = set(target_values) | {
        name for name in protected if _is_machine_replace_key(name)
    }
    filament_keys = {
        name for name in protected if _is_filament_translate_key(name)
    }
    for filament in filaments:
        filament_keys.update(filament.effective_values)
    process_keys = protected - machine_keys - filament_keys
    if process is not None:
        process_keys.update(set(process.effective_values) - machine_keys - filament_keys)

    def differs(value: object, parent: object) -> bool:
        # Profile vectors commonly contain one value while the flattened
        # project contains one value per filament.  Singleton vectors are the
        # same value for comparison purposes.
        if isinstance(value, list) and len(value) == 1:
            value = value[0]
        if isinstance(parent, list) and len(parent) == 1:
            parent = parent[0]
        return value != parent

    process_mask = {
        name for name in process_keys
        if name in project and (
            process is None
            or name not in process.effective_values
            or differs(project[name], process.effective_values[name])
        )
    }
    # Anycubic may initialize its installed parent with a schema filename
    # default different from the resolved JSON. Keep the project-local output
    # naming rule explicit so external-preset refresh cannot replace it and
    # immediately dirty the embedded process when flattened values are applied.
    if process is not None and "filename_format" in project:
        process_mask.add("filename_format")
    filament_masks: list[set[str]] = []
    for index in range(count):
        parent = filaments[index].effective_values if index < len(filaments) else None
        mask: set[str] = set()
        for name in filament_keys:
            if name not in project:
                continue
            value = project[name]
            if isinstance(value, list):
                if not value:
                    continue
                value = value[index] if index < len(value) else value[-1]
            if parent is None or name not in parent or differs(value, parent[name]):
                mask.add(name)
        filament_masks.append(mask)
    machine_mask = {
        name for name in machine_keys
        if name in project and (
            name not in parent_machine_values
            or differs(project[name], parent_machine_values[name])
        )
    }

    # These serialized vector fields become per-preset names while loading.
    if "print_compatible_printers" in process_mask:
        process_mask.add("compatible_printers")
    expressions = project.get("compatible_machine_expression_group")
    if isinstance(expressions, list):
        if expressions and expressions[0]:
            process_mask.add("compatible_printers_condition")
        for index, mask in enumerate(filament_masks, start=1):
            if index < len(expressions) and expressions[index]:
                mask.add("compatible_printers_condition")
        if len(expressions) > count + 1 and expressions[count + 1]:
            machine_mask.add("compatible_printers_condition")
    process_expressions = project.get("compatible_process_expression_group")
    if isinstance(process_expressions, list):
        for index, mask in enumerate(filament_masks):
            if index < len(process_expressions) and process_expressions[index]:
                mask.add("compatible_prints_condition")

    return [
        ";".join(sorted(mask))
        for mask in (process_mask, *filament_masks, machine_mask)
    ]


def _retarget_scope_vectors(project, machine_group, process, filaments):
    """Replace only selected scopes in Anycubic's serialized preset vectors."""
    count = len(machine_group) - 2
    changes = {"inherits_group": list(machine_group)}

    def vector(key, size):
        old = project.get(key, [])
        if not isinstance(old, list) or len(old) > size or not all(isinstance(v, str) for v in old):
            raise PlanError(f"Cannot safely align {key} with source filament slots")
        return old + [""] * (size - len(old))

    machine_conditions = vector("compatible_machine_expression_group", count + 2)
    process_conditions = vector("compatible_process_expression_group", count)
    # A project reference's plain inherits belongs to its machine, not process.
    if process is not None:
        option = process.process
        if option.source_kind == "reference":
            parents = process.effective_values.get("inherits_group", [])
            parent = parents[0] if isinstance(parents, list) and parents else ""
            expressions = process.effective_values.get("compatible_machine_expression_group", [])
            condition = expressions[0] if isinstance(expressions, list) and expressions else ""
        else:
            parent = option.label if option.source_kind == "official" else option.inherits or ""
            condition = process.effective_values.get("compatible_printers_condition", "")
        if not isinstance(parent, str) or not isinstance(condition, str):
            raise PlanError("Selected process has malformed inheritance/compatibility metadata")
        changes["inherits_group"][0] = parent
        machine_conditions[0] = condition
    if filaments:
        selected = filaments * count if len(filaments) == 1 else filaments
        if len(selected) != count:
            raise PlanError("Filament selection does not match project compatibility-vector slots")
        for index, item in enumerate(selected):
            option = item.filament
            parent = option.label if option.source_kind == "official" else option.inherits or ""
            condition = item.effective_values.get("compatible_printers_condition", "")
            print_condition = item.effective_values.get("compatible_prints_condition", "")
            if not all(isinstance(v, str) for v in (parent, condition, print_condition)):
                raise PlanError("Selected filament has malformed inheritance/compatibility metadata")
            changes["inherits_group"][index + 1] = parent
            machine_conditions[index + 1] = condition
            process_conditions[index] = print_condition
    if process is not None or filaments:
        changes["compatible_machine_expression_group"] = machine_conditions
    if filaments:
        changes["compatible_process_expression_group"] = process_conditions
    return changes


def build_conversion_plan(
    source_path: str | Path,
    target: ResolvedMachineTarget,
    *,
    process: ResolvedProcessTarget | None = None,
    filaments: tuple[ResolvedFilamentTarget, ...] = (),
    nozzle_hardware_type: str = "profile",
    hotend_type: str = "unspecified",
    max_nozzle_temperature: str | int | float | None = None,
    nice_supports_beta: bool = False,
    use_process_layer_height: bool = False,
    layer_height_override: str | float | None = None,
    scale_percent: str | float | None = None,
    scale_to_fit: bool = False,
    bed_type: str = "Textured PEI Plate",
    rules: RuleSet | None = None,
) -> ConversionPlan:
    source = Path(source_path).expanduser().resolve()
    project_member, project = read_project_settings(source)
    with source.open("rb") as stream:
        source_hash = hashlib.file_digest(stream, "sha256").hexdigest().upper()
    selected_rules = rules or load_rules()
    target_values = dict(target.effective_values)
    if bed_type not in SUPPORTED_BED_TYPES:
        raise PlanError(f"Unsupported bed type {bed_type!r}; choose one of {', '.join(SUPPORTED_BED_TYPES)}")
    # Anycubic refreshes its printer-side bed selector from this machine value
    # during project loading. Without it, the UI falls back to Smooth Plate.
    target_values["default_bed_type"] = BED_TYPE_ENUM_VALUES[bed_type]
    custom_height = None
    if layer_height_override is not None:
        if use_process_layer_height:
            raise PlanError("Choose either a custom layer height or the selected process height")
        if process is None:
            raise PlanError("Custom layer height requires an exact process for the other settings")
        custom_height = _positive_decimal(layer_height_override)
        if custom_height is None:
            raise PlanError("Custom layer height must be a finite positive number")
    normalized_custom_height = (
        format(custom_height.normalize(), "f") if custom_height is not None else None
    )
    requested_scale = None
    if scale_percent is not None:
        requested_scale = _positive_decimal(scale_percent)
        if requested_scale is None or requested_scale > 100:
            raise PlanError("Scale percent must be greater than 0 and at most 100")
    if scale_to_fit and requested_scale is not None:
        raise PlanError("Choose automatic scale-to-fit or an explicit scale percent, not both")
    if scale_to_fit and target_values.get("printer_model") != "Anycubic Kobra S1":
        raise PlanError("Automatic scale-to-fit requires an Anycubic Kobra S1 target")
    normalized_scale = (
        format(requested_scale.normalize(), "f")
        if requested_scale is not None else None
    )
    if use_process_layer_height and process is None:
        raise PlanError("Using the selected process layer height requires an exact process")
    effective_process_label: str | None = None
    source_layer_height = _positive_decimal(project.get("layer_height"))
    process_layer_height = (
        _positive_decimal(
            process.effective_values.get("layer_height", process.process.layer_height)
        )
        if process is not None
        else None
    )
    if process is not None:
        if normalized_custom_height is not None:
            effective_process_label = (
                f"{normalized_custom_height}mm custom height ({process.process.label} settings)"
            )
        elif (
            not use_process_layer_height
            and source_layer_height is not None
            and process_layer_height is not None
            and source_layer_height != process_layer_height
        ):
            source_height_label = format(source_layer_height.normalize(), "f")
            effective_process_label = (
                f"{source_height_label}mm source height "
                f"({process.process.label} settings)"
            )
        else:
            effective_process_label = process.process.label
        # A project-embedded process needs its own identity. Reusing a system
        # preset name makes Anycubic display the project settings as a dirty
        # system preset and risks collisions between unrelated projects.
        source_title = re.sub(r"\s+", " ", source.stem.replace("+", " ")).strip()
        source_title = source_title[:36].rstrip() or "source"
        effective_process_label = (
            f"[Optimized] {effective_process_label} - {source_title} {source_hash[:8]}"
        )
        target_values["default_print_profile"] = effective_process_label
    if filaments:
        target_values["default_filament_profile"] = [
            item.filament.label for item in filaments
        ]
    elif _same_target_s1_machine(project, target):
        # Re-optimizing a saved S1 project without filament reassignment must
        # not silently replace its PETG/other material default with the
        # machine profile's generic PLA default.
        source_default = project.get("default_filament_profile")
        if (isinstance(source_default, list) and source_default
                and all(isinstance(name, str) and name for name in source_default)):
            target_values["default_filament_profile"] = source_default
    actions: list[PlanAction] = []
    if project.get("curr_bed_type") != bed_type:
        actions.append(PlanAction(
            action="REPLACE", setting_name="curr_bed_type",
            old_value=project.get("curr_bed_type"), new_value=bed_type,
            confidence="SAFE", rationale="Set selected Anycubic build-plate type",
            setting_was_present="curr_bed_type" in project,
        ))
    warnings: list[str] = [
        f"Check Plate Type before slicing: this project requests {bed_type}, "
        "but Anycubic Slicer Next may restore its remembered plate preference "
        "on opening. Select the requested plate in the editable Plate Type "
        "dropdown if needed; exported defaults do not prove the active plate."
    ]
    raw_filament_ids = project.get("filament_settings_id")
    filament_slots = (
        len(raw_filament_ids)
        if isinstance(raw_filament_ids, list)
        else 1 if raw_filament_ids is not None else 0
    )
    archive_actions, write_blockers = _archive_review(
        source, target, process, filaments, project, filament_slots
    )
    archive = ThreeMFArchive(source)
    members = archive.validate().members
    plate_member = next((member.name for member in members
                         if PurePosixPath(member.name).name.casefold() == "model_settings.config"), None)
    model_member = next((member.name for member in members
                         if member.name.casefold() == "3d/3dmodel.model"), None)
    plate_scale_percentages: tuple[str, ...] = ()
    if (requested_scale is not None or scale_to_fit) and (plate_member is None or model_member is None):
        write_blockers.append("Scaling requires both model_settings.config and 3D/3dmodel.model")
    if plate_member is not None:
        raw_plate_settings = archive.read_member(plate_member, max_bytes=MAX_STRUCTURED_MEMBER_BYTES)
        try:
            if clear_plate_bed_types(raw_plate_settings) != raw_plate_settings:
                archive_actions.append(ArchiveAction(
                    "CLEAR_PLATE_BED_TYPE", plate_member, "bed_type", None, None,
                    "SAFE", "Use the selectable global S1 plate type; remove inaccessible per-plate overrides",
                ))
            # Single-plate projects have no grid relocation unless the user
            # explicitly requests scaling. Do not load an
            # arbitrarily large mesh XML merely to discover that fact; normal
            # model validation remains streamed and bounded elsewhere.
            plate_count = len(parse_model_settings(raw_plate_settings).findall("plate"))
            if model_member is not None and (
                plate_count >= 2 or requested_scale is not None or scale_to_fit
            ):
                skeletons = {}
                def read_skeleton(name):
                    if name not in skeletons:
                        with archive.open_member(name, max_bytes=MAX_XML_MEMBER_BYTES) as stream:
                            skeleton = model_skeleton(stream)
                        if sum(map(len, skeletons.values())) + len(skeleton) > MAX_STRUCTURED_MEMBER_BYTES:
                            raise PlanError("Combined model graph metadata exceeds structured safety limit")
                        skeletons[name] = skeleton
                    return skeletons[name]

                def read_vertices(name, object_id):
                    with archive.open_member(name, max_bytes=MAX_XML_MEMBER_BYTES) as stream:
                        yield from mesh_vertices(stream, object_id)

                raw_model = read_skeleton(model_member)
                relocations = plan_plate_relocation(
                    raw_model, raw_plate_settings, project.get("printable_area"),
                    target_values.get("printable_area"),
                    read_member=read_skeleton,
                    read_vertices=read_vertices,
                    target_grid_pitch=(
                        S1_NATIVE_GRID_PITCH
                        if target_values.get("printer_model") == "Anycubic Kobra S1"
                        and target_values.get("printable_area") ==
                        ["0x0", "250x0", "250x250", "0x250"]
                        else None
                    ),
                    scale_percent=requested_scale,
                    scale_to_fit=scale_to_fit,
                    edge_margin=(
                        _scale_edge_margin(project)
                        if requested_scale is not None or scale_to_fit else Decimal(0)
                    ),
                )
                if scale_to_fit:
                    percentages = ["100"] * plate_count
                    for change in relocations:
                        if "plate_index" in change and "scale" in change:
                            percentage = Decimal(str(change["scale"])) * 100
                            percentages[int(change["plate_index"])] = format(
                                percentage.normalize(), "f"
                            )
                    plate_scale_percentages = tuple(percentages)
                if relocations:
                    changed_dimensions = requested_scale is not None or any(
                        percent != "100" for percent in plate_scale_percentages
                    )
                    archive_actions.append(ArchiveAction(
                        "RELOCATE_PLATES", model_member, "build_item_xy", None,
                        relocations, "REVIEW" if changed_dimensions else "SAFE",
                        (
                            f"Uniformly scale all plate geometry to {normalized_scale}% and preserve each object's local placement on the S1 grid"
                            if requested_scale is not None else
                            "Automatically fit S1 plates: " + ", ".join(
                                f"plate {index + 1} {percent}%"
                                for index, percent in enumerate(plate_scale_percentages)
                            ) if scale_to_fit else
                            "Preserve each object's local position on the native S1 plate grid"
                        ),
                    ))
        except (PlanError, ValueError) as exc:
            write_blockers.append(str(exc))
    assignment_validation = validate_filament_assignments(source, filament_slots)
    if requested_scale is not None:
        warnings.append(
            f"All plates were uniformly scaled to {normalized_scale}%; physical part dimensions changed. "
            "Bed-fit audit includes the requested brim and 0.5 mm extra margin, but prime-tower, support, and purge-path clearance require native slice review"
        )
    if scale_to_fit:
        details = ", ".join(
            f"plate {index + 1}: {percent}%"
            for index, percent in enumerate(plate_scale_percentages)
        ) or "fit calculation incomplete"
        warnings.append(
            f"Automatic S1 plate fit requested ({details}). Only plates below 100% change physical dimensions. "
            "The vertex audit includes requested brim and 0.5 mm extra margin; prime-tower, support and purge-path clearance still require native slice review"
        )
    warnings.extend(assignment_validation.warnings)
    write_blockers.extend(assignment_validation.blockers)
    normalized_nozzle_hardware_type = (
        nozzle_hardware_type.strip().casefold().replace("_", "-")
    )
    allowed_nozzle_hardware_types = {
        "profile",
        "brass",
        "hardened-steel",
        "stainless-steel",
        "bimetal",
        "other",
    }
    if normalized_nozzle_hardware_type not in allowed_nozzle_hardware_types:
        raise PlanError(
            "Physical nozzle type must be one of: profile, brass, hardened-steel, "
            "stainless-steel, bimetal, other"
        )
    profile_nozzle_type = target.target.nozzle_type.strip().casefold().replace("-", "_")
    profile_hardware_type = profile_nozzle_type.replace("_", "-")
    nozzle_hardware_source = (
        "profile" if normalized_nozzle_hardware_type == "profile" else "user"
    )
    effective_nozzle_hardware_type = (
        profile_hardware_type
        if nozzle_hardware_source == "profile"
        else normalized_nozzle_hardware_type
    )
    supported_hardware_overrides = {
        "brass": "brass",
        "hardened-steel": "hardened_steel",
        "stainless-steel": "stainless_steel",
    }
    slicer_nozzle_override = supported_hardware_overrides.get(
        effective_nozzle_hardware_type
    )
    hardware_override_active = (
        nozzle_hardware_source == "user"
        and slicer_nozzle_override is not None
        and slicer_nozzle_override != profile_nozzle_type
    )
    effective_machine_label = target.target.label
    if hardware_override_active:
        effective_machine_label = (
            f"{target.target.label} ({target.target.nozzle_diameter} mm "
            f"{effective_nozzle_hardware_type} hardware override)"
        )
        target_values["nozzle_type"] = slicer_nozzle_override
        target_values["nozzle_hrc"] = "0"
        target_values["printer_settings_id"] = effective_machine_label
        warnings.append(
            f"Physical nozzle type {effective_nozzle_hardware_type!r} differs from "
            f"the selected profile declaration {profile_hardware_type!r}. The slicer "
            "nozzle type and output identity will be changed with REVIEW confidence; "
            "thermal and flow settings still come from the selected profiles and "
            "require review for this hardware"
        )
    elif nozzle_hardware_source == "user" and slicer_nozzle_override is None:
        warnings.append(
            f"Physical nozzle type {effective_nozzle_hardware_type!r} has no exact "
            "Anycubic Slicer Next nozzle enum. It is recorded in the report, while "
            f"the project keeps profile nozzle type {profile_hardware_type!r}; "
            "filament hardness compatibility cannot be confirmed from the material name"
        )
    normalized_hotend_type = hotend_type.strip().casefold().replace("_", "-")
    allowed_hotend_types = {
        "unspecified",
        "ptfe-lined",
        "all-metal",
        "aftermarket-ceramic",
        "other",
    }
    if normalized_hotend_type not in allowed_hotend_types:
        raise PlanError(
            "Hotend type must be one of: unspecified, ptfe-lined, all-metal, "
            "aftermarket-ceramic, other"
        )
    normalized_temperature_limit: str | None = None
    if max_nozzle_temperature is not None:
        parsed_limit = _positive_decimal(max_nozzle_temperature)
        if parsed_limit is None:
            raise PlanError("Hotend maximum nozzle temperature must be a positive number")
        normalized_temperature_limit = format(parsed_limit.normalize(), "f")

    required_machine_names: set[str] = set()
    if target.target.source_kind == "reference":
        required_machine_names.update({"inherits", "default_print_profile", "printer_settings_id"})
        warnings.append(
            "Machine and process tuning comes from the selected saved S1 reference; "
            "review its hardware and calibration before slicing. Source model intent is preserved."
        )
    if "nozzle_hrc" in target_values:
        required_machine_names.add("nozzle_hrc")
    if hardware_override_active:
        required_machine_names.update({"nozzle_type", "nozzle_hrc", "printer_settings_id", "inherits"})
        target_values["inherits"] = target.compatibility_parent or target.target.label
    if target.target.source_kind == "community" and target.compatibility_parent:
        required_machine_names.update(
            {"inherits", "default_filament_profile", "default_print_profile"}
        )
        warnings.append(
            f"Community machine overlay is linked to nozzle-matched official parent "
            f"{target.compatibility_parent!r} so compatible stock filament/process "
            "profiles remain discoverable"
        )
        warnings.append(
            f"The output uses community-derived machine identity {effective_machine_label!r}; "
            "install/import that profile bundle in Anycubic Slicer Next if the project "
            "opens on its official parent instead"
        )
    # These are machine-owned estimation allowances, not source model intent.
    required_machine_names.update(key for key in (
        "machine_load_filament_time", "machine_unload_filament_time", "machine_tool_change_time",
        "support_multi_bed_types", "default_bed_type",
    ) if key in target_values)
    machine_names = set(project).union(required_machine_names)
    for name in sorted(machine_names, key=lambda value: (value.casefold(), value)):
        if not _is_machine_replace_key(name):
            continue
        if name not in target_values:
            warnings.append(
                f"Verified machine setting {name!r} is present in the source but absent "
                "from the resolved target; it will remain unchanged"
            )
            continue
        old_value = project.get(name)
        new_value = target_values[name]
        if old_value == new_value:
            continue
        actions.append(
            PlanAction(
                action="REPLACE",
                setting_name=name,
                old_value=old_value,
                new_value=new_value,
                confidence=(
                    "REVIEW"
                    if hardware_override_active
                    and name in {"nozzle_type", "nozzle_hrc", "printer_settings_id"}
                    else "SAFE"
                ),
                rationale=(
                    "Explicit physical-nozzle override; no independent thermal/flow "
                    "profile was synthesized"
                    if hardware_override_active
                    and name in {"nozzle_type", "nozzle_hrc", "printer_settings_id"}
                    else "Verified machine-owned setting from the resolved target profile"
                ),
                setting_was_present=name in project,
            )
        )

    # The loader ignores plain machine `inherits` when splitting a project.
    # Official targets must point at the selectable leaf, not its internal base.
    machine_parent = (
        target.target.label if target.target.source_kind == "official"
        else target.compatibility_parent or target.target.inherits
    )
    if machine_parent:
        group = _machine_inherits_group(project, machine_parent)
        if group != project.get("inherits_group"):
            actions.append(PlanAction(
                action="TRANSLATE", setting_name="inherits_group",
                old_value=project.get("inherits_group"), new_value=group,
                confidence="SAFE",
                rationale="Set the machine parent in Anycubic's project inheritance vector; preserve other scopes",
                setting_was_present="inherits_group" in project,
            ))

    minimum_layer_height, maximum_layer_height = _layer_height_bounds(target_values)
    for name in ("layer_height", "initial_layer_print_height"):
        raw_height = (
            process.effective_values.get(name)
            if use_process_layer_height and process is not None
            else project.get(name)
        )
        if name == "layer_height" and custom_height is not None:
            raw_height = normalized_custom_height
        if raw_height is None:
            continue
        height = _positive_decimal(raw_height)
        if height is None:
            write_blockers.append(
                f"{name} is not a single positive numeric value; target layer-height "
                "limits cannot be verified"
            )
            continue
        if minimum_layer_height is not None and height < minimum_layer_height:
            write_blockers.append(
                f"{name} {format(height.normalize(), 'f')} mm is below the selected "
                f"machine minimum {format(minimum_layer_height.normalize(), 'f')} mm"
            )
        if maximum_layer_height is not None and height > maximum_layer_height:
            write_blockers.append(
                f"{name} {format(height.normalize(), 'f')} mm is above the selected "
                f"machine maximum {format(maximum_layer_height.normalize(), 'f')} mm"
            )

    if process is not None:
        if process.process.nozzle_diameter != target.target.nozzle_diameter:
            raise PlanError("Selected process nozzle does not match the machine target")
        process_values = process.effective_values
        # Output filename syntax is slicer-specific, not model print intent.
        # A Bambu template can become a dirty or invalid Anycubic process.
        if ("filename_format" in project
                and "filename_format" in process_values
                and project["filename_format"] != process_values["filename_format"]):
            actions.append(PlanAction(
                action="TRANSLATE", setting_name="filename_format",
                old_value=project["filename_format"],
                new_value=process_values["filename_format"],
                confidence="SAFE",
                rationale="Use the explicitly selected Anycubic process G-code filename syntax, including updated S1 profiles",
            ))
        nozzle_diameter = _positive_decimal(target.target.nozzle_diameter)
        nominal_line_width = _positive_decimal(process_values.get("line_width"))
        if (
            nozzle_diameter is not None
            and nominal_line_width is not None
            and nominal_line_width < nozzle_diameter
        ):
            warnings.append(
                f"Selected process nominal line width "
                f"{format(nominal_line_width.normalize(), 'f')} mm is narrower than the "
                f"{format(nozzle_diameter.normalize(), 'f')} mm nozzle. This can be a "
                "deliberate profile choice; confirm it or select a wider-line process "
                "after reviewing the values shown in the process list"
            )
        assert effective_process_label is not None
        old_process_id = project.get("print_settings_id")
        if old_process_id != effective_process_label:
            actions.append(
                PlanAction(
                    action="REPLACE",
                    setting_name="print_settings_id",
                    old_value=old_process_id,
                    new_value=effective_process_label,
                    confidence="SAFE",
                    rationale=(
                        "Truthful output process identity for the selected process settings "
                        "and effective layer-height policy"
                    ),
                    setting_was_present="print_settings_id" in project,
                )
            )

        if custom_height is not None:
            old_value = project.get("layer_height")
            new_value = _from_decimal(custom_height, old_value if old_value is not None else "")
            if old_value != new_value:
                actions.append(PlanAction(
                    action="TRANSLATE", setting_name="layer_height",
                    old_value=old_value, new_value=new_value, confidence="REVIEW",
                    rationale="User-selected custom layer height; selected process widths retained",
                    setting_was_present="layer_height" in project,
                ))
            warnings.append(
                "Custom layer height applied; source first-layer height is retained. "
                "Review object-specific and variable-layer heights in Preview."
            )
        elif use_process_layer_height:
            if process_layer_height is None:
                raise PlanError("Selected process has no usable positive layer height")
            for name in ("layer_height", "initial_layer_print_height"):
                raw_target = process_values.get(name)
                target_height = _positive_decimal(raw_target)
                if target_height is None:
                    if name == "layer_height":
                        target_height = process_layer_height
                        raw_target = process.process.layer_height
                    else:
                        continue
                old_value = project.get(name)
                template = old_value if old_value is not None else raw_target
                new_value = _from_decimal(target_height, template)
                if old_value == new_value:
                    continue
                actions.append(
                    PlanAction(
                        action="TRANSLATE",
                        setting_name=name,
                        old_value=old_value,
                        new_value=new_value,
                        confidence="REVIEW",
                        rationale=(
                            "User explicitly chose the selected process layer height; "
                            "review object-specific and variable-layer overrides in Preview"
                        ),
                        setting_was_present=name in project,
                    )
                )
            warnings.append(
                "Selected process layer height was applied. Review first-layer, "
                "object-specific and variable-layer heights in Preview before printing"
            )
        elif (
            source_layer_height is not None
            and process_layer_height is not None
            and source_layer_height != process_layer_height
        ):
            warnings.append(
                f"Source layer height {format(source_layer_height.normalize(), 'f')} mm "
                f"was preserved while importing settings from the selected "
                f"{format(process_layer_height.normalize(), 'f')} mm process; the output "
                "uses a custom truthful process label"
            )

        for name, translations in _LEGACY_PROCESS_VALUE_TRANSLATIONS.items():
            old_value = project.get(name)
            translated = translations.get(old_value) if isinstance(old_value, str) else None
            if translated is None:
                continue
            target_value = process_values.get(name)
            if target_value != translated:
                warnings.append(
                    f"Legacy process setting {name!r} cannot be translated against the "
                    "selected process; it remains unchanged"
                )
                continue
            actions.append(
                PlanAction(
                    action="TRANSLATE",
                    setting_name=name,
                    old_value=old_value,
                    new_value=translated,
                    confidence="SAFE",
                    rationale=(
                        "Legacy slicer enum translated to the equivalent Anycubic "
                        "Slicer Next value"
                    ),
                )
            )

        for name in sorted(project, key=lambda value: (value.casefold(), value)):
            if not _is_nozzle_width_key(name) or name not in process_values:
                continue
            source_width = _positive_decimal(project[name])
            target_width = _positive_decimal(process_values[name])
            if source_width is None or target_width is None:
                warnings.append(
                    f"Nozzle width setting {name!r} is not a positive numeric value in both "
                    "source and selected process; it remains unchanged"
                )
                continue
            new_value = _from_decimal(target_width, project[name])
            if new_value == project[name]:
                continue
            actions.append(
                PlanAction(
                    action="TRANSLATE",
                    setting_name=name,
                    old_value=project[name],
                    new_value=new_value,
                    confidence="SAFE",
                    rationale=(
                        "Nozzle-dependent extrusion width from the explicitly selected "
                        "compatible process profile"
                    ),
                )
            )

        for name in sorted(selected_rules.clamp, key=lambda value: (value.casefold(), value)):
            if name not in project:
                continue
            if name not in process_values:
                warnings.append(
                    f"CLAMP setting {name!r} has no value in the resolved process; "
                    "the source value remains unchanged"
                )
                continue
            new_value, reason = _clamped_value(project[name], process_values[name])
            if reason is not None:
                warnings.append(
                    f"CLAMP setting {name!r} has {reason}; it remains unchanged"
                )
                continue
            if new_value != project[name]:
                actions.append(
                    PlanAction(
                        action="CLAMP",
                        setting_name=name,
                        old_value=project[name],
                        new_value=new_value,
                        confidence="SAFE",
                        rationale="Source exceeds the selected Kobra S1 process ceiling",
                    )
                )

    if filaments:
        for filament in filaments:
            if filament.filament.nozzle_diameter != target.target.nozzle_diameter:
                raise PlanError("Selected filament nozzle does not match the machine target")
        old_ids = project.get("filament_settings_id")
        old_id_values, ids_are_list = _as_values(old_ids)
        if old_ids is None or not old_id_values:
            raise PlanError("Source has no filament_settings_id slots to retarget")
        slot_count = len(old_id_values)
        if len(filaments) == 1:
            selected_filaments = filaments * slot_count
        elif len(filaments) == slot_count:
            selected_filaments = filaments
        else:
            raise PlanError(
                f"Provide one filament profile or exactly {slot_count} ordered profiles"
            )

        source_materials, _ = _as_values(project.get("filament_type"))
        if len(source_materials) == 1 and slot_count > 1:
            source_materials *= slot_count
        if len(source_materials) == slot_count:
            for index, (source_material, selected) in enumerate(
                zip(source_materials, selected_filaments, strict=True), start=1
            ):
                if (
                    isinstance(source_material, str)
                    and source_material
                    and source_material.casefold() != selected.filament.material.casefold()
                ):
                    raise PlanError(
                        f"Filament slot {index} material mismatch: source "
                        f"{source_material!r}, target {selected.filament.material!r}"
                    )
        else:
            warnings.append(
                "Source filament_type slots cannot be aligned; selected filament "
                "identities require manual material review"
            )

        selected_ids = [item.filament.label for item in selected_filaments]
        new_ids: object = selected_ids if ids_are_list else selected_ids[0]
        if old_ids != new_ids:
            actions.append(
                PlanAction(
                    action="TRANSLATE",
                    setting_name="filament_settings_id",
                    old_value=old_ids,
                    new_value=new_ids,
                    confidence="REVIEW",
                    rationale="Exact user-selected, material-matched Anycubic filament profiles",
                )
            )

        for name in sorted(project, key=lambda value: (value.casefold(), value)):
            if not _is_filament_translate_key(name):
                continue
            new_value, reason = _translated_filament_value(
                project[name], selected_filaments, name
            )
            if reason is not None:
                warnings.append(
                    f"TRANSLATE setting {name!r} {reason}; the source value remains unchanged"
                )
                continue
            if new_value != project[name]:
                actions.append(
                    PlanAction(
                        action="TRANSLATE",
                        setting_name=name,
                        old_value=project[name],
                        new_value=new_value,
                        confidence="REVIEW",
                        rationale=(
                            "Material-owned setting from the explicitly selected, "
                            "material-matched Anycubic filament profile"
                        ),
                    )
                )

        volumetric_name = "filament_max_volumetric_speed"
        if volumetric_name in project:
            ceilings = [
                item.effective_values.get(volumetric_name) for item in selected_filaments
            ]
            ceiling_values = [
                value[0] if isinstance(value, list) and len(value) == 1 else value
                for value in ceilings
            ]
            new_value, reason = _clamped_value(project[volumetric_name], ceiling_values)
            if reason:
                warnings.append(
                    f"TRANSLATE setting {volumetric_name!r} has {reason}; it remains unchanged"
                )
            elif new_value != project[volumetric_name]:
                actions.append(
                    PlanAction(
                        action="CLAMP",
                        setting_name=volumetric_name,
                        old_value=project[volumetric_name],
                        new_value=new_value,
                        confidence="SAFE",
                        rationale="Source volumetric flow exceeds selected filament ceiling",
                    )
                )

        hardness_requirements = [item.filament.required_nozzle_hrc for item in selected_filaments]
        if all(value is not None and required_nozzle_hrc(value) is not None for value in hardness_requirements):
            new_requirements = [str(required_nozzle_hrc(value)) for value in hardness_requirements]
            old_requirements = project.get("required_nozzle_HRC")
            if new_requirements != old_requirements:
                actions.append(PlanAction(
                    action="TRANSLATE", setting_name="required_nozzle_HRC",
                    old_value=old_requirements, new_value=new_requirements,
                    confidence="REVIEW",
                    rationale="Required nozzle hardness from the selected ordered filament profiles",
                    setting_was_present="required_nozzle_HRC" in project,
                ))

        for item in selected_filaments:
            required = item.filament.required_nozzle_hrc
            explicit_hrc = (
                None if effective_nozzle_hardware_type in {"bimetal", "other"}
                else target_values.get("nozzle_hrc", project.get("nozzle_hrc"))
            )
            meets = nozzle_meets_hrc(effective_nozzle_hardware_type, required, explicit_hrc)
            if meets is True:
                continue
            required_value = required_nozzle_hrc(required)
            actual_value = nozzle_hrc_for_type(effective_nozzle_hardware_type, explicit_hrc)
            if meets is False:
                warnings.append(
                    f"Selected filament {item.filament.label!r} requires nozzle HRC "
                    f"{required_value}, but physical nozzle "
                    f"{effective_nozzle_hardware_type!r} maps to HRC {actual_value}"
                )
            else:
                warnings.append(
                    f"Selected filament {item.filament.label!r} nozzle-hardness "
                    f"requirement {required!r} cannot be verified for physical nozzle "
                    f"{effective_nozzle_hardware_type!r}"
                )

        if normalized_temperature_limit is not None:
            limit_number = Decimal(normalized_temperature_limit)
            for item in selected_filaments:
                lows, _ = _as_values(
                    item.effective_values.get("nozzle_temperature_range_low")
                )
                valid_lows = [
                    number
                    for value in lows
                    if (number := _positive_decimal(value)) is not None
                ]
                if valid_lows and limit_number < max(valid_lows):
                    write_blockers.append(
                        f"Hotend ceiling {normalized_temperature_limit} C is below the "
                        f"selected filament minimum for {item.filament.label}"
                    )

    if normalized_temperature_limit is not None:
        for name in sorted(_NOZZLE_TEMPERATURE_CEILING_KEYS):
            if name not in project:
                continue
            existing_index = next(
                (
                    index
                    for index, action in enumerate(actions)
                    if action.setting_name == name
                ),
                None,
            )
            value_before_ceiling = (
                actions[existing_index].new_value
                if existing_index is not None
                else project[name]
            )
            new_value, reason = _clamped_value(
                value_before_ceiling, normalized_temperature_limit
            )
            if reason:
                warnings.append(
                    f"Hotend ceiling could not be applied to {name!r}: {reason}"
                )
            elif existing_index is not None and new_value != value_before_ceiling:
                existing = actions[existing_index]
                actions[existing_index] = PlanAction(
                    action=existing.action,
                    setting_name=name,
                    old_value=existing.old_value,
                    new_value=new_value,
                    confidence=existing.confidence,
                    rationale=(
                        existing.rationale
                        + "; capped by the explicit user-provided hotend ceiling"
                    ),
                )
            elif existing_index is None and new_value != project[name]:
                actions.append(
                    PlanAction(
                        action="CLAMP",
                        setting_name=name,
                        old_value=project[name],
                        new_value=new_value,
                        confidence="SAFE",
                        rationale=(
                            "Source temperature exceeds the explicit user-provided "
                            "hotend ceiling"
                        ),
                    )
                )

    if process is not None:
        if normalized_hotend_type == "unspecified":
            warnings.append(
                "Hotend / heatbreak construction was not specified; no "
                "construction-specific temperature limit was inferred"
            )
        else:
            warnings.append(
                f"Hotend type {normalized_hotend_type!r} is recorded for traceability "
                "only; no temperature limit was inferred from the type"
            )
        if filaments:
            warnings.append(
                "Selected filament identities, temperatures, cooling, pressure advance, "
                "retraction, purge values, and volumetric ceilings were applied from exact "
                "material/nozzle profiles; review material-specific tuning before printing"
            )
        else:
            filament_ids = project.get("filament_settings_id")
            slot_count = len(filament_ids) if isinstance(filament_ids, list) else 1
            warnings.append(
                f"{slot_count} source filament slot(s), temperatures, cooling, retraction, "
                "and purge settings are preserved; review them in Anycubic Slicer Next"
            )
        warnings.append(
            "The output is a slicer project, not G-code; open and slice it in "
            "Anycubic Slicer Next before printing"
        )

    # Validate the proposed value after downward clamps. Keep one action per
    # key, with the original old_value, so the writer's preconditions remain
    # valid. Different tool values are not resolved by arbitrarily taking one.
    indexed_actions = {action.setting_name: index for index, action in enumerate(actions)}
    for name in sorted(SCALAR_KEYS.intersection(project)):
        if nice_supports_beta and name in NICE_SUPPORTS_BETA_SPEED_CEILINGS:
            # The beta ceiling may make otherwise different source-tool values
            # converge; validate the final result in the overlay block below.
            continue
        index = indexed_actions.get(name)
        previous = actions[index] if index is not None else None
        proposed = previous.new_value if previous else project[name]
        normalized, blocker = scalarize(name, proposed)
        if blocker:
            write_blockers.append(blocker)
        elif normalized != proposed:
            rationale = "Agreeing source-tool values mapped to Anycubic's scalar representation"
            if previous:
                actions[index] = replace(previous, new_value=normalized,
                                         rationale=previous.rationale + "; " + rationale)
            else:
                actions.append(PlanAction("TRANSLATE", name, project[name], normalized, "SAFE", rationale))
    if nice_supports_beta:
        if process is None:
            raise PlanError("Nice supports - beta requires an exact process profile")
        indexed_actions = {
            action.setting_name: index for index, action in enumerate(actions)
        }
        rationale = (
            "Opt-in Nice supports - beta overlay derived from the user-supplied "
            "Amazing_Support_Settings.3mf reference"
        )
        for name, new_value in NICE_SUPPORTS_BETA_SETTINGS.items():
            index = indexed_actions.get(name)
            action = PlanAction(
                action="TRANSLATE",
                setting_name=name,
                old_value=project.get(name),
                new_value=new_value,
                confidence="REVIEW",
                rationale=rationale,
                setting_was_present=name in project,
            )
            if index is None:
                indexed_actions[name] = len(actions)
                actions.append(action)
            else:
                previous = actions[index]
                actions[index] = replace(
                    action,
                    old_value=previous.old_value,
                    setting_was_present=previous.setting_was_present,
                )
        for name, beta_ceiling in NICE_SUPPORTS_BETA_SPEED_CEILINGS.items():
            if name not in project:
                warnings.append(
                    f"{name} is absent; Nice supports - beta did not add a speed "
                    "because the source provides no downward-clamp baseline"
                )
                continue
            ceiling: object = beta_ceiling
            process_ceiling = process.effective_values.get(name)
            if process_ceiling is not None:
                lowered, issue = _clamped_value(beta_ceiling, process_ceiling)
                if issue is None and lowered is not None:
                    ceiling = lowered
            index = indexed_actions.get(name)
            previous = actions[index] if index is not None else None
            baseline = previous.new_value if previous is not None else project[name]
            new_value, issue = _clamped_value(baseline, ceiling)
            if issue is not None or new_value is None:
                warnings.append(
                    f"Nice supports - beta could not safely clamp {name}: {issue}; "
                    "the existing conversion behavior remains"
                )
                continue
            new_value, blocker = scalarize(name, new_value)
            if blocker:
                write_blockers.append(blocker)
                continue
            action = PlanAction(
                action="CLAMP",
                setting_name=name,
                old_value=previous.old_value if previous is not None else project[name],
                new_value=new_value,
                confidence="SAFE",
                rationale=(
                    "Downward-only Nice supports - beta speed ceiling, also limited "
                    "by the selected process"
                ),
            )
            if index is None:
                indexed_actions[name] = len(actions)
                actions.append(action)
            else:
                actions[index] = action
        warnings.append(
            "Nice supports - beta is enabled: support generation and build-plate-only "
            "tree supports are intentional; inspect both plates and support interfaces "
            "in Preview before printing"
        )

    changed_names = {action.setting_name for action in actions}
    tree_wall_count = project.get("tree_support_wall_count")
    if str(tree_wall_count) == "-1" and "tree_support_wall_count" not in changed_names:
        actions.append(
            PlanAction(
                action="TRANSLATE",
                setting_name="tree_support_wall_count",
                old_value=tree_wall_count,
                new_value=_from_decimal(Decimal(0), tree_wall_count),
                confidence="SAFE",
                rationale=(
                    "Legacy Bambu automatic sentinel translated to Anycubic's documented "
                    "0=automatic value in the accepted 0..2 range"
                ),
            )
        )

    raft_expansion = project.get("raft_first_layer_expansion")
    if str(raft_expansion) == "-1" and "raft_first_layer_expansion" not in changed_names:
        raft_layers = _nonnegative_decimal(project.get("raft_layers"))
        if raft_layers == 0:
            actions.append(
                PlanAction(
                    action="TRANSLATE",
                    setting_name="raft_first_layer_expansion",
                    old_value=raft_expansion,
                    new_value=_from_decimal(Decimal(0), raft_expansion),
                    confidence="SAFE",
                    rationale=(
                        "Invalid negative Bambu sentinel normalized to Anycubic's minimum; "
                        "rafts are disabled so expansion has no generated-raft effect"
                    ),
                )
            )
        else:
            target_raft_expansion = (
                _nonnegative_decimal(
                    process.effective_values.get("raft_first_layer_expansion")
                )
                if process is not None
                else None
            )
            if raft_layers is not None and raft_layers > 0 and target_raft_expansion is not None:
                actions.append(
                    PlanAction(
                        action="TRANSLATE",
                        setting_name="raft_first_layer_expansion",
                        old_value=raft_expansion,
                        new_value=_from_decimal(target_raft_expansion, raft_expansion),
                        confidence="REVIEW",
                        rationale=(
                            "Active raft cannot use Bambu's invalid -1 sentinel; substituted "
                            "the exact selected Anycubic process value"
                        ),
                    )
                )
                warnings.append(
                    "Active raft first-layer expansion was translated from Bambu -1 to the "
                    "selected Anycubic process value; inspect raft footprint in Preview"
                )
            else:
                write_blockers.append(
                    "raft_first_layer_expansion is -1 but raft activity or a valid selected "
                    "process replacement cannot be established"
                )

    confirmed_destination_names = set(target_values)
    if process is not None:
        confirmed_destination_names.update(process.effective_values)
    for name, feature in _UNCONFIRMED_ACTIVE_FEATURES.items():
        if (
            name in project
            and name not in confirmed_destination_names
            and _is_enabled(project[name])
        ):
            warnings.append(
                f"{feature} is enabled in the source via {name!r}, but its semantics "
                "are not confirmed in the reviewed Anycubic source or selected profiles. "
                "The value is preserved; verify whether Anycubic Slicer Next applies it"
            )

    if machine_parent and (process is not None or filaments):
        scope_values = _retarget_scope_vectors(
            project, _machine_inherits_group(project, machine_parent), process, filaments,
        )
        for name, value in scope_values.items():
            actions = [item for item in actions if item.setting_name != name]
            if value != project.get(name):
                actions.append(PlanAction(
                    action="TRANSLATE", setting_name=name,
                    old_value=project.get(name), new_value=value, confidence="SAFE",
                    rationale="Replace inheritance/compatibility metadata only for explicitly selected destination scopes",
                    setting_was_present=name in project,
                ))

    if process is not None:
        # PresetBundle loads this project-only list into the process preset,
        # independently of machine inheritance. Do not retain Bambu names.
        compatible_machines = list(dict.fromkeys(
            label for label in (effective_machine_label, machine_parent) if label
        ))
        if project.get("print_compatible_printers") != compatible_machines:
            actions.append(PlanAction(
                action="TRANSLATE", setting_name="print_compatible_printers",
                old_value=project.get("print_compatible_printers"),
                new_value=compatible_machines, confidence="SAFE",
                rationale="Associate the explicitly retargeted process with the selected machine and its compatibility parent",
                setting_was_present="print_compatible_printers" in project,
            ))

    # The external preset loader refreshes any unlisted key from an installed
    # parent/system preset. Protect KEEP values as well as changed values.
    explicit_names = set(project) | {item.setting_name for item in actions}
    projected = dict(project)
    projected.update({item.setting_name: item.new_value for item in actions})
    masks = _explicit_settings_masks(
        projected, explicit_names, target_values, target.effective_values,
        process, filaments
    )
    # Re-optimizing an already-S1 project without selecting replacement
    # filaments must not turn every retained filament value into a new
    # override. In particular, doing so makes unchanged, comment-only
    # filament G-code trigger Anycubic's Modified G-code dialog.
    old_masks = project.get("different_settings_to_system")
    same_s1_machine = _same_target_s1_machine(project, target)
    if (
        not filaments and same_s1_machine
        and isinstance(old_masks, list)
        and len(old_masks) == len(masks)
        and all(isinstance(mask, str) for mask in old_masks)
    ):
        changed_filament_keys = {
            item.setting_name for item in actions
            if _is_filament_translate_key(item.setting_name)
        }
        for index in range(1, len(masks) - 1):
            retained = set(filter(None, old_masks[index].split(";")))
            if all(re.fullmatch(r"[A-Za-z0-9_]+", name) for name in retained):
                masks[index] = ";".join(sorted(retained | changed_filament_keys))
    if masks != project.get("different_settings_to_system"):
        actions.append(PlanAction(
            action="TRANSLATE", setting_name="different_settings_to_system",
            old_value=project.get("different_settings_to_system"), new_value=masks,
            confidence="SAFE",
            rationale="Preserve all explicitly written settings against Anycubic's installed-preset refresh on import",
            setting_was_present="different_settings_to_system" in project,
        ))

    override_warnings, override_blockers = audit_process_overrides(
        source, {item.setting_name for item in actions},
        minimum_layer_height, maximum_layer_height,
    )
    warnings.extend(override_warnings)
    write_blockers.extend(override_blockers)
    actions.sort(key=lambda item: (item.setting_name.casefold(), item.setting_name))
    archive_actions.sort(
        key=lambda item: (item.source_member.casefold(), item.source_member)
    )
    warnings.extend(write_blockers)
    kept = len(project) - sum(
        action.setting_was_present for action in actions
    )
    return ConversionPlan(
        source_path=str(source),
        source_sha256=source_hash,
        project_member=project_member,
        target=target,
        process=process,
        filaments=filaments,
        nozzle_hardware_type=effective_nozzle_hardware_type,
        nozzle_hardware_source=nozzle_hardware_source,
        effective_machine_label=effective_machine_label,
        hotend_type=normalized_hotend_type,
        max_nozzle_temperature=normalized_temperature_limit,
        nice_supports_beta=nice_supports_beta,
        use_process_layer_height=use_process_layer_height,
        layer_height_override=normalized_custom_height,
        scale_percent=normalized_scale,
        scale_to_fit=scale_to_fit,
        plate_scale_percentages=plate_scale_percentages,
        effective_process_label=effective_process_label,
        assignment_validation=assignment_validation,
        rules=selected_rules,
        actions=tuple(actions),
        archive_actions=tuple(archive_actions),
        kept_top_level_settings=kept,
        warnings=tuple(warnings),
        write_blockers=tuple(write_blockers),
    )


def plan_json(plan: ConversionPlan) -> str:
    return json.dumps(plan.to_dict(), indent=2, ensure_ascii=False, sort_keys=True)
