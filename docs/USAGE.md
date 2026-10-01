# CLI usage

Saved S1 projects can be added through the profile-bundle picker or `--bundle`.
Valid flattened projects identifying Kobra S1 and Klipper appear as `reference`
targets. Select that target to expose its saved process tuning. Its explicit
machine settings override the official matching-nozzle parent; source model
walls, supports, geometry and layout remain source-owned. Reference filament
slots appear in the separate material-filtered filament selectors, each labelled
with its original slot number. Two slots sharing a name remain distinct choices.
Only the finite material-setting allowlist is imported; malformed slot arrays
are rejected. Selected reference flow limits still clamp source flow downward.

Use `--layer-height 0.18` to choose a custom height while retaining the selected
process's line widths and the source first-layer height. The GUI has the same
custom-mm field. Leave it blank to preserve source height, or use the existing
selected-process-height checkbox instead; the two overrides cannot be combined.
Custom heights are checked against machine limits and receive a custom process
identity. Object-specific and variable-layer heights still need Preview review.

The safest workflow is discovery, dry-run, then export. Stable IDs include
profile hashes, so copy them from the current command output rather than
guessing them.

```powershell
$bundle = "C:\Users\USER\Downloads\Profiles+0.2+0.6+0.8+V2.3mf"

python -m s1_optimizer targets --nozzle 0.6 --bundle $bundle
python -m s1_optimizer processes --target-id TARGET_ID --bundle $bundle
python -m s1_optimizer filaments --target-id TARGET_ID --material PETG --bundle $bundle

python -m s1_optimizer optimize source.3mf `
  --target-id TARGET_ID `
  --process-id PROCESS_ID `
  --filament-id FILAMENT_ID `
  --bundle $bundle `
  --dry-run

python -m s1_optimizer optimize source.3mf `
  --target-id TARGET_ID `
  --process-id PROCESS_ID `
  --filament-id FILAMENT_ID `
  --hotend-type all-metal `
  --bundle $bundle
```

To opt into the reference-derived support overlay, add
`--nice-supports-beta`. The GUI provides the equivalent unchecked-by-default
`Nice supports - beta` checkbox. It intentionally enables build-plate-only tree
supports; review every plate in Preview. Details: `NICE_SUPPORTS_BETA.md`.

By default, the converter preserves the source layer height. If that differs
from the selected process preset, the output uses a custom label that records
both the retained height and the base preset. Add
`--use-process-layer-height` to instead apply the selected process's project
and initial-layer heights. The GUI exposes the same unchecked-by-default
choice. Always review object-specific and variable-layer overrides in Preview.

Without `--output`, export creates
`source_KobraS1_<diameter>mm.3mf` beside the source. A text or JSON change
report is created beside it. Existing files are never overwritten.

For multi-slot projects, one filament ID is repeated across every source slot
only when all source material types match it. Otherwise repeat `--filament-id`
in source-slot order. A material-family mismatch is refused.

## What export changes

- verified machine identity, geometry, G-code, and machine-limit settings;
- selected process identity;
- numeric speed and acceleration values only when above the selected process;
- nozzle-dependent line widths and machine min/max layer bounds;
- selected, material-matched filament identity, temperature, bed temperature,
  cooling, pressure advance, retraction, and purge-related values;
- filament maximum volumetric flow only when above the selected filament;
- plate JSON nozzle metadata when the selected nozzle differs.

Everything else remains unchanged. The writer hashes every untouched member,
validates core 3MF/XML/JSON structure, and checks model/object/plate counts.

## Review boundary

Material-owned temperature, cooling, pressure advance, retraction, and purge
values come from each explicitly selected exact material/nozzle profile and are
reported with `REVIEW` confidence. Lower source volumetric-flow limits remain
lower. Object/part extruder assignments are preserved, validated as one-based
slot references, and block export if they fall outside the selected slot count.
The output is a slicer project and must still be reviewed and sliced before
printing.

An optional `--hotend-max-temp` CLI value, or the GUI's hotend ceiling field,
can impose an explicit user-provided maximum nozzle temperature. It only lowers
the selected filament temperature values. Export is blocked when that ceiling is below the
selected filament profile's stated minimum; the program never invents a limit
for PTFE-lined, all-metal, or aftermarket ceramic hardware.

Use `--hotend-type` (or the GUI selector) to record `ptfe-lined`, `all-metal`,
`aftermarket-ceramic`, `other`, or `unspecified` in the change report. This
identification never implies a temperature limit.

Reviewed Anycubic source registers embedded presets first and applies the full
`project_settings.config` afterward. Accordingly, a lone foreign embedded
`machine_settings`, `process_settings`, or `filament_settings` snapshot may be
removed only when that scope is explicitly retargeted and every substantive
snapshot key is present in the authoritative flattened project config.
Different values are expected after retargeting. Unselected scopes are
preserved; multiple candidates, excess selected filament snapshots, or even one
unflattened value remain export blockers. This prevents a hidden source preset
from overriding the selected target without discarding untargeted source data.

After this reconciliation, Anycubic Slicer Next may display the inherited base
machine name with an asterisk instead of the community overlay's full name.
The effective Printer Settings and the change report remain authoritative; for
the validated 0.4 mm community overlay, the slicer showed `Hardened steel` as
the effective nozzle type.
