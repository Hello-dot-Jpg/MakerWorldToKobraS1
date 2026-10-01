"""Standalone filament JSON conversion. Never modifies installed slicer presets."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
import tempfile
import shutil
import zipfile

from .constants import MAX_STRUCTURED_MEMBER_BYTES
from .errors import PlanError
from .filaments import ResolvedFilamentTarget, nozzle_meets_hrc
from .parser import decode_json
from .resolution import ResolvedMachineTarget
from .preset_sources import ArchivePreset, read_bundle_source
from .preset_ini import IniPreset, read_ini_source


# Explicit material-owned fields only. Foreign macros/calibration/machine fields
# are deliberately not copied, even when their names exist in both slicers.
NUMERIC = {
    "filament_density", "filament_cost", "filament_diameter",
    "filament_max_volumetric_speed", "nozzle_temperature",
    "nozzle_temperature_initial_layer", "nozzle_temperature_range_low",
    "nozzle_temperature_range_high", "fan_min_speed", "fan_max_speed",
    "close_fan_the_first_x_layers", "fan_cooling_layer_time",
    "slow_down_layer_time", "slow_down_min_speed", "overhang_fan_speed",
    "full_fan_speed_layer", "required_nozzle_HRC",
}
PLATE_KEYS = {f"{plate}_temp{suffix}" for plate in
              ("cool_plate", "eng_plate", "hot_plate", "textured_plate", "supertack_plate")
              for suffix in ("", "_initial_layer")}
TEXT = {"filament_vendor", "filament_type"}
IDENTITY = {"name", "inherits", "type", "from", "version", "instantiation",
            "filament_settings_id", "filament_id", "setting_id", "is_custom_defined",
            "compatible_printers", "compatible_printers_condition",
            "compatible_prints", "compatible_prints_condition"}


def scalar(value):
    if isinstance(value, list) and len(value) == 1:
        value = value[0]
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        raise PlanError("Expected a scalar or one-element filament value")
    return str(value)


def number(value):
    try:
        result = Decimal(scalar(value))
        if not result.is_finite() or result < 0:
            raise ValueError()
        return result
    except (InvalidOperation, ValueError) as exc:
        raise PlanError(f"Invalid non-negative numeric value: {value!r}") from exc


def read_source(path: Path, seen=()):
    if isinstance(path, ArchivePreset):
        return read_bundle_source(path)
    if isinstance(path, IniPreset) or Path(path).suffix.lower() in {".ini", ".config"}:
        return read_ini_source(path)
    path = Path(path).resolve()
    if path in seen or len(seen) >= 32:
        raise PlanError("Source filament inheritance cycle or depth limit")
    if path.suffix.lower() != ".json" or path.stat().st_size > MAX_STRUCTURED_MEMBER_BYTES:
        raise PlanError("Select a bounded standalone JSON filament preset")
    with path.open("rb") as stream:
        raw = stream.read(MAX_STRUCTURED_MEMBER_BYTES + 1)
    if len(raw) > MAX_STRUCTURED_MEMBER_BYTES:
        raise PlanError("Source JSON exceeds the structured-member size limit")
    data = decode_json(raw)
    if not isinstance(data, dict):
        raise PlanError("Filament JSON must be an object")
    parent = data.get("inherits", "")
    if not isinstance(parent, str):
        raise PlanError("Filament inherits must be a string")
    values, provenance = {}, []
    if parent:
        if any(c in parent for c in '/\\:') or parent in {".", ".."}:
            raise PlanError("Inherited filename must stay in the source folder")
        parent_path = path.parent / (parent + ".json")
        if parent_path.resolve().parent != path.parent:
            raise PlanError("Inherited profile resolves outside source folder")
        if not parent_path.is_file():
            raise PlanError(f"Missing source parent: {parent}.json")
        values, provenance = read_source(parent_path, (*seen, path))
    values.update(data)
    provenance.append({"file": str(path), "sha256": hashlib.sha256(raw).hexdigest()})
    return values, provenance


@dataclass
class PresetPlan:
    name: str
    filename: str
    values: dict
    provenance: list
    decisions: list
    warnings: list
    blockers: list

    def to_dict(self):
        return asdict(self)


def convert_preset(source: Path, machine: ResolvedMachineTarget,
                   base: ResolvedFilamentTarget, *, max_nozzle_temp=None,
                   max_bed_temp=None, nozzle_material="profile",
                   hotend="unspecified", ceramic_firmware_confirmed=False,
                   accept_base_material=False) -> PresetPlan:
    source = source if isinstance(source, (ArchivePreset, IniPreset)) else Path(source)
    data, provenance = read_source(source)
    material = scalar(data.get("filament_type", ""))
    original_material = material
    if accept_base_material:
        if getattr(base.filament, "source_kind", None) != "explicit":
            raise PlanError("Material correction requires an explicitly selected destination base")
        material = base.filament.material
    if not material or material != base.filament.material:
        raise PlanError(f"Source material {material!r} does not match destination base {base.filament.material!r}")
    if base.filament.nozzle_diameter != machine.target.nozzle_diameter:
        raise PlanError("Destination filament and machine nozzle sizes differ")
    if nozzle_material not in {"profile", "hardened-steel", "brass", "stainless-steel", "bimetal"}:
        raise PlanError("Unknown physical nozzle material")
    values = {}
    decisions, blockers = [], []
    warnings = ["REVIEW: not calibrated for this S1 nozzle/hotend. Destination flow ratio, pressure advance, retraction and G-code replace source calibration/macros.",
                "Review filled/abrasive material suitability and nozzle diameter; material names alone do not prove compatibility."]
    if any("mappings" in item for item in provenance):
        warnings.append("INI beta: only explicitly mapped scalar material fields are portable. Cooling, calibration and macros use the destination base; review omitted fields in the audit.")
        if any(mapping.get("review") for item in provenance for mapping in item.get("mappings", [])):
            warnings.append("INI bed temperatures apply ONLY to Textured PEI Plate. Other plate temperatures remain inherited from the destination base; review them before selecting another plate.")
    # These are this project's user-reported equipment limits, not manufacturer
    # ratings or a claim that a material is suitable at the maximum temperature.
    if hotend not in {"unspecified", "ptfe-lined", "all-metal", "ceramic"}:
        raise PlanError("Unknown hotend construction")
    if ceramic_firmware_confirmed and hotend != "ceramic":
        raise PlanError("Ceramic firmware confirmation requires the ceramic hotend")
    declared_ceiling = {"ptfe-lined": 300, "all-metal": 320,
                        "ceramic": 350 if ceramic_firmware_confirmed else 320}.get(hotend)
    if declared_ceiling is not None:
        if max_nozzle_temp in (None, ""):
            max_nozzle_temp = str(declared_ceiling)
        elif number(max_nozzle_temp) > declared_ceiling:
            blockers.append(f"Entered nozzle ceiling exceeds user-reported {hotend} limit {declared_ceiling} C")
        warnings.append(f"User-reported {hotend} ceiling: {declared_ceiling} C; not independently verified. This does not change firmware or print temperatures.")
        if hotend == "ceramic":
            warnings.append("350 C requires an explicitly confirmed firmware change; otherwise ceramic is limited to 320 C.")
    limits = {}
    for key, raw in (("nozzle", max_nozzle_temp), ("bed", max_bed_temp)):
        if raw is None or raw == "":
            blockers.append(f"Confirm the physical {key} temperature ceiling before exporting")
        else:
            limits[key] = number(raw)
            if limits[key] <= 0:
                raise PlanError("Physical temperature ceilings must be positive")
    for key, old in sorted(data.items()):
        action, new, reason = "OMIT", None, "Not an approved portable material setting"
        if key in IDENTITY:
            action, reason = "REPLACE", "Generate destination identity/compatibility"
        elif key in TEXT:
            new = [scalar(old)]
            action, reason = "KEEP", "Material identity"
            if key == "filament_type" and accept_base_material:
                new = [material]
                action, reason = "TRANSLATE", "User explicitly accepted the reviewed base material instead of the source declaration"
        elif key in NUMERIC | PLATE_KEYS and key in base.effective_values:
            try:
                n = number(old)
                if key in {"filament_density", "filament_diameter", "filament_max_volumetric_speed", "nozzle_temperature", "nozzle_temperature_initial_layer"} and n <= 0:
                    raise PlanError(f"{key} must be positive")
                if key == "filament_diameter" and n != number(base.effective_values[key]):
                    raise PlanError("Filament diameter differs from destination")
                if "fan_" in key and key.endswith("speed") and n > 100:
                    raise PlanError("Fan percentage exceeds 100")
                new = [str(n)]
                action, reason = "KEEP", "Supported material setting; review for target hardware"
                if key == "filament_max_volumetric_speed":
                    ceiling = number(base.effective_values[key])
                    if ceiling <= 0:
                        raise PlanError("Destination volumetric ceiling must be positive")
                    new = [str(min(n, ceiling))]
                    action, reason = "CLAMP", "Never exceed destination material flow ceiling"
                thermal = "nozzle" if key.startswith("nozzle_temperature") else "bed" if key in PLATE_KEYS else None
                if thermal in limits and n > limits[thermal]:
                    blockers.append(f"{key}={n} exceeds physical {thermal} ceiling {limits[thermal]}; choose appropriate hardware/material, not silent temperature reduction")
                values[key] = new
            except PlanError as exc:
                blockers.append(f"{key}: {exc}")
                action, reason = "BLOCK", str(exc)
        if key in TEXT:
            values[key] = new
        if action == "OMIT" and key in base.effective_values:
            action, new, reason = "REPLACE", base.effective_values[key], "Retain destination default through inheritance"
        elif action == "OMIT" and key in NUMERIC | PLATE_KEYS:
            reason = "Approved material key is absent from destination base; not copied"
            warnings.append(f"REVIEW: {key} is not present in the destination base and was omitted; verify the effective setting before use.")
        decisions.append({"key": key, "action": action, "source": old, "destination": new, "reason": reason})
    hrc = scalar(data.get("required_nozzle_HRC", "0"))
    physical_type = machine.target.nozzle_type if nozzle_material == "profile" else nozzle_material
    explicit_hrc = machine.effective_values.get("nozzle_hrc") if nozzle_material == "profile" else None
    if nozzle_meets_hrc(physical_type, hrc, explicit_hrc) is not True:
        blockers.append(f"Nozzle hardness is insufficient or unverified for source requirement HRC {hrc}")
    if nozzle_material != "profile":
        warnings.append(f"Physical nozzle declared {nozzle_material}; filament import does not change the slicer's machine nozzle-type setting. Select matching hardware in Anycubic before printing.")
    for key in ("nozzle_temperature", "nozzle_temperature_initial_layer", "filament_max_volumetric_speed"):
        if key not in values:
            blockers.append(f"Source needs an explicit supported {key}")
    # INI sources often omit range metadata. Validate the range the slicer will
    # actually inherit, rather than skipping the check for those sources.
    effective_range = {**base.effective_values, **values}
    if all(k in effective_range for k in ("nozzle_temperature_range_low", "nozzle_temperature_range_high")):
        lo, hi = (number(effective_range[k]) for k in ("nozzle_temperature_range_low", "nozzle_temperature_range_high"))
        if lo > hi:
            blockers.append("Declared nozzle temperature range is inverted")
        else:
            temperatures = [number(values[k]) for k in
                            ("nozzle_temperature", "nozzle_temperature_initial_layer") if k in values]
            required_lo = min([lo, *temperatures])
            required_hi = max([hi, *temperatures])
            if lo - required_lo > 15 or required_hi - hi > 15:
                blockers.append("Nozzle temperatures lie more than 15 C outside the stated material range")
            else:
                for key, old_bound, new_bound in (
                    ("nozzle_temperature_range_low", lo, required_lo),
                    ("nozzle_temperature_range_high", hi, required_hi),
                ):
                    if new_bound == old_bound:
                        continue
                    # Physical limits were already checked against every print
                    # temperature. Extending metadata never overrides those checks.
                    message = (f"REVIEW: {key} extended from {old_bound} to {new_bound} C "
                               f"({abs(new_bound - old_bound)} C) to include the source print temperatures; "
                               "within the user-authorized 15 C tolerance. Print temperatures are unchanged.")
                    values[key] = [str(new_bound)]
                    warnings.append(message)
                    for decision in decisions:
                        if decision["key"] == key:
                            decision.update(action="TRANSLATE", destination=values[key], reason=message)
                            break
                    else:
                        decisions.append({"key": key, "action": "TRANSLATE", "source": None,
                                          "destination": values[key], "reason": message + " Original bound inherited from destination base."})
    # Check the effective destination too, not just explicit source fields: a
    # plate temperature inherited from the base must not bypass physical limits.
    # Every export is detached below. Keep Anycubic's nozzle-material variants
    # aligned before flattening, rather than reviving the base temperatures.
    for key in base.effective_values:
        root = key.removesuffix("_HS").removesuffix("_BRASS")
        if root != key and root in values and root in NUMERIC | PLATE_KEYS:
            values[key] = values[root]
    for root in ("nozzle_temperature", "nozzle_temperature_initial_layer"):
        if root in values:
            for suffix in ("_HS", "_BRASS"):
                values[root + suffix] = values[root]
    values["activate_chamber_temp_control"] = ["0"]
    for key, raw in {**base.effective_values, **values}.items():
        thermal_key = key.removesuffix("_HS").removesuffix("_BRASS")
        thermal = "nozzle" if thermal_key in {"nozzle_temperature", "nozzle_temperature_initial_layer", "nozzle_temperature_range_high"} else "bed" if thermal_key in PLATE_KEYS else None
        if thermal in limits:
            try:
                if number(raw) > limits[thermal]:
                    message = f"Effective {key} exceeds physical {thermal} ceiling {limits[thermal]}"
                    if not any(key in b and f"physical {thermal} ceiling" in b for b in blockers):
                        blockers.append(message)
            except PlanError as exc:
                blockers.append(f"Cannot verify effective {key}: {exc}")
    source_name = scalar(data.get("name", source.stem)).split(" @")[0][:100]
    # Anycubic uses the display name as its persisted JSON filename. A safe
    # export filename alone is insufficient: '/' imports into memory but fails
    # to save. Keep the original in provenance and normalize the identity too.
    original_name = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f]', "_", source_name).strip(" .") or "Imported filament"
    if original_name != source_name:
        message = "Preset name normalized for Anycubic/Windows persistence; original name remains in the source audit."
        warnings.append(message)
        decisions.append({"key": "name", "action": "TRANSLATE", "source": source_name,
                          "destination": original_name, "reason": message})
    digest = hashlib.sha256(json.dumps(["detached-v1", provenance, machine.to_dict(), base.to_dict(), values, nozzle_material], sort_keys=True).encode()).hexdigest()[:10]
    name = f"{original_name} @S1 {machine.target.nozzle_diameter} {physical_type} {digest} REVIEW"
    values.update({"type": "filament", "from": "User", "instantiation": "true",
                   "name": name, "filament_settings_id": [name], "filament_id": f"S1{digest}",
                   "inherits": base.filament.label, "version": "1.0.0.0",
                   "compatible_printers": [machine.target.label], "compatible_printers_condition": "",
                   "compatible_prints": [], "compatible_prints_condition": ""})
    # Native Anycubic project save/reopen can omit the inherited preset's
    # difference mask and silently restore system values under the custom name.
    # Preserve destination defaults explicitly; foreign macros are never used.
    values = {**base.effective_values, **values}
    values.pop("setting_id", None)
    values.update(inherits="", is_custom_defined="1")
    warnings.append("Destination base flattened into this REVIEW export to preserve settings on project reopen; no parent installation dependency. Calibrate destination defaults before printing.")
    if accept_base_material:
        values["filament_type"] = [material]
        warnings.append(f"Explicit material correction: {original_material!r} -> {material!r}. Verify the actual spool; source file unchanged.")
        provenance.append({"material_correction": {"source": original_material,
                            "destination": material, "explicitly_accepted": True}})
    filename = "S1_" + re.sub(r"[^A-Za-z0-9._-]+", "_", name) + ".json"
    provenance.append({"destination_machine": machine.to_dict(), "destination_base": base.to_dict(), "physical_nozzle": physical_type, "confirmed_nozzle_ceiling": max_nozzle_temp, "confirmed_bed_ceiling": max_bed_temp,
                       "hotend": hotend, "ceramic_firmware_confirmed": ceramic_firmware_confirmed,
                       "hotend_limit_source": "user-reported 2026-09-07" if declared_ceiling else None})
    return PresetPlan(name, filename, values, provenance, decisions, warnings, blockers)


def render_preset_review(plans: list[PresetPlan], errors=()) -> str:
    """Put actionable messages ahead of the detailed provenance/field audit."""
    lines = ["FILAMENT PRESET REVIEW - no installed presets modified"]
    for error in errors:
        lines.append(f"BLOCKED: {error}")
    for plan in plans:
        lines.extend(("", plan.name))
        lines.extend(f"BLOCKED: {item}" for item in plan.blockers)
        lines.extend(plan.warnings)
    lines.extend(("", "DETAILED FIELD AUDIT", json.dumps(
        [p.to_dict() for p in plans], ensure_ascii=False, indent=2)))
    return "\n".join(lines)


def export_presets(plans: list[PresetPlan], parent: Path) -> Path:
    """Publish a fresh directory; no overwrite or installed-profile writes."""
    if not plans or any(p.blockers for p in plans):
        raise PlanError("Review and resolve all selected preset blockers before export")
    if len({p.filename.casefold() for p in plans}) != len(plans):
        raise PlanError("Duplicate output identities; remove duplicate selections")
    parent = Path(parent).resolve()
    if not parent.is_dir():
        raise PlanError("Choose an existing output folder")
    # A unique folder avoids both filesystem overwrites and filename races.
    folder = Path(tempfile.mkdtemp(prefix="S1-filaments-", dir=parent))
    try:
        preset_bytes: list[tuple[str, bytes]] = []
        for plan in plans:
            if Path(plan.filename).name != plan.filename or any(c in plan.filename for c in '/\\:'):
                raise PlanError("Unsafe output filename")
            raw = json.dumps(plan.values, ensure_ascii=False, indent=2).encode("utf-8")
            with (folder / plan.filename).open("xb") as stream:
                stream.write(raw)
            preset_bytes.append((plan.filename, raw))
        with zipfile.ZipFile(folder / "importable-presets.zip", "x", compression=zipfile.ZIP_DEFLATED) as bundle:
            for filename, raw in preset_bytes:
                bundle.writestr(filename, raw)
        with (folder / "conversion-report.txt").open("x", encoding="utf-8") as stream:
            stream.write("REVIEW ONLY. Import importable-presets.zip or individual JSONs using Anycubic File > Import > Import Configs.\nNo installed presets were modified.\n\n")
            stream.write(render_preset_review(plans))
    except Exception:
        if folder.resolve().parent == parent and folder.name.startswith("S1-filaments-"):
            shutil.rmtree(folder)  # Only the exact fresh directory created above.
        raise
    return folder
