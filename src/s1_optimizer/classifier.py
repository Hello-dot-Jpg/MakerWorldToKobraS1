from __future__ import annotations

import re


_TOKEN_SPLIT = re.compile(r"[^a-z0-9]+")

_CATEGORY_TERMS: dict[str, frozenset[str]] = {
    "printer": frozenset(
        {
            "printer", "machine", "nozzle", "bed", "printable", "gcode",
            "extruder", "kinematics", "firmware", "toolchange", "tool",
        }
    ),
    "process": frozenset(
        {
            "process", "layer", "wall", "infill", "support", "seam",
            "ironing", "brim", "raft", "bridge", "skirt", "shell",
        }
    ),
    "filament": frozenset(
        {
            "filament", "material", "temperature", "cooling", "retraction",
            "purge", "flow", "fan", "spool",
        }
    ),
    "speed": frozenset({"speed", "velocity"}),
    "acceleration": frozenset({"acceleration", "accelerate", "jerk"}),
}


def classify_setting(
    name: str,
    logical_path: str,
    source_member: str = "",
) -> tuple[str, ...]:
    """Return conservative, non-exclusive heuristic tags for a setting."""
    tokens = set(
        _TOKEN_SPLIT.split(f"{name} {logical_path} {source_member}".casefold())
    )
    tokens.discard("")
    return tuple(
        category
        for category, terms in _CATEGORY_TERMS.items()
        if tokens.intersection(terms)
    )
