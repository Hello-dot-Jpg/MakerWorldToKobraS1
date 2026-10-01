from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path

from .constants import MAX_STRUCTURED_MEMBER_BYTES
from .errors import ProfileValidationError
from .parser import DuplicateJsonKeyError, decode_json
from .settings import Setting, flatten_json


@dataclass(frozen=True, slots=True)
class ProfileInspection:
    path: Path
    sha256: str
    profile_kind: str
    settings: tuple[Setting, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "path": str(self.path),
            "sha256": self.sha256,
            "profile_kind": self.profile_kind,
            "settings": [setting.to_dict() for setting in self.settings],
        }


def _profile_kind(path: Path) -> tuple[str, str]:
    parent = path.parent.name.casefold()
    if parent == "machine":
        return "machine", "printer"
    if parent == "process":
        return "process", "process"
    if parent == "filament":
        return "filament", "filament"
    return "unknown", "unknown"


def inspect_profile(path: str | Path) -> ProfileInspection:
    resolved = Path(path).expanduser().resolve()
    if not resolved.exists():
        raise ProfileValidationError(f"File does not exist: {resolved}")
    if not resolved.is_file():
        raise ProfileValidationError(f"Path is not a file: {resolved}")
    try:
        size = resolved.stat().st_size
        if size > MAX_STRUCTURED_MEMBER_BYTES:
            raise ProfileValidationError(
                "Profile exceeds the safe structured-file inspection limit "
                f"of {MAX_STRUCTURED_MEMBER_BYTES} bytes: {resolved}"
            )
        raw = resolved.read_bytes()
        parsed = decode_json(raw)
    except ProfileValidationError:
        raise
    except (
        DuplicateJsonKeyError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        OSError,
    ) as exc:
        raise ProfileValidationError(f"Cannot parse slicer profile: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ProfileValidationError("Slicer profile root must be a JSON object")

    kind, scope = _profile_kind(resolved)
    settings = tuple(
        sorted(
            flatten_json(parsed, resolved.name, scope_override=scope),
            key=lambda setting: (
                setting.name.casefold(),
                setting.name,
                setting.identity.casefold(),
                setting.identity,
            ),
        )
    )
    return ProfileInspection(
        path=resolved,
        sha256=hashlib.sha256(raw).hexdigest().upper(),
        profile_kind=kind,
        settings=settings,
    )
