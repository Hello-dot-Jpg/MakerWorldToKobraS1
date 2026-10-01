"""Bounded, read-only filament bundle input; no archive extraction."""
from dataclasses import dataclass
import hashlib
from pathlib import Path, PurePosixPath
import re
import stat
import zipfile

from .constants import MAX_STRUCTURED_MEMBER_BYTES
from .errors import PlanError
from .parser import decode_json

MAX_BUNDLE_BYTES = 64 * 1024 * 1024
MAX_MEMBERS = 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024


@dataclass(frozen=True)
class ArchivePreset:
    archive: Path
    member: str

    @property
    def name(self):
        return f"{self.archive.name}::{self.member}"

    @property
    def stem(self):
        return PurePosixPath(self.member).stem

    def __str__(self):
        return f"{self.archive}::{self.member}"


def _validated_members(archive):
    infos = archive.infolist()
    if len(infos) > MAX_MEMBERS or sum(i.file_size for i in infos) > MAX_TOTAL_BYTES:
        raise PlanError("Filament bundle exceeds member count or expanded-size limit")
    seen = set()
    for info in infos:
        name = info.orig_filename
        parts = name.rstrip("/").split("/")
        if (not name or name.startswith("/") or "\\" in name or ":" in name
                or any(ord(c) < 32 for c in name)
                or any(p in {"", ".", ".."} or p.endswith((" ", ".")) for p in parts)
                or any(re.fullmatch(r"(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?", p) for p in parts)):
            raise PlanError(f"Unsafe filament bundle member: {name!r}")
        if name.casefold() in seen:
            raise PlanError(f"Duplicate/case-colliding filament bundle member: {name}")
        seen.add(name.casefold())
        if info.flag_bits & 1 or stat.S_ISLNK(info.external_attr >> 16):
            raise PlanError(f"Encrypted/symlink member is unsupported: {name}")
        if info.file_size > MAX_STRUCTURED_MEMBER_BYTES:
            raise PlanError(f"Filament bundle member is too large: {name}")
    return infos


def _objects(path):
    path = Path(path).resolve()
    if path.suffix.lower() not in {".zip", ".orca_filament"}:
        raise PlanError("Select a ZIP or .orca_filament bundle")
    if path.stat().st_size > MAX_BUNDLE_BYTES:
        raise PlanError("Compressed filament bundle is too large")
    objects = {}
    try:
        with zipfile.ZipFile(path) as archive:
            infos = _validated_members(archive)
            for info in infos:
                if info.is_dir() or not info.filename.lower().endswith(".json"):
                    continue
                raw = archive.read(info)
                value = decode_json(raw)
                if not isinstance(value, dict):
                    raise PlanError(f"Bundle JSON must be an object: {info.filename}")
                objects[info.filename] = (value, hashlib.sha256(raw).hexdigest())
    except (zipfile.BadZipFile, RuntimeError, ValueError, NotImplementedError) as exc:
        raise PlanError(f"Invalid filament bundle: {exc}") from exc
    return objects


def list_bundle_presets(path):
    path = Path(path).resolve()
    objects = _objects(path)
    return tuple(ArchivePreset(path, name) for name, (data, _) in objects.items()
                 if data.get("type") not in {"machine", "process"}
                 and (data.get("type") == "filament" or "filament_type" in data
                      or "filament_settings_id" in data))


def read_bundle_source(source):
    objects = _objects(source.archive)

    def resolve(member, seen=()):
        if member in seen or len(seen) >= 32:
            raise PlanError("Bundle filament inheritance cycle or depth limit")
        if member not in objects:
            raise PlanError(f"Missing filament bundle member: {member}")
        data, sha = objects[member]
        parent = data.get("inherits", "")
        if not isinstance(parent, str):
            raise PlanError("Bundle filament inherits must be a string")
        values, provenance = {}, []
        if parent:
            # Vendor bundles often use arbitrary filenames; inheritance is a
            # preset name, not permission to follow a filesystem/network path.
            matches = [name for name, (item, _) in objects.items()
                       if item.get("name") == parent and item.get("type") not in {"machine", "process"}]
            if len(matches) != 1:
                raise PlanError(f"Missing or ambiguous bundled parent: {parent}")
            values, provenance = resolve(matches[0], (*seen, member))
        values.update(data)
        provenance.append({"file": str(source.archive), "member": member, "sha256": sha})
        return values, provenance

    return resolve(source.member)
