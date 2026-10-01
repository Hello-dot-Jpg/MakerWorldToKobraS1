# Acceptance status (2026-10-01)

Current beta scope: representative converter/native checks passed; the user
accepted the plate-choice warning plus editable selector as a beta limitation.
Automatic plate selection and physical calibration are NOT claimed complete.
Publication preflight passed216 tests (14.801s), compile and package
release-check-am4qeo8x with MIT metadata. The0.4.1 executable and release ZIP
passed runtime/CRC/hash checks. Later packaging/documentation changes do not
change converter behavior. Earlier pending-scope statements below are
chronological history, not current blockers.

UI0.4.1 refresh PASS for presentation/runtime scope: both tabs visually reviewed,
source Enter-load/overview, profile discovery and scrolling retested. Busy-state
readonly restoration and frozen runtime smoke PASS.216/216 full tests and
release-check-zjnvcg9b package PASS. Final EXE q6y__d6a in CHECKPOINT; previous
intermediate UI builds superseded. No fresh native slicing/installation claim.

User accepted remembered plate preference limitation with editable selector
and warning for beta. It remains a bug, not automatic-selection acceptance.
Windows0.4.0-beta executable built; frozen runtime and native GUI launch,
real source Enter-load and local profile discovery PASS.212/212 tests PASS.
Exact release artifact/hash and verification scopes are in CHECKPOINT.


Latest212/212 full tests PASS, including actual GUI export-success callback
warning test. Package release-check-i8sx5rk1 still matches unchanged production
code. Native success-notice visual rendering not separately tested. Automatic
plate-default failure remains; no user scope decision received.


Latest warning mitigation passes211/211 tests and package
release-check-i8sx5rk1. Plans/reports and GUI success notice explicitly tell
users to verify requested Plate Type because native remembered preference
can override it. This does NOT close the automatic-default gate; user choice
on beta scope is pending. Native notice wording itself has not been retested.


Reconciled latest gates: GUI auto-fit/export/reset PASS; representative large
multi-plate open and both slices PASS; corrected0.4/0.6 optimized processes
PASS;0.6 fresh-process restart persistence PASS. Latest210/210 suite and
release-check-u6wd4dbp package PASS. Only current native acceptance failure
is remembered Cool Plate overriding exported PEI on0.4. Manual selector is
editable. Experimental unique machine failed and is not a production fix.
Overall acceptance remains incomplete. Entries below are chronological
history, not additional outstanding gates.


Latest verification: 210/210 automated tests and package verification PASS
(`release-check-u6wd4dbp`). Experimental plate selector is editable and was
restored to Textured PEI; automatic default remains FAIL, not accepted.


Current plate-default gate FAIL: experimental unique embedded printer loads
correctly but still displays remembered Cool Plate instead of exported PEI.
Not promoted to normal exports. Native candidate filament-menu/slice checks
stopped at this failure. Overall local feature acceptance remains incomplete.
The GUI and large multi-plate gates passed; older pending notes are historical.


Converter GUI native auto-fit export/reset PASS: success dialog, generated
94.4%/100% report with zero blockers and valid CRC; next source clears prior
options/output/report. Current required outstanding gate is native remembered
bed preference overriding project PEI. Overall acceptance remains incomplete.

Large multi-plate representative native gate PASS: synthetic tools output
opens cleanly and freshly slices BOTH plates to inspected support/brim
previews: 30.15 g / 1h21m and 38.48 g / 1h39m. No native bounds error.
0.6 same-session reopen passes. Plate-default and GUI smoke gates remain.

Streamed large multi-plate planner/writer implemented and regression-tested:
210/210 full tests PASS, package `release-check-h5s6biy7` PASS. Exact large
model bytes are preserved except planned build transforms; rotated-component
audit matches prior implementation. Native large multi-plate acceptance is
not yet established; Downloads has no existing >25 MiB multi-plate fixture.

Latest 0.6 selected-naming candidate passes native clean-process open and
fresh single-plate slice (74.50 g, 3h27m, supports/brim visible), without a
Modified G-code dialog or bounds error. Reopen persistence remains pending.
204/204 suite and `release-check-7z7w2skr` package PASS. Latest overall feature
acceptance still incomplete: plate-default, GUI and large multi-plate gates.

Newest follow-up removes the native support-ironing mismatch. The 0.6
optimized process is still modified by filename format, hence not accepted
as clean. Full 203/203 tests and package check `release-check-ugvq6_uo` PASS.
Newest schema-fix artifact opened without warning but was not freshly sliced.

Latest resumed regression: 203/203 full tests PASS and package verification
PASS at `reports/release-check-nx631tzz`. Native 0.6 parent-fix opens safely
with correct layers/widths but is still starred (filename format and support
ironing spacing); clean-preset acceptance remains incomplete. This newest
candidate has not been sliced. See the checkpoint for exact current state.

2026-10-01 latest native checks: repaired RODSLOTH `[Optimized]` 0.16 mm
opens unstarred and slices plate 1 (9.71 g, 37m45s); only intentional
PETG flow-limit override remains in its comparison. Routine tracker after
the schema-process-field fix opens with an unstarred `[Optimized]` process
and freshly slices both plates (212.22 g / 6h55m; 7.37 g / 20m25s).
Large single-plate tools / 0.6 HS loads and slices (74.50 g / 3h27m),
but its regenerated process still has a native default/preset mismatch.
Plate dropdown override works; remembered Cool Plate on fresh 0.4 imports
still needs resolution. Full 202/202 tests and package verification PASS
at `reports/release-check-9ln1vpip`. Exact artifacts and caveats are at the
top of `CHECKPOINT.md`. Latest feature acceptance remains incomplete.

2026-09-30: Opt-in per-plate automatic S1 fitting and the Routine tracker
auto-fit export pass static mesh-fit/archive checks and 202/202 automated
tests. Plate 1 scales to 94.4%; plate 2 remains 100%. The previous manual
94%-on-both-plates export remains a separate artifact. Native opening/slicing
and physical dimensional fit remain unverified; the auto-fit export is a
REVIEW artifact, not a print-ready acceptance result.

The Bambu-source mismatch has a repaired candidate at
`reports/rodsloth-petg-04-scope-fix-candidate.3mf` (details and hash in
`CHECKPOINT.md`). Static checks and 198/198 automated tests pass, but the
new candidate has not yet been opened or sliced in Anycubic. Do not count it
as a native pass; the older candidate's comparison dialog remains open.

The new project-local `[Optimized]` process preset and read-only original
process reference are **partially natively accepted**. The current painted-
support scoped-process candidate opened in a fresh Anycubic instance without
a Modified G-code warning; its checked `[Optimized]` 0.16 mm process appeared
under **Project-inside presets**. Plates 1 and 2 each completed a fresh slice
with support/interface toolpaths (29.23 g / 1h16m and 48.02 g / 1h40m).
After discarding test-only unsaved filament overrides and restarting the
slicer, the same file reopened with the optimized process selected at 0.16 mm.
The real Bambu candidate then **failed** the clean-preset check: Anycubic
opened it without a G-code warning but starred both the printer and
`[Optimized]` process. Its unsaved-change comparison lists three extruder-
clearance differences, PETG price/volumetric-speed differences, filename
format, and ironing angle. No slice was attempted and no settings were saved.
The 0.6 mm alternate-nozzle candidate still needs a native spot check.
Exact artifacts and hashes are at the top of
`CHECKPOINT.md`. This new feature gate is separate from the historical 12/12
beta gate below.

The previous local native beta gate was **12/12 passed**. The last fixture,
`reports/asa-heat-bed-clamps-selectable-04hs-review.3mf`, opened without a
Modified G-code dialog, showed ASA in slot 2 and a selectable Textured PEI
plate, and sliced to a Preview toolpath (1.29g, 6m14s, `T:1`). The archive's
machine scripts match the currently installed official S1 0.4 preset and its
scoped difference mask contains no G-code fields. A generic static G-code
validator still flags six official-script purge/presentation Y moves outside
the 250mm printable square; their physical travel safety was not validated.
This is local **software** beta acceptance, not print readiness, filament
calibration, or approval of the optional ironing test. The 34-plate hose
holder was checked on PETG plate 1 and ABS plate 16 only. On the corrected
Communication Cards export, plates 12, 13 and 14 were sliced; plates 1 and
2 were sliced on earlier candidates. Do not infer that every plate was sliced.
Fresh final checks: 193/193 automated tests and package verification PASS at
`reports/release-check-530ojfx_/verification.json` (two byte-identical
wheels, isolated imports and CLI help). The historical entries below record
earlier candidates and should not be read as the current gate status.
Read-only Siddament persistence recheck found 50/50 installed batch hashes
and 106/106 pre-install file hashes unchanged. It does not establish every
profile's native menu visibility or print calibration.
Native dropdown spot-check subsequently showed Siddament entries alongside
stock PETG/PLA for all four official S1 nozzle sizes (0.25/0.4/0.6/0.8).
This is co-visibility, not a 50-item menu count or all-field editor audit.

Painted-support native check passed on
`reports/painted-support-bucket-current-04-masked-review.3mf`: both plates
sliced, support and interface paths are visible, and the painted model members
are unchanged from the source. The old all-keys mask was replaced by a scoped
one, eliminating the Modified G-code dialog without changing the installed S1
scripts. The remaining precise-wall warning is a print-quality note, not a
support-slicing failure. At that stage the beta gate was **11/12 passed**;
the ASA fixture subsequently passed as recorded above.

Latest native representative check: regenerated the 34-plate ABS/PETG
hose-holder as `reports/abs-petg-hose-holder-plates-04hs-native-grid-review.3mf`
after the measured Anycubic plate-grid correction. It opened without a
Modified G-code warning; PETG plate 1 and ABS plate 16 each sliced with
toolpaths, and the sidebar showed `Slice all 2/34`. The prior export showed
`Failed 2/32` after the same two representative slices and predates the grid
fix; do not use it for acceptance. The other 32 plates have not been sliced.
This closed the representative ABS/PETG native check, so the beta gate at
that stage was **10/12 passed**. The two later fixtures passed as above.
The ASA/painted archive machine G-code values match the current installed
official S1 0.4 machine preset; a stale research copy previously suggested a
difference. Their native Modified G-code warning remains unapproved and needs
an exact mask/inheritance explanation.

Latest targeted native result: the corrected Communication Cards export
`reports/CommunicationCardsV2_KobraS1_0.4HS_PLA_NATIVE_GRID_FILAMENT_REVIEW.3mf`
opens with Textured PEI, 14 plates and seven colour slots. Plates 12 Green,
13 Red and 14 Black each sliced successfully in Anycubic Slicer Next 2.0.0.3
after correcting the native plate-grid pitch. This closes the observed
off-bed failure for those plates only; the other plates have not all been
sliced. Automated regression suite: 193/193 PASS. Package verification:
`reports/release-check-weu_g6nt/verification.json` PASS. The first verifier
attempt without the project-local build dependencies was incomplete at
`reports/release-check-6tl4xg07/verification.json`; this was an environment
setup error, not a package failure. The official 0.6 HS PETG fixture also
opened and sliced natively (76.61g including support, 3h10m, zero filament
changes), reducing the manifest gap to four fixtures. The next ironing/
negative-volume import stopped at an unreviewed Modified G-code warning
covering machine start/end/pause, layer/filament changes and custom fields;
it was **not** acknowledged or sliced. At the user's direction, this
special-purpose ironing test is now outside routine beta acceptance. It
remains in the 13-file inventory, but not the 12-fixture native beta gate.
The warning is still unreviewed, not deemed safe. Three native beta-gate
fixtures remain, so the local beta is not accepted yet.

The following historical entries retain their original dates and scopes.

The next Textured PEI startup-default candidate is
`reports/CommunicationCardsV2_KobraS1_0.4HS_PLA_TEXTURED_MASKED_REVIEW.3mf`.
It fixes the converter's machine override mask so `default_bed_type=4` cannot
be silently replaced by the installed printer preset. This exact candidate
has **not** been reopened natively; no acceptance pass is claimed. Automated
tests: 192/192. Post-change release verification:
`reports/release-check-7p7ccbul/verification.json` PASS. The slicer remains
open on the preceding task-generated project with an unsaved manual plate
selection; action-time confirmation to discard that change was requested.

Latest native check: `CommunicationCardsV2_KobraS1_0.4HS_PLA_TEXTURED_REVIEW.3mf`
opens with 14 plates and seven colour slots. Its Plate Type selector is
enabled, and plate 2 (Help, red/white) sliced successfully after manually
selecting Textured PEI. **The selected plate still opens as Smooth Plate**
despite explicit Textured PEI project and machine-default settings, so the
requested automatic plate default is not accepted. Plate 1 is shown as
`Failed 1/14` in this session; that result has not been investigated. No
other plate in this review file is counted as sliced. The native manifest
count below remains 8/13. The preceding regression suite was 191/191 and its
package verification passed at
`reports/release-check-70en00wk/verification.json`.

The 34-plate ABS/PETG hose-holder was regenerated with verified S1 plate
relocation as `reports/abs-petg-hose-holder-plates-04hs-review.3mf`.
`reports/acceptance-manifest-2026-09-25-v2.json` inventories it and the
selectable-plate ASA fixture; 13/13 archives are prepared with zero errors.
Native slices of both remain pending. An earlier package check passed at
`reports/release-check-ldweqlek/verification.json`.

The 2026-09-25 plate follow-up is recorded at the top of
`CHECKPOINT.md`. All 14 Communication Cards object groups are statically
within the resized S1 beds. Residual 4-12 mm off-centre positions come from
the source 3MF and are preserved. A new review export explicitly carries the
official S1 `support_multi_bed_types=1` setting so its global plate choice
should remain available. Native reopen, plate-choice override, and additional
plate slices are still pending because the slicer contains an unrelated
unsaved user project. The preceding suite was 189/189 and package verification
passed at `reports/release-check-w7bl3pjx/verification.json`.
The ASA review fixture was regenerated without its inaccessible per-plate bed
override as `reports/asa-heat-bed-clamps-selectable-04hs-review.3mf`;
`reports/acceptance-manifest-2026-09-25.json` inventories 13/13 prepared
fixtures with zero archive errors. This refresh is not a native slicing pass.

The local beta is **not accepted yet**. The latest native check opened the
Communication Cards project and sliced plate 1, but plate 2 reported an object
over the plate boundary. Per the stop-on-unexpected-failure rule, no other
Communication Cards plates or remaining manifest fixtures were counted as
passes. See `ACCEPTANCE_2026_09_24.md` for the current evidence and blockers.

The counts below use explicit scopes so automated tests are not confused with
native slicer checks or physical calibration:

| Scope | Complete | Remaining | Total |
| --- | ---: | ---: | ---: |
| Automated regression suite (`unittest`) | 193 | 0 | 193 |
| Acceptance-manifest fixture preparation | 13 | 0 | 13 |
| Native beta-gate open/slice coverage (ironing excluded) | 12 | 0 | 12 |

The selectable-plate ASA clamps, painted-support bucket, and representative
ABS/PETG hose-holder plates passed on the reviewed outputs named above.
Historical ASA and painted-support attempts stopped at Anycubic's `Modified
G-code` confirmation and were intentionally not accepted. All 13 inventory
fixtures are prepared, including the optional ironing test; that is archive
evidence, not a claim of native slicing for every plate.

Separate follow-up subchecks remain outside the native-fixture-gate count:
saved-project reopen for some fixtures, broader Siddament import-field
persistence, physical nozzle/material calibration, and publication decisions.
The routine native beta gate does not close those separate follow-ups.

The scoped difference-mask correction has automated, archive and release-build
evidence. The selectable-plate ASA fixture subsequently opened and sliced
natively without a Modified G-code confirmation, as recorded at the top.

On 2026-09-15, an isolated Anycubic CLI attempt generated G-code from that
refreshed ASA fixture, but static validation failed on absolute Y moves beyond
the verified 250 mm printable area; the slicer also logged an exclude-triangles
error. The generated G-code is review evidence only, not an accepted native
open/slice or print-ready artifact. See `CHECKPOINT.md` for exact paths and
counts.
