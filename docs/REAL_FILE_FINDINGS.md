# First real-file findings

Inspection date: 2026-09-04. All inputs were opened read-only. SHA-256 hashes
were checked before and after every inspection pass and remained unchanged.

## Inputs

| Role | File | SHA-256 |
|---|---|---|
| MakerWorld source | `tools.3mf` | `B531A33523343F3A6900BF0DFD54627DDDD4B3C8A5E0028AD39AF63F81BCD6BA` |
| Kobra reference candidate | `KS1_Lid_Holder+PETG.3mf` | `B0ED1C64FD47A8A6CA69277B55041E0E07AE07601DE43B8D6FEE52E08C67520C` |
| Known-good printed Kobra reference | `迪士尼小城堡-Sumee1798.3mf` | `1E57EB3027C4AF267C9FB9F9BDD89138B64C1E9A2D364F5722F0917BAC9FA6C2` |
| Printed compatibility case | `Flexible_Cat.3mf` | `0738D6C63C23CD6A6927EEB50B8F7A454134AD6561E1ABAB65F4C2D4CE0FEF6C` |
| Printed compatibility case | `Helicopter_Back.3mf` | `077C2CF72A76BFF06E976CD06F9346731E51CD3B6C4C7283CEC430DE12C1235D` |

The original Kobra path supplied in chat used backslashes before the filename
segments. The existing file found in the named Downloads area is
`KS1_Lid_Holder+PETG.3mf`.

## Structural inspection

| Finding | MakerWorld | Kobra candidate |
|---|---:|---:|
| Valid core 3MF structure and XML | yes | yes |
| Archive members | 24 | 17 |
| Parsed setting leaves | 607 | 1,484 |
| Cross-file value conflicts | 0 | 114 |
| Parser/validation warnings | 0 | 2 |

Structural counts:

| Structure | MakerWorld | Kobra candidate |
|---|---:|---:|
| 3MF resource objects | 16 | 3 |
| 3MF mesh objects | 8 | 2 |
| 3MF build items | 8 | 1 |
| Model-settings objects | 8 | 1 |
| Model-settings parts | 8 | 2 |
| Model instances | 8 | 1 |
| Plates | 1 | 1 |
| Assembly items | 8 | 1 |

These are different models, so their geometry counts are not expected to
match. The implemented writer retains the MakerWorld source's structural
counts; target geometry is never imported.

The MakerWorld source has settings in `Metadata/project_settings.config`. The
Kobra candidate also has separate machine, process, and two filament settings
configs. `model_settings.config` and `slice_info.config` are XML in both files.

Name-level comparison, which matches array and scalar locations without hiding
their sources:

- 206 setting names only in the MakerWorld file.
- 157 setting names only in the Kobra candidate.
- 161 shared names with differing typed value sets.
- 192 shared names with equal typed value sets.

The JSON report retains the stricter member-plus-canonical-path comparison:
265 only left, 1,142 only right, 117 changed, and 225 equal.

## High-risk target contradiction

The Kobra candidate is not internally consistent enough to serve as an
unquestioned machine source of truth:

- `Metadata/project_settings.config` identifies `Anycubic Kobra S1` and
  `Anycubic Kobra S1 0.4 nozzle`.
- `Metadata/machine_settings_1.config` identifies
  `Creality Ender-3 V3 Plus` and a custom Creality-derived preset named for this
  3MF.
- Both files use `gcode_flavor = klipper`, but machine limits differ between
  the project snapshot and separate machine profile.

This may be a deliberate custom-profile inheritance artifact. Subsequent review
of Anycubic source established that embedded presets are registered before the
complete project config is applied. The converter therefore treats flattened
project values as authoritative only for explicitly retargeted scopes, while
still blocking any embedded key that was not flattened.

The user confirmed the foreign Creality identity was not intentional. The file
was downloaded from MakerOnline and was probably an Ender project retargeted by
its publisher. It remains useful as a conversion case study but is not a clean
machine reference.

## Known-good printed Kobra reference

The user confirmed `迪士尼小城堡-Sumee1798.3mf` printed very well and that they
probably saved it with their hardened-steel preset. It is the strongest
available schema/reference candidate:

- valid semantic 3MF package with 25 members;
- 1,005 parsed settings, all from `project_settings.config`;
- no separate embedded machine/process/filament snapshots;
- no cross-file conflicts or parser/validation warnings;
- consistently identifies `Anycubic Kobra S1`, Klipper, 250 mm printable
  height, and a 0.4 mm nozzle;
- uses a custom `Anycubic Kobra S1 0.4 nozzle Hardened Steel -` preset;
- contains four model-settings objects/parts/instances across two plates,
  making it useful for structural preservation tests.

Compared only at effective project-settings level with the Ender-derived Kobra
file, 497 names are shared: 391 have equal typed value sets and 106 differ.
Important shared values include printer model, G-code flavour, printable area
and height, machine start G-code, default acceleration, travel acceleration,
and machine maximum travel acceleration. This supports treating the earlier
file's separate Creality machine profile as foreign baggage.

The clean candidate is not automatically a universal process-limit profile.
Its machine X/Y acceleration arrays are all 20,000 mm/s², while X/Y speed
arrays contain 600, 300, and 780 mm/s. Those arrays exactly match the locally
installed Anycubic Slicer Next 2.0.0.2 Kobra S1 profile. Their third-slot
semantics remain opaque, so the whole machine array may be sourced from the
installed target profile but individual positions must not be interpreted.
Conversion must never increase a MakerWorld process value merely because this
profile contains a higher machine maximum.

The user subsequently identified the 0.4 mm hardened-steel preset as a
community profile that works very well. Its local definition is a thin overlay
inheriting the official Anycubic 0.4 mm machine profile, which explains why the
castle's machine arrays and G-code match the installed official base exactly.
No corresponding community overlays are known for the other nozzle sizes.

## Successful foreign-Anycubic compatibility cases

The user also confirmed that `Flexible_Cat.3mf` and `Helicopter_Back.3mf`
printed well on the Kobra S1. They are useful outcome-labelled compatibility
cases, not Kobra S1 machine references:

- `Flexible_Cat.3mf` is a valid seven-member legacy AnycubicSlicer 1.4.1
  archive with one mesh/build item and no plate metadata. Its 317 parsed
  `Slic3r_PE.config` settings target Kobra 3 and ABS rather than Kobra S1.
- `Helicopter_Back.3mf` is a valid 22-member, three-plate Anycubic Slicer Next
  1.3.4.0 project with 547 parsed settings, targeting Kobra 2 Pro with a
  0.4 mm brass nozzle. Its selected filament profile and `filament_type` both
  identify PETG; the separate PLA-named default is not the active slot.

These successful prints show that a foreign Anycubic project can work on the
S1, but they do not make foreign printer identity, G-code, or machine limits
safe to KEEP automatically.

## Speed and acceleration observations

Values are strings in these configs and must be parsed only by a rule that
expects a numeric setting.

| Setting | MakerWorld | Kobra project | Kobra separate profile | Initial interpretation |
|---|---:|---:|---:|---|
| outer wall speed | 200 | 200 | 200 | equal |
| inner wall speed | 300 | 300 | 300 | equal |
| sparse infill speed | 270 | 270 | 300 | preserve 270 |
| internal solid infill speed | 250 | 250 | 300 | preserve 250 |
| top surface speed | 200 | 200 | 200 | equal |
| support speed | 150 | 150 | 150 | equal |
| support interface speed | 80 | 80 | 80 | equal |
| bridge speed | 50 | 50 | 50 | equal |
| gap infill speed | 250 | 250 | 300 | preserve 250 |
| travel speed | 700 | 300 | 500 | target precedence required |
| default acceleration | 6000 | 10000 | 12000 | preserve 6000 |
| outer wall acceleration | 5000 | 5000 | 5000 | equal |
| inner wall acceleration | 0 | 5000 | 5000 | sentinel/inheritance review |
| top surface acceleration | 2000 | 2000 | 5000 | preserve 2000 |
| travel acceleration | 10000 | 10000 | 8000 | target precedence required |

The source printer is a Bambu Lab A1 mini, not a P1S. Its Bambu-specific
machine G-code is now handled by the verified REPLACE allowlist, never KEEP.
Its model-specific process values use independent KEEP/CLAMP classification.

## Conversion gate results

1. Exact installed/versioned Kobra S1 machine JSON remains separate from
   project/process/material evidence and is recorded by hash.
2. Foreign separate-profile baggage cannot override the selected target;
   strictly flattened snapshots may be removed and ambiguity blocks export.
3. XML object, plate, part, instance, assembly, and assignment counts are
   validated before and after every write.
4. Only verified mappings are executable rules; UNKNOWN remains KEEP.
