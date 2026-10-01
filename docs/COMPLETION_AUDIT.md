# Completion audit - updated 2026-09-15

## Publication preparation - 2026-10-01

216/216 tests and the 0.4.1 GUI/runtime/package checks passed. The user
accepted the editable plate selector plus warning for beta; automatic plate
selection remains a known issue. Public repository name MakerWorldToKobraS1
and MIT licence are approved. Older pending-decision/publication statements
below are historical. GitHub publication status is recorded separately in
PUBLICATION_CHECKLIST.md; physical calibration is still outside acceptance.

## Superseding evidence - 2026-10-01

Read CHECKPOINT.md and ACCEPTANCE_STATUS.md for current exact artifacts.
GUI load/discovery/auto-fit/export/new-source-reset, representative large
two-plate native slices, corrected optimized process settings, and0.6
fresh-process persistence pass.211/211 tests and release-check-i8sx5rk1
package verification pass before the latest GUI notice regression test.
Remaining native failure: remembered plate preference can override exported
Textured PEI. Experimental unique printer did not solve it; editable selector
works. Warning mitigation does not satisfy automatic selection. User beta
scope choice is pending. Physical calibration/fit, licence, first commit and
GitHub remain outside this acceptance work. Older entries below are historical.


## Current evidence update - 2026-09-15

2026-09-15 release verification rerun passes with bundled offline build
dependencies; see `reports/release-check-pr83cf7w/verification.json`.

The repository currently passes all 164 `unittest` tests and Python compile
checks; CLI help and `git diff --check` also pass. Release verification also
passes with bundled offline build dependencies. Read-only Siddament dry audits
for 0.25/0.4/0.8 mm produce 14/17/15 review-ready plans, with missing bases
reported rather than guessed. Native acceptance has since added successful open/slice evidence
for official 0.25, 0.4 and 0.8 mm hardened-steel fixtures, castle and all three
coaster plates, preservation of a variable-layer profile through native save,
preservation of the 126.423/0/0 filament timing fields, and a zero-difference
detached INI save/reopen.
The refreshed Downloads inheritance audit is
`reports/download-inheritance-audit-2026-09-15.txt`; a later full-corpus
rerun returned no output within its window and is not treated as evidence.

The goal is not complete: several complex multi-plate cases and additional
native saved-project reopen checks remain outstanding. Controlled application
restart is now PASS.
The 2026-09-15 active-path Siddament recheck also found broader imported-value
differences; prior zero-difference evidence is limited to its documented field
subset.
The painted-support bucket currently stops at an Anycubic `Modified G-code`
confirmation; that warning has not been accepted. No physical-print or
firmware evidence is implied.

For the current resume position, read `CHECKPOINT.md` first. The dated
acceptance logs supersede older native-check pending statements: Xiaomi and
painted-colour scraper slices passed; engineering restart completed with
documented redundant metadata removal. Current suite: 164 passing tests.
Explicit base selection is implemented in the GUI and matching logic; native
visual acceptance of that control remains pending.

The imported-preset blocker was investigated without touching the installed
store: the current exporter now synchronizes explicit portable root,
`_HS`, and `_BRASS` fan/slowdown values, and fresh 0.6 mm output confirms
those fields are present. Native re-import/reopen of that fresh batch is still
required before the historical installed differences can be closed.

## Latest verification

- 164 automated tests pass, including INI adapter/engine export and installed
  preset audit regressions. Local wheel build and isolated-folder CLI launch pass.
- The native Anycubic restart check passed: corrected Siddament names persist,
  failed slash-name entries are absent, and stock filaments remain visible.
  Read-only evidence: `reports/S1-filaments-8rbt5e9w/installed-verification-after-restart.json`.
  All 15 expected identities match their checked effective fields; 14 additions
  relative to the snapshot that already contained the first PETG import; no
  unexpected additions or pre-existing changes.
- INI beta is connected to the filament tab; real vendor INI conversion and
  detached save/reopen evidence pass, while new-control visual acceptance and
  broader physical calibration remain pending. See USER_HANDOFF.md for the
  distinction between engineering follow-up and user print tests.

The historical detail below remains useful but earlier test counts and restart
pending notes are superseded by this section.

The goal is still active. A runnable converter and passing unit suite do not
prove the full outline complete.

## Current evidence

- Local repository on main; CLI, GUI, source, tests, and publication checklist
  exist. Version 0.4.0; no remote or first commit yet.
- 130 unit tests pass, including scoped inheritance, compatibility-vector and
  difference-mask tests. A consolidated cupholder metadata review export has
  passed archive comparison; installed-slicer acceptance remains pending.
- The user confirmed the current 0.6 mm hardened-steel / 0.18 mm cupholder
  Nice supports export opens without errors, slices, and has satisfactory
  supports (2026-09-06). Stock-filament visibility initially failed; the user
  confirmed the inheritance-vector repair opens, slices, and has no missing
  filaments. A separate difference-mask repair candidate remains unverified
  in the installed slicer.
- Single-material 0.6 mm, four-slot 0.4 mm, and support-heavy P2S conversions
  opened and sliced in Anycubic Slicer Next. See MANUAL_ACCEPTANCE.md.
  The later download audit found more scalar-array mismatches; earlier exports
  must be regenerated and do not establish full setting fidelity.
- Source files and untouched archive members are hash checked. Geometry,
  object, plate, part, instance, and assembly counts are checked on export.
- Exact nozzle/machine/process/filament selection and hotend identification are
  implemented. Model layer height remains source-owned by default, with an
  explicit selected-process-height option; speeds clamp downward.

## Outstanding requirements and next evidence

See DOWNLOAD_SETTINGS_AUDIT.md for the 122-file, no-desktop audit and newly
implemented scalar compatibility checks. Follow up on unresolved active unknown
settings and per-filament process overrides.
Enabled unconfirmed Bambu features now receive focused preservation warnings;
full semantic translation remains follow-up work.
The newer CORPUS_DRY_PLAN_AUDIT.md records 128 current files: 108 plans without
blockers, 12 blocked plans and eight legacy/non-modern rejections. Its three
undeclared `slic3rpe` XML cases now pass targeted export checks after the reviewed
legacy-tag/zero-assignment repair. Two are duplicate inputs. Their text/shape
metadata remains byte-identical; installed-slicer interpretation is unverified.

1. Embedded profile precedence: reviewed Anycubic source shows embedded presets
   are registered before the complete project config is applied. The planner
   now preserves unselected scopes, removes a lone explicitly retargeted scope
   only when all substantive keys are flattened, and blocks ambiguity or missing
   keys. A current three-plate coaster export passes archive/hash/structure
   validation; installed-slicer open/save/slice acceptance remains. The old
   coaster output is historical evidence only.
2. Broader real-model coverage: painted supports/colour, modifiers, variable
   layers, active ironing, intentionally slow tuning, and ASA/ABS must have
   explicit per-case evidence. A file merely containing default keys is not
   proof that the feature is active or preserved by the destination slicer.
   ACTIVE_FEATURE_COVERAGE.md now identifies actual ASA/ABS assignments,
   cupholder modifier settings, local ironing/negative parts and variable-layer
   members. New current ASA and ABS/PETG exports pass hash/structure checks,
   including the original 34-plate hose-holder layout; destination checks remain.
   Current painted-colour/active-ironing scraper and painted-manual-support
   bucket exports also pass, with actual nonempty triangle painting data and
   byte-identical paint-bearing model members. Destination interpretation still
   requires Preview checks; no such result is inferred from archive hashes.
   The `Nice supports - beta` engine/CLI/GUI path is implemented and passes a
   real-file export on the cupholder; the user has confirmed opening, slicing,
   and supports for that exact artifact. Other feature cases remain pending.
3. Continue validating nozzle changes against object and variable-layer
   overrides. The planner now reports local metadata overrides of changed keys,
   checks explicit local layer heights against machine bounds, and flags retained
   variable-layer files. Known `layer_heights_profile.txt` data now receives numeric,
   ordering and bounds checks; incompatible profiles block instead of being
   flattened. Object linkage and mesh-Z endpoint validation is now enforced for these
   profiles. Complete destination semantics still need testing for
   overrides. Automated real-file exports now cover 0.25 and 0.8 mm as well as
   0.4 and 0.6 mm; installed-slicer acceptance for the new extremes remains.
   A current Triceratops variable-layer export passed with all 175 profile
   points and the complete member unchanged; see ACTIVE_FEATURE_COVERAGE.md.
   A refreshed four-nozzle official/PETG matrix now passes current export/hash
   checks at 0.25/0.4/0.6/0.8 mm, with explicit hardened-steel selection and
   selected-process heights. The 0.25/0.4 hardware overrides are REVIEW, not
   calibrated community presets. See MANUAL_ACCEPTANCE.md for exact artifacts.
   Custom height selection is implemented in CLI/GUI with source first-layer
   retention; see ROADMAP.md. Source-versus-process height choice, bounds
   checks, line-width visibility/warnings, and accurate effective-profile naming
   are implemented.
   Reviewed `PrintConfig.cpp` validation rejects non-positive actual layer and
   first-layer heights; `Slicing.cpp` uses the object height directly. The
   local-height guard therefore correctly rejects zero rather than treating it
   as inheritance. Regression checks cover zero, negative, NaN, infinity,
   percentages and inclusive valid bounds without changing source bytes.
   Machine min/max-height zero values now follow `Slicing.cpp` automatic-limit
   semantics: 0.07 mm minimum and 0.75 times nozzle diameter maximum, with the
   maximum no lower than the minimum. Positive minimums have the slicer's
   0.01 mm floor. Tests cover all four supported nozzle diameters, missing
   limits, malformed values, and inconsistent positive bounds. Missing values
   remain unknown; explicit malformed limits or automatic maximums without
   valid nozzle diameters reject planning. Actual layer heights are never
   silently changed by these validation rules.
4. Audit user-provided reference handling against the original outline,
   including flattened custom reference projects and user calibration profiles.
   Saved S1 project machine/process discovery and export are now implemented and
   tested. The user's castle is discovered as a reference with four distinct
   filament-slot choices. Slot import is covered by export tests for ordering,
   temperatures, downward-only flow and exclusion of machine settings. Current
   reference outputs still need installed-slicer testing.
   A current real `tools.3mf` export using the castle reference and its PETG
   slot passes with 23 unchanged members, correct scope parents, retained
   source heights and the saved PETG temperature; see MANUAL_ACCEPTANCE.md.
   Custom-nozzle profiles now link to the nozzle-matched official parent and
   replace stale default filament/process references while retaining the
   community overlay. Plain inheritance alone failed the user's visibility
   check; the project-vector repair has now passed user-reported open, slice,
   and stock-filament visibility acceptance for the 0.6 mm cupholder.
   PROJECT_INHERITANCE_AUDIT.md records a 128-file read-only corpus check and
   the remaining process/filament scope and difference-mask investigation.
5. Confirm the GUI's final layout and workflow after the hotend selector change.
   A display-free GUI-to-worker contract regression now verifies every hotend
   selector mapping, physical nozzle, custom height, beta supports, temperature
   ceiling and ordered PETG/TPU slots reach the planner unchanged. The queued
   snapshot is unaffected by later control edits. This proves argument wiring,
   not visual layout or interactive end-to-end acceptance.
   GUI export guard tests additionally prove existing output/report files prevent
   work from being queued, invalid selections stop before export, and a report
   created after preflight is not overwritten. The latter reports partial
   success explicitly rather than claiming both files were saved.
   A withdrawn-window runtime smoke check passed on 2026-09-06: construction,
   physical-nozzle/custom-height/beta-support control variables, idle layout
   processing, and clean shutdown. All 76 unit tests also passed again. This
   involved no slicer interaction and does not prove visual layout or the full
   interactive export workflow.
6. Keep README, usage, and roadmap claims tied to current evidence. External
   rule configuration beyond CLAMP and intelligent intent detection were
   explicitly future features in the original outline.

No user information is currently required for the next engineering step.
Publication remains deferred as requested; model files and upstream research
checkouts remain excluded from Git.

## Final-pass evidence and new requests (2026-09-06)

- Refreshed 128-file dry-plan audit: 120 plans, 110 without blockers, 10 blocked,
  eight rejected for missing project configuration. This is planner coverage,
  not 110 destination-slicer acceptance passes.
- Fixed case-insensitive inherited extruder lookup and added a regression.
- Opened Xiaomi in Anycubic and saved a separate
  `reports/xiaomi-anycubic-import-roundtrip.3mf`. Hardened steel, 0.6 mm nozzle,
  1 mm community retraction, 0.2 mm layers, 0.62 mm widths, outer/inner speeds
  100/150, PETG at 230 C and tree supports survived. The displayed/default preset
  names changed; this did not discard those effective community values.
- The roundtrip selected Cool Plate despite the exported Textured PEI setting.
  User confirmed the print completed and came out great on the physical PEI
  plate. This is not evidence to recommend using the wrong bed selection.
  User requested a default Textured PEI selector with alternatives.
- Other roundtrip differences (including flush multiplier and filename format)
  remain recorded for investigation. Zig-zag to rectilinear is an explicit
  destination legacy normalization in PrintConfig.cpp, not lost geometry.
- GUI visual check: source loading, nozzle choice and discovery worked and
  controls were visible. A full GUI export was not completed before the new
  feature request arrived.
- Standalone filament conversion/import requested as a separate tab; feasibility
  and acceptance plan are in FILAMENT_PROFILE_IMPORT.md. The beta JSON/folder
  multi-nozzle review/export workflow is now implemented, isolated from existing
  3MF filament reassignment. Installed-slicer import acceptance is pending.
- Build-plate selector implemented in CLI/GUI, defaulting to Textured PEI.
  Both global `curr_bed_type` and per-plate XML `bed_type` are set. The byte-local
  XML patch handles existing/missing entries, multiple/self-closing plates,
  comments and legacy text; malformed/duplicate bed metadata blocks. Unit suite
  now has 106 passing tests; compilation and a real Xiaomi export pass.
  `reports/xiaomi-textured-pei-review.3mf` changes only project settings and
  model-settings bed metadata, with 18 untouched members and unchanged structure.
  SHA-256: `7CA8CD9F4C9675A2EC994733EC91BAD8FEF2FE7B2BD9F821C96BE9A9DA591CD6`.
  Installed-slicer verification of this new plate repair remains pending.

## Filament bundle implementation (2026-09-07)

- Added ZIP/`.orca_filament` source adapters without filesystem extraction,
  archive-local named inheritance, bounded reads and unsafe-entry rejection.
- Closed inherited plate-temperature validation gap; effective destination
  defaults must also fit the user's confirmed physical ceilings.
- Brief native desktop acceptance passed: both tabs render, all four installed
  S1 sizes are discovered, the 17-file Siddament test bundle loads, and review
  shows 15 plans plus two missing bases. Missing thermal confirmations block
  export as intended. No installed profiles changed.
- INI translation, explicit unmatched-material base mapping and real Anycubic
  preset import/reopen acceptance remain outstanding; this is not feature complete.

## Hotend declarations and base matching (2026-09-07)

- Added explicit standalone-import hotend selection using Justin's stated
  300 C PTFE / 320 C all-metal or ceramic limits. Ceramic 350 C requires an
  explicit firmware-change confirmation. Limits are user-reported, not
  independently verified. Lower entered ceilings remain enforceable.
- Selection starts unspecified; bed limits remain independently required.
  Hardware declarations are recorded in review provenance. No firmware or
  installed machine presets are changed.
- Replaced hard-coded-only filament base matching with canonical preference
  followed by a unique exact-material/nozzle fallback; ambiguous matches block.
- 125 tests and compilation pass. GUI construction passes; worker regression
  proves hotend/firmware values are snapshotted before background conversion.
  New controls have not had another visual desktop pass.

## Siddament native import and persistence repair (2026-09-07)

- Current user-confirmed setup: ceramic 0.6 HS, nozzle max 320 C; use 110 C
  effective software bed limit, not the reported 120 C hardware ceiling.
- 15 of 17 source profiles converted and installed through Anycubic's native
  Import Configs UI. PC-CF/PLA-CF remain excluded without matching 0.6 mm bases.
- Fixed display-name path characters: `/` names appeared imported in memory
  but failed persistence. Re-imported only the three normalized identities.
- All 15 final presets exist on disk and match 35 checked effective fields
  each. Previously existing 15 preset JSONs remain byte-identical. Native PETG
  editor confirms HS 255 C / textured PEI 70 C / flow 16 mm3/s, and stock
  filaments remain visible. Fresh-session reopen and print calibration remain.
- Exports now include a flat JSON-only ZIP, with exclusive creation, fresh
  directories and cleanup regression coverage. 130 tests and compilation pass.
- Corrected artifacts: `reports/S1-filaments-8rbt5e9w/`; evidence and caveats in
  FILAMENT_PROFILE_IMPORT.md. No printer commands or firmware changes were sent.
