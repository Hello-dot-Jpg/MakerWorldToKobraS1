# Project handoff - current acceptance state

Public beta published (2026-10-01):
https://github.com/Hello-dot-Jpg/MakerWorldToKobraS1/releases/tag/v0.4.1-beta .
Plain-English executable/UI instructions are in root USING_THE_APP.md and
included in the ZIP. Public repository is MIT-licensed. Hosted CI passes all
216 tests on Python 3.11/3.12/3.13; release assets and tag verified anonymously.
Models/private presets/reports/research and the local checkpoint are excluded.
Signing, installer and physical calibration remain outside this release.

Latest UI release (2026-10-01):0.4.1-beta refreshes both tabs with a shared
charcoal/blue theme, numbered cards, scrollable settings and separate source/
review areas. Converter export controls stay visible. Advanced options are
expandable; original conversion defaults/install confirmations remain.
216/216 tests and release-check-zjnvcg9b package PASS. Frozen GUI runtime and
readonly busy-state restoration PASS. Current executable:
`dist/S1Optimizer-0.4.1-beta-q6y__d6a/S1Optimizer-0.4.1-beta.exe`.
Native source load, original-settings overview, profile discovery and form
scrolling retested after the keyboard-only focus-scroll fix. No new exports
or live preset installation claimed in the UI pass.
Plate warning was explicitly accepted for beta; automatic selection remains
a known issue, not a claimed fix. Older blocked scope notes below superseded.


Latest 2026-10-01: corrected0.6 optimized process passes clean open/slice
and fresh-process restart persistence. Large multi-plate streaming passes
fresh slices of BOTH synthetic plates; converter GUI auto-fit/export/reset
passes.210/210 tests and package release-check-u6wd4dbp pass. The remaining
native failure is remembered Cool Plate overriding exported Textured PEI
on0.4. Experimental unique embedded printer also failed; not integrated.
Manual plate selection remains editable. Overall acceptance incomplete.
See CHECKPOINT for exact artifacts and current session.

2026-10-01 native progress: repaired RODSLOTH opens with a clean optimized
process and slices; Routine tracker auto-fit after a focused schema-field
fix opens cleanly and slices both plates. Large 0.6 HS tools loads/slices,
but its regenerated optimized process still has default-value mismatches.
The plate selector is usable; fresh imports honoring Textured PEI over a
remembered Cool Plate still needs resolution. 202/202 tests and current
package verification PASS. See the top of `docs/CHECKPOINT.md` for exact
outputs, hashes, plate results and next actions; earlier pending notes
below are historical.

2026-09-27 Bambu repair candidate: the seven-value mismatch has a focused
code repair and new RODSLOTH export; 198/198 tests and isolated package
verification pass. Native open/slice is pending while the older test-only
unsaved-changes dialog is cleared. See `docs/CHECKPOINT.md` for exact values
and candidate hash. The 0.6 HS candidate also remains natively pending.

2026-09-27 update: the new project-local `[Optimized]` process and read-only
source-process reference pass 196/196 automated tests and packaged-release
verification. The current painted-support candidate opened natively without
a Modified G-code warning, showed the 0.16 mm `[Optimized]` entry under
Project-inside presets, freshly sliced both plates with supports, and reopened
with the same selected process after a clean slicer restart. The real Bambu
spot-check exposed a scope/inheritance defect: Anycubic starred printer and
process settings on open, so it was not sliced. The 0.6 mm alternate-nozzle
spot check remains pending. Current archive
candidates and exact status are at the top of `docs/CHECKPOINT.md`. The 12/12
result below applies to the prior converter behavior.

2026-09-26 current status: the scoped **local software beta** gate is
**12/12 passed** (the special-purpose ironing file is excluded). The final
ASA clamp project opened without a Modified G-code warning and sliced with
ASA in slot 2; the refreshed 34-plate hose holder passed representative
PETG/ABS plates, and both refreshed painted-support plates sliced. The
corrected Communication Cards export sliced plates 12-14; earlier candidates
sliced plates 1-2. No claim that all plates of either multi-plate project
were sliced. Fresh automated suite: 193/193 PASS; package verification:
`reports/release-check-530ojfx_/verification.json` PASS. See
`docs/ACCEPTANCE_STATUS.md` and `docs/CHECKPOINT.md` for exact artifacts and
limitations. Physical print travel/calibration, wider Siddament field
persistence, optional ironing, licensing, first commit and GitHub publication
remain outside this gate. Older entries below are historical and superseded
where they conflict with this status.
The installed Siddament batch also passed a fresh 50/50 hash check, prior
presets passed 106/106 hashes, and the native filament dropdown showed
Siddament and stock choices on all four official nozzle sizes. This was a
menu spot-check, not item-by-item editor-field or physical calibration.

2026-09-24 update: local beta acceptance is blocked, not complete. The new
Siddament batch passes installed-file/hash checks and the 45+3 new plans have
zero field differences, but two 0.6 PC-CF/PLA-CF names are duplicated under
`filament/base`, and older 0.6 HS fan/slowdown/ASA temperatures differ from
their exports. The installer now catches future `base/` name collisions;
isolated rollback/collision tests and the full 185-test suite pass. Package
verification passes at `reports/release-check-gbc2c8fx/verification.json`.
Communication Cards opens and plate 1 slices; plate 2 hits an over-boundary
error, so native tests stopped. Five manifest fixtures remain untested. See
`ACCEPTANCE_2026_09_24.md` for exact remaining work. No installed presets,
saved projects, printer firmware or GitHub state were changed by this check.

2026-09-15 continuation: automated recheck passes all 164 tests, source
compile, CLI help and whitespace validation. Read-only Siddament dry audits
cover 0.25/0.4/0.8 mm with 14/17/15 review-ready plans respectively; skips
are explicitly reported where no matching destination base exists. No export
or installed preset changed. The active-path persistence recheck still shows
broader fan/slowdown/ASA differences, so full-field import fidelity remains
open. Native warning-gated cases remain untouched.

Numeric status: 180/180 automated tests pass (0 remaining); 13/13 acceptance
manifest fixture-preparation rows are ready; and 8/13 manifest fixtures have
native open/slice evidence (5 remaining). Two historical attempts stopped at
the unaccepted `Modified G-code` confirmation. See
`docs/ACCEPTANCE_STATUS.md` for the exact five remaining cases.
The scoped difference-mask fix and a fresh ASA archive are ready for native
recheck; no slicer pass is claimed yet. Fresh package verification passes at
`reports/release-check-pajo5oi9/verification.json`.

2026-09-14 continuation: local `unittest discover` passes all 164 tests and
`compileall` passes. Downloads audit refreshed to 137 archives / 129 modern
project-settings members; three known unbound-prefix XML cases remain partial.
Native .25/.4/.8, variable-layer, timing, detached INI and three-plate coasters
checks are recorded in ACCEPTANCE_2026_09_14.md. Controlled restart now also
passes. Painted-support remains stopped at the Modified
G-code confirmation; no warning was accepted.

2026-09-14: detached INI saved-project roundtrip PASS (all config values
identical; same slice estimate). Installed preset audit passes unchanged.
Timing fixture open/slice/native-save preserves 126.423/0/0. Official .25 and
.8 nozzle fixtures open/slice with correct widths/layers and stock filaments.
Details: ACCEPTANCE_2026_09_14.md. Remaining native matrix and complex-file
coverage are still outstanding; no new code changes or physical-print claims.

2026-09-13: recovered detached INI import succeeded, with fresh strict audit:
40 compared keys match and all 51 prior presets unchanged. Do not reimport.
Native round-trip validation is still pending. Latest package verification PASS:
reports/release-check-o5s3v6wa/verification.json (includes detachment fix).
This supersedes the pending-build/import statements below.

2026-09-10 LATEST: all six engineering guide materials have 0.6 HS cube
slice/save evidence. Saved INI reopening exposed a silent reset to stock
temperatures/flow despite retaining the custom name. A detached-preset export
fix is implemented; 164 tests pass. Fresh gpkh6spe export awaits native
import/restart/save/reopen verification. Previous initial-slice passes remain
valid but do NOT establish round-trip fidelity. No installed presets replaced.
See CHECKPOINT.md for exact continuation. Release rebuild required after fix.

2026-09-10 update: corrected real INI preset 7ea9264060 now passes native
import/restart/editor/cube slicing; 50 prior presets unchanged. Saved review
project: reports/ini-prusament-petg-06hs-corrected-review.3mf (6.78 g / 18m28s).
Range fix release rebuild passed at reports/release-check-0cckgvm0/verification.json.
163 tests pass. Remaining engineering/nozzle/complex-case acceptance is still
pending; see CHECKPOINT.md. Earlier pending INI/rebuild statements below are
historical and superseded by this update.

Latest continuation: see `CHECKPOINT.md` and `ACCEPTANCE_2026_09_09.md`.
163 tests now pass. Native INI GUI review/export/import passed, but its editor
exposed an inherited range mismatch (240 C range versus 245 C print setting).
Source fix and regression now apply the existing <=15 C warning rule to
inherited ranges too. Corrected re-export/import and native validation remain;
old installed Prusament is retained as pre-fix evidence, not overwritten.
Latest reproducible package verification (predates this range fix; rebuild needed):
`reports/release-check-ufl47dm_/verification.json` (passed).
Explicit PC -> PC-CF correction is implemented with an opt-in checkbox;
Siddament PC-CF REVIEW export `reports/S1-filaments-nc8jzvvg/` is installed.
Discard approval resolved; temporary scraper changes discarded, saved file untouched.
Corrected PC-CF imported and verified after restart; 48 existing presets unchanged.
PLA-CF and PC-CF visible on S1 0.6 after restart. Corrected Siddament PC-CF
passed native cube slicing and saved-config checks (engineering-cube-pccf-06hs-review.3mf).
Remaining engineering presets and saved-cube reopen still need native acceptance.
Xiaomi Textured PEI and painted-colour scraper native slices
pass. Engineering restart completed, with redundant range-HS metadata removal
documented; engineering slicing remains pending. These updates supersede the
older historical notes elsewhere. Explicit base selection and engineering-base
loading are implemented in the GUI; native visual acceptance remains pending.
Scraper slicing reports a floating-cantilever warning: colour preservation
passed, but physical support adequacy is not established.

Usable beta, not feature-complete or universally print-calibrated. Continue to
review converted projects in Anycubic before printing. Launch with `run_gui.cmd`;
restart an already-open converter to load the latest controls.

## Completed and checked

- Core 3MF retargeting, independent nozzle/process/layer-height selection,
  Nice supports beta, stock filament inheritance repair and Textured PEI default.
- User-confirmed successful cupholder slicing/supports and Xiaomi printing.
- Separate filament tab: JSON, ZIP/orca_filament and limited INI input,
  multi-size destination selection, hardware ceiling gates and audit output.
- Fifteen Siddament 0.6 HS review presets installed and verified after Anycubic
  restart; no pre-existing preset changes. Read-only all-size dry audits now
  cover 0.25/0.4/0.6/0.8 mm; only the 0.6 batch has native installation
  evidence, and missing bases remain explicit review skips.
- One additional Siddament PLA-CF 0.6 HS preset imported using an explicit
  engineering base. Exact saved-field audit passes; all 47 pre-existing
  root/base presets unchanged. Restart and visibility passed; slicing remains.
- Corrected Siddament PC-CF 0.6 HS imported and audited after restart; all 48
  pre-import presets unchanged. Both filled-material presets remain REVIEW-only.
- 159 tests; reproducible independent wheel builds and isolated installation
  checks pass. Latest evidence: `reports/release-check-ufl47dm_/verification.json`.
  This is not a standalone EXE. See RELEASE_VERIFICATION.md.

## What Justin needs to do

1. Calibrate a small sample of each material before larger prints: temperature,
   flow ratio, pressure advance and maximum volumetric flow. Start with the
   current ceramic 0.6 HS setup. Record the exact preset name and results; the
   imported presets intentionally retain destination calibration rather than
   assuming Bambu calibration transfers.
2. When using other nozzle sizes or constructions, confirm the physically
   fitted nozzle and hotend. Do not treat a successful 0.6 PETG print as evidence
   for 0.25/0.4/0.8 or abrasive materials. Supplier suitability/minimum-nozzle
   guidance is needed for filled filaments, especially the smallest nozzle.
3. PC-CF/PLA-CF missing-base research found installed S1 0.4 and S1 Max references.
   The authorized S1 Max guide generator now supplies REVIEW candidates; see
   ENGINEERING_FILAMENT_GUIDES.md. You no longer need to locate these references,
   but their material/nozzle calibration still needs physical testing. PLA-CF
   and PC-CF are imported. User delegated the PC-CF interpretation: its source
   PC declaration was explicitly corrected to PC-CF with an audit trail;
   original source bytes remain unchanged. No material-choice approval is pending.
4. Before GitHub publication, choose repository name/visibility and a licence.
   No remote, public upload or initial commit has been made. Local downloaded
   models, reports and research checkouts are ignored, not intended for upload.

Current agreed effective limits: ceramic 320 C, bed 110 C. The reported hardware
bed maximum is 120 C; the software discrepancy remains unexplained. Nothing in
this project changes firmware. The optional ceramic 350 C mode requires explicit
confirmation of a real firmware change; it is not active for the current setup.

## Remaining engineering/acceptance work (not homework for Justin)

- Textured PEI open/save acceptance passed: `reports/xiaomi-textured-pei-review.3mf`
  opened without errors and saved as `reports/xiaomi-textured-pei-final-roundtrip.3mf`.
  Project and plate metadata retain Textured PEI; nozzle 0.6/hardened_steel,
  layer 0.2, line width 0.62 and textured plate temperature 75 C survived saving.
  New-artifact Preview/slicing passed; earlier user print evidence is separate.
- All 18 engineering starting-point presets are installed; six materials are
  visible for 0.6. Restart passed identity persistence; nine presets lost redundant
  range-HS fields, explicitly recorded in the strict audit. Ordinary temperatures
  remain correct. Cleaned-up replacements are exported but not reimported.
  Engineering-material slicing/physical calibration remain pending.
- Finish current-artifact coverage for embedded profiles, multiple plates,
  painted colour/manual supports, variable layers, ironing and ASA/ABS. Exact
  candidates and their limits are in MANUAL_ACCEPTANCE.md and ACTIVE_FEATURE_COVERAGE.md.
- Check stock filament visibility on the other nozzle sizes in Anycubic.
- Native GUI acceptance of the new INI controls and real vendor INI import.
  Actual Prusament PETG INI parsing/conversion/export passed; see REAL_INI_ACCEPTANCE.md.
- Explicit destination-base selection visual acceptance; more mapped
  vendor-specific settings only when their semantics are established.
- Publication review and optional standalone Windows distribution. Reproducible
  wheel packaging is verified locally, not a complete product acceptance pass.

These checks can be continued by the agent with focused desktop use. A usable
headless Anycubic workflow was not established, so archive comparisons alone
must not be labelled successful destination slicing.
