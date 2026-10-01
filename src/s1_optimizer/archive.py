from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Iterator
import zipfile

from .constants import (
    CONTENT_TYPES_MEMBER,
    MAX_CRC_SCAN_BYTES,
    MODEL_SUFFIX,
    ROOT_RELATIONSHIPS_MEMBER,
)
from .errors import ArchiveValidationError


@dataclass(frozen=True, slots=True)
class ArchiveMember:
    name: str
    size: int
    compressed_size: int
    encrypted: bool
    suspicious_path: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ArchiveInventory:
    path: Path
    members: tuple[ArchiveMember, ...]
    duplicate_names: tuple[str, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "path": str(self.path),
            "members": [member.to_dict() for member in self.members],
            "duplicate_names": list(self.duplicate_names),
            "warnings": list(self.warnings),
        }


def _is_suspicious_member_name(name: str) -> bool:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    return (
        path.is_absolute()
        or ".." in path.parts
        or (len(normalized) >= 2 and normalized[1] == ":")
    )


class ThreeMFArchive:
    """Read-only access to a validated 3MF ZIP archive."""

    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser().resolve()
        self._inventory: ArchiveInventory | None = None

    def validate(self) -> ArchiveInventory:
        if self._inventory is not None:
            return self._inventory
        if not self.path.exists():
            raise ArchiveValidationError(f"File does not exist: {self.path}")
        if not self.path.is_file():
            raise ArchiveValidationError(f"Path is not a file: {self.path}")
        if not zipfile.is_zipfile(self.path):
            raise ArchiveValidationError(f"Not a valid ZIP/3MF archive: {self.path}")

        try:
            with zipfile.ZipFile(self.path, "r") as archive:
                infos = archive.infolist()
                total_uncompressed = sum(info.file_size for info in infos)
                crc_scan_skipped = total_uncompressed > MAX_CRC_SCAN_BYTES
                if not crc_scan_skipped:
                    bad_member = archive.testzip()
                    if bad_member is not None:
                        raise ArchiveValidationError(
                            f"Archive CRC check failed for member: {bad_member}"
                        )
        except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
            raise ArchiveValidationError(f"Cannot read archive: {exc}") from exc

        names = [info.filename for info in infos]
        counts = Counter(names)
        duplicates = tuple(sorted(name for name, count in counts.items() if count > 1))
        members = tuple(
            sorted(
                (
                    ArchiveMember(
                        name=info.filename,
                        size=info.file_size,
                        compressed_size=info.compress_size,
                        encrypted=bool(info.flag_bits & 0x1),
                        suspicious_path=_is_suspicious_member_name(info.filename),
                    )
                    for info in infos
                ),
                key=lambda member: (member.name.casefold(), member.name),
            )
        )

        name_lookup = set(names)
        warnings: list[str] = []
        if crc_scan_skipped:
            warnings.append(
                "Full CRC scan skipped because total uncompressed size "
                f"exceeds {MAX_CRC_SCAN_BYTES} bytes"
            )
        if CONTENT_TYPES_MEMBER not in name_lookup:
            warnings.append(f"Missing required 3MF member: {CONTENT_TYPES_MEMBER}")
        if ROOT_RELATIONSHIPS_MEMBER not in name_lookup:
            warnings.append(f"Missing required 3MF member: {ROOT_RELATIONSHIPS_MEMBER}")
        if not any(name.endswith(MODEL_SUFFIX) for name in names):
            warnings.append("No .model member was found; archive is not a complete 3MF model")
        if duplicates:
            warnings.append("Duplicate member names are ambiguous and will not be parsed")
        if any(member.suspicious_path for member in members):
            warnings.append("Archive contains suspicious absolute or traversal member paths")
        if any(member.encrypted for member in members):
            warnings.append("Archive contains encrypted members that cannot be inspected safely")

        self._inventory = ArchiveInventory(
            path=self.path,
            members=members,
            duplicate_names=duplicates,
            warnings=tuple(warnings),
        )
        return self._inventory

    def _checked_member(self, name: str, max_bytes: int) -> ArchiveMember:
        inventory = self.validate()
        if name in inventory.duplicate_names:
            raise ArchiveValidationError(f"Refusing ambiguous duplicate member: {name}")
        matching = [member for member in inventory.members if member.name == name]
        if not matching:
            raise ArchiveValidationError(f"Archive member does not exist: {name}")
        member = matching[0]
        if member.encrypted:
            raise ArchiveValidationError(f"Cannot read encrypted member: {name}")
        if member.size > max_bytes:
            raise ArchiveValidationError(
                f"Member is too large to inspect safely ({member.size} bytes): {name}"
            )
        return member

    @contextmanager
    def open_member(self, name: str, *, max_bytes: int) -> Iterator[BinaryIO]:
        """Open one unambiguous bounded member as a read-only stream."""
        self._checked_member(name, max_bytes)
        try:
            with zipfile.ZipFile(self.path, "r") as archive:
                with archive.open(name, "r") as stream:
                    yield stream
        except (OSError, zipfile.BadZipFile, RuntimeError, KeyError) as exc:
            raise ArchiveValidationError(f"Cannot read member {name}: {exc}") from exc

    def read_member(self, name: str, *, max_bytes: int) -> bytes:
        with self.open_member(name, max_bytes=max_bytes) as stream:
            return stream.read()
