from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import os
from pathlib import Path
import re
from typing import Iterable

from .archive import ThreeMFArchive
from .constants import MAX_STRUCTURED_MEMBER_BYTES
from .errors import TargetDiscoveryError
from .parser import decode_json, inspect_archive
from .resolution import ProfileLayer, ResolvedMachineTarget


@dataclass(frozen=True, slots=True)
class ProcessOption:
    process_id: str
    label: str
    nozzle_diameter: str
    layer_height: str | None
    source_kind: str
    source_path: str
    source_member: str | None
    inherits: str | None
    association_basis: str
    sha256: str
    line_width: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ResolvedProcessTarget:
    process: ProcessOption
    layers: tuple[ProfileLayer, ...]
    effective_values: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "process": self.process.to_dict(),
            "layers": [layer.to_dict() for layer in self.layers],
            "effective_values": self.effective_values,
        }


def default_process_profile_dir() -> Path | None:
    # Slicer-managed system profiles can be updated independently of the
    # application bundle. Resolve against the same active definitions rather
    # than embedding stale bundled values under a current system identity.
    app_data = os.environ.get("APPDATA")
    if app_data:
        path = Path(app_data) / "AnycubicSlicerNext" / "system" / "Anycubic" / "process"
        if path.is_dir():
            return path
    program_files = os.environ.get("ProgramFiles")
    if program_files:
        path = (
            Path(program_files)
            / "AnycubicSlicerNext"
            / "resources"
            / "profiles"
            / "Anycubic"
            / "process"
        )
        if path.is_dir():
            return path
    app_data = os.environ.get("APPDATA")
    if app_data:
        path = (
            Path(app_data)
            / "AnycubicSlicerNext"
            / "ota"
            / "profiles"
            / "Anycubic"
            / "process"
        )
        if path.is_dir():
            return path
    return None


def _read_object(raw: bytes, source: str) -> dict[str, object]:
    try:
        value = decode_json(raw)
    except (UnicodeDecodeError, ValueError) as exc:
        raise TargetDiscoveryError(f"Cannot parse process profile {source}: {exc}") from exc
    if not isinstance(value, dict):
        raise TargetDiscoveryError(f"Process profile root is not an object: {source}")
    return value


def _string(data: dict[str, object], key: str) -> str:
    value = data.get(key)
    return value if isinstance(value, str) else ""


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-") or "process"


def _file_layer(path: Path) -> ProfileLayer:
    if not path.is_file():
        raise TargetDiscoveryError(f"Inherited process profile not found: {path}")
    if path.stat().st_size > MAX_STRUCTURED_MEMBER_BYTES:
        raise TargetDiscoveryError(f"Process profile is too large: {path}")
    raw = path.read_bytes()
    values = _read_object(raw, str(path))
    label = _string(values, "print_settings_id") or _string(values, "name") or path.stem
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
    label = _string(values, "print_settings_id") or _string(values, "name") or member
    return ProfileLayer(
        label=label,
        source_path=str(path.resolve()),
        source_member=member,
        sha256=hashlib.sha256(raw).hexdigest().upper(),
        values=values,
    )


def _resolve_layers(leaf: ProfileLayer, process_dir: Path) -> tuple[ProfileLayer, ...]:
    leaf_to_root: list[ProfileLayer] = []
    current = leaf
    seen: set[str] = set()
    while True:
        identity = current.label.casefold()
        if identity in seen:
            raise TargetDiscoveryError(
                f"Process profile inheritance cycle detected at: {current.label}"
            )
        seen.add(identity)
        leaf_to_root.append(current)
        inherits = _string(current.values, "inherits")
        if not inherits:
            break
        current = _file_layer(process_dir / f"{inherits}.json")
    return tuple(reversed(leaf_to_root))


def _effective(layers: tuple[ProfileLayer, ...]) -> dict[str, object]:
    values: dict[str, object] = {}
    for layer in layers:
        values.update(layer.values)
    return values


def _compatible_printers(values: dict[str, object]) -> tuple[str, ...]:
    raw = values.get("compatible_printers")
    if isinstance(raw, str):
        return (raw,)
    if isinstance(raw, list) and all(isinstance(item, str) for item in raw):
        return tuple(raw)
    return ()


def _decimal(value: object) -> Decimal | None:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return number if number > 0 else None


def _normalized_decimal(value: object) -> str | None:
    number = _decimal(value)
    return format(number.normalize(), "f") if number is not None else None


def machine_compatibility_labels(machine: ResolvedMachineTarget) -> set[str]:
    result = {machine.target.label.casefold()}
    target_nozzle = _normalized_decimal(machine.target.nozzle_diameter)
    for layer in machine.layers:
        layer_nozzle = layer.values.get("nozzle_diameter")
        if isinstance(layer_nozzle, list) and len(layer_nozzle) == 1:
            layer_nozzle = layer_nozzle[0]
        normalized = _normalized_decimal(layer_nozzle)
        if normalized is None or normalized == target_nozzle:
            result.add(layer.label.casefold())
    model = _string(machine.effective_values, "printer_model")
    if model and target_nozzle:
        result.add(f"{model} {target_nozzle} nozzle".casefold())
    return result


def _option(
    *,
    leaf: ProfileLayer,
    layers: tuple[ProfileLayer, ...],
    nozzle: str,
    source_kind: str,
    association_basis: str,
    bundle_digest: str | None = None,
) -> ProcessOption:
    values = _effective(layers)
    label = _string(leaf.values, "print_settings_id") or leaf.label
    identity_hash = bundle_digest or leaf.sha256
    return ProcessOption(
        process_id=(
            f"{source_kind}:{identity_hash[:12].casefold()}:{nozzle}:"
            f"{leaf.sha256[:8].casefold()}:{_slug(label)}"
        ),
        label=label,
        nozzle_diameter=nozzle,
        layer_height=_normalized_decimal(values.get("layer_height")),
        source_kind=source_kind,
        source_path=leaf.source_path,
        source_member=leaf.source_member,
        inherits=_string(leaf.values, "inherits") or None,
        association_basis=association_basis,
        sha256=identity_hash,
        line_width=_normalized_decimal(values.get("line_width")),
    )


def discover_processes(
    machine: ResolvedMachineTarget,
    *,
    process_dir: str | Path | None = None,
    bundles: Iterable[str | Path] = (),
) -> tuple[ProcessOption, ...]:
    directory = Path(process_dir) if process_dir is not None else default_process_profile_dir()
    if directory is None or not directory.is_dir():
        raise TargetDiscoveryError(
            "Anycubic process profile directory was not found; pass --process-dir"
        )
    directory = directory.resolve()
    nozzle = machine.target.nozzle_diameter
    labels = machine_compatibility_labels(machine)
    options: list[ProcessOption] = []
    if machine.target.source_kind == "reference":
        leaf = _bundle_layer(Path(machine.target.source_path), machine.target.source_member)
        options.append(_option(
            leaf=leaf, layers=(leaf,), nozzle=nozzle, source_kind="reference",
            association_basis="selected_reference_project", bundle_digest=machine.target.sha256,
        ))

    for path in sorted(directory.glob("*.json")):
        try:
            leaf = _file_layer(path)
            if _string(leaf.values, "type") not in {"", "process"}:
                continue
            layers = _resolve_layers(leaf, directory)
        except TargetDiscoveryError:
            continue
        compatible = _compatible_printers(_effective(layers))
        if not compatible or not any(item.casefold() in labels for item in compatible):
            continue
        options.append(
            _option(
                leaf=leaf,
                layers=layers,
                nozzle=nozzle,
                source_kind="official",
                association_basis="compatible_printers",
            )
        )

    target_nozzle = Decimal(nozzle)
    for bundle_value in bundles:
        bundle = Path(bundle_value).expanduser().resolve()
        inspection = inspect_archive(str(bundle))
        archive = ThreeMFArchive(bundle)
        archive.validate()
        with bundle.open("rb") as stream:
            bundle_digest = hashlib.file_digest(stream, "sha256").hexdigest().upper()
        printer_variants = [v for v in inspection.profile_variants if v.scope == "printer"]
        same_target_bundle = Path(machine.target.source_path) == bundle
        for variant in inspection.profile_variants:
            if variant.scope != "process":
                continue
            leaf = _bundle_layer(bundle, variant.member)
            layers = _resolve_layers(leaf, directory)
            values = _effective(layers)
            compatible = _compatible_printers(values)
            basis: str | None = None
            if compatible and any(item.casefold() in labels for item in compatible):
                basis = "compatible_printers"
            elif len(printer_variants) == 1 and same_target_bundle:
                basis = "single_machine_bundle"
            else:
                width = _decimal(leaf.values.get("line_width"))
                if width is not None and abs(width - target_nozzle) <= Decimal("0.05"):
                    basis = "explicit_line_width"
            if basis is None:
                continue
            options.append(
                _option(
                    leaf=leaf,
                    layers=layers,
                    nozzle=nozzle,
                    source_kind="community",
                    association_basis=basis,
                    bundle_digest=bundle_digest,
                )
            )

    by_id = {option.process_id: option for option in options}
    return tuple(
        sorted(
            by_id.values(),
            key=lambda item: (
                Decimal(item.layer_height or "999"),
                item.source_kind,
                item.label.casefold(),
            ),
        )
    )


def select_process(
    processes: Iterable[ProcessOption], process_id: str
) -> ProcessOption:
    matches = [item for item in processes if item.process_id == process_id]
    if len(matches) != 1:
        word = "Unknown" if not matches else "Ambiguous"
        raise TargetDiscoveryError(f"{word} process profile ID: {process_id}")
    return matches[0]


def resolve_process_target(
    process: ProcessOption, *, process_dir: str | Path
) -> ResolvedProcessTarget:
    directory = Path(process_dir).expanduser().resolve()
    if process.source_member is None:
        leaf = _file_layer(Path(process.source_path))
    else:
        leaf = _bundle_layer(Path(process.source_path), process.source_member)
    layers = (leaf,) if process.source_kind == "reference" else _resolve_layers(leaf, directory)
    return ResolvedProcessTarget(process, layers, _effective(layers))
