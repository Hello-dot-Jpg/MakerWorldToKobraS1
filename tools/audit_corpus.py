"""Read-only settings inventory; candidate findings are NOT conversion rules.

Run from the repository with Python after installing the package editable.
Only JSON settings and small model-settings XML are read, never mesh payloads.
Reports may contain local filenames: keep them out of Git.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile

from s1_optimizer.plan import _is_filament_translate_key, _is_machine_replace_key
from s1_optimizer.rules import DEFAULT_CLAMP_KEYS
from s1_optimizer.compatibility import SCALAR_KEYS

SCALARS = {"coBool", "coInt", "coFloat", "coFloatOrPercent", "coPercent", "coEnum", "coString"}
CONFIG = re.compile(r"(?:project|machine|process|filament)_settings(?:_\d+)?\.config$", re.I)
LIMIT = 16 * 1024 * 1024


def policy(key):
    if _is_machine_replace_key(key):
        return "machine replacement if target has key"
    if _is_filament_translate_key(key):
        return "filament translation if selected target has key"
    if key in DEFAULT_CLAMP_KEYS or key == "filament_max_volumetric_speed":
        return "clamp if compatible target value exists"
    if key in {"enable_overhang_speed", "ensure_vertical_shell_thickness"}:
        return "explicit compatibility translation"
    if key in SCALAR_KEYS:
        return "unanimous scalar translation; mixed values block"
    if key == "line_width" or key.endswith("_line_width"):
        return "nozzle-width translation if target has key"
    return "preserved; no explicit rule"


def audit(root: Path, schema: Path, profiles: Path):
    types = dict(re.findall(r'this->add\("([^"\n]+)",\s*(co\w+)\)', schema.read_text(encoding="utf-8")))
    profile_shapes = defaultdict(set)
    for path in profiles.rglob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(data, dict):
            for key, value in data.items():
                profile_shapes[key].add("array" if isinstance(value, list) else "scalar")
    findings = defaultdict(list)
    keys = defaultdict(set)
    counts = Counter()
    errors = []
    without_modern = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.casefold() != ".3mf":
            continue
        counts["files"] += 1
        has_project = False
        try:
            with zipfile.ZipFile(path) as archive:
                names = Counter(archive.namelist())
                for info in archive.infolist():
                    member = info.filename
                    basename = member.rsplit("/", 1)[-1]
                    if not CONFIG.fullmatch(basename) and basename != "model_settings.config":
                        continue
                    if names[member] != 1 or info.file_size > LIMIT or info.flag_bits & 1:
                        errors.append({"file": str(path.relative_to(root)), "member": member, "error": "ambiguous, oversized or encrypted member skipped"})
                        continue
                    try:
                        raw = archive.read(info)
                        if basename == "model_settings.config":
                            xml = ET.fromstring(raw)
                            for item in xml.iter("metadata"):
                                key = item.get("key")
                                if key in types:
                                    keys["model_override:" + key].add(str(path.relative_to(root)))
                            continue
                        data = json.loads(raw.decode("utf-8-sig"))
                        if not isinstance(data, dict):
                            raise ValueError("Settings root is not an object")
                        counts["json_members"] += 1
                        if basename.lower() == "project_settings.config":
                            has_project = True
                            counts["project_settings_members"] += 1
                        for key, value in data.items():
                            keys[key].add(str(path.relative_to(root)))
                            reason = None
                            if types.get(key) in SCALARS and isinstance(value, list):
                                reason = "array_for_scalar"
                            elif key in {"raft_first_layer_expansion", "tree_support_wall_count"} and str(value) == "-1":
                                reason = "legacy_negative_sentinel"
                            if reason:
                                findings[(reason, key)].append({"file": str(path.relative_to(root)), "member": member, "value": value})
                    except (ValueError, UnicodeError, ET.ParseError, OSError, RuntimeError, zipfile.BadZipFile) as exc:
                        errors.append({"file": str(path.relative_to(root)), "member": member, "error": str(exc)})
        except (OSError, zipfile.BadZipFile) as exc:
            errors.append({"file": str(path.relative_to(root)), "error": str(exc)})
        if not has_project:
            counts["files_without_modern_project_settings"] += 1
            without_modern.append(str(path.relative_to(root)))
    return {
        "basis": {"root": str(root), "schema": str(schema), "profiles": str(profiles), "caveat": "Checked-out source schema may differ from installed binary. Profile shape corroboration is not a complete schema. Unknown keys are inventory, not proven bugs. No mesh CRC or slicing validation performed."},
        "counts": dict(counts), "errors": errors,
        "files_without_modern_project_settings": without_modern,
        "findings": [{"kind": kind, "key": key, "schema_type": types.get(key), "installed_profile_shapes": sorted(profile_shapes[key]), "policy": policy(key), "files": len({x['file'] for x in rows}), "occurrences": rows} for (kind, key), rows in sorted(findings.items())],
        "inventory": [{"key": key, "files": len(files), "schema_type": types.get(key), "installed_profile_shapes": sorted(profile_shapes[key]), "policy": policy(key), "examples": sorted(files)[:3]} for key, files in sorted(keys.items())],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--profiles", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.suffix.lower() != ".json":
        parser.error("Output must be a new .json report, not a source archive")
    report = audit(args.root, args.schema, args.profiles)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps({"counts": report["counts"], "errors": len(report["errors"]),
                      "distinct_keys": len(report["inventory"]),
                      "finding_groups": len(report["findings"]),
                      "report": str(args.output.resolve())}, indent=2))


if __name__ == "__main__":
    main()
