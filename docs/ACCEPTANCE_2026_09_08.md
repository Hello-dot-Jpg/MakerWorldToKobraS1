# Acceptance continuation

## 2026-09-09 PC-CF correction

User delegated interpretation of Siddament PC-CF's PC declaration. Added explicit
base-material correction opt-in, restricted to an explicitly selected base,
with original material retained in decisions/provenance. Source bytes unchanged.
`reports/S1-filaments-nc8jzvvg/` exports PC-CF 0.6 HS with no blockers: nozzle
270 first / 280 other, textured PEI 110, flow 6 mm3/s, chamber recommendation
65 and active control off. NOT imported yet. 159 tests pass. UI visual and
native import/restart/slice acceptance remain pending; no print initiated.

## Reproducible packaging continuation

- `tools/verify_release.py reports --build-deps .research/build-deps` passes for
  current source. Evidence: `reports/release-check-sfeepnzx/verification.json`.
  Independent wheel builds are byte-identical; isolated package origin, GUI
  imports and CLI help pass. No publishing/global installation performed.
- Explicit-base worker bypasses automatic filament discovery; regression passes.
  Full suite remains 156 passing tests. Native Discard dialog is untouched.

## Siddament PLA-CF explicit-base native import

- `reports/S1-filaments-9rw9ph2f/`: self-contained PLA-CF 0.6 HS review export,
  220 C nozzle (ordinary/HS), 55 C textured PEI, 12 mm3/s flow ceiling.
- Native Import Configs reports one config imported, no overwrite prompt.
  `installed-verification.json` passes; all 47 snapshotted root/base presets
  unchanged. Snapshot tool now includes `filament/base` as well as root files.
- Three GUI-worker tests pass, including explicit selection snapshot and
  load-error blocking; full suite 156 tests. Visual GUI acceptance pending.
- Switching printer to 0.6 for visibility checking triggered temporary preset
  Discard/Save prompt; paused for approval. Restart and slicing pending.
- Scraper Preview subsequently displayed floating-cantilever warning for
  Schaber.stl. Colour/slice acceptance stands, but support adequacy is not
  established and this case must not be described as warning-free/print-ready.

## Explicit destination-base implementation (latest)

- Filament tab adds Choose REVIEW base JSON / Use automatic base controls.
  Selected file must be a standalone filament base with exact selected printer
  compatibility. Material mismatch remains blocked; no PC-to-PC-CF inference.
- Exports flatten explicit defaults rather than relying on an installed parent.
  Foreign source macros/calibration remain excluded, converted HS/brass portable
  variants synchronize, chamber control is off, and thermal variants are checked
  against confirmed limits. Existing 3MF reassignment is unchanged.
- 154 tests pass, including loader rejection, self-contained identity,
  destination macros/calibration, flow ceiling and HS-temperature regression.
- GUI visual/native import and real vendor explicit-base acceptance pending.

- 18 engineering presets imported through Anycubic Import Configs, without an
  overwrite prompt. All six material names appear for the 0.6 S1 printer.
- Saved values audited against export, including HS and chamber fields. No
  differences; 29 pre-existing root presets unchanged. Standalone custom bases
  use `filament/base`, now covered by the audit tool and a regression test.
- Xiaomi Textured PEI review opens without repair/error and saves to a new
  round-trip copy. Both project/plate bed types survive, alongside expected
  0.6 HS / 0.2 layer / 0.62 width / 75 C textured plate values. ZIP check passes.
- 148 automated tests pass. Fixed HS range-extension consistency and missing
  required-temperature-field errors in the engineering generator.

## Restart and native Preview continuation

- Engineering restart completed. All 18 identities remain installed; the 29
  previously snapshotted root presets are unchanged. Nine presets lost the two
  redundant `_HS` recommended-range fields. All other audited fields match.
  Strict evidence: `reports/S1-filaments-j7d442cn/installed-verification-after-restart-corrected.json`.
  This intentionally remains a failed exact-field audit, not a hidden exception.
- The earlier restart audit incorrectly substituted historical scaffold values
  for absent standalone fields. Fixed both expected/actual standalone handling;
  missing supported fields remain failures. Added regression coverage.
- Native PA6-CF 0.6 HS editor confirms 260–300 C range, 260/260 C print
  temperatures, textured PEI 110/110 C, chamber recommendation 65 C and active
  chamber control OFF. No material values were edited in this inspection.
- Future engineering exports omit only the two redundant range-HS fields after
  normalizing the ordinary range. Fresh six-material 0.6 export:
  `reports/S1-filaments-s42dvacj/` (not imported; installed identities unchanged).
- Xiaomi round-trip reopened and native Slice completed without an error dialog.
  Preview shows model toolpaths and green tree supports, 451 layers / 90.20 mm,
  16.10 g total and estimated 1h20m. Textured PEI, 0.6 nozzle, 0.20 layer and
  0.62 widths remain visible. This is native Preview acceptance, not independent
  G-code validation or a physical print. No Remote Print action was taken.
- Current automated suite: 151 tests pass.

## Painted-colour continuation

- User-approved Discard cleared the Xiaomi temporary preset overrides; the saved
  round-trip 3MF was not overwritten.
- Opening `painted-colour-scraper-current-04-review.3mf` produced Anycubic's
  Modified G-code warning listing printer/filament macros. Paused at this warning
  for user acknowledgement; did not suppress future warnings or start a print.
  Painted-colour native open/slice acceptance is not yet recorded as passed.
- Subsequently acknowledged the warning with explicit user approval, leaving
  "Don't show again" unchecked. Native open and Slice completed successfully.
  Preview preserves the dark scraper and white lettering, uses filament slots
  1 and 4 (one change), and reports 40 layers / 6.83 mm, 19.24 g, estimated
  1h21m. Four filament slots remain listed. The selected printer is S1 0.4,
  Textured PEI, with source 0.17 mm layer height retained. No print started.
  This closes this case's native colour/slice check, not the entire painting
  matrix or independent G-code safety validation.

Not claimed complete: engineering slicing, broad multi-plate/painting/
variable-layer Preview matrix, GUI INI acceptance, and connecting accepted
engineering bases to the standalone vendor importer. No G-code was handed to a
printer and no physical print was started during this continuation.
