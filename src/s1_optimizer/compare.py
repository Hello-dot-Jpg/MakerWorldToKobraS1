from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import json
from typing import Iterable

from .parser import Inspection
from .settings import Setting


@dataclass(frozen=True, slots=True)
class ChangedSetting:
    identity: str
    left: Setting
    right: Setting

    def to_dict(self) -> dict[str, object]:
        return {
            "identity": self.identity,
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
        }


def _value_signature(setting: Setting) -> tuple[str, str]:
    return (
        setting.value_type,
        json.dumps(
            setting.value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
    )


@dataclass(frozen=True, slots=True)
class SettingGroup:
    name: str
    occurrences: tuple[Setting, ...]

    @property
    def value_signatures(self) -> frozenset[tuple[str, str]]:
        return frozenset(_value_signature(setting) for setting in self.occurrences)

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "occurrences": [setting.to_dict() for setting in self.occurrences],
        }


@dataclass(frozen=True, slots=True)
class ChangedSettingGroup:
    name: str
    left: SettingGroup
    right: SettingGroup

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class NameComparison:
    only_left: tuple[SettingGroup, ...]
    only_right: tuple[SettingGroup, ...]
    changed: tuple[ChangedSettingGroup, ...]
    equal: tuple[tuple[SettingGroup, SettingGroup], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "summary": {
                "only_left": len(self.only_left),
                "only_right": len(self.only_right),
                "changed": len(self.changed),
                "equal": len(self.equal),
            },
            "only_left": [group.to_dict() for group in self.only_left],
            "only_right": [group.to_dict() for group in self.only_right],
            "changed": [change.to_dict() for change in self.changed],
            "equal": [
                {"name": left.name, "left": left.to_dict(), "right": right.to_dict()}
                for left, right in self.equal
            ],
        }


@dataclass(frozen=True, slots=True)
class Comparison:
    left_path: str
    right_path: str
    only_left: tuple[Setting, ...]
    only_right: tuple[Setting, ...]
    changed: tuple[ChangedSetting, ...]
    equal: tuple[Setting, ...]
    by_name: NameComparison
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "left_path": self.left_path,
            "right_path": self.right_path,
            "summary": {
                **self.by_name.to_dict()["summary"],
                "warnings": len(self.warnings),
            },
            "by_name": self.by_name.to_dict(),
            "exact_identity_summary": {
                "only_left": len(self.only_left),
                "only_right": len(self.only_right),
                "changed": len(self.changed),
                "equal": len(self.equal),
                "warnings": len(self.warnings),
            },
            "only_left": [setting.to_dict() for setting in self.only_left],
            "only_right": [setting.to_dict() for setting in self.only_right],
            "changed": [change.to_dict() for change in self.changed],
            "equal": [setting.to_dict() for setting in self.equal],
            "warnings": list(self.warnings),
        }


def _group_by_name(settings: Iterable[Setting]) -> dict[str, SettingGroup]:
    grouped: dict[str, list[Setting]] = defaultdict(list)
    for setting in settings:
        grouped[setting.name].append(setting)
    return {
        name: SettingGroup(name, tuple(occurrences))
        for name, occurrences in grouped.items()
    }


def _compare_by_name(left: Inspection, right: Inspection) -> NameComparison:
    left_groups = _group_by_name(left.settings)
    right_groups = _group_by_name(right.settings)
    left_names = set(left_groups)
    right_names = set(right_groups)
    sort_key = lambda value: (value.casefold(), value)
    only_left = tuple(
        left_groups[name] for name in sorted(left_names - right_names, key=sort_key)
    )
    only_right = tuple(
        right_groups[name] for name in sorted(right_names - left_names, key=sort_key)
    )
    changed: list[ChangedSettingGroup] = []
    equal: list[tuple[SettingGroup, SettingGroup]] = []
    for name in sorted(left_names & right_names, key=sort_key):
        left_group = left_groups[name]
        right_group = right_groups[name]
        if left_group.value_signatures == right_group.value_signatures:
            equal.append((left_group, right_group))
        else:
            changed.append(ChangedSettingGroup(name, left_group, right_group))
    return NameComparison(only_left, only_right, tuple(changed), tuple(equal))


def compare_inspections(left: Inspection, right: Inspection) -> Comparison:
    left_by_id = {setting.identity: setting for setting in left.settings}
    right_by_id = {setting.identity: setting for setting in right.settings}
    left_ids = set(left_by_id)
    right_ids = set(right_by_id)

    sort_key = lambda value: (value.casefold(), value)
    only_left = tuple(left_by_id[key] for key in sorted(left_ids - right_ids, key=sort_key))
    only_right = tuple(right_by_id[key] for key in sorted(right_ids - left_ids, key=sort_key))
    changed: list[ChangedSetting] = []
    equal: list[Setting] = []
    for key in sorted(left_ids & right_ids, key=sort_key):
        left_setting = left_by_id[key]
        right_setting = right_by_id[key]
        if (
            left_setting.value_type == right_setting.value_type
            and left_setting.value == right_setting.value
        ):
            equal.append(left_setting)
        else:
            changed.append(ChangedSetting(key, left_setting, right_setting))

    warnings = tuple(
        [f"left: {warning}" for warning in left.warnings]
        + [f"right: {warning}" for warning in right.warnings]
    )
    return Comparison(
        left_path=str(left.inventory.path),
        right_path=str(right.inventory.path),
        only_left=only_left,
        only_right=only_right,
        changed=tuple(changed),
        equal=tuple(equal),
        by_name=_compare_by_name(left, right),
        warnings=warnings,
    )
