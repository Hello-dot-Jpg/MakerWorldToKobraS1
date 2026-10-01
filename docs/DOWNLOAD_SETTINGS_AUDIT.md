# Downloaded 3MF settings audit — 2026-09-05

## 2026-09-15 generated-fixture rerun

The latest completed Downloads inheritance audit is
`reports/download-inheritance-audit-2026-09-15.txt` (137 files, 129 modern
projects, zero findings). A subsequent full conversion-plan rerun produced no
output within its window and is explicitly not treated as evidence. The older
counts below describe the historical settings-inventory snapshot, not the
latest corpus size.

The later chunked conversion-plan audit covered all 137 files against the
official 0.4 mm / 0.20 mm target: 129 planned, 118 without blockers, 11
blocked and 8 rejected. See
`reports/download-plan-audit-0.4-0.20-chunked-2026-09-15.txt`; this remains
planner coverage, not native slicer acceptance.

The read-only rerun over `reports/` found 16 `nozzle_volume=[107]` shape
observations and two legacy negative sentinels. These are already covered by
the machine-owned nozzle-volume policy and explicit sentinel-translation tests;
no additional rule change was justified.

No desktop automation, slicing, downloads, source-model edits, or printer
operations were used for this audit. One small read-only agent checked the
upstream repositories while the main pass inspected local files.

## Scope and evidence

`tools/audit_corpus.py` recursively scans Downloads, reads bounded JSON settings
members (project and embedded machine/process/filament presets), and inventories
recognized metadata keys in model-settings XML. It never extracts ZIP paths or
reads mesh payloads. Generated JSON reports are ignored by Git and contain local
filenames. The command refuses to overwrite an existing report.

- 122 archives, 276 JSON configuration members, 114 modern project settings.
- Eight archives have no modern project settings. These are not eight corrupt
  files: legacy/geometry-only formats are outside the modern converter path.
- 860 distinct inventory names, including 40 `model_override:` entries.
- Three model-settings XML parse failures (unbound namespace prefixes). Their
  JSON settings were still audited; object-level coverage is incomplete there.
- 32 distinct array-versus-scalar candidates across 21 files. Fourteen files
  share the newer Bambu process-array pattern, including `tools.3mf`, the Crocs
  projects, `Amazing_Support_Settings.3mf`, and the gimballed cupholder.
- 214 names appear in neither the sampled source schema nor installed profile
  keys. These are NOT 214 confirmed bugs: they include metadata, vendor-specific
  keys, and newer options. Unknown settings remain preserved, which does not
  prove that Anycubic executes their semantics.

Schema evidence is the reviewed Anycubic source commit
`6103ed8b511609658d00d0538cc7f0609cdb57da`, `src/libslic3r/PrintConfig.cpp`.
Installed-profile shape corroboration uses Anycubic Slicer Next 2.0.0.2 resources.
The source checkout is not proven identical to the installed binary. Shape
checks do not constitute a complete enum/range/semantic compatibility audit.

## Findings and changes

| Finding | Files | Treatment |
| --- | ---: | --- |
| `enable_overhang_speed` arrays | 14 | Existing boolean fix generalized into explicit scalar compatibility validation. |
| Speeds, acceleration, overhang speeds, small-perimeter settings | 14 per affected key | Translate unanimous values; apply existing downward clamps first; block remaining differences or invalid array values. |
| `top_solid_infill_flow_ratio` arrays | 6 | Preserve the common ratio as one scalar, not a new default. |
| `nozzle_volume` arrays | 18 | Now machine-owned: use the exact resolved target value when available. Bundled S1 0.4 defines scalar `107`; no universal constant is hard-coded. |
| `flush_multiplier` arrays | 14 | Unanimous numeric scalar translation, supported by source schema only (not present in sampled installed profiles). |
| `thumbnails` arrays | 3 | No rewrite: installed profiles themselves contain both shapes. |
| `raft_first_layer_expansion = -1` | 24 | Translate to 0 only when rafts are disabled; for active rafts use the selected process value or block. |
| `tree_support_wall_count = -1` | 23 | Translate to Anycubic's documented `0 = automatic` value. |

`nozzle_type` was already replaced from the chosen machine profile. Genuine
filament-slot arrays, mode arrays, coordinates, unknown arrays, geometry, paint,
and assignments are not generically flattened. The compatibility allowlist is
finite and checked into source; the research checkout is not a runtime dependency.

Different source-tool values must not be resolved by picking the first entry.
For example, the support project has `outer_wall_speed = ["200", "500"]`.
An explicit target ceiling of `200` makes both values `200`, which can be
represented losslessly *after the approved clamp*. `["20", "40"]` under that
same ceiling still differs and blocks export. Existing CLAMP coverage is not
expanded merely because another setting name contains "speed".

## Validation and limits

- 76 unit tests now pass; compile checks pass. Added tests cover agreeing/mixed
  arrays, percentages, zero sentinels, non-finite/invalid values, untouched
  filament arrays, machine-only planning, and writer old-value preconditions.
- A read-only plan check of all 14 newer-array projects against installed
  official S1 0.4 / 0.20 Standard completed without blockers. This diagnostic
  retained source filaments; it is NOT material approval or print acceptance.
- Previous test exports predate these additional fixes. They are historical
  open/slice observations, not evidence that all array values were interpreted
  correctly. Regenerate them before subsequent acceptance testing or printing.
- Embedded-profile precedence is resolved from reviewed Anycubic source and
  exercised by a regenerated real-file export; installed-slicer acceptance is
  still pending. Newer filament-specific process overrides, full enums/ranges,
  and object/plate override semantics remain follow-up work. No claim of
  feature completeness is made.

After the initial audit, the planner gained a finite warning list for enabled
Bambu-only features that were absent from both the reviewed Anycubic source and
the selected destination profiles. Disabled defaults remain quiet; enabled
values are preserved and explicitly flagged for slicer verification rather
than guessed or deleted. This is triage, not proof of destination semantics.

The two known invalid `-1` support sentinels are now handled from direct source
evidence. Anycubic declares `tree_support_wall_count` as 0..2 with 0 meaning
automatic. Raft expansion has a minimum of 0 but no equivalent automatic
meaning, so the planner only uses 0 when rafts are disabled; active rafts use
the exact selected process value and are marked for Preview review, or export
is blocked when no such value can be established.

## Upstream answer

This project uses independently implemented plumbing informed by upstream
references; the upstream checkouts live under ignored `.research/`, not as
vendored runtime code. It is not a direct code fork of 3MF Sanitizer.

At reviewed Sanitizer commit `8e47a26e7da2eac3d6a29d76b5b97ff97e1f0118`,
`sanitizer.py:18-22` defines only two fixes: the raft and tree-support keys above,
both replaced with zero. Its rewrite loop at lines 139–166 does not handle
`enable_overhang_speed` or scalar-array conversion.

At reviewed maker-with-settings commit
`7a677f37fe0af5cdebf10d3760a34fb95d9280a1`, `make_bambu_3mf.py` has no special
overhang-switch mapping; generic conversion preserves existing array lengths
(lines 276–283, applied at 399–415). That tool targets Bambu project creation,
not comprehensive Anycubic compatibility. These are statements about the
reviewed local versions, not claims that current remote HEAD is unchanged.

## Repeat locally

```powershell
python tools\audit_corpus.py C:\Users\USER\Downloads `
  --schema .research\AnycubicSlicerNext\src\libslic3r\PrintConfig.cpp `
  --profiles "C:\Program Files\AnycubicSlicerNext\resources\profiles" `
  --output reports\download-settings-audit-new.json
```

The initial report records pre-fix policy classifications. The `-v2.json` report
uses the updated rule inventory; source values are intentionally unchanged.
