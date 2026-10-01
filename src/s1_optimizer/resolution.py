from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path

from .archive import ThreeMFArchive
from .constants import MAX_STRUCTURED_MEMBER_BYTES
from .errors import TargetDiscoveryError
from .parser import decode_json
from .targets import TargetOption


@dataclass(frozen=True, slots=True)
class ProfileLayer:
    label: str
    source_path: str
    source_member: str | None
    sha256: str
    values: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "label": self.label,
            "source_path": self.source_path,
            "source_member": self.source_member,
            "sha256": self.sha256,
            "values": self.values,
        }


@dataclass(frozen=True, slots=True)
class ResolvedMachineTarget:
    target: TargetOption
    layers: tuple[ProfileLayer, ...]
    effective_values: dict[str, object]
    declared_parent: str | None
    compatibility_parent: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "target": self.target.to_dict(),
            "layers": [layer.to_dict() for layer in self.layers],
            "effective_values": self.effective_values,
            "declared_parent": self.declared_parent,
            "compatibility_parent": self.compatibility_parent,
        }


def _object(raw: bytes, source: str) -> dict[str, object]:
    value = decode_json(raw)
    if not isinstance(value, dict):
        raise TargetDiscoveryError(f"Profile root must be a JSON object: {source}")
    return value


def _file_layer(path: Path) -> ProfileLayer:
    if not path.is_file():
        raise TargetDiscoveryError(f"Machine profile does not exist: {path}")
    size = path.stat().st_size
    if size > MAX_STRUCTURED_MEMBER_BYTES:
        raise TargetDiscoveryError(
            f"Machine profile exceeds {MAX_STRUCTURED_MEMBER_BYTES} byte limit: {path}"
        )
    raw = path.read_bytes()
    values = _object(raw, str(path))
    label = values.get("printer_settings_id") or values.get("name") or path.stem
    return ProfileLayer(
        label=str(label),
        source_path=str(path.resolve()),
        source_member=None,
        sha256=hashlib.sha256(raw).hexdigest().upper(),
        values=values,
    )


def _bundle_layer(target: TargetOption) -> ProfileLayer:
    if target.source_member is None:
        raise TargetDiscoveryError("Community target is missing its archive member")
    archive = ThreeMFArchive(target.source_path)
    raw = archive.read_member(
        target.source_member, max_bytes=MAX_STRUCTURED_MEMBER_BYTES
    )
    values = _object(raw, f"{target.source_path}::{target.source_member}")
    if target.source_kind == "reference":
        values["inherits"] = target.inherits
    label = values.get("printer_settings_id") or values.get("name") or target.label
    return ProfileLayer(
        label=str(label),
        source_path=target.source_path,
        source_member=target.source_member,
        sha256=target.sha256,
        values=values,
    )


def _official_path(machine_dir: Path, profile_name: str) -> Path:
    path = machine_dir / f"{profile_name}.json"
    if not path.is_file():
        raise TargetDiscoveryError(
            f"Inherited machine profile was not found: {profile_name!r} in {machine_dir}"
        )
    return path


def resolve_machine_target(
    target: TargetOption, *, machine_dir: str | Path
) -> ResolvedMachineTarget:
    directory = Path(machine_dir).expanduser().resolve()
    if target.source_kind == "official":
        leaf = _file_layer(Path(target.source_path))
    elif target.source_kind in {"community", "reference"}:
        leaf = _bundle_layer(target)
    else:
        raise TargetDiscoveryError(f"Unsupported target source kind: {target.source_kind}")

    declared_parent = (
        leaf.values.get("inherits")
        if isinstance(leaf.values.get("inherits"), str)
        and leaf.values.get("inherits")
        else None
    )
    compatibility_parent = declared_parent
    first_parent: ProfileLayer | None = None
    if target.source_kind == "community" and declared_parent:
        declared_layer = _file_layer(_official_path(directory, declared_parent))
        model = declared_layer.values.get("printer_model")
        if isinstance(model, str) and model:
            matched_name = f"{model} {target.nozzle_diameter} nozzle"
            matched_path = directory / f"{matched_name}.json"
            if matched_path.is_file():
                matched_layer = _file_layer(matched_path)
                matched_nozzle = matched_layer.values.get("nozzle_diameter")
                if isinstance(matched_nozzle, list) and len(matched_nozzle) == 1:
                    matched_nozzle = matched_nozzle[0]
                if str(matched_nozzle) == target.nozzle_diameter:
                    first_parent = matched_layer
                    compatibility_parent = matched_layer.label

    leaf_to_root: list[ProfileLayer] = []
    seen: set[str] = set()
    current = leaf
    while True:
        identity = current.label.casefold()
        if identity in seen:
            raise TargetDiscoveryError(
                f"Machine profile inheritance cycle detected at: {current.label}"
            )
        seen.add(identity)
        leaf_to_root.append(current)
        inherits = current.values.get("inherits")
        if not isinstance(inherits, str) or not inherits:
            break
        if current is leaf and first_parent is not None:
            current = first_parent
        else:
            current = _file_layer(_official_path(directory, inherits))

    layers = tuple(reversed(leaf_to_root))
    effective: dict[str, object] = {}
    for layer in layers:
        effective.update(layer.values)
    if target.source_kind == "community" and compatibility_parent:
        # The project remains named after the selected community overlay, but
        # Anycubic can now identify its nozzle-matched official parent.
        effective["inherits"] = compatibility_parent
    return ResolvedMachineTarget(
        target,
        layers,
        effective,
        declared_parent,
        compatibility_parent,
    )
