# Remaining work (2026-10-01)

User accepted plate warning for beta. Automatic plate selection remains known
bug, no longer a beta blocking user decision. Windows portable executable
built and smoke verified; see local CHECKPOINT for path/hash. Signing,
installer and physical calibration remain later. MIT licence, first commit,
public GitHub repository and 0.4.1 beta release are COMPLETE; see
PUBLICATION_CHECKLIST.md for remote links and verified hashes.

Publication update: user approved public MakerWorldToKobraS1 + MIT on
2026-10-01. Publication and hosted CI checks are now complete; see
PUBLICATION_CHECKLIST.md. Latest UI release passes 216 tests. Earlier pending
beta-decision entries below are historical, not current blockers.


Current:212/212 tests PASS; package release-check-i8sx5rk1 PASS, no run in
progress. Goal blocked pending user beta decision on native plate-default
failure. Warning/editable selector is implemented but not an automatic fix.
No further completed checks need rerunning until code changes. Native GUI
notice rendering is unverified; callback behavior has automated coverage.


Plate-default limitation now explicitly warned in conversion report and GUI
success notice, with selected plate named. This is mitigation, not a fix.
Await user choice: accept warning/editable selector for beta, or continue to
hold automatic-default gate. No scope waiver inferred. Full regression/package
rerun after warning addition is in progress; native GUI notice not retested.


Reconciled current remaining work: resolve automatic Textured PEI selection
when native0.4 printer remembers Cool Plate, preserving editable plate choice
and stock filament compatibility; retest affected export and regression/package
after a real fix.0.6 fresh-process persistence now PASS. GUI, representative
large multi-plate, corrected process and210/210 suite/package gates PASS.
Physical calibration/fit, licence, first commit and GitHub are later work.
Older pending entries below are historical and superseded by this summary.


Current unresolved failure: unique project-local machine candidate did not
prevent remembered Cool Plate overriding PEI on native open. Do not promote
it. Find a solution preserving user-editable global plate selection; no live
app_config edits or locked per-plate overrides. Fresh-process0.6 persistence
is additional evidence; final suite/package rerun remains. GUI and large
multi-plate native gates are passed, superseding older pending entries.


GUI native auto-fit checkbox/export/new-source-reset smoke PASS. Exact
artifact/report and default brass choice are in CHECKPOINT. Current required
remaining issue is remembered native plate preference overriding exported
PEI; preserve selectable global plate and do not edit live user preferences.

LATEST: representative large multi-plate streamed conversion native open/
fresh slices PASS on BOTH synthetic plates (30.15 g / 1h21m and 38.48 g /
1h39m). 0.6 same-session reopen also PASS. Remaining acceptance: remembered
Cool Plate default, GUI auto-fit/export/reset; fresh-process restart check
for 0.6 still optional additional persistence evidence. Historical pending
large-model and process-mismatch statements below are superseded.

Large multi-plate streamed planning AND writing are now implemented, with
large-file preservation, rotated-component equivalence, and bounded mesh
allocation regressions. Native large multi-plate acceptance still remains;
older "unimplemented" statements below are superseded. Other pending gates
remain 0.6 reopen, remembered plate default, and GUI auto-fit/export/reset.

Large-model writer now streams relocation via a disk spool; 26 MiB fixture
preserves all mesh bytes with bounded source reads. The planner still needs
streamed graph/vertex measurements; do not count large multi-plate accepted.
Current full suite 206/206 PASS. See checkpoint for package result/state.

Current superseding result: selected-naming 0.6 artifact opens with a clean
optimized process and freshly slices its one plate (74.50 g / 3h27m).
Reopen persistence remains. Filename/support-ironing mismatches below are
historical failed candidates, not current failures. Latest suite 204/204;
package `release-check-7z7w2skr` PASS. Remaining active gates: remembered
Cool Plate default, GUI auto-fit/export/reset, large multi-plate streaming.

Newest schema-scope retest: support-ironing mismatch resolved; only filename
format remains in the 0.6 process comparison. Both embedded and flattened
values now include the format, so merely adding the field again is not a
fix. Check native external-preset selection/difference-mask handling next.
203/203 tests and `reports/release-check-ugvq6_uo` package verification PASS.
Newest artifact: `reports/tools-06hs-018-schema-fix-20261001.3mf`.

Latest resumed evidence: 203/203 tests and package check
`reports/release-check-nx631tzz` PASS. Selected-leaf parent repair removes
0.6 prime-volume/cone differences, but filename format and support-ironing
spacing still dirty the optimized preset. Native slicing/reopen of the
latest parent-fix candidate remain pending. GUI Enter-load and discovery
pass; checkbox/export/new-source-reset still need the native smoke check.

2026-10-01 current remaining checks/features (supersedes pending statements
below):
- Routine tracker both-plate native slicing and clean optimized process PASS;
  repaired RODSLOTH clean process/open/slice PASS; large single-plate tools
  load/slice PASS. Detailed plate results are in `CHECKPOINT.md`.
- Resolve why fresh 0.4 imports show remembered Cool Plate despite correct
  Textured PEI project JSON; selector override itself passed.
- Resolve remaining 0.6 optimized-process differences (prime volume, cone
  apex and filename format), then slice/reopen the regenerated candidate.
- Native GUI auto-fit/load/reset smoke check remains.
- Large multi-plate streamed relocation remains unimplemented.
- Physical fit/calibration, licence/first commit/GitHub remain later steps.
Latest automated suite is 202/202; current package verification is
`reports/release-check-9ln1vpip` PASS.

2026-09-30: The opt-in GUI `Scale to fit S1 plate` / CLI `--scale-to-fit`
path and Routine tracker auto-fit export (plate 1: 94.4%; plate 2: 100%)
are implemented and statically checked. The earlier fixed 94% export is
retained separately; explicit `--scale-percent` is advanced CLI-only.
Native open/slice of both plates is still required, especially prime tower,
support, brim and purge paths. User must confirm the 94.4% plate-1 dimensions
are acceptable for any fit-critical use. See the top of `CHECKPOINT.md`.

Use the local, untracked CHECKPOINT.md for the interrupted-run state and
[ACCEPTANCE_STATUS.md](ACCEPTANCE_STATUS.md) for exact historical fixture
evidence. The prior local software beta gate passed 12/12 representative
fixtures; this list concerns newer changes or wider validation.

## New project-process preset feature

- The current painted-support candidate passed native open, project-inside
  `[Optimized]` 0.16 mm menu selection, fresh slices of both support plates,
  and reopen persistence without a Modified G-code dialog. See the top of
  `CHECKPOINT.md` for exact outputs and limits.
- The real Bambu-source candidate opened without a G-code warning but failed
  the clean-preset check: printer and `[Optimized]` were immediately starred.
  A focused repair and regression coverage produced
  `reports/rodsloth-petg-04-scope-fix-candidate.3mf`; repeat native
  open/slice and inspect any remaining deliberate overrides. The 0.6 HS/0.18 mm PETG candidate is
  `reports/tools-06hs-018-optimized-process-candidate.3mf`; it is statically
  verified but not natively opened. Avoid opening multiple slicer windows at
  once; replace or close only this task's test project, and do not Save
  temporary overrides into installed presets. The Bambu comparison dialog
  is open with no Save/Discard selected.
- The source process is intentionally kept as a read-only JSON reference in
  the output, not an S1-selectable profile. It has not been print validated.

## Wider validation and user decisions

- Do not treat one successful painted-support fixture as all-profile
  acceptance; the real Bambu and alternate-nozzle checks above remain.
- Single-plate `tools.3mf` now exports despite its 65,830,959-byte model XML;
  native open/slice is pending. Large *multi-plate* model XML still needs a
  bounded/streamed relocation path; do not raise the safety cap blindly.
- The optional ironing/negative-volume fixture remains excluded from routine
  beta acceptance and has an unreviewed Modified G-code warning.
- Physical print calibration remains for Siddament and engineering materials;
  confirm hardware/firmware thermal limits before using high-temperature
  profiles. Installed Siddament menu co-visibility is not all-field validation.
- Choose a licence and privacy policy, review staged files for private data,
  then make the first local commit and configure/push a GitHub remote if wanted.

Current automated status: 202/202 unit tests and packaged-release
verification pass. These do not replace the native checks above. No firmware
change, print initiation, commit or remote publication is part of this checkpoint.
