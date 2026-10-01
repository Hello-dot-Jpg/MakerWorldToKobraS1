# Project specification

## Goal

Retarget a MakerWorld/Bambu 3MF project to an Anycubic Kobra S1 reference
profile without destroying model-specific tuning. Preserve the archive and
creator intent, constrain unsafe machine-dependent values, and explain every
change. The original file must never be modified.

## Setting behavior model

Every setting will eventually resolve to one behavior:

- **KEEP**: preserve model intent, including layer/wall/infill choices,
  supports and support painting, seams, ironing, brims/rafts, modifiers,
  colour painting, filament assignments, geometry, and plate layout.
- **CLAMP**: use `min(source, target_limit)` for verified speed, acceleration,
  and related limits. A source value must never be increased.
- **REPLACE**: use reference-profile values for verified machine identity,
  geometry, kinematics, limits, G-code, fans, bed definitions, and
  hardware-specific purge or tool-change behavior.
- **TRANSLATE**: use dedicated, reviewable logic for AMS/ACE Pro assignments,
  filament profiles, volumetric flow, pressure advance, retraction, cooling,
  temperatures, purge volume, and conditional G-code.
- **UNKNOWN**: preserve by default unless it is demonstrably inside a replaced
  machine-definition section.

Classification rules should become external YAML or JSON after real schemas
have been mapped. Kobra S1 machine values should primarily come from the exact
installed/versioned Anycubic nozzle profile, with a user-supplied known-good
reference 3MF providing project/process/material evidence. Neither source is
replaced by hard-coded defaults.

The target hardware description must independently record:

- printer model;
- nozzle diameter;
- nozzle material/type;
- hotend/heatbreak construction;
- exact installed-profile path, version, and SHA-256;
- user calibration overrides and their provenance.

The installed Anycubic profiles do not distinguish the user's PTFE-lined,
all-metal, and aftermarket ceramic hotends. Exact filament/nozzle profile
temperature, flow, retraction, and material values are therefore translated as
`REVIEW`; an optional explicit user hotend ceiling may only lower temperature.

The known-good community 0.4 mm hardened-steel machine preset is an inherited
overlay on the official 0.4 mm profile and may be offered as the preferred
calibrated 0.4 mm target. It must retain its provenance and inheritance chain.
It is not a template for synthesizing hardened-steel presets at other nozzle
diameters.

## Safety invariants

- Never overwrite or modify an input.
- Never silently increase source speed or acceleration.
- Preserve archive members unless a reviewed rule explicitly changes them.
- Dry-run and detailed change reports precede archive-writing functionality.
- Maintain model, object, plate, painting, modifier, and assignment counts.
- Validate rebuilt ZIP, XML, JSON, and structural invariants.
- Treat Bambu-specific machine G-code as hardware-specific, not model intent.

## Intended commands

Milestone 1:

```text
s1optimizer inspect source.3mf
s1optimizer compare source.3mf reference.3mf
s1optimizer targets --nozzle 0.6 --bundle community-profiles.3mf
```

Milestone 2 and later:

```text
s1optimizer optimize source.3mf --target-id TARGET_ID --process-profile PROFILE --dry-run
s1optimizer optimize source.3mf --target-id TARGET_ID --process-profile PROFILE --output output.3mf
```

Target discovery filters on actual nozzle diameter and returns a stable ID for
each exact official or community machine profile. Optimization must require one
of those IDs; filenames and display names alone are not sufficiently precise.
Process-profile choices are filtered after the machine/nozzle target and cannot
change the selected nozzle diameter implicitly.

Implemented options include `--verbose`, `--report`, `--rules`,
`--hotend-type`, and `--hotend-max-temp`.

## Reports

Optimization reports must identify source and reference files; list preserved,
clamped, replaced, translated, and unknown settings; show old and new values;
include source locations; and present warnings and summary counts. Implemented
confidence labels use `SAFE` and `REVIEW`; uncertain material-owned
translations are never presented as automatically safe.

## Non-goals

The tool will not rewrite model geometry, reslice models, generate G-code,
optimize purely for speed, discard unknown settings, assume a fixed source
printer, or assume all Kobra S1 owners use identical tuning.

## Current conversion boundary

The reviewed Milestone 2 mapping now permits automatic replacement of the
explicit machine identity/G-code/limit allowlist, nozzle-dependent width and
layer-bound translation, and numeric clamping of the documented
speed/acceleration allowlist. Exact selected filament/nozzle profiles translate
material-owned values with `REVIEW` confidence, while volumetric flow never
increases. Real-file output is rebuilt to a new path, assignments are checked
against ACE slot count, and every untouched member is hash-verified.
Hotend/heatbreak construction is independently recorded in the plan and report,
but does not imply a guessed temperature limit. Reviewed Anycubic load order
makes the complete flattened project config authoritative after embedded
presets are registered. One unambiguous foreign embedded snapshot may therefore
be removed for a scope explicitly retargeted by the user only when every
substantive key is flattened; unselected, ambiguous, or unflattened scopes are
preserved or block export as appropriate.
