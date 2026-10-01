"""Bounded, read-only adapter for local Prusa/SuperSlicer filament INI files.

This module intentionally handles only material-owned scalar settings.  It does
not discover installed profiles, fetch parents, or interpret g-code/calibration
fields.
"""
from __future__ import annotations

from configparser import ConfigParser, Error as ConfigError
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re

from .constants import MAX_STRUCTURED_MEMBER_BYTES
from .errors import PlanError


@dataclass(frozen=True)
class IniPreset:
    path: Path
    section: str | None = None

    def __post_init__(self):
        object.__setattr__(self, "path", Path(self.path))

    @property
    def name(self):
        return self.section.split(":", 1)[1] if self.section and self.section.casefold().startswith("filament:") else self.path.stem

    @property
    def stem(self):
        return self.name

    def __str__(self):
        return f"{self.path}::{self.section}" if self.section else str(self.path)


# Deliberately finite: an unknown setting remains auditable but is not made
# portable by accident.  Bed temperatures are mapped to the destination's
# textured plate keys and are called out as review translations in provenance.
_MAPPING = {
    "temperature": "nozzle_temperature",
    "first_layer_temperature": "nozzle_temperature_initial_layer",
    "bed_temperature": "textured_plate_temp",
    "first_layer_bed_temperature": "textured_plate_temp_initial_layer",
    "filament_type": "filament_type",
    "filament_vendor": "filament_vendor",
    "filament_density": "filament_density",
    "filament_diameter": "filament_diameter",
    "filament_cost": "filament_cost",
    "filament_max_volumetric_speed": "filament_max_volumetric_speed",
}
_NUMERIC = {key for key in _MAPPING if key not in {"filament_type", "filament_vendor"}}
_SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*$")


def _read(path: Path) -> tuple[bytes, ConfigParser, bool]:
    path = Path(path).resolve()
    if path.suffix.lower() not in {".ini", ".config"}:
        raise PlanError("Select a standalone filament INI file")
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise PlanError(f"Cannot read INI source: {exc}") from exc
    if size > MAX_STRUCTURED_MEMBER_BYTES:
        raise PlanError("INI source exceeds the structured-member size limit")
    try:
        # Read one byte beyond the limit so a growing/racy file cannot bypass
        # the bound based on a prior stat result.
        with path.open("rb") as stream:
            raw = stream.read(MAX_STRUCTURED_MEMBER_BYTES + 1)
        if len(raw) > MAX_STRUCTURED_MEMBER_BYTES:
            raise PlanError("INI source exceeds the structured-member size limit")
        text = raw.decode("utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        raise PlanError(f"Invalid UTF-8 INI source: {exc}") from exc
    has_sections = any(_SECTION_RE.match(line) for line in text.splitlines())
    parser = ConfigParser(interpolation=None, strict=True, delimiters=("=", ":"),
                          inline_comment_prefixes=None, empty_lines_in_values=False)
    parser.optionxform = str  # Prusa keys are case-sensitive for audit purposes.
    try:
        parser.read_string(text if has_sections else "[__standalone__]\n" + text)
    except ConfigError as exc:
        raise PlanError(f"Invalid filament INI source: {exc}") from exc
    return raw, parser, has_sections


def list_ini_presets(path):
    """List selectable local filament sections (or the one standalone export)."""
    _, parser, has_sections = _read(Path(path))
    sections = [s for s in parser.sections() if s.casefold().startswith("filament:")
                and not (s.split(":", 1)[1].startswith("*") and s.endswith("*"))]
    if sections:
        return tuple(IniPreset(Path(path).resolve(), section) for section in sections)
    if has_sections:
        return tuple()
    return (IniPreset(Path(path).resolve(), None),)


def _section_name(parent: str, sections: list[str]) -> str | None:
    candidates = [parent] if parent in sections else [s for s in sections if s.casefold() == ("filament:" + parent).casefold()]
    if len(candidates) > 1:
        raise PlanError(f"Ambiguous local INI parent: {parent}")
    return candidates[0] if candidates else None


def read_ini_source(source: IniPreset | Path):
    """Return flattened translated values and provenance for a local INI source."""
    if isinstance(source, IniPreset):
        requested = source.section
        path = source.path
    else:
        requested = None
        path = Path(source)
    raw, parser, has_sections = _read(path)
    sections = [s for s in parser.sections() if s.casefold().startswith("filament:")]
    if requested is None:
        if len(sections) > 1:
            raise PlanError("INI contains multiple filament sections; select IniPreset(path, section)")
        section = sections[0] if sections else ("__standalone__" if not has_sections else None)
        if section is None:
            raise PlanError("INI has no selectable filament section")
    else:
        section = requested
        if not section.casefold().startswith("filament:"):
            raise PlanError("INI selection must name a filament section")
        if section not in parser.sections():
            raise PlanError(f"Missing INI filament section: {section}")
    local_sections = [s for s in parser.sections() if s.casefold().startswith("filament:")]

    def flatten(name, seen=()):
        if name in seen or len(seen) >= 32:
            raise PlanError("INI filament inheritance cycle or depth limit")
        values = {}
        own = dict(parser.items(name, raw=True))
        parent_raw = own.get("inherits", "").strip()
        if parent_raw:
            if ";" in parent_raw or "," in parent_raw:
                raise PlanError("INI filament inherits must name exactly one local parent")
            parent = _section_name(parent_raw, local_sections)
            if parent is None:
                raise PlanError(f"Missing local INI parent: {parent_raw}")
            values.update(flatten(parent, (*seen, name)))
        values.update(own)
        return values

    values = flatten(section)
    translated = {}
    destinations = {}
    decisions = []
    for key, value in values.items():
        if key == "inherits":
            continue
        # Mapping is case-sensitive by design; a differently-cased unknown key
        # must remain visible rather than silently becoming a portable setting.
        destination = _MAPPING.get(key)
        if destination is None:
            destination = "ini_unmapped_" + re.sub(r"[^A-Za-z0-9_.-]", "_", key)
            if destination in destinations:
                raise PlanError(f"INI keys collide after unmapped normalization: {destinations[destination]!r}, {key!r}")
            destinations[destination] = key
            translated[destination] = value
            decisions.append({"source": key, "destination": destination, "action": "PRESERVE_UNMAPPED"})
            continue
        if key in _NUMERIC:
            if ";" in value:
                raise PlanError(f"INI numeric setting {key} contains multi-extruder values")
            try:
                number = Decimal(value.strip())
                if not number.is_finite() or number < 0:
                    raise ValueError
            except (InvalidOperation, ValueError) as exc:
                raise PlanError(f"Invalid numeric INI setting {key}: {value!r}") from exc
        if destination in destinations:
            raise PlanError(f"INI keys collide at translated destination: {destinations[destination]!r}, {key!r}")
        destinations[destination] = key
        translated[destination] = value.strip()
        review = key in {"bed_temperature", "first_layer_bed_temperature"}
        decisions.append({"source": key, "destination": destination,
                          "action": "TRANSLATE", "review": review})
    mapping_hash = hashlib.sha256(json.dumps(decisions, sort_keys=True).encode()).hexdigest()
    provenance = [{"file": str(Path(path).resolve()), "section": section,
                   "sha256": hashlib.sha256(raw).hexdigest(),
                   "mapping_sha256": mapping_hash, "mappings": decisions}]
    # Primary local destination-key evidence (AnycubicSlicerNext profile
    # resources): common material keys at lines 60, 96, 99, 132 in
    # .research/AnycubicSlicerNext/resources/profiles/Anycubic/filament/fdm_filament_common.json.
    translated.setdefault("type", "filament")
    translated["name"] = (section.split(":", 1)[1] if section.casefold().startswith("filament:") else Path(path).stem)
    return translated, provenance
