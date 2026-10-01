"""Inventory known local acceptance fixtures; never claim native slicing passes.

Output is exclusive-create and contains local paths; keep it out of publication.
"""
import argparse
import hashlib
import json
from pathlib import Path

from s1_optimizer.archive import ThreeMFArchive
from s1_optimizer.constants import MAX_STRUCTURED_MEMBER_BYTES
from s1_optimizer.errors import InspectorError
from s1_optimizer.parser import decode_json


CASES = (
    ("current-official-0.25-hs-petg-review.3mf", "0.25", "0.10", "0.27", "stock list / nozzle extreme"),
    ("current-official-0.4-hs-petg-review.3mf", "0.4", "0.20", "0.42", "stock list"),
    ("current-official-0.6-hs-petg-review.3mf", "0.6", "0.24", "0.62", "stock list"),
    ("current-official-0.8-hs-petg-review.3mf", "0.8", "0.40", "0.82", "stock list / nozzle extreme"),
    ("cupholder-06hs-018-consolidated-review.3mf", "0.6", "0.18", "0.62", "community / modifier / beta supports"),
    ("painted-colour-scraper-current-04-review.3mf", "0.4", "0.17", "0.42", "painted colour / global ironing; historical native pass with cantilever warning"),
    ("painted-support-bucket-current-04-review.3mf", "0.4", None, None, "manual painted supports / both plates"),
    ("triceratops-variable-layers-04-petg-review.3mf", "0.4", None, None, "variable layers"),
    ("coasters-current-reconciled.3mf", "0.4", None, None, "embedded profiles / three plates"),
    ("tools-castle-reference-04-review.3mf", "0.4", "0.20", "0.42", "saved custom reference"),
    ("asa-heat-bed-clamps-selectable-04hs-review.3mf", "0.4", None, None, "active ASA assignment / selectable default plate"),
    ("abs-petg-hose-holder-plates-04hs-review.3mf", "0.4", None, None, "active ABS/PETG / 34 relocated plates"),
    ("ironing-negative-volume-current-04hs-review.3mf", "0.4", "0.20", "0.42", "local ironing / negative volumes / reviewed PLA and PLA+ destinations"),
)
KEYS = (
    "printer_settings_id", "print_settings_id", "nozzle_diameter", "nozzle_type",
    "layer_height", "initial_layer_print_height", "line_width", "curr_bed_type",
    "support_multi_bed_types",
    "filament_type", "filament_settings_id", "nozzle_temperature",
    "textured_plate_temp", "inherits_group", "support_type", "enable_support",
    "ironing_type", "machine_load_filament_time", "machine_unload_filament_time",
    "machine_tool_change_time",
)


def inspect_fixture(path, expected):
    archive = ThreeMFArchive(path)
    inventory = archive.validate()
    raw = archive.read_member("Metadata/project_settings.config", max_bytes=MAX_STRUCTURED_MEMBER_BYTES)
    config = decode_json(raw)
    if not isinstance(config, dict):
        raise ValueError("Project settings must be an object")
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    names = [member.name for member in inventory.members]
    model_settings = b""
    if "Metadata/model_settings.config" in names:
        model_settings = archive.read_member(
            "Metadata/model_settings.config", max_bytes=MAX_STRUCTURED_MEMBER_BYTES
        )
    return {
        "path": str(path.resolve()), "sha256": digest,
        "project_settings_sha256": hashlib.sha256(raw).hexdigest(),
        "archive_warnings": list(inventory.warnings), "member_count": len(names),
        "expected_from_acceptance_docs": expected,
        "observed_project_settings": {key: config.get(key) for key in KEYS},
        "plate_json_members": [name for name in names if Path(name).name.startswith("plate_") and name.endswith(".json")],
        "variable_layer_members": [name for name in names if "layer_height" in name],
        "feature_observations": {
            "local_topmost_ironing_overrides": model_settings.count(
                b'key="ironing_type" value="topmost"'
            ),
            "negative_parts": model_settings.count(b'subtype="negative_part"'),
        },
        "native_status": "not_run_by_this_manifest",
        "limitations": "No source comparison, effective inheritance resolution, mesh preservation or slicing proof. Values are observations, not validated expectations.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    records = []
    for filename, nozzle, height, width, purpose in CASES:
        expected = {"nozzle_mm": nozzle, "layer_mm": height, "width_mm": width, "purpose": purpose}
        try:
            records.append(inspect_fixture(args.reports / filename, expected))
        except (InspectorError, OSError, ValueError, RuntimeError) as error:
            records.append({"file": filename, "error": str(error)})
    result = {"cases": records, "unprepared_cases": []}
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False)
    failures = sum("error" in record for record in records)
    print(f"Inventoried {len(records)} fixtures; {failures} errors; no native checks performed.")
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
