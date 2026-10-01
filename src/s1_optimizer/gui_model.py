from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from pathlib import Path
import re
from typing import TYPE_CHECKING, Iterable

from .errors import PlanError
from .plan import read_project_settings

if TYPE_CHECKING:
    from .filaments import FilamentOption
    from .processes import ProcessOption
    from .targets import TargetOption


SUPPORTED_NOZZLES = ("0.25", "0.4", "0.6", "0.8")


@dataclass(frozen=True, slots=True)
class SourceFilamentSlot:
    index: int
    profile_id: str
    material: str


@dataclass(frozen=True, slots=True)
class SourceSummary:
    path: str
    printer: str
    process: str
    nozzle_diameter: str
    nozzle_type: str
    layer_height: str
    initial_layer_height: str
    line_width: str
    wall_loops: str
    infill_density: str
    infill_pattern: str
    support_enabled: str
    support_type: str
    bed_type: str
    filament_slots: tuple[SourceFilamentSlot, ...]


def _values(value: object) -> list[object]:
    return list(value) if isinstance(value, list) else [value]


def _first_text(value: object) -> str:
    if isinstance(value, list):
        value = value[0] if value else ""
    return value if isinstance(value, str) else str(value) if value is not None else ""


def _decimal(value: object) -> Decimal | None:
    try:
        number = Decimal(_first_text(value))
    except (InvalidOperation, ValueError):
        return None
    return number if number > 0 else None


def _normalized_words(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def _profile_stem(value: str) -> str:
    return _normalized_words(value.split("@", 1)[0])


def closest_supported_nozzle(
    source_nozzle: str, supported: Iterable[str] = SUPPORTED_NOZZLES,
) -> str:
    choices = tuple(supported)
    if not choices:
        raise ValueError("At least one supported nozzle is required")
    source = _decimal(source_nozzle)
    parsed = [(choice, _decimal(choice)) for choice in choices]
    valid = [(choice, value) for choice, value in parsed if value is not None]
    if source is None or not valid:
        return "0.4" if "0.4" in choices else choices[0]
    return min(valid, key=lambda item: (abs(item[1] - source), item[1]))[0]


def suggest_target(
    summary: SourceSummary, targets: Iterable["TargetOption"],
) -> "TargetOption | None":
    options = tuple(targets)
    if not options:
        return None
    source_nozzle = _decimal(summary.nozzle_diameter)
    source_type = summary.nozzle_type.casefold().replace("-", "_")
    kind_priority = {"official": 0, "community": 1, "reference": 2}

    def score(item: "TargetOption") -> tuple[object, ...]:
        diameter = _decimal(item.nozzle_diameter)
        distance = (
            abs(diameter - source_nozzle)
            if diameter is not None and source_nozzle is not None
            else Decimal("999")
        )
        target_type = item.nozzle_type.casefold().replace("-", "_")
        type_mismatch = 0 if source_type and target_type == source_type else 1
        return (
            distance,
            type_mismatch,
            kind_priority.get(item.source_kind, 9),
            item.label.casefold(),
            item.target_id,
        )

    return min(options, key=score)


def suggest_process(
    summary: SourceSummary, processes: Iterable["ProcessOption"],
) -> "ProcessOption | None":
    options = tuple(processes)
    if not options:
        return None
    source_height = _decimal(summary.layer_height)
    source_width = _decimal(summary.line_width)
    source_label = _normalized_words(summary.process)
    source_is_standard = "standard" in source_label
    kind_priority = {"official": 0, "community": 1, "reference": 2}

    def score(item: "ProcessOption") -> tuple[object, ...]:
        height = _decimal(item.layer_height)
        width = _decimal(item.line_width)
        height_distance = (
            abs(height - source_height)
            if height is not None and source_height is not None
            else Decimal("999")
        )
        width_distance = (
            abs(width - source_width)
            if width is not None and source_width is not None
            else Decimal("999") if source_width is not None else Decimal("0")
        )
        label = _normalized_words(item.label)
        standard_mismatch = 0 if source_is_standard == ("standard" in label) else 1
        similarity = SequenceMatcher(None, source_label, label).ratio() if source_label else 0
        return (
            height_distance,
            width_distance,
            standard_mismatch,
            -similarity,
            kind_priority.get(item.source_kind, 9),
            item.label.casefold(),
            item.process_id,
        )

    return min(options, key=score)


def suggest_filament(
    slot: SourceFilamentSlot, filaments: Iterable["FilamentOption"],
) -> "FilamentOption | None":
    options = tuple(filaments)
    if not options:
        return None
    source_stem = _profile_stem(slot.profile_id)
    source_label = _normalized_words(slot.profile_id)
    kind_priority = {"official": 0, "community": 1, "reference": 2}

    def score(item: "FilamentOption") -> tuple[object, ...]:
        stem = _profile_stem(item.label)
        label = _normalized_words(item.label)
        stem_mismatch = 0 if source_stem and stem == source_stem else 1
        similarity = SequenceMatcher(None, source_label, label).ratio() if source_label else 0
        return (
            stem_mismatch,
            -similarity,
            kind_priority.get(item.source_kind, 9),
            item.label.casefold(),
            item.filament_id,
        )

    return min(options, key=score)


def summarize_source(path: str | Path) -> SourceSummary:
    source = Path(path).expanduser().resolve()
    _, project = read_project_settings(source)
    raw_ids = project.get("filament_settings_id")
    if raw_ids is None:
        raise PlanError("Source has no filament_settings_id")
    ids = _values(raw_ids)
    materials = _values(project.get("filament_type", ""))
    if len(materials) == 1 and len(ids) > 1:
        materials *= len(ids)
    if len(materials) != len(ids):
        raise PlanError(
            "Source filament_settings_id and filament_type slot counts do not align"
        )
    slots = tuple(
        SourceFilamentSlot(
            index=index,
            profile_id=value if isinstance(value, str) else str(value),
            material=material if isinstance(material, str) else str(material),
        )
        for index, (value, material) in enumerate(
            zip(ids, materials, strict=True), start=1
        )
    )
    nozzle = project.get("nozzle_diameter", "")
    if isinstance(nozzle, list) and nozzle:
        nozzle = nozzle[0]
    return SourceSummary(
        path=str(source),
        printer=str(project.get("printer_settings_id") or project.get("printer_model") or ""),
        process=str(project.get("print_settings_id") or project.get("default_print_profile") or ""),
        nozzle_diameter=str(nozzle),
        nozzle_type=_first_text(project.get("nozzle_type")),
        layer_height=_first_text(project.get("layer_height")),
        initial_layer_height=_first_text(project.get("initial_layer_print_height")),
        line_width=_first_text(project.get("line_width")),
        wall_loops=_first_text(project.get("wall_loops")),
        infill_density=_first_text(project.get("sparse_infill_density")),
        infill_pattern=_first_text(project.get("sparse_infill_pattern")),
        support_enabled=_first_text(project.get("enable_support")),
        support_type=_first_text(project.get("support_type")),
        bed_type=_first_text(project.get("curr_bed_type")),
        filament_slots=slots,
    )
