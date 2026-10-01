"""Explicit REVIEW-only S1 material bases guided by installed S1 Max presets.

Not a general cross-printer importer. No machine profile or firmware is changed.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from .errors import PlanError
from .preset_conversion import NUMERIC, PLATE_KEYS, PresetPlan, number, read_source, scalar

MATERIALS = ("PC", "PLA-CF", "PA6-CF", "PET-CF", "PC-CF", "PC-GF")


def plan_engineering_preset(directory, material, nozzle, *, max_nozzle=320, max_bed=110):
    """Use S1 calibration/macros and same-size Max portable material guidance.

    PC-CF/GF explicitly use the S1 PC calibration scaffold, not a claim of
    calibration equivalence. 0.25 is deliberately unsupported without a donor.
    """
    if material not in MATERIALS or nozzle not in {"0.4", "0.6", "0.8"}:
        raise PlanError("Engineering guide requires a listed material and 0.4/0.6/0.8 nozzle")
    nozzle_limit, bed_limit = number(max_nozzle), number(max_bed)
    if nozzle_limit <= 0 or nozzle_limit > 320 or bed_limit <= 0 or bed_limit > 110:
        raise PlanError("This review generator is limited to the current 320 C nozzle / 110 C bed setup")
    directory = Path(directory)
    scaffold_material = "PC" if material in {"PC-CF", "PC-GF"} else material
    base_name = f"Anycubic {scaffold_material} @Anycubic Kobra S1 0.4 nozzle"
    donor_name = f"Anycubic {material} @Anycubic Kobra S1 Max {nozzle} nozzle"
    base, base_history = read_source(directory / (base_name + ".json"))
    donor, donor_history = read_source(directory / (donor_name + ".json"))
    for data, name, expected_material, printer in (
        (base, base_name, scaffold_material, "Anycubic Kobra S1 0.4 nozzle"),
        (donor, donor_name, material, f"Anycubic Kobra S1 Max {nozzle} nozzle"),
    ):
        if (data.get("name") != name or scalar(data.get("filament_type")) != expected_material
                or data.get("compatible_printers") != [printer]):
            raise PlanError("Installed reference identity/material/compatibility mismatch")
    values = deepcopy(base)
    decisions, blockers = [], []
    portable = NUMERIC | PLATE_KEYS | {"chamber_temperature"}
    for key, value in donor.items():
        root = key.removesuffix("_HS")
        if root not in portable:
            continue
        n = number(value)
        if root in {"filament_density", "filament_diameter", "filament_max_volumetric_speed", "nozzle_temperature", "nozzle_temperature_initial_layer"} and n <= 0:
            raise PlanError(f"{key} must be positive")
        if root == "filament_diameter" and n != number(base[key]):
            raise PlanError("Reference filament diameters differ")
        if root.startswith("fan_") and root.endswith("speed") and n > 100:
            raise PlanError("Reference fan percentage exceeds 100")
        if root == "filament_max_volumetric_speed":
            n = min(n, number(base[root]))
        values[key] = [str(n)]
        decisions.append({"key": key, "action": "GUIDE", "source": value,
                          "destination": values[key], "reason": "S1 Max material guidance; flow never exceeds S1 scaffold"})
    # Keep explicit HS values and the ordinary values consistent for this HS-only
    # review export. Do not carry contradictory brass-specific overrides.
    for key in list(values):
        if key.endswith("_BRASS"):
            del values[key]
        elif key.endswith("_HS") and key.removesuffix("_HS") in portable:
            root = key.removesuffix("_HS")
            if key not in donor and root in donor:
                # Do not resurrect a stale scaffold HS variant over the newly
                # selected donor value (some S1 filled-material ranges are PLA-like).
                values[key] = deepcopy(values[root])
            else:
                values[root] = deepcopy(values[key])
    values["activate_chamber_temp_control"] = ["0"]
    values["filament_type"] = [material]
    values["filament_vendor"] = ["Anycubic"]
    for key, value in values.items():
        root = key.removesuffix("_HS")
        limit = nozzle_limit if root.startswith("nozzle_temperature") else bed_limit if root in PLATE_KEYS or ("plate_temp" in root) else None
        if limit is not None and number(value) > limit:
            blockers.append(f"{key} exceeds confirmed ceiling {limit} C")
    range_warnings = []
    for key in ("nozzle_temperature_range_low", "nozzle_temperature_range_high", "nozzle_temperature", "nozzle_temperature_initial_layer"):
        if key not in values:
            raise PlanError(f"Reference profile lacks required field {key}")
    low, high = (number(values[k]) for k in ("nozzle_temperature_range_low", "nozzle_temperature_range_high"))
    temps = [number(values[k]) for k in ("nozzle_temperature", "nozzle_temperature_initial_layer")]
    new_low, new_high = min(low, *temps), max(high, *temps)
    if low > high or low - new_low > 15 or new_high - high > 15:
        blockers.append("HS temperatures conflict with donor material range by more than 15 C, or range is inverted")
    else:
        for key, old, new in (("nozzle_temperature_range_low", low, new_low), ("nozzle_temperature_range_high", high, new_high)):
            if old != new:
                values[key] = [str(new)]
                if key + "_HS" in values:
                    values[key + "_HS"] = [str(new)]
                range_warnings.append(f"{key} extended from {old} to {new} C within authorized 15 C tolerance; print temperature unchanged.")
                decisions.append({"key": key, "action": "TRANSLATE", "source": [str(old)], "destination": [str(new)], "reason": range_warnings[-1]})
    warnings = [
        "REVIEW ONLY: S1 Max guidance is not proof of calibration on the original S1.",
        "S1 0.4 scaffold flow ratio, pressure advance, retraction and G-code retained; calibrate for this nozzle/material.",
        "Chamber temperature retained as a recommendation; active chamber control is OFF. Verify actual chamber conditions before printing.",
        "Hardened-steel review preset only; select matching physical nozzle in Anycubic. No firmware changes or installation performed.",
    ]
    warnings.extend(range_warnings)
    # Native restart acceptance shows these scaffold-only variants are dropped.
    # The ordinary range above already carries the HS recommendation. Keep real
    # HS print-temperature overrides, but do not emit redundant range metadata.
    for key in ("nozzle_temperature_range_low_HS", "nozzle_temperature_range_high_HS"):
        if key in values:
            removed = values.pop(key)
            decisions.append({"key": key, "action": "REMOVE", "source": removed,
                              "destination": None, "reason": "Native restart drops this metadata; ordinary range retained"})
            warnings.append(f"{key} omitted: Anycubic drops this metadata at restart; ordinary HS-normalized range retained.")
    if material in {"PC-CF", "PC-GF"}:
        warnings.append("Filled PC uses an unfilled S1 PC calibration scaffold; verify abrasion/nozzle suitability and calibrate before use.")
    digest = hashlib.sha256(json.dumps([base_history, donor_history, values, nozzle], sort_keys=True).encode()).hexdigest()[:10]
    name = f"Anycubic {material} S1-Max-guide @S1 {nozzle} HS {digest} REVIEW"
    for key in ("setting_id", "filament_id", "filament_settings_id", "inherits", "name"):
        values.pop(key, None)
    values.update(name=name, type="filament", **{"from": "User"}, instantiation="true",
                  is_custom_defined="1", inherits="", filament_id=f"S1{digest}",
                  filament_settings_id=[name], compatible_printers=[f"Anycubic Kobra S1 {nozzle} nozzle"],
                  compatible_printers_condition="", compatible_prints=[], compatible_prints_condition="")
    history = [{"S1_scaffold": base_history, "S1_Max_guide": donor_history,
                "destination_base": {"effective_values": base}, "material": material,
                "nozzle": nozzle, "nozzle_ceiling": str(nozzle_limit), "bed_ceiling": str(bed_limit)}]
    return PresetPlan(name, f"S1_{material}_{nozzle}_HS_{digest}_REVIEW.json", values, history, decisions, warnings, blockers)
