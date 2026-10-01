# Nice supports - beta

`Nice supports - beta` is an explicit, off-by-default support overlay derived
from Justin's known-good `Amazing_Support_Settings.3mf` project (SHA-256
`8FF01B6DCF49EFD0E0641EE438A7745C0A8B9D79CD9758AD049E490540EB6FB3`).
Its reference and version are recorded in every JSON conversion plan.

The overlay enables build-plate-only automatic tree supports and applies the
reference's support gaps, threshold, interface, base pattern, and tree-branch
geometry. Every such change appears as `TRANSLATE [REVIEW]` in the report.
Support and interface speeds use downward-only ceilings of 150 and 80 mm/s,
respectively, and are also limited by the selected process. They never increase
a slower source value.

The Bambu/P2S reference is not copied wholesale. The beta option deliberately
excludes machine G-code, printer identity, filament/AMS and purge settings,
cooling, raft settings, support-filament assignments, and support ironing.
Nozzle-dependent support line width continues to come from the selected process
profile. The source's Bambu `tree_support_wall_count = -1` auto sentinel is
translated to Anycubic's documented `0 = auto` value and marked `REVIEW`.

The option may add a missing compatible support setting to modern project JSON.
It does not modify geometry, paint, modifiers, plate layout, or object/part
filament assignments. Existing files are never overwritten.

The checkbox means the converter will intentionally enable supports even if the
source had them disabled. Always inspect every plate in Anycubic Slicer Next's
Preview before printing. In particular, confirm that build-plate-only support
can reach every required overhang and that 0.25 mm top Z distance is suitable
for the chosen layer height/material.

CLI equivalents:

```powershell
python -m s1_optimizer plan source.3mf `
  --target-id TARGET_ID --process-id PROCESS_ID `
  --nice-supports-beta

python -m s1_optimizer optimize source.3mf `
  --target-id TARGET_ID --process-id PROCESS_ID `
  --nice-supports-beta --dry-run
```

A selected process is required. Use dry run first and review every change.
