from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from .errors import PlanError


DEFAULT_CLAMP_KEYS = frozenset(
    {
        "bridge_speed",
        "default_acceleration",
        "gap_infill_speed",
        "initial_layer_acceleration",
        "initial_layer_infill_speed",
        "initial_layer_speed",
        "inner_wall_acceleration",
        "inner_wall_speed",
        "internal_solid_infill_speed",
        "outer_wall_acceleration",
        "outer_wall_speed",
        "sparse_infill_speed",
        "support_interface_speed",
        "support_speed",
        "top_surface_acceleration",
        "top_surface_speed",
        "travel_acceleration",
        "travel_speed",
    }
)


@dataclass(frozen=True, slots=True)
class RuleSet:
    clamp: frozenset[str]
    source_path: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "clamp": sorted(self.clamp, key=lambda value: (value.casefold(), value)),
            "source_path": self.source_path,
        }


def load_rules(path: str | Path | None = None) -> RuleSet:
    if path is None:
        return RuleSet(DEFAULT_CLAMP_KEYS)
    rule_path = Path(path).expanduser().resolve()
    if not rule_path.is_file():
        raise PlanError(f"Rule file does not exist: {rule_path}")
    try:
        value = json.loads(rule_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PlanError(f"Cannot read JSON rule file {rule_path}: {exc}") from exc
    if not isinstance(value, dict) or set(value) != {"clamp"}:
        raise PlanError("Rule file must be an object containing only a 'clamp' array")
    clamp = value["clamp"]
    if not isinstance(clamp, list) or not all(
        isinstance(item, str) and item for item in clamp
    ):
        raise PlanError("Rule file 'clamp' must be an array of non-empty setting names")
    if len(clamp) != len(set(clamp)):
        raise PlanError("Rule file contains duplicate clamp setting names")
    return RuleSet(frozenset(clamp), str(rule_path))
