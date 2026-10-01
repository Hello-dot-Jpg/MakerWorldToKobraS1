from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
import xml.etree.ElementTree as ET

from .archive import ThreeMFArchive
from .constants import MAX_STRUCTURED_MEMBER_BYTES, MAX_XML_MEMBER_BYTES
from .model_xml import parse_model_settings


@dataclass(frozen=True, slots=True)
class AssignmentValidation:
    filament_slots: int
    model_settings_members: tuple[str, ...]
    assignments_checked: int
    assignments_used: tuple[int, ...]
    warnings: tuple[str, ...]
    blockers: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def audit_variable_heights(
    raw: bytes,
    minimum: Decimal | None,
    maximum: Decimal | None,
    object_extents: dict[int, tuple[Decimal, ...]] | None = None,
):
    """Inspect BBS object_id=N|z;height;... profiles without altering them."""
    warnings, blockers, seen = [], [], set()
    try:
        lines = raw.decode("utf-8-sig").splitlines()
    except UnicodeDecodeError:
        return [], ["Variable-layer profile is not UTF-8 text"]
    for number, line in enumerate(lines, 1):
        try:
            header, values = line.split("|")
            key, identity = header.split("=")
            object_id = int(identity)
            if key != "object_id" or object_id < 1 or object_id in seen:
                raise ValueError("invalid or duplicate object id")
            seen.add(object_id)
            profile = [Decimal(value) for value in values.split(";")]
            if len(profile) <= 4 or len(profile) % 2 or not all(v.is_finite() for v in profile):
                raise ValueError("expected at least three finite z/height pairs")
            positions, heights = profile[::2], profile[1::2]
            if any(z < 0 for z in positions) or any(a > b for a, b in zip(positions, positions[1:])):
                raise ValueError("z positions must be nonnegative and nondecreasing")
            if min(heights) <= 0:
                raise ValueError("layer heights must be positive")
            lower, upper = min(heights), max(heights)
            detail = f"Variable-layer object {object_id}: {len(heights)} points, heights {lower}..{upper} mm"
            if ((minimum is not None and lower < minimum)
                    or (maximum is not None and upper > maximum)):
                blockers.append(detail + "; outside selected machine bounds; profile was not flattened or clamped")
            else:
                warnings.append(detail + "; retained unchanged, review in Preview")
            if object_extents is not None:
                extents = object_extents.get(object_id, ())
                if not extents:
                    blockers.append(
                        detail + "; object id has no matching mesh resource in the 3MF"
                    )
                elif len(extents) != 1:
                    blockers.append(
                        detail + "; object id matches multiple mesh resources with ambiguous extents"
                    )
                else:
                    endpoint, extent = positions[-1], extents[0]
                    tolerance = Decimal("0.001")
                    if endpoint > extent + tolerance:
                        blockers.append(
                            detail + f"; profile endpoint {endpoint} mm exceeds mesh Z extent "
                            f"{extent} mm"
                        )
                    else:
                        allowed_gap = maximum if maximum is not None else upper
                        gap = extent - endpoint
                        if gap > allowed_gap + tolerance:
                            warnings.append(
                                detail + f"; profile endpoint {endpoint} mm ends {gap} mm "
                                "below the mesh Z extent; retained for native Preview review"
                            )
                        else:
                            warnings.append(
                                detail + f"; object linkage and mesh Z extent {extent} mm verified"
                            )
        except (ValueError, InvalidOperation) as error:
            blockers.append(f"Invalid variable-layer profile at line {number}: {error}")
    return warnings, blockers


def _mesh_extents_by_object_id(archive: ThreeMFArchive) -> dict[int, tuple[Decimal, ...]]:
    """Collect direct-mesh Z extents keyed by package object id."""
    found: dict[int, list[Decimal]] = {}
    for member in archive.validate().members:
        if not member.name.casefold().endswith(".model"):
            continue
        try:
            with archive.open_member(member.name, max_bytes=MAX_XML_MEMBER_BYTES) as stream:
                current_id: int | None = None
                minimum_z: Decimal | None = None
                maximum_z: Decimal | None = None
                for event, element in ET.iterparse(stream, events=("start", "end")):
                    tag = _local_name(element.tag)
                    if event == "start" and tag == "object":
                        current_id = int(element.get("id", ""))
                        minimum_z = maximum_z = None
                    elif event == "start" and tag == "vertex" and current_id is not None:
                        z_value = Decimal(element.get("z", ""))
                        if not z_value.is_finite():
                            raise ValueError("non-finite mesh vertex")
                        minimum_z = z_value if minimum_z is None else min(minimum_z, z_value)
                        maximum_z = z_value if maximum_z is None else max(maximum_z, z_value)
                    elif event == "end" and tag == "object":
                        if current_id is not None and current_id > 0 and minimum_z is not None:
                            found.setdefault(current_id, []).append(maximum_z - minimum_z)
                        current_id = None
                        minimum_z = maximum_z = None
                    if event == "end":
                        element.clear()
        except (ET.ParseError, UnicodeDecodeError, ValueError, InvalidOperation):
            continue
    return {object_id: tuple(extents) for object_id, extents in found.items()}


def audit_process_overrides(
    source_path: str | Path, changed_settings: set[str],
    minimum_height: Decimal | None, maximum_height: Decimal | None,
) -> tuple[list[str], list[str]]:
    archive = ThreeMFArchive(source_path)
    warnings, blockers = [], []
    object_extents: dict[int, tuple[Decimal, ...]] | None = None
    for member in archive.validate().members:
        basename = PurePosixPath(member.name).name.casefold()
        if "layer_height" in basename and basename != "model_settings.config":
            warnings.append(f"Variable-layer data retained in {member.name}; review its heights for the selected nozzle")
            if basename == "layer_heights_profile.txt":
                if object_extents is None:
                    object_extents = _mesh_extents_by_object_id(archive)
                variable_warnings, variable_blockers = audit_variable_heights(
                    archive.read_member(member.name, max_bytes=MAX_STRUCTURED_MEMBER_BYTES),
                    minimum_height, maximum_height, object_extents,
                )
                warnings.extend(variable_warnings)
                blockers.extend(variable_blockers)
        if basename != "model_settings.config":
            continue
        try:
            root = parse_model_settings(archive.read_member(member.name, max_bytes=MAX_STRUCTURED_MEMBER_BYTES))
        except (ET.ParseError, UnicodeDecodeError, ValueError):
            # Assignment validation already reports this as a write blocker.
            continue
        def visit(element, location):
            tag = _local_name(element.tag)
            if tag in {"object", "part", "plate", "volume", "layer_range"}:
                location = f"{location}/{tag}[{element.get('id', '?')}]"
            if tag == "metadata":
                key, value = element.get("key", ""), element.get("value", "")
                if key in changed_settings:
                    warnings.append(
                        f"Preserved local override {location}: {key}={value!r}; "
                        "it may take precedence over the converted project setting"
                    )
                if key in {"layer_height", "initial_layer_print_height"}:
                    try:
                        height = Decimal(value)
                        valid = height.is_finite() and height > 0
                    except InvalidOperation:
                        valid = False
                    if not valid:
                        blockers.append(f"Invalid local {key}={value!r} at {location}")
                    elif ((minimum_height is not None and height < minimum_height)
                          or (maximum_height is not None and height > maximum_height)):
                        blockers.append(f"Local {key}={value!r} at {location} exceeds selected machine layer-height bounds")
            for child in element:
                visit(child, location)
        visit(root, member.name)
    return sorted(set(warnings)), sorted(set(blockers))


def validate_filament_assignments(
    source_path: str | Path, filament_slots: int
) -> AssignmentValidation:
    archive = ThreeMFArchive(Path(source_path).expanduser().resolve())
    inventory = archive.validate()
    members = tuple(
        member.name
        for member in inventory.members
        if PurePosixPath(member.name).name.casefold() == "model_settings.config"
    )
    warnings: list[str] = []
    blockers: list[str] = []
    assignments: list[int] = []

    if not members:
        warnings.append(
            "No model_settings.config was found; explicit object/part extruder "
            "assignments could not be validated"
        )

    for member in members:
        try:
            root = parse_model_settings(
                archive.read_member(member, max_bytes=MAX_STRUCTURED_MEMBER_BYTES)
            )
        except (ET.ParseError, UnicodeDecodeError, ValueError) as exc:
            blockers.append(f"Cannot validate filament assignments in {member}: {exc}")
            continue
        parents = {child: parent for parent in root.iter() for child in parent}
        for element in root.iter():
            if _local_name(element.tag).casefold() != "metadata":
                continue
            if element.attrib.get("key", "").casefold() != "extruder":
                continue
            raw_value = element.attrib.get("value")
            try:
                value = int(raw_value) if raw_value is not None else 0
            except ValueError:
                blockers.append(
                    f"Non-integer extruder assignment {raw_value!r} in {member}"
                )
                continue
            if value == 0:
                owner = parents.get(element)
                owner_tag = _local_name(owner.tag) if owner is not None else ""
                if owner_tag in {"object", "part"}:
                    inherited = 1
                    ancestor = parents.get(owner) if owner_tag == "part" else None
                    while ancestor is not None:
                        if _local_name(ancestor.tag) == "object":
                            for child in ancestor:
                                if child.get("key", "").casefold() == "extruder":
                                    try:
                                        inherited = int(child.get("value", "0")) or 1
                                    except ValueError:
                                        inherited = -1
                            break
                        ancestor = parents.get(ancestor)
                    value = inherited
                    warnings.append(
                        f"Zero {owner_tag} extruder in {member} uses inherited/default slot {value}; source metadata is preserved"
                    )
            assignments.append(value)
            if value < 1 or value > filament_slots:
                blockers.append(
                    f"Extruder assignment {value} in {member} is outside the "
                    f"available filament slots 1..{filament_slots}"
                )

    return AssignmentValidation(
        filament_slots=filament_slots,
        model_settings_members=members,
        assignments_checked=len(assignments),
        assignments_used=tuple(sorted(set(assignments))),
        warnings=tuple(warnings),
        blockers=tuple(blockers),
    )
