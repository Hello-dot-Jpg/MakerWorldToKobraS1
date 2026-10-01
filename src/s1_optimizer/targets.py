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
from .profile import inspect_profile


_OFFICIAL_S1_PROFILE = re.compile(
    r"^Anycubic Kobra S1 (?P<diameter>\d+(?:\.\d+)?) nozzle\.json$"
)


@dataclass(frozen=True, slots=True)
class TargetOption:
    target_id: str
    label: str
    nozzle_diameter: str
    nozzle_type: str
    source_kind: str
    source_path: str
    source_member: str | None
    inherits: str | None
    sha256: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _normalized_diameter(value: object) -> str:
    if isinstance(value, list) and len(value) == 1:
        value = value[0]
    if not isinstance(value, (str, int, float)):
        raise TargetDiscoveryError(f"Invalid nozzle diameter: {value!r}")
    try:
        number = Decimal(str(value))
    except InvalidOperation as exc:
        raise TargetDiscoveryError(f"Invalid nozzle diameter: {value!r}") from exc
    if number <= 0:
        raise TargetDiscoveryError(f"Invalid nozzle diameter: {value!r}")
    return format(number.normalize(), "f")


def default_machine_profile_dir() -> Path | None:
    program_files = os.environ.get("ProgramFiles")
    if program_files:
        bundled = (
            Path(program_files)
            / "AnycubicSlicerNext"
            / "resources"
            / "profiles"
            / "Anycubic"
            / "machine"
        )
        if bundled.is_dir():
            return bundled
    app_data = os.environ.get("APPDATA")
    if app_data:
        ota = (
            Path(app_data)
            / "AnycubicSlicerNext"
            / "ota"
            / "profiles"
            / "Anycubic"
            / "machine"
        )
        if ota.is_dir():
            return ota
    return None


def _read_object(raw: bytes, source: str) -> dict[str, object]:
    value = decode_json(raw)
    if not isinstance(value, dict):
        raise TargetDiscoveryError(f"Profile root must be a JSON object: {source}")
    return value


def _string(data: dict[str, object], key: str, default: str = "") -> str:
    value = data.get(key, default)
    return value if isinstance(value, str) else default


def _slug(value: str) -> str:
    result = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return result or "profile"


def _official_options(
    machine_dir: Path,
) -> tuple[list[TargetOption], dict[str, dict[str, object]]]:
    if not machine_dir.is_dir():
        raise TargetDiscoveryError(f"Machine profile directory does not exist: {machine_dir}")
    options: list[TargetOption] = []
    profiles_by_name: dict[str, dict[str, object]] = {}
    for path in sorted(machine_dir.glob("Anycubic Kobra S1 * nozzle.json")):
        match = _OFFICIAL_S1_PROFILE.fullmatch(path.name)
        if match is None:
            continue
        profile = inspect_profile(path)
        data = _read_object(path.read_bytes(), str(path))
        label = _string(data, "printer_settings_id") or _string(data, "name")
        diameter = _normalized_diameter(data.get("nozzle_diameter", match["diameter"]))
        nozzle_type = _string(data, "nozzle_type", "unspecified")
        profiles_by_name[label] = data
        options.append(
            TargetOption(
                target_id=f"official:anycubic-kobra-s1:{diameter}:{_slug(nozzle_type)}",
                label=label,
                nozzle_diameter=diameter,
                nozzle_type=nozzle_type,
                source_kind="official",
                source_path=str(path.resolve()),
                source_member=None,
                inherits=_string(data, "inherits") or None,
                sha256=profile.sha256,
            )
        )
    return options, profiles_by_name


def _bundle_options(
    bundle_path: Path,
    official_by_name: dict[str, dict[str, object]],
) -> list[TargetOption]:
    inspection = inspect_archive(str(bundle_path))
    archive = ThreeMFArchive(bundle_path)
    archive.validate()
    with bundle_path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest().upper()
    options: list[TargetOption] = []
    project_members = [m.name for m in inspection.inventory.members
                       if Path(m.name).name.casefold() == "project_settings.config"]
    if len(project_members) == 1:
        member = project_members[0]
        values = _read_object(archive.read_member(member, max_bytes=MAX_STRUCTURED_MEMBER_BYTES), member)
        if inspection.is_valid_3mf and values.get("printer_model") == "Anycubic Kobra S1" and values.get("gcode_flavor") == "klipper":
            diameter = _normalized_diameter(values.get("nozzle_diameter"))
            label = _string(values, "printer_settings_id") or f"{bundle_path.stem} S1 reference"
            nozzle_type = _string(values, "nozzle_type", "unspecified")
            options.append(TargetOption(
                target_id=f"reference:{digest[:12].casefold()}:{diameter}:{_slug(label)}",
                label=label, nozzle_diameter=diameter, nozzle_type=nozzle_type,
                source_kind="reference", source_path=str(bundle_path.resolve()),
                source_member=member, inherits=f"Anycubic Kobra S1 {diameter} nozzle",
                sha256=digest,
            ))
    for variant in inspection.profile_variants:
        if variant.scope != "printer":
            continue
        overlay = _read_object(
            archive.read_member(
                variant.member, max_bytes=MAX_STRUCTURED_MEMBER_BYTES
            ),
            variant.member,
        )
        inherits = _string(overlay, "inherits")
        effective = dict(official_by_name.get(inherits, {}))
        effective.update(overlay)
        label = _string(overlay, "printer_settings_id") or _string(overlay, "name")
        diameter = _normalized_diameter(effective.get("nozzle_diameter"))
        nozzle_type = _string(effective, "nozzle_type", "unspecified")
        options.append(
            TargetOption(
                target_id=(
                    f"community:{digest[:12].casefold()}:{diameter}:"
                    f"{_slug(nozzle_type)}:{_slug(label)}"
                ),
                label=label,
                nozzle_diameter=diameter,
                nozzle_type=nozzle_type,
                source_kind="community",
                source_path=str(bundle_path.resolve()),
                source_member=variant.member,
                inherits=inherits or None,
                sha256=digest,
            )
        )
    return options


def discover_targets(
    *,
    machine_dir: str | Path | None = None,
    bundles: Iterable[str | Path] = (),
    nozzle: str | None = None,
) -> tuple[TargetOption, ...]:
    resolved_machine_dir = Path(machine_dir) if machine_dir is not None else None
    if resolved_machine_dir is None:
        resolved_machine_dir = default_machine_profile_dir()
    if resolved_machine_dir is None:
        raise TargetDiscoveryError(
            "Anycubic machine profile directory was not found; pass --machine-dir"
        )

    official, official_by_name = _official_options(resolved_machine_dir.resolve())
    options = list(official)
    for bundle in bundles:
        path = Path(bundle).expanduser().resolve()
        if not path.is_file():
            raise TargetDiscoveryError(f"Profile bundle does not exist: {path}")
        options.extend(_bundle_options(path, official_by_name))

    if nozzle is not None:
        normalized = _normalized_diameter(nozzle)
        options = [item for item in options if item.nozzle_diameter == normalized]

    by_id = {item.target_id: item for item in options}
    return tuple(
        sorted(
            by_id.values(),
            key=lambda item: (
                Decimal(item.nozzle_diameter),
                item.source_kind,
                item.label.casefold(),
                item.label,
            ),
        )
    )


def select_target(
    targets: Iterable[TargetOption], target_id: str
) -> TargetOption:
    matches = [target for target in targets if target.target_id == target_id]
    if not matches:
        raise TargetDiscoveryError(f"Unknown conversion target ID: {target_id}")
    if len(matches) > 1:
        raise TargetDiscoveryError(f"Ambiguous conversion target ID: {target_id}")
    return matches[0]
