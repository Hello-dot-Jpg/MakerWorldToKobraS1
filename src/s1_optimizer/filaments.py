from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import hashlib
import os
from pathlib import Path
import re
from typing import Iterable

from .archive import ThreeMFArchive
from .constants import MAX_STRUCTURED_MEMBER_BYTES
from .errors import TargetDiscoveryError
from .parser import decode_json, inspect_archive
from .processes import machine_compatibility_labels
from .resolution import ProfileLayer, ResolvedMachineTarget


# Anycubic Slicer Next reads the same values from resources/info/nozzle_info.json.
# Keep this finite mapping aligned with the reviewed source fallback so filament
# HRC warnings compare actual thresholds instead of treating every non-zero
# requirement as "hardened steel required".
NOZZLE_HRC_BY_TYPE = {
    "hardened_steel": 55,
    "stainless_steel": 20,
    "brass": 2,
    "undefine": 0,
    "unspecified": 0,
}


def nozzle_hrc_for_type(nozzle_type: str, explicit_hrc: object = None) -> int | None:
    if explicit_hrc is not None:
        if isinstance(explicit_hrc, bool) or not isinstance(explicit_hrc, (str, int)):
            return None
        try:
            rating = int(explicit_hrc)
        except ValueError:
            return None
        if not 0 <= rating <= 500:
            return None
        if rating > 0:
            return rating
    return NOZZLE_HRC_BY_TYPE.get(nozzle_type.strip().casefold().replace("-", "_"))


def required_nozzle_hrc(value: str | None) -> int | None:
    if value is None:
        return 0
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed >= 0 else None


def nozzle_meets_hrc(
    nozzle_type: str, required: str | None, explicit_hrc: object = None,
) -> bool | None:
    required_hrc = required_nozzle_hrc(required)
    if required_hrc is None:
        return None
    if required_hrc == 0:
        return True
    actual_hrc = nozzle_hrc_for_type(nozzle_type, explicit_hrc)
    if actual_hrc is None:
        return None
    return actual_hrc != 0 and actual_hrc >= required_hrc


@dataclass(frozen=True, slots=True)
class FilamentOption:
    filament_id: str
    label: str
    material: str
    nozzle_diameter: str
    source_kind: str
    source_path: str
    source_member: str | None
    inherits: str | None
    required_nozzle_hrc: str | None
    confidence: str
    sha256: str
    reference_slot: int | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ResolvedFilamentTarget:
    filament: FilamentOption
    layers: tuple[ProfileLayer, ...]
    effective_values: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "filament": self.filament.to_dict(),
            "layers": [layer.to_dict() for layer in self.layers],
            "effective_values": self.effective_values,
        }


def default_filament_profile_dir() -> Path | None:
    candidates: list[Path] = []
    if os.environ.get("ProgramFiles"):
        candidates.append(
            Path(os.environ["ProgramFiles"])
            / "AnycubicSlicerNext/resources/profiles/Anycubic/filament"
        )
    if os.environ.get("APPDATA"):
        candidates.append(
            Path(os.environ["APPDATA"])
            / "AnycubicSlicerNext/ota/profiles/Anycubic/filament"
        )
    return next((path for path in candidates if path.is_dir()), None)


def _read_object(raw: bytes, source: str) -> dict[str, object]:
    try:
        value = decode_json(raw)
    except (UnicodeDecodeError, ValueError) as exc:
        raise TargetDiscoveryError(f"Cannot parse filament profile {source}: {exc}") from exc
    if not isinstance(value, dict):
        raise TargetDiscoveryError(f"Filament profile root is not an object: {source}")
    return value


def _string(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], str):
        return value[0]
    return ""


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-") or "filament"


def _file_layer(path: Path) -> ProfileLayer:
    if not path.is_file():
        raise TargetDiscoveryError(f"Inherited filament profile not found: {path}")
    if path.stat().st_size > MAX_STRUCTURED_MEMBER_BYTES:
        raise TargetDiscoveryError(f"Filament profile is too large: {path}")
    raw = path.read_bytes()
    values = _read_object(raw, str(path))
    label = _string(values.get("filament_settings_id")) or _string(values.get("name")) or path.stem
    return ProfileLayer(
        label=label,
        source_path=str(path.resolve()),
        source_member=None,
        sha256=hashlib.sha256(raw).hexdigest().upper(),
        values=values,
    )


def _bundle_layer(path: Path, member: str) -> ProfileLayer:
    raw = ThreeMFArchive(path).read_member(member, max_bytes=MAX_STRUCTURED_MEMBER_BYTES)
    values = _read_object(raw, f"{path}::{member}")
    label = _string(values.get("filament_settings_id")) or _string(values.get("name")) or member
    return ProfileLayer(
        label=label,
        source_path=str(path.resolve()),
        source_member=member,
        sha256=hashlib.sha256(raw).hexdigest().upper(),
        values=values,
    )


def _resolve_layers(leaf: ProfileLayer, directory: Path) -> tuple[ProfileLayer, ...]:
    result: list[ProfileLayer] = []
    seen: set[str] = set()
    current = leaf
    while True:
        identity = current.label.casefold()
        if identity in seen:
            raise TargetDiscoveryError(
                f"Filament profile inheritance cycle detected at: {current.label}"
            )
        seen.add(identity)
        result.append(current)
        inherits = _string(current.values.get("inherits"))
        if not inherits:
            break
        current = _file_layer(directory / f"{inherits}.json")
    return tuple(reversed(result))


def _effective(layers: tuple[ProfileLayer, ...]) -> dict[str, object]:
    result: dict[str, object] = {}
    for layer in layers:
        result.update(layer.values)
    return result


def _compatible(values: dict[str, object], labels: set[str]) -> bool:
    raw = values.get("compatible_printers")
    entries = [raw] if isinstance(raw, str) else raw if isinstance(raw, list) else []
    return any(isinstance(item, str) and item.casefold() in labels for item in entries)


def _option(
    leaf: ProfileLayer,
    layers: tuple[ProfileLayer, ...],
    *,
    machine: ResolvedMachineTarget,
    source_kind: str,
    identity_hash: str,
) -> FilamentOption:
    values = _effective(layers)
    material = _string(values.get("filament_type"))
    required_hrc = _string(values.get("required_nozzle_HRC")) or None
    hrc_compatible = nozzle_meets_hrc(
        machine.target.nozzle_type, required_hrc, machine.effective_values.get("nozzle_hrc")
    )
    confidence = "SAFE" if hrc_compatible is True else "REVIEW"
    return FilamentOption(
        filament_id=(
            f"{source_kind}:{identity_hash[:12].casefold()}:"
            f"{machine.target.nozzle_diameter}:{_slug(material)}:"
            f"{leaf.sha256[:8].casefold()}:{_slug(leaf.label)}"
        ),
        label=leaf.label,
        material=material,
        nozzle_diameter=machine.target.nozzle_diameter,
        source_kind=source_kind,
        source_path=leaf.source_path,
        source_member=leaf.source_member,
        inherits=_string(leaf.values.get("inherits")) or None,
        required_nozzle_hrc=required_hrc,
        confidence=confidence,
        sha256=identity_hash,
    )


def load_standalone_filament_base(path: str | Path, machine: ResolvedMachineTarget) -> ResolvedFilamentTarget:
    """Load one explicitly selected base without following external parents.

    Separate from automatic discovery and 3MF reassignment. Exact compatibility
    is required; a broad/unrestricted profile is not evidence of S1 suitability.
    """
    leaf = _file_layer(Path(path).resolve())
    values = leaf.values
    if values.get("type") != "filament" or values.get("inherits") not in (None, ""):
        raise TargetDiscoveryError("Choose a standalone filament JSON with no inherited parent")
    if not _string(values.get("filament_type")) or not _string(values.get("name")):
        raise TargetDiscoveryError("Explicit base requires a material and preset name")
    if values.get("compatible_printers") != [machine.target.label]:
        raise TargetDiscoveryError("Explicit base must target exactly the selected S1 printer/nozzle")
    if values.get("compatible_printers_condition") not in (None, ""):
        raise TargetDiscoveryError("Conditional printer compatibility is unsupported for explicit bases")
    option = _option(leaf, (leaf,), machine=machine, source_kind="explicit",
                     identity_hash=leaf.sha256)
    return ResolvedFilamentTarget(option, (leaf,), dict(values))


def discover_filaments(
    machine: ResolvedMachineTarget,
    *,
    filament_dir: str | Path | None = None,
    bundles: Iterable[str | Path] = (),
    material: str | None = None,
) -> tuple[FilamentOption, ...]:
    directory = Path(filament_dir) if filament_dir is not None else default_filament_profile_dir()
    if directory is None or not directory.is_dir():
        raise TargetDiscoveryError(
            "Anycubic filament profile directory was not found; pass --filament-dir"
        )
    directory = directory.resolve()
    labels = machine_compatibility_labels(machine)
    options: list[FilamentOption] = []
    if machine.target.source_kind == "reference":
        project = _bundle_layer(Path(machine.target.source_path), machine.target.source_member)
        ids = project.values.get("filament_settings_id")
        ids = ids if isinstance(ids, list) else [ids] if isinstance(ids, str) else []
        for slot in range(len(ids)):
            leaf = _reference_slot_layer(project, slot)
            option = _option(leaf, (leaf,), machine=machine, source_kind="reference",
                             identity_hash=machine.target.sha256)
            options.append(replace(option, reference_slot=slot,
                                   filament_id=f"{option.filament_id}:slot-{slot + 1}"))

    for path in sorted(directory.glob("*.json")):
        try:
            leaf = _file_layer(path)
            if _string(leaf.values.get("type")) not in {"", "filament"}:
                continue
            layers = _resolve_layers(leaf, directory)
        except TargetDiscoveryError:
            continue
        if not _compatible(_effective(layers), labels):
            continue
        options.append(
            _option(
                leaf,
                layers,
                machine=machine,
                source_kind="official",
                identity_hash=leaf.sha256,
            )
        )

    for bundle_value in bundles:
        bundle = Path(bundle_value).expanduser().resolve()
        inspection = inspect_archive(str(bundle))
        ThreeMFArchive(bundle).validate()
        with bundle.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest().upper()
        for variant in inspection.profile_variants:
            if variant.scope != "filament":
                continue
            leaf = _bundle_layer(bundle, variant.member)
            layers = _resolve_layers(leaf, directory)
            if not _compatible(_effective(layers), labels):
                continue
            options.append(
                _option(
                    leaf,
                    layers,
                    machine=machine,
                    source_kind="community",
                    identity_hash=digest,
                )
            )

    if material:
        normalized = material.casefold()
        options = [item for item in options if item.material.casefold() == normalized]
    by_id = {item.filament_id: item for item in options}
    return tuple(
        sorted(
            by_id.values(),
            key=lambda item: (
                item.material.casefold(),
                item.source_kind,
                item.label.casefold(),
            ),
        )
    )


def select_filament(
    filaments: Iterable[FilamentOption], filament_id: str
) -> FilamentOption:
    matches = [item for item in filaments if item.filament_id == filament_id]
    if len(matches) != 1:
        word = "Unknown" if not matches else "Ambiguous"
        raise TargetDiscoveryError(f"{word} filament profile ID: {filament_id}")
    return matches[0]


def resolve_filament_target(
    filament: FilamentOption, *, filament_dir: str | Path
) -> ResolvedFilamentTarget:
    directory = Path(filament_dir).expanduser().resolve()
    leaf = (
        _file_layer(Path(filament.source_path))
        if filament.source_member is None
        else _bundle_layer(Path(filament.source_path), filament.source_member)
    )
    if filament.source_kind == "reference":
        if filament.reference_slot is None:
            raise TargetDiscoveryError("Reference filament has no slot index")
        leaf = _reference_slot_layer(leaf, filament.reference_slot)
        layers = (leaf,)
    else:
        layers = _resolve_layers(leaf, directory)
    return ResolvedFilamentTarget(filament, layers, _effective(layers))


def _reference_slot_layer(project: ProfileLayer, slot: int) -> ProfileLayer:
    # Import at call time: the planner imports filament resolution, and owns
    # the finite translation allowlist used to select material-owned fields.
    from .plan import _is_filament_translate_key

    ids = project.values.get("filament_settings_id")
    ids = ids if isinstance(ids, list) else [ids] if isinstance(ids, str) else []
    if not 0 <= slot < len(ids):
        raise TargetDiscoveryError("Reference filament slot is out of range")
    values = {}
    for key, raw in project.values.items():
        if not (_is_filament_translate_key(key) or key in {
            "filament_type", "filament_settings_id", "filament_max_volumetric_speed",
            "required_nozzle_HRC",
        }):
            continue
        entries = raw if isinstance(raw, list) else [raw]
        if len(entries) != len(ids):
            raise TargetDiscoveryError(
                f"Reference filament field {key!r} has {len(entries)} values for "
                f"{len(ids)} slots; save aligned filament settings before using it"
            )
        values[key] = [entries[slot]]
    # Project-level vectors use process / filaments / machine ordering, unlike
    # ordinary per-filament arrays. Never copy the plain machine `inherits`.
    for source_key, destination_key, offset, size in (
        ("inherits_group", "inherits", 1, len(ids) + 2),
        ("compatible_machine_expression_group", "compatible_printers_condition", 1, len(ids) + 2),
        ("compatible_process_expression_group", "compatible_prints_condition", 0, len(ids)),
    ):
        entries = project.values.get(source_key, [])
        if (not isinstance(entries, list) or len(entries) > size
                or not all(isinstance(entry, str) for entry in entries)):
            raise TargetDiscoveryError(f"Reference {source_key!r} is malformed or exceeds its slot count")
        index = slot + offset
        values[destination_key] = entries[index] if index < len(entries) else ""
    if not _string(values.get("filament_type")):
        raise TargetDiscoveryError(f"Reference slot {slot + 1} has no filament material")
    label = f"{ids[slot]} (reference slot {slot + 1})"
    values["filament_settings_id"] = [label]
    return replace(project, label=label, values=values)
