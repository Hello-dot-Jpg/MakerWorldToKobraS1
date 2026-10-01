# Native acceptance - 2026-09-10

## Engineering guide cubes

Reused the 25 mm cube, official S1 0.6 hardened steel, 0.30 mm layers,
0.62 mm widths and Textured PEI. Each completed Preview shows 83 layers,
24.90 mm last layer and no visible warning. No physical print started.

| Preset | Saved project under reports/ | Filament | Estimate |
| --- | --- | --- | --- |
| PC guide 0dcf06719c REVIEW | engineering-cube-pc-guide-06hs-review.3mf | 5.67 g | 16m32s |
| PET-CF guide 697b71c5da REVIEW | engineering-cube-petcf-guide-06hs-review.3mf | 7.04 g | 13m17s |
| PC-CF guide 1da7672cdc REVIEW | engineering-cube-pccf-guide-06hs-review.3mf | 5.67 g | 19m10s |
| PC-GF guide 03c449836a REVIEW | engineering-cube-pcgf-guide-06hs-review.3mf | 5.67 g | 19m10s |
| PLA-CF guide a9117e3388 REVIEW | engineering-cube-placf-guide-06hs-review.3mf | 7.32 g | 13m4s |

Saved config readback confirms PC: HS 260 C, PEI 110 C, flow 6, chamber
recommendation 65 C/control off. PET-CF: HS 270 C, PEI 80 C, flow 8,
chamber 0/control off. Presets assigned to slot 1; three unused PLA slots remain.
Saved-project reopen and physical calibration are separate pending checks.
No prior artifact or installed preset was overwritten.

PC-CF and PC-GF saved readback: correct distinct material types, HS 270 C,
PEI 110 C, flow 6, chamber recommendation 65 C/control off. PLA-CF: HS 230 C,
PEI 60 C, flow 12, chamber 0/control off. All three native slices completed
without visible warnings, with the same 83 layers / 24.90 mm result.

Together with the prior PA6-CF pass, all six engineering guide materials now
have native 0.6 HS cube slice/save evidence. These are distinct from the
Siddament filled-material passes. Continue remaining acceptance using
ACCEPTANCE_FINISH_PLAN.md; these passes do not cover other nozzle sizes.
