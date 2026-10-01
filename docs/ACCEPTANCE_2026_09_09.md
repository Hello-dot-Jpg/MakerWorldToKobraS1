# Acceptance continuation - 2026-09-09

## Evening GUI and INI acceptance

Follow-up finding: Prusament appeared and selected successfully, but the native
editor showed inherited range 190-240 C versus exported 245 C print temperature.
Fixed the converter to apply the authorized <=15 C metadata extension/warning
to inherited ranges, not only explicit source ranges. 163 tests pass including
inherited 245/255 acceptance and 256 rejection against high 240. No installed
preset overwritten. Corrected re-export/native acceptance and release rebuild
remain pending; the running converter still has pre-fix code loaded.

- Recovered the existing converter; no duplicate instance started. INI picker
  showed 16 public sections; Prusament PETG @BIBO2 selected alone.
- Native review and export passed for official 0.6 hardened steel / ceramic
  (default ceiling 320 C) / bed ceiling 110 C / automatic filament base.
  Output `reports/S1-filaments-v4prmt_q/`: PETG, nozzle 245/245, Textured PEI
  70/70, flow 8. Original INI hash unchanged.
- Native review of all four official sizes passed: 4 plans, 0 blocked.
- Off-by-default material correction was enabled without a base for a negative
  test: expected explicit-base error appeared; dismissed and restored OFF.
- Anycubic Import Configs imported the fresh ZIP: one config, no overwrite
  prompt. Installed audit passes; all 49 pre-existing presets unchanged.
  Evidence and pre-import snapshot are in the fresh export folder.
- INI restart, dropdown/editor and slicing remain pending. This does not prove
  engineering material calibration or the remaining complex 3MF acceptance.

## PLA-CF and PA6-CF continuation

Reused the native 25 mm cube on official S1 0.6 HS, 0.30 process, 0.62 width.
Both slices completed without a visible warning; 83 layers, final layer 24.90 mm.
Saved separately without overwriting PC-CF evidence:

- reports/engineering-cube-placf-06hs-review.3mf: Siddament 11eabdc2c8 REVIEW,
  7.32 g / 11m50s. Saved config confirms PLA-CF slot 1, HS 220/220 C, textured
  PEI 55 C and flow 12 mm3/s.
- reports/engineering-cube-pa6cf-06hs-review.3mf: Anycubic S1-Max-guide
  5226f09f46 REVIEW, 5.81 g / 13m11s. Saved config confirms PA6-CF slot 1,
  HS 260/260 C, PEI 110 C, flow 7.5 mm3/s, chamber 65 C/control OFF.

Other guide presets, saved-project reopen and physical calibration are separate
pending checks. Three unused stock PLA slots remain listed in each project.

## Local preparation

- Twelve known 3MF fixtures inventoried with hashes and bounded settings reads:
  reports/acceptance-manifest-2026-09-09.json. No archive read errors. This is not
  an assertion that observed settings are correct or preserved from source.
- Historical timing values remain in several fixtures; ASA clamps uses High
  Temp Plate. Regenerate affected cases before claiming current defaults pass.
- Current converter produced reports/timing-acceptance-dgbiwl02/ with a fresh
  official 0.6 HS/PETG project, selected 0.24 process height. Source tools.3mf
  untouched; 21 members hash-verified unchanged, eight objects and one plate.
  Load/unload/tool-change values match target: 126.423/0/0. Native test pending.
- Twelve planner tests passed. New helper tools affect acceptance preparation,
  not shipped package code; prior package verification is not rerun here.

## Corrected Siddament PC-CF native acceptance

The installed 544a887fdb REVIEW preset remains selectable after restart. Editor
shows PC-CF, recommended range 260-290 C, HS first/other 270/280 C, Textured PEI
110/110 C, flow 6 mm3/s, chamber recommendation 65 C with active control OFF.

Created native built-in 25 mm cube on empty plate. Official S1 0.6 HS and
0.30 Standard process, 0.62 mm width. Slice completed: 83 layers, last layer
24.90 mm, 5.67 g, estimated 16m32s. No warning visible at completed Preview.
Saved without overwrite as reports/engineering-cube-pccf-06hs-review.3mf.
Read-back project confirms the displayed values. Model-settings XML assigns
the sole Cube to extruder 1, the PC-CF slot; three listed PLA slots are unused.

This validates one imported preset's simple native slice, not physical print
quality, every engineering preset, a converter-generated mesh or full G-code
safety. No printer job started. Saved-project reopen and remaining presets
are the next checks; preserve this file as evidence when reusing the cube.
