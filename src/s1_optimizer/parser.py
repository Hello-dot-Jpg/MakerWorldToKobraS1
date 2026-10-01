from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from io import BytesIO
import json
from pathlib import PurePosixPath
import re
from typing import Any
import xml.etree.ElementTree as ET

from .archive import ArchiveInventory, ThreeMFArchive
from .constants import (
    CONFIG_SUFFIXES,
    JSON_SUFFIXES,
    MAX_STRUCTURED_MEMBER_BYTES,
    MAX_XML_MEMBER_BYTES,
    PROJECT_SETTINGS_BASENAME,
    ROOT_RELATIONSHIPS_MEMBER,
    XML_SUFFIXES,
)
from .errors import ArchiveValidationError
from .settings import JsonValue, Setting, flatten_json


_SEPARATE_SETTINGS_CONFIG = re.compile(
    r"(machine|process|filament)_settings(?:_\d+)?\.config",
    re.IGNORECASE,
)
_PROFILE_ID_NAMES = {
    "printer": frozenset(("printer_settings_id", "name")),
    "process": frozenset(("print_settings_id", "name")),
    "filament": frozenset(("filament_settings_id", "name")),
}
_PROJECT_ACTIVE_ID_NAMES = {
    "printer": frozenset(("printer_settings_id",)),
    "process": frozenset(("print_settings_id",)),
    "filament": frozenset(("filament_settings_id",)),
}
_NON_CONFLICT_PROFILE_METADATA_NAMES = frozenset(("inherits", "name", "version"))


@dataclass(frozen=True, slots=True)
class StructuredMember:
    name: str
    detected_type: str
    parse_status: str
    message: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SettingConflict:
    name: str
    occurrences: tuple[Setting, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "occurrences": [setting.to_dict() for setting in self.occurrences],
        }


@dataclass(frozen=True, slots=True)
class ProfileVariant:
    member: str
    scope: str
    identifiers: tuple[str, ...]
    selection: str

    def to_dict(self) -> dict[str, object]:
        return {
            "member": self.member,
            "scope": self.scope,
            "identifiers": list(self.identifiers),
            "selection": self.selection,
        }


@dataclass(frozen=True, slots=True)
class XmlMemberSummary:
    name: str
    root_element: str
    element_counts: dict[str, int]

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "root_element": self.root_element,
            "element_counts": self.element_counts,
        }


@dataclass(frozen=True, slots=True)
class Inspection:
    inventory: ArchiveInventory
    structured_members: tuple[StructuredMember, ...]
    xml_summaries: tuple[XmlMemberSummary, ...]
    core_validation_issues: tuple[str, ...]
    settings: tuple[Setting, ...]
    warnings: tuple[str, ...]

    @property
    def profile_variants(self) -> tuple[ProfileVariant, ...]:
        by_member: dict[str, list[Setting]] = defaultdict(list)
        active_ids: dict[str, set[str]] = defaultdict(set)
        for setting in self.settings:
            basename = PurePosixPath(setting.source_member).name
            if _SEPARATE_SETTINGS_CONFIG.fullmatch(basename):
                by_member[setting.source_member].append(setting)
            elif setting.scope == "project" and isinstance(setting.value, str):
                for scope, names in _PROJECT_ACTIVE_ID_NAMES.items():
                    if setting.name in names:
                        active_ids[scope].add(setting.value)

        records: list[tuple[str, str, tuple[str, ...]]] = []
        members_by_scope: dict[str, list[str]] = defaultdict(list)
        for member, settings in by_member.items():
            scope = settings[0].scope
            id_names = _PROFILE_ID_NAMES.get(scope, frozenset(("name",)))
            identifiers = tuple(
                sorted(
                    {
                        setting.value
                        for setting in settings
                        if setting.name in id_names and isinstance(setting.value, str)
                    },
                    key=lambda value: (value.casefold(), value),
                )
            )
            records.append((member, scope, identifiers))
            members_by_scope[scope].append(member)

        result: list[ProfileVariant] = []
        for member, scope, identifiers in records:
            matched = bool(set(identifiers) & active_ids[scope])
            any_match = any(
                bool(set(other_ids) & active_ids[scope])
                for _, other_scope, other_ids in records
                if other_scope == scope
            )
            if matched:
                selection = "selected"
            elif any_match or len(members_by_scope[scope]) > 1:
                selection = "alternative"
            else:
                selection = "unresolved"
            result.append(ProfileVariant(member, scope, identifiers, selection))
        return tuple(
            sorted(result, key=lambda item: (item.scope, item.member.casefold(), item.member))
        )

    @property
    def setting_conflicts(self) -> tuple[SettingConflict, ...]:
        variants = self.profile_variants
        ignored_members = {
            variant.member
            for variant in variants
            if variant.selection == "alternative"
        }
        selected_counts = Counter(
            variant.scope for variant in variants if variant.selection == "selected"
        )
        # Several selected filament/profile members represent distinct slots,
        # not competing values for one setting. Until slot correspondence is
        # modelled, leave them visible as variants without calling them
        # cross-file contradictions.
        ignored_members.update(
            variant.member
            for variant in variants
            if variant.selection == "selected" and selected_counts[variant.scope] > 1
        )
        grouped: dict[str, list[Setting]] = defaultdict(list)
        for setting in self.settings:
            if setting.source_member in ignored_members:
                continue
            if setting.name in _NON_CONFLICT_PROFILE_METADATA_NAMES:
                continue
            grouped[setting.name].append(setting)

        conflicts: list[SettingConflict] = []
        for name, occurrences in grouped.items():
            source_members = {setting.source_member for setting in occurrences}
            typed_values = {
                (
                    setting.value_type,
                    json.dumps(
                        setting.value,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                )
                for setting in occurrences
            }
            if len(source_members) > 1 and len(typed_values) > 1:
                conflicts.append(SettingConflict(name, tuple(occurrences)))
        return tuple(sorted(conflicts, key=lambda item: (item.name.casefold(), item.name)))

    @property
    def structure_counts(self) -> dict[str, int]:
        counts = {
            "resource_objects": 0,
            "mesh_objects": 0,
            "build_items": 0,
            "model_settings_objects": 0,
            "model_settings_parts": 0,
            "model_instances": 0,
            "plates": 0,
            "assembly_items": 0,
        }
        for summary in self.xml_summaries:
            if summary.name.endswith(".model"):
                counts["resource_objects"] += summary.element_counts.get("object", 0)
                counts["mesh_objects"] += summary.element_counts.get("mesh", 0)
                counts["build_items"] += summary.element_counts.get("item", 0)
            elif PurePosixPath(summary.name).name.casefold() == "model_settings.config":
                counts["model_settings_objects"] += summary.element_counts.get("object", 0)
                counts["model_settings_parts"] += summary.element_counts.get("part", 0)
                counts["model_instances"] += summary.element_counts.get("model_instance", 0)
                counts["plates"] += summary.element_counts.get("plate", 0)
                counts["assembly_items"] += summary.element_counts.get("assemble_item", 0)
        return counts

    @property
    def is_valid_3mf(self) -> bool:
        names = {member.name for member in self.inventory.members}
        has_content_types = "[Content_Types].xml" in names
        has_root_relationships = ROOT_RELATIONSHIPS_MEMBER in names
        has_model = any(name.endswith(".model") for name in names)
        unvalidated_core_xml = any(
            item.parse_status != "valid"
            and (
                item.name == "[Content_Types].xml"
                or item.name == ROOT_RELATIONSHIPS_MEMBER
                or item.name.endswith(".model")
            )
            for item in self.structured_members
        )
        duplicate_core_xml = any(
            name == "[Content_Types].xml"
            or name == ROOT_RELATIONSHIPS_MEMBER
            or name.endswith(".model")
            for name in self.inventory.duplicate_names
        )
        return (
            has_content_types
            and has_root_relationships
            and has_model
            and not unvalidated_core_xml
            and not duplicate_core_xml
            and not self.core_validation_issues
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "validation": {
                "zip": "valid",
                "three_mf": "valid" if self.is_valid_3mf else "invalid_or_incomplete",
                "core_issues": list(self.core_validation_issues),
            },
            "inventory": self.inventory.to_dict(),
            "structured_members": [item.to_dict() for item in self.structured_members],
            "xml_summaries": [summary.to_dict() for summary in self.xml_summaries],
            "structure_counts": self.structure_counts,
            "settings": [setting.to_dict() for setting in self.settings],
            "profile_variants": [item.to_dict() for item in self.profile_variants],
            "setting_conflicts": [conflict.to_dict() for conflict in self.setting_conflicts],
            "warnings": list(self.warnings),
        }


def detect_member_type(name: str) -> str | None:
    lower = name.casefold()
    if lower.endswith(JSON_SUFFIXES):
        return "json"
    if lower.endswith(XML_SUFFIXES):
        return "xml"
    if lower.endswith(CONFIG_SUFFIXES):
        return "config"
    return None


class DuplicateJsonKeyError(ValueError):
    """Raised rather than silently discarding a duplicate JSON object key."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJsonKeyError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def decode_json(raw: bytes) -> JsonValue:
    text = raw.decode("utf-8-sig")
    value: Any = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    return value


_LEGACY_SLIC3R_SETTINGS_BASENAME = "slic3r_pe.config"
_LEGACY_SETTING_LINE = re.compile(r"^\s*;\s*([A-Za-z0-9_]+)\s*=\s?(.*)$")


def _is_settings_config(name: str) -> bool:
    basename = PurePosixPath(name).name
    return (
        basename.casefold() == PROJECT_SETTINGS_BASENAME.casefold()
        or _SEPARATE_SETTINGS_CONFIG.fullmatch(basename) is not None
    )


def _is_legacy_slic3r_settings(name: str) -> bool:
    return PurePosixPath(name).name.casefold() == _LEGACY_SLIC3R_SETTINGS_BASENAME


def _decode_legacy_slic3r(raw: bytes) -> dict[str, str]:
    """Parse comment-prefixed Slic3r config snapshots without guessing types.

    Legacy 3MF exports store one ``; key = value`` setting per physical line.
    Values remain strings because commas, semicolons, percentages, quoted
    expressions, and escaped G-code all have setting-specific semantics.
    """
    result: dict[str, str] = {}
    for line in raw.decode("utf-8-sig").splitlines():
        match = _LEGACY_SETTING_LINE.match(line)
        if match is None:
            continue
        key, value = match.groups()
        if key in result:
            raise DuplicateJsonKeyError(f"duplicate legacy config key: {key!r}")
        result[key] = value
    return result


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _count_xml_elements(stream: Any) -> tuple[str, dict[str, int]]:
    counts: Counter[str] = Counter()
    root_element = ""
    for event, element in ET.iterparse(stream, events=("start", "end")):
        local_name = _local_name(element.tag)
        if event == "start" and not root_element:
            root_element = local_name
        elif event == "end":
            counts[local_name] += 1
            element.clear()
    return root_element, dict(
        sorted(counts.items(), key=lambda item: (item[0].casefold(), item[0]))
    )


def _validate_core_semantics(
    archive: ThreeMFArchive,
    inventory: ArchiveInventory,
    xml_summaries: list[XmlMemberSummary],
) -> tuple[str, ...]:
    issues: list[str] = []
    names = {member.name for member in inventory.members}
    summaries = {summary.name: summary for summary in xml_summaries}

    content_summary = summaries.get("[Content_Types].xml")
    if content_summary is not None and content_summary.root_element != "Types":
        issues.append("[Content_Types].xml root element is not Types")
    if content_summary is not None:
        try:
            root = ET.fromstring(
                archive.read_member(
                    "[Content_Types].xml", max_bytes=MAX_STRUCTURED_MEMBER_BYTES
                )
            )
            declares_model = any(
                (
                    _local_name(element.tag) == "Default"
                    and element.attrib.get("Extension", "").casefold() == "model"
                    and "3dmanufacturing-3dmodel"
                    in element.attrib.get("ContentType", "").casefold()
                )
                or (
                    _local_name(element.tag) == "Override"
                    and element.attrib.get("PartName", "").endswith(".model")
                    and "3dmanufacturing-3dmodel"
                    in element.attrib.get("ContentType", "").casefold()
                )
                for element in root
            )
            if not declares_model:
                issues.append("[Content_Types].xml does not declare a 3D model content type")
        except ArchiveValidationError:
            pass

    relationship_summary = summaries.get(ROOT_RELATIONSHIPS_MEMBER)
    if relationship_summary is not None and relationship_summary.root_element != "Relationships":
        issues.append(f"{ROOT_RELATIONSHIPS_MEMBER} root element is not Relationships")
    if relationship_summary is not None:
        try:
            root = ET.fromstring(
                archive.read_member(
                    ROOT_RELATIONSHIPS_MEMBER, max_bytes=MAX_STRUCTURED_MEMBER_BYTES
                )
            )
            model_targets = [
                element.attrib.get("Target", "").replace("\\", "/").lstrip("/")
                for element in root
                if _local_name(element.tag) == "Relationship"
                and element.attrib.get("Type", "").casefold().endswith("/3dmodel")
            ]
            if not model_targets:
                issues.append(f"{ROOT_RELATIONSHIPS_MEMBER} has no 3D model relationship")
            elif not any(target in names for target in model_targets):
                issues.append(
                    f"{ROOT_RELATIONSHIPS_MEMBER} 3D model target is missing from the archive"
                )
        except ArchiveValidationError:
            pass

    for name in sorted(
        (name for name in names if name.endswith(".model")),
        key=lambda value: (value.casefold(), value),
    ):
        summary = summaries.get(name)
        if summary is not None and summary.root_element != "model":
            issues.append(f"{name} root element is not model")
    return tuple(issues)


def inspect_archive(path: str) -> Inspection:
    archive = ThreeMFArchive(path)
    inventory = archive.validate()
    structured: list[StructuredMember] = []
    xml_summaries: list[XmlMemberSummary] = []
    settings: list[Setting] = []
    warnings = list(inventory.warnings)

    for member in inventory.members:
        detected = detect_member_type(member.name)
        if detected is None:
            continue
        if member.name in inventory.duplicate_names:
            structured.append(
                StructuredMember(member.name, detected, "skipped", "duplicate member name")
            )
            continue
        inspection_limit = (
            MAX_XML_MEMBER_BYTES if detected == "xml" else MAX_STRUCTURED_MEMBER_BYTES
        )
        if member.size > inspection_limit:
            message = f"member exceeds {inspection_limit} byte inspection limit"
            structured.append(StructuredMember(member.name, detected, "skipped", message))
            warnings.append(f"{member.name}: {message}")
            continue

        try:
            is_settings_config = _is_settings_config(member.name)
            is_legacy_slic3r = _is_legacy_slic3r_settings(member.name)
            if detected == "xml":
                with archive.open_member(member.name, max_bytes=MAX_XML_MEMBER_BYTES) as stream:
                    root_element, element_counts = _count_xml_elements(stream)
                xml_summaries.append(
                    XmlMemberSummary(member.name, root_element, element_counts)
                )
                structured.append(StructuredMember(member.name, detected, "valid"))
                continue

            raw = archive.read_member(member.name, max_bytes=MAX_STRUCTURED_MEMBER_BYTES)
            if detected == "json" or is_settings_config:
                parsed = decode_json(raw)
                parsed_type = "json" if detected == "json" else "json-config"
                structured.append(StructuredMember(member.name, parsed_type, "parsed"))
                if is_settings_config:
                    settings.extend(flatten_json(parsed, member.name))
            elif is_legacy_slic3r:
                parsed = _decode_legacy_slic3r(raw)
                structured.append(
                    StructuredMember(member.name, "legacy-slic3r-config", "parsed")
                )
                settings.extend(flatten_json(parsed, member.name))
            else:
                # Unknown .config formats are detected but not guessed. A JSON
                # config is still recognized for discovery purposes.
                stripped = raw.lstrip(b"\xef\xbb\xbf \t\r\n")
                if stripped.startswith((b"{", b"[")):
                    decode_json(raw)
                    structured.append(StructuredMember(member.name, "json-config", "valid"))
                elif stripped.startswith(b"<"):
                    if PurePosixPath(member.name).name.casefold() == "model_settings.config":
                        from .model_xml import parse_model_settings
                        root = parse_model_settings(raw)
                        root_element = _local_name(root.tag)
                        element_counts = dict(Counter(_local_name(item.tag) for item in root.iter()))
                    else:
                        root_element, element_counts = _count_xml_elements(BytesIO(raw))
                    xml_summaries.append(
                        XmlMemberSummary(member.name, root_element, element_counts)
                    )
                    structured.append(StructuredMember(member.name, "xml-config", "valid"))
                else:
                    structured.append(StructuredMember(member.name, detected, "unparsed"))
        except (
            ArchiveValidationError,
            DuplicateJsonKeyError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            ET.ParseError,
        ) as exc:
            message = str(exc)
            structured.append(StructuredMember(member.name, detected, "invalid", message))
            warnings.append(f"{member.name}: {message}")

    sorted_settings = tuple(
        sorted(
            settings,
            key=lambda setting: (
                setting.name.casefold(),
                setting.name,
                setting.identity.casefold(),
                setting.identity,
            ),
        )
    )
    sorted_structured = tuple(
        sorted(structured, key=lambda item: (item.name.casefold(), item.name))
    )
    core_validation_issues = _validate_core_semantics(
        archive,
        inventory,
        xml_summaries,
    )
    warnings.extend(core_validation_issues)
    provisional = Inspection(
        inventory=inventory,
        structured_members=sorted_structured,
        xml_summaries=tuple(
            sorted(xml_summaries, key=lambda item: (item.name.casefold(), item.name))
        ),
        core_validation_issues=core_validation_issues,
        settings=sorted_settings,
        warnings=tuple(warnings),
    )
    high_risk_names = {
        "gcode_flavor",
        "nozzle_diameter",
        "printer_model",
        "printer_settings_id",
    }
    for conflict in provisional.setting_conflicts:
        if conflict.name in high_risk_names:
            locations = ", ".join(
                sorted(
                    {setting.source_member for setting in conflict.occurrences},
                    key=lambda value: (value.casefold(), value),
                )
            )
            warnings.append(
                f"Conflicting high-risk setting {conflict.name!r} across: {locations}"
            )
    return Inspection(
        inventory=inventory,
        structured_members=sorted_structured,
        xml_summaries=provisional.xml_summaries,
        core_validation_issues=core_validation_issues,
        settings=sorted_settings,
        warnings=tuple(warnings),
    )
