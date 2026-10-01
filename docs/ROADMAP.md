# Roadmap

## Milestone 1: inspect and compare (complete)

- Validate and inventory 3MF archives without modifying them.
- Parse and flatten JSON project settings with source locations.
- Categorize likely printer, process, filament, speed, and acceleration keys.
- Produce deterministic human-readable and JSON comparisons.
- Review sanitized output from representative real files.
- Snapshot the installed Anycubic Slicer Next Kobra S1 profiles for every
  supported nozzle without copying them into the repository.
- Resolve the discovered project-settings versus separate-profile precedence
  from Anycubic source and exercise it in a real-file export. (Source ordering
  and automated export complete; regenerated slicer open/slice remains.)

Exit criterion: we understand the concrete MakerWorld/Bambu and Anycubic
Slicer Next schemas well enough to document exact setting equivalences.

## Milestone 2: minimal safe retargeting (implemented; reconciliation audit open)

- Introduce editable KEEP/CLAMP/REPLACE/TRANSLATE rules. (JSON CLAMP override
  implemented; broader rule schema remains.)
- Load an exact installed/reference Anycubic machine JSON separately from the
  source and known-good project 3MF.
- Require a stable discovered target ID for export; filter machine choices by
  actual nozzle diameter, then filter compatible process profiles.
- Resolve slicer `inherits` chains deterministically and report every base and
  overlay source hash; initially support the known-good community 0.4 mm
  hardened-steel overlay without extrapolating it to other diameters.
- Keep unknown settings by default.
- Replace only verified machine identity, machine G-code, and machine limits.
- Clamp verified major speed and acceleration settings with
  `min(source, target)`; never increase a source value.
- Generate dry-run, text, and JSON change reports before archive writing.
- Rebuild to a new output path and validate unchanged model/object/plate data.
  (Implemented with member-level SHA-256 verification.)
- Update plate-level nozzle metadata when changing diameter. For scopes the
  user explicitly retargets, reconcile one unambiguous embedded snapshot only
  when all substantive keys are present in authoritative flattened project
  settings; preserve unselected scopes and block ambiguous or unflattened
  snapshots.
- Open and slice a converted 0.6 mm hardened/PETG project in Anycubic Slicer
  Next 2.0.0.2 without a repair or profile error. (Complete.)

## Milestone 3: materials and multi-colour (implemented)

- Translate exact material/nozzle filament identity, cooling, pressure advance,
  retraction, temperature, and purge settings; clamp volumetric flow downward.
- Validate one-based object/part extruder assignments against the selected
  filament-slot count and block invalid exports.
- Preserve colour, painting, modifiers, supports, geometry, and layout by
  member hash and structural-count invariants; update only nozzle plate JSON.
- Add `SAFE`/`REVIEW` confidence labels to every proposed change.
- Open and slice a four-slot project in Anycubic Slicer Next with slot order,
  colours, and object assignments preserved. (Complete.)
- Open and slice a P2S support project while preserving overhang slowdown.
  (Complete; agreeing boolean arrays translated, mixed values blocked.)
- Resolve conflicting embedded profile precedence without losing model tuning.
  (Implemented from reviewed Anycubic load order and validated on a regenerated
  three-plate export; installed-slicer open/slice acceptance remains.)
- Add an off-by-default `Nice supports - beta` overlay from the known-good
  support project, with finite support-only scope, report provenance, safe
  scalar translation, and downward-only speeds. (Implemented; visual/slice
  acceptance on a non-reference model remains.)

## Milestone 4: desktop interface (complete)

- Keep the conversion engine independent of the UI. (Implemented.)
- Add source/bundle selection, exact nozzle/profile choices, analysis summary,
  hotend-construction identification, report review, and an explicit validated
  create action. (Implemented.)
- Complete visual/runtime QA on a Windows desktop with native app control.
  (Completed for the end-to-end single- and four-slot workflows.)

## TODO: source loading and starting-profile selection

- [x] Loading a different source 3MF resets all converter settings and selections
  from the previous file before analyzing the new one. Verify that stale nozzle,
  process, filament, support, bed, and export choices cannot carry over.
- [x] Combine the current Browse and Load actions into one source-file control.
  Choosing a file through Browse loads it immediately; pressing Enter in the
  source path box attempts to load that path. Show a clear error when the path
  is not a readable 3MF.
- [x] Before conversion, display the source 3MF's available printer/nozzle and
  print-profile information (including effective layer height and other useful
  print settings) so the user can see what the file currently contains.
- [x] After profile discovery, preselect the closest compatible Kobra S1 nozzle
  and print-process choices to the source settings. Show what was matched and
  allow the user to override every suggested selection before review/export.

Implemented on 2026-09-19. The reset covers machine, process, filament, nozzle
hardware, hotend, layer-height, support, plate and output choices while leaving
the reusable profile-bundle list available. Source inspection now shows printer,
process, nozzle/material, heights, line width, walls, infill, supports, plate and
ordered filament slots. Discovery suggests a diameter/material-aware machine,
the closest layer-height/line-width/process-name match and each closest
material-compatible filament. All selectors remain editable.

## TODO: independent layer height and accurate export profiles

- [x] Preserve source layer height by default, add an explicit CLI/GUI option
  to use the selected process height, validate both policies against machine
  bounds, and warn about object/variable-layer overrides.
- [x] Allow a custom layer height independently of available process presets
  through CLI `--layer-height` and the GUI custom-mm field. Source first-layer
  height is retained; machine bounds are checked and overrides need Preview review.
- [x] Make compatible 0.18, 0.20, and 0.24 mm process choices usable with a
  0.6 mm nozzle without requiring a preset labelled 0.30 mm just to obtain
  suitable line widths. Resolve widths from verified nozzle/profile evidence,
  not an assumed universal formula. The profile list now shows both effective
  layer and nominal line width; installed 0.18/0.24 use 0.62 mm while the
  installed 0.20 preset deliberately uses 0.42 mm.
- [x] Label exported effective settings accurately when source height is
  retained: distinguish the base
  preset name from the actual nozzle, nozzle material, and layer height in
  the UI, report, and exported profile identity. A 0.20 mm export must not
  misleadingly appear to use 0.30 mm layers; preserve base-preset provenance.
- [x] Flag suspicious nozzle/line-width combinations before export, including
  the installed 0.6 mm / 0.20 mm preset containing 0.42 mm line widths. Present
  the actual values and an explicit resolution choice; do not silently switch
  presets or declare all narrower-than-nozzle widths invalid. Exact process
  selection is the resolution choice and narrower widths produce a warning.
- [x] Add regression tests based on the cupholder conversion: 0.6 mm hardened
  steel, retained 0.20 mm layers, verified 0.62 mm widths, and truthful naming;
  cover explicit 0.18/0.24 mm choices and incompatible-height warnings too.
- [x] Complete installed-slicer acceptance for the 0.25 and 0.8 mm extremes.
  Current PETG real-file exports pass archive/hash/structure validation and use
  their selected 0.10 and 0.40 mm process heights respectively; native open,
  stock-filament visibility and Preview slicing passed on 2026-09-14.

## TODO: explicit nozzle hardware variants

- [ ] Represent physical nozzle material independently when no exact profile
  exists, including installed-slicer acceptance. GUI/CLI declaration and
  REVIEW export overrides are implemented; see NOZZLE_HARDWARE.md. The original
  hardware coverage requirement remains:
  the installed profiles expose 0.25/0.4 as brass and 0.6/0.8 as
  hardened steel, while the user owns brass, hardened-steel, and bimetal
  hardware across all sizes. Do not synthesize a thermal/flow profile merely by
  renaming `nozzle_type`; require verified profile evidence or a clearly
  reviewable hardware override policy.

## TODO: stock filament visibility for custom nozzle profiles

- [x] Fix exported custom printer-profile identity/inheritance so Anycubic
  Slicer can associate stock filaments with the matching official nozzle
  profile. Reproduce the reported case where only unrestricted custom PA
  profiles appear for the custom 0.6 mm hardened-steel printer. The converter
  now rebases the overlay on the nozzle-matched official parent and a regression
  proves only matching stock filaments are discovered; installed-slicer UI
  confirmation failed on 2026-09-06 (only PETG shown). Investigation found
  `PresetBundle.cpp` project loading overwrites plain `inherits` using
  `inherits_group[num_filaments + 1]`; that vector was absent in the export.
  The converter now writes the machine parent at that index while preserving
  other scope entries, pads short vectors like the loader, and rejects malformed
  or oversized vectors. Regression tests and an otherwise-identical cupholder
  candidate pass automated checks. The user confirmed the repaired 0.6 mm
  cupholder opens, slices and has no missing filaments on 2026-09-06. Native
  .25/.4/.8 stock-list visibility is now recorded as passed; see
  PROJECT_INHERITANCE_AUDIT.md for the separate difference-mask
  import-fidelity repair.
- [x] Replace stale source default-filament/process references with verified
  destination references. The cupholder export retained Bambu defaults, and
  the community 0.6 mm machine inherits a 0.4 mm default filament reference.
- [x] Preserve effective custom machine settings while repairing compatibility;
  do not blindly rebase onto another machine or remove filament restrictions
  globally. Do not modify the user's installed custom PA profiles.
- [x] Test stock filament visibility separately from the converter's discovery
  list: matching 0.6 mm stock presets should be available after import, with
  source material assignments retained and unrelated nozzle profiles excluded.
  Cover other supported custom nozzle sizes and verify installed-slicer
  behaviour only when file/source-based tests cannot establish it. Native
  .25/.4/.8 stock lists were visible on 2026-09-14; .6 was confirmed earlier.

## Required real-world coverage

Use redistributable or locally ignored fixtures for one-colour, multi-colour,
painted/tree supports, modifiers, variable layers, ironing, multiple plates,
slow intentional tuning, high-speed profiles, and PLA/PETG/ASA or ABS.

## New request: standalone filament profiles

- [x] Add a separate Filament profiles tab for batch conversion of external
  Bambu/Orca JSON presets and importable Anycubic user-preset output.
- [x] Support Siddament downloads as the first real vendor corpus, with
  per-material selection, exact destination nozzle compatibility, safe G-code
  replacement, calibration warnings and non-overwriting import. Fifteen 0.6 HS
  presets imported, persisted and verified after fresh-session reopen;
  unmatched bases and material calibration remain separate acceptance work.
- [x] Keep existing 3MF ordered filament reassignment unchanged.

See FILAMENT_PROFILE_IMPORT.md for verified sample format, implemented beta
workflow and pending import acceptance. JSON/folder batch review and fresh-folder
export are implemented across all four nozzle sizes. ZIP/`.orca_filament` input
and native GUI bundle review are verified. Limited INI input is implemented
with automated export coverage; native INI acceptance, unmatched base
mapping remains pending. Backed-up, opt-in direct installation and quarantined
rollback were added on 2026-09-23 alongside the manual Import Configs path.
The active account now has 65 Siddament REVIEW identities across four nozzle
sizes; three 0.25 mm materials lack suitable bases. Native verification of the
new direct-install batch and material calibration remain pending.
