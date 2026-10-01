from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import PurePosixPath
from typing import Any, Iterator

from .classifier import classify_setting


JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]


def json_type(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


@dataclass(frozen=True, slots=True)
class Setting:
    name: str
    logical_path: str
    canonical_path: str
    value: JsonValue
    value_type: str
    source_member: str
    scope: str
    categories: tuple[str, ...]

    @property
    def identity(self) -> str:
        return f"{self.source_member}::{self.canonical_path}"

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["identity"] = self.identity
        data["categories"] = list(self.categories)
        return data


def _render_logical_path(segments: tuple[str | int, ...]) -> str:
    if not segments:
        return "$"
    result = ""
    for segment in segments:
        if isinstance(segment, int):
            result += f"[{segment}]"
        elif segment.isidentifier():
            result += f".{segment}" if result else segment
        else:
            result += f"[{json.dumps(segment, ensure_ascii=False)}]"
    return result


def _canonical_path(segments: tuple[str | int, ...]) -> str:
    # JSON encoding retains the difference between object keys and array
    # indices and cannot collide when a key itself contains dots or brackets.
    return json.dumps(segments, ensure_ascii=False, separators=(",", ":"))


def _scope_from_source(source_member: str) -> str:
    basename = PurePosixPath(source_member).name.casefold()
    if basename.startswith("machine_settings"):
        return "printer"
    if basename.startswith("process_settings"):
        return "process"
    if basename.startswith("filament_settings"):
        return "filament"
    if basename == "project_settings.config":
        return "project"
    if basename == "slic3r_pe.config":
        return "legacy-project"
    return "unknown"


def flatten_json(
    value: JsonValue,
    source_member: str,
    segments: tuple[str | int, ...] = (),
    *,
    scope_override: str | None = None,
) -> Iterator[Setting]:
    """Flatten JSON into leaf settings while preserving arrays and JSON types."""
    if isinstance(value, dict) and value:
        for key in sorted(value, key=lambda item: (item.casefold(), item)):
            yield from flatten_json(
                value[key],
                source_member,
                (*segments, key),
                scope_override=scope_override,
            )
        return
    if isinstance(value, list) and value:
        for index, item in enumerate(value):
            yield from flatten_json(
                item,
                source_member,
                (*segments, index),
                scope_override=scope_override,
            )
        return

    logical_path = _render_logical_path(segments)
    name = next(
        (segment for segment in reversed(segments) if isinstance(segment, str)),
        "$",
    )
    yield Setting(
        name=name,
        logical_path=logical_path,
        canonical_path=_canonical_path(segments),
        value=value,
        value_type=json_type(value),
        source_member=source_member,
        scope=scope_override or _scope_from_source(source_member),
        categories=classify_setting(name, logical_path, source_member),
    )
