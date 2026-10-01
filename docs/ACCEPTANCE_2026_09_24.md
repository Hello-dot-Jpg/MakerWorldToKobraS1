# Local beta acceptance continuation — 2026-09-24

Status: **not accepted**. No printing, firmware change, GitHub publication,
live preset rollback, or overwrite of a saved project occurred.

## Siddament installation

- The user's prior slicer session was confirmed closed before native work.
  Anycubic Slicer Next 2.0.0.3 restarted. The installed account is `789721`.
- `reports/S1-preset-backup-a5hvhnwv/install-manifest.json` remains installed.
  All 50 new files and all 106 pre-existing root files still match the
  manifest's SHA-256 hashes after the restart.
- Full-field comparison of the 45 plans in `reports/S1-filaments-bns_a95e`
  and three plans in `reports/S1-filaments-2b472xxk` found zero differences
  from their installed root JSONs. This is file-level persistence, not proof
  that the slicer selected the intended preset or that any material is tuned.
- On the 0.4 hardened-steel printer, the filament menu visibly contained
  Siddament user presets (including Matte PLA, PC-ABS, PC-CF, PETG, PLA-CF,
  TPU) and stock Anycubic choices (including ABS, ASA and PC). The complete
  native menu and saved fields were not checked across all four nozzle sizes.
- Two newly installed 0.6 presets, PC-CF `544a887fdb` and PLA-CF
  `11eabdc2c8`, duplicate existing identities in `filament/base`. The strict
  audit sees two candidates for each. Their effective native precedence and
  field persistence are unproven. The installer now checks `base/` for future
  collisions, with an isolated regression test. The live duplicates were not
  deleted or rolled back.
- The 15 older 0.6 HS presets from `reports/S1-filaments-8rbt5e9w` differ
  from their export plans on `slow_down_layer_time_HS`; seven also differ on
  `fan_max_speed_HS`. ASA and ASA-CF additionally differ on
  `nozzle_temperature_HS` and `nozzle_temperature_initial_layer_HS`. For
  example, installed ASA has fan max 50 vs exported 20, nozzle 290 vs 270 C,
  initial nozzle 280 vs 270 C, and slowdown 3 vs 10 s. Do not treat those
  older profiles as verified exports until reconciled.
- Collision refusal and rollback-to-quarantine were exercised against an
  isolated temporary account-store copy by the five installer tests; the
  live installation was not rolled back.

## Communication Cards

- Opened `reports/CommunicationCardsV2_KobraS1_0.4HS_PLA_REVIEW.3mf` in
  Anycubic. The archive has 14 plates and seven ordered colour/filament slots;
  the native project displayed the seven slots and plate list.
- Its Modified G-code warning named only filament start/end fields. All seven
  start values are the `; filament start gcode` comment and all seven end
  values are the `; filament end gcode` comment. No executable command is in
  those fields. Confirmed this one warning under the user's condition.
- The native printer selector displays a modified stock `Anycubic Kobra S1
  0.4 nozzle` label; the archive itself declares `nozzle_type=hardened_steel`,
  0.4 mm diameter, and a hardened-steel hardware-override printer ID. The
  native UI label alone does not prove or disprove that effective hardware
  override. The selected plate showed Textured PEI at plate level.
- Plate 1, **Okay**, sliced successfully with white and green (slots 1 and
  4), one filament change, estimated 21m11s. This is the only verified native
  plate slice in this run.
- Selecting plate 2, **Help**, showed a red error toast: `An object is laid
  over the boundary of the ...`; the Preview sidebar also displayed
  `Failed 1/8`. Several thumbnails were marked red. No corrective placement
  edits or additional slice attempts were made after this unexpected result.
  The file is not accepted as a complete 14-plate project.

## Remaining manifest fixtures and G-code checks

The five previously outstanding manifest-native checks remain **untested in
this run**: official 0.6, ironing/negative volumes, representative ABS/PETG
hose-holder plates, ASA clamps, and painted supports. Baseline native coverage
remains 8/13, not 13/13.

Read-only G-code audit found that the ASA and painted-support 3MF machine
scripts match the corresponding installed official S1 0.4 effective scripts;
no Bambu-specific `M620`, `M621`, `G392` or `M1007` markers were found.
Their reviewed filament start/end scripts likewise match official Anycubic
profiles. The old CLI out-of-print-area Y=255/255.45 and Y=270 moves are in
the installed official S1 0.4 before-layer and end scripts (purge/park), not
model toolpath, but this does not prove the physical travel envelope or clear
the separate exclude-triangles log. Do not turn those static comparisons into
native fixture passes. If a future warning lists any other commands, stop
that fixture for review.

## Code and package checks

- `preset_install.py` now rejects an exported preset whose name is already
  present as JSON or INFO in either the account root or `base/`.
- Installer tests use the project's standard `unittest` runner, not an
  undeclared `pytest` dependency. The Python 3.13 full suite passes 185 tests.
- `tools/verify_release.py` passed at
  `reports/release-check-gbc2c8fx/verification.json`: two byte-identical
  wheels, isolated import provenance, GUI imports and installed CLI help.

## Resume sequence

1. Resolve Communication Cards plate 2 boundary placement and separately
   inspect the other red plates. Regenerate only that review output if the
   converter is at fault; preserve colour assignments and the source file.
2. Reconcile the two 0.6 duplicate identities and old HS-field mismatches
   without overwriting or rolling back live presets while the slicer is open.
3. With the slicer in a safe saved/closed state, verify complete Siddament
   native visibility and persisted values on 0.25, 0.4, 0.6 and 0.8; then
   resume the five manifest-native fixtures one at a time.
4. Keep physical filament calibration, the first commit, licence choice and
   GitHub push as later decisions.
