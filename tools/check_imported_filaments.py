"""Read-only comparison of installed presets against a conversion report.

Inherited presets use the destination base snapshot in the export report.
Standalone presets are compared without inventing a parent. This does not
simulate slicing; missing fields remain strict differences.
"""
import argparse
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path

from s1_optimizer.preset_conversion import NUMERIC, PLATE_KEYS, TEXT
from s1_optimizer.constants import MAX_STRUCTURED_MEMBER_BYTES

MAX_REPORT_BYTES = 64 * 1024 * 1024
MAX_PRESET_BYTES = MAX_STRUCTURED_MEMBER_BYTES


def _preset_files(installed_folder):
    """Yield only standalone presets in the install root and its base folder."""
    root = Path(installed_folder)
    yield from ((path, path.name) for path in sorted(root.glob("*.json")))
    base = root / "base"
    if base.is_dir():
        yield from ((path, f"base/{path.name}") for path in sorted(base.glob("*.json")))


def _has_preset_files(folder):
    return any(_preset_files(folder))


def _matching_identity_count(folder, expected_names):
    names = set()
    for path, _ in _preset_files(folder):
        try:
            data = _json_file(path, MAX_PRESET_BYTES, "installed preset")
        except ValueError:
            continue
        if isinstance(data, dict) and isinstance(data.get("name"), str):
            names.add(data["name"])
    return len(names & expected_names)


def _resolve_installed_folder(folder, expected_names):
    """Accept a filament store or resolve one unique account below a user root."""
    root = Path(folder).resolve()
    if _has_preset_files(root):
        return root
    candidates = []
    direct = root / "filament"
    if _has_preset_files(direct):
        candidates.append(direct)
    if root.is_dir():
        for child in sorted(root.iterdir()):
            candidate = child / "filament"
            if child.is_dir() and _has_preset_files(candidate):
                candidates.append(candidate)
    candidates = list(dict.fromkeys(candidate.resolve() for candidate in candidates))
    scored = [(_matching_identity_count(candidate, expected_names), candidate)
              for candidate in candidates]
    best_score = max((score for score, _ in scored), default=0)
    best = [candidate for score, candidate in scored if score == best_score and score > 0]
    if len(best) != 1:
        detail = ", ".join(f"{path} ({score} matches)" for score, path in scored) or "none"
        raise ValueError(
            "Could not resolve one active Anycubic filament store from the supplied path; "
            f"candidates: {detail}"
        )
    return best[0]


def _canonical_snapshot_filename(filename):
    """Accept only a root JSON name or base/<JSON name>, in either separator style."""
    if not isinstance(filename, str) or not filename:
        raise ValueError(f"Unsafe pre-import snapshot filename: {filename!r}")
    canonical = filename.replace("\\", "/")
    parts = canonical.split("/")
    if (len(parts) == 1 and parts[0]) or (len(parts) == 2 and parts[0] == "base" and parts[1]):
        leaf = parts[-1]
    else:
        raise ValueError(f"Unsafe pre-import snapshot filename: {filename!r}")
    # Reject traversal, drive/ADS syntax, and non-preset targets. A leaf is
    # deliberately limited to a single path component above.
    if (leaf in {".", ".."} or ":" in leaf or not leaf.casefold().endswith(".json")):
        raise ValueError(f"Unsafe pre-import snapshot filename: {filename!r}")
    return canonical


def file_hash(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def normalized(value):
    if isinstance(value, list):
        return [normalized(item) for item in value]
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return value


def _json_file(path, limit, label):
    """Read one bounded JSON file, converting input failures to audit errors."""
    try:
        if not path.is_file():
            raise ValueError(f"{label} is missing: {path}")
        with path.open("rb") as stream:
            raw = stream.read(limit + 1)
        if len(raw) > limit:
            raise ValueError(f"{label} exceeds {limit} bytes: {path}")
        return json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"Cannot read {label}: {exc}") from exc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export_folder", type=Path)
    parser.add_argument("installed_folder", type=Path)
    parser.add_argument("--output", type=Path, help="Write evidence to a new JSON file (no overwrite)")
    parser.add_argument("--before", type=Path, help="Optional pre-import filename/hash snapshot")
    args = parser.parse_args()
    results = []
    report_path = args.export_folder / "conversion-report.txt"
    try:
        with report_path.open("rb") as stream:
            raw_report = stream.read(MAX_REPORT_BYTES + 1)
        if len(raw_report) > MAX_REPORT_BYTES:
            raise ValueError(f"conversion report exceeds {MAX_REPORT_BYTES} bytes")
        report = raw_report.decode("utf-8")
        report = report.replace("\r\n", "\n").replace("\r", "\n")
        marker = "DETAILED FIELD AUDIT\n"
        if marker not in report:
            raise ValueError("conversion report has no detailed field audit")
        plans = json.loads(report.split(marker, 1)[1])
        if not isinstance(plans, list) or not plans:
            raise ValueError("conversion report contains no plans")
        for plan in plans:
            if (not isinstance(plan, dict) or not isinstance(plan.get("name"), str)
                    or not isinstance(plan.get("values"), dict)
                    or not isinstance(plan.get("provenance"), list)
                    or not plan["provenance"]
                    or not isinstance(plan["provenance"][-1], dict)
                    or not isinstance(plan["provenance"][-1].get("destination_base"), dict)
                    or not isinstance(plan["provenance"][-1]["destination_base"].get("effective_values"), dict)):
                raise ValueError("conversion report contains a malformed plan")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        evidence = {"results": [{"error": str(exc)}], "audit_error": str(exc),
                    "preexisting_snapshot_checked": False, "preexisting_changed": [],
                    "added_presets": []}
        print(json.dumps(evidence, indent=2))
        return 1
    try:
        installed_folder = _resolve_installed_folder(
            args.installed_folder, {plan["name"] for plan in plans}
        )
    except (OSError, ValueError) as exc:
        evidence = {"results": [{"error": str(exc)}], "audit_error": str(exc),
                    "preexisting_snapshot_checked": False, "preexisting_changed": [],
                    "added_presets": []}
        print(json.dumps(evidence, indent=2))
        return 1
    installed = {}
    invalid_installed = []
    for path, relative_name in _preset_files(installed_folder):
        try:
            data = _json_file(path, MAX_PRESET_BYTES, "installed preset")
            if not isinstance(data, dict):
                raise ValueError("installed preset JSON must be an object")
            if not isinstance(data.get("name"), str):
                raise ValueError("installed preset name must be a string")
            installed.setdefault(data["name"], []).append((path, relative_name, data))
        except ValueError as exc:
            invalid_installed.append({"file": relative_name, "error": str(exc)})
    results.extend(invalid_installed)
    for plan in plans:
        matches = installed.get(plan["name"], [])
        if len(matches) != 1:
            results.append({"name": plan["name"], "error": f"Expected one installed identity; found {len(matches)}"})
            continue
        path, relative_name, data = matches[0]
        base = plan["provenance"][-1]["destination_base"]["effective_values"]
        expected = {**(base if plan["values"].get("inherits") else {}), **plan["values"]}
        # Standalone presets have no parent. Missing native keys must never be
        # filled from the historical calibration scaffold used to generate them.
        actual = {**(base if plan["values"].get("inherits") else {}), **data}
        keys = (NUMERIC | PLATE_KEYS | TEXT | {key + "_HS" for key in NUMERIC | PLATE_KEYS} | {"chamber_temperature", "activate_chamber_temp_control", "filament_flow_ratio", "pressure_advance",
                "filament_start_gcode", "filament_end_gcode", "compatible_printers", "inherits"}) & expected.keys()
        differences = {key: {"expected": expected[key], "actual": actual.get(key)}
                       for key in sorted(keys) if normalized(expected[key]) != normalized(actual.get(key))}
        results.append({"name": plan["name"], "file": relative_name, "compared_keys": len(keys),
                        "differences": differences, "installed_sha256": file_hash(path)})
    before_path = args.before or args.export_folder / "installed-before-batch.json"
    changed = []
    snapshot_error = None
    snapshot_checked = False
    if before_path.exists() or args.before:
        try:
            before = _json_file(before_path, MAX_REPORT_BYTES, "pre-import snapshot")
            if not isinstance(before, dict):
                raise ValueError("pre-import snapshot must be an object mapping filenames to hashes")
            snapshot_checked = True
        except ValueError as exc:
            snapshot_error = str(exc)
            before = {}
    if snapshot_checked:
        for filename, digest in before.items():
            try:
                canonical = _canonical_snapshot_filename(filename)
            except ValueError as exc:
                snapshot_error = str(exc)
                break
            if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdefABCDEF" for c in digest):
                snapshot_error = f"Invalid pre-import snapshot digest for: {filename!r}"
                break
            path = installed_folder / Path(*canonical.split("/"))
            if not path.is_file() or file_hash(path).lower() != digest.lower():
                changed.append(canonical)
    current_names = {relative_name for entries in installed.values()
                     for path, relative_name, data in entries}
    before_names = set()
    if snapshot_checked:
        for filename in before:
            try:
                before_names.add(_canonical_snapshot_filename(filename))
            except ValueError:
                pass
    added = sorted(current_names - before_names) if snapshot_checked else []
    expected_names = {plan.get("name") for plan in plans if isinstance(plan, dict)}
    expected_paths = {relative_name for entries in installed.values()
                      for path, relative_name, data in entries if data.get("name") in expected_names}
    expected_added = [relative_name for relative_name in added if relative_name in expected_paths]
    unexpected_added = [relative_name for relative_name in added if relative_name not in expected_added]
    evidence = {"results": results, "resolved_installed_folder": str(installed_folder),
                "preexisting_snapshot_checked": snapshot_checked,
                "preexisting_changed": changed, "added_presets": added,
                "expected_added_presets": expected_added, "unexpected_added_presets": unexpected_added}
    if snapshot_error:
        evidence["snapshot_error"] = snapshot_error
    if args.output:
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(evidence, stream, indent=2)
        print(f"Checked {len(results)} installed presets; evidence: {args.output}")
    else:
        print(json.dumps(evidence, indent=2))
    return int(bool(changed or unexpected_added or snapshot_error) or
               any(item.get("error") or item.get("differences") for item in results))


if __name__ == "__main__":
    raise SystemExit(main())
