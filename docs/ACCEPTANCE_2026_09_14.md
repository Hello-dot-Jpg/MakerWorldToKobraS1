# Native acceptance - 2026-09-14

## ASA heat-bed clamps - NOT RUN

On 2026-09-15, opening `reports/asa-heat-bed-clamps-current-04hs-review.3mf` stopped at Anycubic's `Modified G-code` confirmation (the same full G-code-field warning previously recorded). The dialog was left untouched, so no native slice result is claimed.

## Castle reference - PASS

`reports/tools-castle-reference-04-review.3mf` opened after discarding known task-generated preset changes and sliced in Preview (160 layers / 32.00 mm / 65.68 g total, 56.09 g model). Kobra S1 0.4 Hardened Steel, .20 mm layer, .42 mm default width and Textured PEI were retained; no blocking warning appeared.

## Coasters three-plate coverage - PASS

`reports/coasters-current-reconciled.3mf` opened after discarding known task-generated unsaved preset changes. All three plates were sliced individually in Preview without a blocking modal: plate 1 66 layers / 41.98 g / 1h7m; plate 2 24.52 g / 42m54s; plate 3 27.29 g / 50m5s. S1 0.4, .28 mm layer, .42 mm default width and Textured PEI remained visible. Anycubic showed only a non-blocking precise-wall notice.

## Timing fixture fresh-session reopen - PASS

After the controlled restart, `reports/timing-acceptance-dgbiwl02/tools-06hs-petg-timing-native-review.3mf` reopened without a warning and sliced successfully (133 layers / 31.98 mm / 76.61 g total, 64.48 g model). S1 0.6, .24 mm layer, .62 mm widths and Textured PEI remained visible.

## Controlled restart persistence - PASS

After a fresh Anycubic Slicer Next launch, `reports/ini-prusament-detached-06hs-roundtrip-review.3mf` reopened with the normal custom-preset notice, retained the detached review identity, Kobra S1 0.6 nozzle, Textured PEI Plate and Prusament PETG, and sliced successfully (83 layers / 24.90 mm / 6.78 g / 17m12s total). No Modified G-code warning appeared; no source or installed-preset changes were made.

## Detached INI

38062b3ddd REVIEW: saved project reopened, sliced and saved separately to
`reports/ini-prusament-detached-06hs-roundtrip-review.3mf`. Complete
project_settings.config equals the original detached native save: zero differing
values. Both slices 83 layers / 24.90 mm / 6.78 g / 17m12s; no visible warning.
Installed audit `reports/S1-filaments-gpkh6spe/installed-verification-2026-09-14.json`
passes.

## Timing

`reports/timing-acceptance-dgbiwl02/tools-06hs-petg-timing-review.3mf`
opened/sliced/saved to separate `tools-06hs-petg-timing-native-review.3mf` in
the same folder. 133 layers / 31.98 mm / 76.61 g total / 64.48 g model.
No visible warning. Native saved timing values 126.423 / 0 / 0 match exported
load/unload/tool-change values. .6 HS / .24 layer / .62 width / textured PEI
retained. Reopen pending. No measured physical ACE duration.

## Official 0.8 HS nozzle

`reports/current-official-0.8-hs-petg-review.3mf` opens and slices to Preview
without visible warning: 80 layers / 32.00 mm / 98.55 g total / 85.14 g model.
Native UI confirms S1 .8 nozzle, .40 layers, .82 widths, PETG and textured PEI.
Filament dropdown visibly includes stock ABS, ASA, PLA and PLA Galaxy in
addition to PETG and user engineering presets. Selection left unchanged.
This is initial open/slice evidence; native saved roundtrip remains untested.
Fixture predates timing fix and does not establish timing regression coverage.

## Official 0.25 HS nozzle

`reports/current-official-0.25-hs-petg-review.3mf` opens and slices without
visible warning: 319 layers / 31.95 mm / 58.89 g total / 51.22 g model.
UI confirms S1 .25 nozzle, .10 layer (.15 first), .27 default/outer width
(.30 first/inner), PETG and textured PEI. Dropdown shows stock PETG, ABS, ASA
and PLA, plus SUNLU user presets. No filled-material availability is inferred.
Selection unchanged. Initial open/slice only; roundtrip and timing not covered.

## Official 0.4 HS nozzle

`reports/current-official-0.4-hs-petg-review.3mf` opens and slices without
visible warning: 160 layers / 32.00 mm / 66.37 g total / 56.68 g model.
UI confirms S1 .4 nozzle, .20 layers, .42 default/outer widths (.50 first,
.45 inner), PETG and textured PEI. Dropdown shows ABS/ASA/PLA and numerous
PLA variants; PC/PEBA/PETG-CF also visible. Selection unchanged. Initial
open/slice/list only, not saved roundtrip or new timing validation.

## Variable layers

`reports/triceratops-variable-layers-04-petg-review.3mf` opens and slices without
visible warning: 181 layers / 22.61 mm / 8.02 g, model printing 51m17s plus
5s preparation. S1 .4 / PETG / textured PEI. Saved NEW as
`reports/triceratops-variable-layers-04-petg-native-review.3mf`.
Metadata/layer_heights_profile.txt is byte-identical: 3248 bytes, 175 pairs.
This proves native save preservation; saved-project reopen still pending.

No physical print, firmware change, installed-preset edit or source edit.

## Painted support bucket — blocked warning

Opening `reports/painted-support-bucket-current-04-review.3mf` produced an
Anycubic `Modified G-code` modal listing modified layer-change, filament,
machine, pause/start/end, printing-by-object, template-custom and time-lapse
G-code fields. The warning was not accepted, so this fixture has no native
slice result in this run.
