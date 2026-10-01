# S1 Max guided engineering presets - 2026-09-07

User authorized S1 Max profiles as guidance for missing S1 nozzle sizes and
PC-CF/PC-GF, including retention of chamber-temperature values.

Implemented a separate explicit REVIEW generator, not an automatic fallback in
the existing converter. `tools/export_engineering_guides.py` reads the installed
Anycubic filament resources. It never installs profiles or changes firmware.

Policy:

- Original S1 0.4 material profile supplies calibration, retraction and macros.
  PC-CF/PC-GF explicitly use the unfilled S1 PC calibration scaffold, with a warning.
- Same-size S1 Max profile supplies allowlisted material temperatures, cooling,
  physical material properties and maximum flow. Flow cannot exceed the S1
  scaffold's ceiling. These are not calibrated nozzle-size conversions.
- Chamber temperature is preserved; active chamber control is explicitly off.
  The numeric recommendation does not establish actual chamber temperature or
  heating capability. No Max machine settings or macros are transplanted.
- HS-specific temperatures are made consistent with ordinary values; brass
  overrides are removed from these HS-only review exports.
- Standalone user JSONs have exact original-S1 nozzle compatibility and unique
  REVIEW identities. No dependency on an S1 Max installed preset remains.
- Current effective ceilings remain 320 C nozzle / 110 C bed. Range metadata may
  extend by at most 15 C with a warning; larger conflicts block export.
- No 0.25 Max donor exists in the examined resources, so 0.25 is rejected.

## Generated evidence

`reports/S1-filaments-j7d442cn/` contains 18 review presets: PC, PLA-CF, PA6-CF,
PET-CF, PC-CF and PC-GF at 0.4, 0.6 and 0.8 mm. Individual JSONs,
`importable-presets.zip` and `conversion-report.txt` are provided.
The earlier `S1-filaments-n31vdc3s` is superseded: its six blocked cases exposed
stale HS-specific temperature ranges in the original S1 scaffold. The adapter
now synchronizes such variants with donor values when the donor has no separate
HS override, instead of letting old scaffold variants override donor guidance.
No print temperatures were silently lowered to force acceptance. All 18 final
plans have no blockers under the current 320/110 ceilings; 147 tests pass.

Native import of all 18 presets succeeded. They are saved under the installed
user `filament/base` folder. All six materials are visible in the original S1
0.6 dropdown. The expanded read-only audit includes HS variants and chamber
temperature/control, with no differences; the 29 previously inventoried
root-level presets remain unchanged. Evidence:
`reports/S1-filaments-j7d442cn/installed-verification-hs-chamber.json`.
The first audit's missing identities were an audit-location error, not an import
failure: standalone user bases are stored separately from inherited presets.
Restart/slice acceptance and physical calibration remain pending.
The existing Siddament imports and 3MF reassignment workflow are unchanged.

Example generation (set PYTHONPATH=src):

```powershell
python tools/export_engineering_guides.py reports --nozzle 0.6 --export-ready
```

Omit `--export-ready` to require every selected material to pass. The generator
is not yet exposed in the GUI and does not automatically resolve missing
Siddament bases; that integration follows acceptance of these review bases.
