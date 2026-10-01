# Real vendor INI acceptance

## Detached preset roundtrip PASS - 2026-09-14

Installed 38062b3ddd REVIEW from gpkh6spe survives native project reopen,
slice and Save As. Original `reports/ini-prusament-detached-06hs-review.3mf`
and new `reports/ini-prusament-detached-06hs-roundtrip-review.3mf` have
identical complete project_settings.config JSON (zero changed values).
Both slices: 83 layers / 24.90 mm / 6.78 g / 17m12s; no visible slice warning.
HS 245 C, textured PEI 70 C and flow 8 remain intact. A fresh application
restart then reopened and re-sliced the roundtrip file successfully with the
same values; only the normal custom-preset notice appeared. Older
inherited-preset failures below remain
historical evidence, not the status of this detached preset.

## Saved-project regression - 2026-09-10

2026-09-13 recovery: gpkh6spe/38062b3ddd was successfully imported once.
installed-verification-resume-2026-09-13.json confirms 40 matching keys,
51 pre-existing presets unchanged and exactly the expected added preset.
Native restart/save/reopen validation remains pending; do not reimport.

Implementation candidate: standalone presets now detach from parent inheritance
and serialize resolved destination defaults with aligned HS/BRASS temperatures.
164 unit tests pass; fresh export `reports/S1-filaments-gpkh6spe/` is **not
installed or native round-trip validated yet**. Intermediate jjod3inz superseded.

Reopen/load and Slice complete, but **round-trip fidelity FAILS**. Saved comparison:
`reports/ini-prusament-petg-06hs-corrected-roundtrip-review.3mf`.
Without any settings edit, slot 1 keeps the corrected preset name but resets
nozzle 245 -> 230, PEI 70 -> 75, flow 8 -> 16, range high 245 -> 240,
density 1.27 -> 1.24, cost 24.99 -> 20, vendor Prusa Polymers -> Anycubic.
Reopened Preview: 83 layers / 24.90 mm / 6.62 g / 17m46s, no visible warning.
Original project lacks `different_settings_to_system` and inherits stock PETG.
This supersedes the pending-reopen statement below; installed preset persistence
and initial slice still passed, but saved-project safety needs a fix. No print.

## Corrected native acceptance - 2026-09-10

Current corrected export `reports/S1-filaments-gves3b5u/` (7ea9264060 REVIEW)
is imported and survives restart; strict installed audit passes and all 50
pre-existing presets are unchanged. Native editor shows range 190-245 C.
Earlier 5decb69023 preset is retained as pre-fix evidence, not the corrected one.
Cube slice passed: 83 layers / 24.90 mm / 6.78 g / 18m28s, no visible warning.
Saved `reports/ini-prusament-petg-06hs-corrected-review.3mf`; readback confirms
245 ordinary/HS nozzle and range high, 70 textured PEI, flow 8, 0.30/.62,
hardened_steel. Its native saved-project reopen and physical tuning are pending.
The repeatable local export command is `PYTHONPATH=src python tools/export_ini_acceptance.py`.
No existing installed preset or source file was overwritten; no print started.

Source: PrusaSlicer's BIBO vendor bundle at the version_2.9.2 tag:
https://raw.githubusercontent.com/prusa3d/PrusaSlicer/version_2.9.2/resources/profiles/BIBO.ini

Local ignored copy: `.research/BIBO-vendor-2.9.2.ini`.
SHA-256: `7251AEEC8B2BCAAAD092167D40ADF83BEA28A9E00511E90DF0A97D2297EE3A95`.
The moving master URL returned 404 despite cached web contents; this test uses
the downloaded versioned source, not a reconstructed or synthetic fixture.

Selected actual section `filament:Prusament PETG @BIBO2`. Local inheritance
resolved and converted to official S1 0.6 with ceramic/HS declaration and 110 C
bed ceiling. Export: `reports/S1-filaments-vobj6cl2/` (not installed).

- No blockers; nozzle 245 C, textured PEI 70 C, maximum flow 8 mm3/s.
- Only the supported INI scalar mapping is portable; cooling/calibration/macros
  remain destination-owned and unknown fields remain in provenance/audit.
- Bed mapping applies to Textured PEI only, not every available plate.
- Native GUI review/export and Anycubic import passed on 2026-09-09 evening.
  Fresh GUI export: `reports/S1-filaments-v4prmt_q/`; one config imported,
  `installed-verification.json` passes and all 49 pre-existing presets are unchanged.
  GUI review also passed all four official nozzle sizes (4 plans, 0 blocked).
  Material correction without an explicit base correctly shows a blocking error.
  Restart, dropdown/editor and slice acceptance of this INI remain pending.

This real bundle also exposed internal `*name*` parent sections in the selectable
list. They are now hidden from selection while remaining resolvable as parents;
a regression test verifies that inherited temperatures are not lost.
This follows the vendor format's internal-preset convention documented at:
https://github.com/prusa3d/PrusaSlicer/wiki/Vendor-bundles-and-updating-process

No source settings are evidence of tuning on the S1. Physical calibration is
still required, and no physical print was started.
