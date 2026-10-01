# Current planner corpus audit — 2026-09-06

Read-only command: `python tools/audit_conversion_plans.py C:\Users\USER\Downloads`

Target: installed official Anycubic Kobra S1 0.4 nozzle; process: installed
0.20 mm Standard for that nozzle. Source heights are preserved. Filaments are
not retargeted in this pass. No output archives or installed settings are written.

Results: 128 files scanned; 120 plans built, of which 108 had no write blockers
and 12 were blocked. Eight files were rejected for lacking a modern
`project_settings.config` (including the legacy Flexible_Cat). This is planner
coverage evidence, not an assertion that all 108 slice correctly or that a
fixed 0.4 mm profile is appropriate for every source.

The 12 blocked files comprise:

- Three with undeclared XML prefixes in `model_settings.config`: the geometry
  ruler tool and both numbered IroningTest_TwoColor files.
- Four with preserved first-layer heights of 0.30/0.35 mm above this target's
  0.28 mm configured maximum. These need a deliberate process/height choice,
  not automatic changes to source intent.
- Five with multiple embedded profiles: four profile-bundle files plus the
  mermaid project. Multiple-profile reconciliation remains deliberately blocked.

## Newly isolated XML case

Read-only excerpts show the undeclared prefix is `slic3rpe` on shape/text
elements, not ordinary extruder metadata. The ironing example also uses
`extruder=0` on a text part adjacent to negative parts. Do not simply suppress
the parse error or remove those elements: investigate Anycubic's text/negative
part handling and zero-assignment semantics before changing validation. Tests
must retain those elements and original member bytes, and distinguish actual
printable assignments from inherited/non-printing assignments.

This audit gives concrete active text/modifier/ironing candidates for the
remaining fidelity coverage; their names alone do not establish active ironing
or successful destination interpretation.

## Targeted compatibility repair results

Reviewed `Format/bbs_3mf.cpp` explicitly recognizes literal `slic3rpe:text` and
`slic3rpe:shape` tags and uses `XML_ParserCreate(nullptr)` (no namespace
processing). The validator now binds only that known legacy prefix in memory
for model-settings inspection. Original archive bytes are never rewritten.
Unknown undeclared prefixes, broken XML and DTD/entity declarations still fail.
Core 3MF XML parsing is unchanged.

The importer also maps object extruder 0 to slot 1 and erases part extruder 0
to inherit its object's setting (around lines 2089–2114). Assignment checks now
recognize those cases and report the effective inherited/default slot. Positive
out-of-range assignments still block rather than accepting the importer's
automatic material reassignment.

All three previously XML-blocked files now plan and export without blockers
using the same official 0.4 mm / 0.20 mm target/process. Their model-settings XML
is byte-identical after export. The two numbered ironing inputs have identical
source hashes, so this is two distinct models, not three independent cases.

| Local review output | Source | Untouched members | Model parts / plates |
| --- | --- | ---: | --- |
| `reports/text-parts-regression-1.3mf` | Geometry tool | 15 | 62 / 1 |
| `reports/text-parts-regression-2.3mf` | Ironing test (1) | 22 | 121 / 2 |
| `reports/text-parts-regression-3.3mf` | Ironing test (2), duplicate | 22 | 121 / 2 |

These are automated review exports, not installed-slicer or print acceptance.
Filament profiles remain source-owned in this regression pass. Unit coverage
includes text/shape retention, effective zero assignments, out-of-range
blocking, unknown/malformed XML rejection and byte-preserving writer round trips.
The full suite has 94 passing tests; the complete corpus has not been rerun
since the targeted repair, so the earlier 108/12 baseline remains historical.
