# Standalone filament-profile conversion - requested 2026-09-06

## 2026-09-23 direct installation and Siddament batch

The **Filament profiles - beta** tab now offers **Install reviewed export…**
and **Rollback install…**. Installation is opt-in and requires Anycubic Slicer
Next to be closed. The installer reads the active account from
`AnycubicSlicerNext.conf`, rejects any existing JSON or `.info` name collision,
backs up the entire active filament folder, and writes each exported preset
under its internal Anycubic display name. A manifest records source and
destination hashes. Rollback moves only that installation's presets into a
quarantine folder alongside the backup; it does not delete the originals.
Changed/tuned presets require the explicit preserve-modified rollback option.

Justin's 17 local Siddament P1S source profiles were prepared for hardened
steel nozzles at the user-reported ceramic 320 C and effective 110 C bed
ceilings. The 15 earlier 0.6 mm imports were left intact. A new reversible
batch installed 50 presets: 14 for 0.25 mm, 17 for 0.4 mm, 2 missing 0.6 mm
PC-CF/PLA-CF variants, and 17 for 0.8 mm. The active account now has 65
Siddament preset identities across these sizes. The 0.25 mm TPU, PC-CF, and
PLA-CF variants remain excluded because no defensible matching S1 base was
available. The PC-CF source declares `PC`; its 0.4/0.6/0.8 conversions use
the previously approved explicit PC-CF material correction and reviewed
engineering bases.

Manifest: `reports/S1-preset-backup-a5hvhnwv/install-manifest.json`.
File-level post-install verification: all 50 new files match their recorded
hashes, all 106 pre-existing files remain unchanged, and all 106 exist in the
backup. Automated suite: 226 passed, 10 skipped, 90 subtests. Native slicer
menu visibility and printing with these newly installed variants are not yet
verified; each remains marked REVIEW and needs appropriate hardware and
calibration before printing.

## 2026-09-15 active-path recheck - REVIEW

The current exporter was rechecked after the broader comparison. A fresh
0.6 mm batch at `reports/S1-filaments-8pj0_7ja/` writes explicit root,
`_HS`, and `_BRASS` values for portable fan/slowdown fields; this is covered
by a regression test and was not installed. The older installed differences
therefore still need one native import/reopen confirmation before being called
fixed.

The active profile store is `...\\AnycubicSlicerNext\\user\\789721\\filament`.
All 15 Siddament identities are present, but a broader installed comparison
found differences in fan limits, slowdown times and ASA nozzle temperatures.
The prior zero-difference result covered a narrower 35-field comparison, so
full-field persistence remains REVIEW pending investigation; no installed
preset was changed.

The read-only installed comparison tool now also accepts the parent
`...\\AnycubicSlicerNext\\user` directory. It inspects only immediate
account/filament candidates, scores them against the conversion report's
expected preset identities, and proceeds only when one candidate has a unique
positive match. A real run resolved `789721\\filament`; zero or tied matches
fail instead of silently auditing the wrong `default` directory.

## 2026-09-15 audit

All-size dry audit at the same declared ceilings found 14/17/15 ready plans
for 0.25/0.4/0.8 mm respectively. The 0.25 skips are PC-CF, PLA-CF and TPU;
the 0.8 skips are PC-CF and PLA-CF. The 0.4 mm target matched all 17 sources.
No export or installed change was made by this audit.

The local Siddament corpus contains 17 sources for the tested 0.6 mm ceramic /
hardened-steel setup (320 C nozzle, 110 C bed): 15 are ready for review export.
PC-CF and PLA-CF remain safely skipped because no matching 0.6 mm destination
base was found; they are not synthesized or silently remapped.

Status: beta engine and separate GUI tab implemented; 15 Siddament 0.6 HS presets
passed native import and fresh-session identity persistence. Broader field
persistence and print calibration remain pending. This is a separate feature,
not a change to the ordered filament reassignment in the 3MF converter.

## Proposed workflow

New **Filament profiles - beta** tab: choose local JSON files/folder or ZIP/`.orca_filament` bundle,
select the installed destination Kobra S1 nozzle/profile, review the materials and
conversion report, then export importable Anycubic user presets. Batch selection
should support one material family per destination, rather than creating copies
of every source-printer variant. An explicit import step should use Anycubic's
supported configuration-import format, preserve existing presets, and detect
name collisions. Direct installation must be opt-in, backed up, and must not
write into an active slicer's configuration directory.

Currently implemented: multi-select JSON/folder/bundle input, installed official S1
printer discovery with multi-select 0.25/0.4/0.6/0.8 mm batch targets, independent
physical nozzle-material declaration, exact material/nozzle base matching, local parent resolution,
per-field review, confirmed physical temperature ceilings, and fresh-directory
batch export, including a single `importable-presets.zip` containing only preset
JSONs. Users may import the ZIP or individual JSONs with Anycubic's Import
Configs command, or opt into the backed-up direct installer. Existing names
are never overwritten by direct installation.

Not yet implemented: full Prusa/SuperSlicer INI compatibility, explicit base
mapping for unsupported materials, community target installation, and broader
destination-slicer acceptance. Source calibration and machine-dependent values
are replaced by inherited destination defaults, rather than copied as calibrated.
Source temperatures beyond the user's confirmed limits block instead of being
silently reduced. Unknown fields are omitted with individual report entries.

## Verified source format

Source: https://siddament.com.au/pages/slicer-profiles (checked 2026-09-06).
The page offers printer-specific Bambu JSON files, universal JSON choices and
Prusa/SuperSlicer INI files. Its public download catalogue is embedded in page
JavaScript; do not execute third-party scripts to obtain it. JSON is the first
supported format to implement; INI needs its own translation adapter.

Inspected the current `Siddament_PETG_Normal__BBL_P1S.json` download. It is a
standalone JSON object with empty inheritance, explicit filament values, and
compatibility restricted to Bambu Lab P1S 0.4 nozzle. It also contains Bambu fan
G-code and vendor-only settings, so changing the printer name alone is not a
valid conversion. Other downloads may have nonempty inheritance and must be
checked separately; this sample does not prove the whole catalogue supported.

## Conversion policy

- Preserve material identity, vendor and meaningful material-specific values
  (temperature, plate temperatures, density, cost and cooling) where supported.
- Resolve source inheritance before mapping. Missing parents must produce an
  actionable error, not silently become Anycubic defaults.
- Use a matching destination filament base and printer/nozzle compatibility.
  Do not remove compatibility restrictions globally.
- Replace foreign filament G-code with destination-safe defaults. Do not run
  commands or macros from downloaded profiles during conversion.
- Treat flow ratio, pressure advance and retraction as calibration-sensitive.
  Preserve provenance and require review; do not label them calibrated for S1.
- Cap volumetric flow against an explicit destination limit; never assume a
  source printer's high-flow rating applies to every S1 nozzle/hotend.
- Validate temperature limits, abrasive-filament nozzle requirements and
  selected nozzle size. Unsupported materials remain review/blocked, not falsely
  advertised as compatible.
- Report every kept, translated, replaced and omitted field. Keep unknown
  settings out of installed presets until destination support is established.
- Generate unique user-preset identities and maintain a source hash/URL manifest.
  Do not redistribute vendor downloads in the repository without permission.

## Acceptance criteria

- Unit tests: inheritance, arrays/nil values, unsupported fields, malicious ZIP
  paths/oversized input, duplicate names, temperatures, flow and hardware limits.
- Real sample tests: Siddament PLA, PETG and one abrasive material; then audit
  all selected material variants before offering a bulk conversion result.
- Anycubic import succeeds, presets appear under the chosen nozzle, reopen with
  the expected effective settings, and do not hide stock/user filaments.
- Existing 3MF filament reassignment tests and workflow remain unchanged.

Feasibility: high for Bambu/Orca JSON. The substantial work is safe parameter
mapping and persistent-preset import validation, not the extra tab itself.

## Local test corpus

With the user's permission, all 17 P1S JSON downloads were staged under
`.research/siddament-p1s/` on 2026-09-06. The source downloads are Git-ignored;
the converted profiles were installed later as described above.
All parse as JSON and have empty inheritance in this snapshot. The set covers
PLA variants, ABS variants, ASA, PETG variants, PC-CF and TPU. Several filled
materials identify themselves with a generic material type; names and hardware
requirements must not be lost. Every file contains nonempty filament G-code.
This corpus will test the new importer; downloading/parsing it is not conversion
or proof of S1 compatibility.

Initial conversion audit against the installed official 0.6 mm base set:
15 plans; PC-CF and PLA-CF have no exact installed base. ASA, ASA-CF and PC-ABS
have source print temperatures outside their stated source temperature ranges
and are blocked. The other 12 await confirmed physical temperature ceilings.
No files were installed and no thermal ceilings were guessed. The full unit
suite has 111 passing tests; two-tab construction/shutdown passed without
desktop interaction. Visual layout and actual Anycubic import remain pending.

All-size audit (physical hardened steel explicitly declared, no guessed thermal
limits): 0.25 mm has 14 matching plans/3 missing bases; 0.4 mm has 17/0;
0.6 and 0.8 mm each have 15/2. Each size has the same three source-temperature
range conflicts. All remain export-blocked until thermal ceilings are confirmed.
This is not proof that filled filaments can print through every nozzle diameter.
The user confirmed current nozzle 0.6 HS but has no bed-temperature limit info;
hotend type/thermal ceiling is still unconfirmed. No presets installed.

The GUI now allows selecting several destination sizes in one batch and defaults
physical material to hardened steel for this user's hardware. This declaration
does not rewrite installed machine presets. Updated suite: 112 tests.

## User-approved range tolerance (2026-09-07)

For valid, ordered declared nozzle ranges, the importer may extend either end
by at most 15 C (inclusive) to cover the source normal/first-layer temperatures.
It extends only as far as needed, never changes print temperatures, and shows
the original/new bound and reason at the top of the GUI/export review report.
The field audit records the range change as TRANSLATE. Inverted ranges or a
discrepancy exceeding 15 C remain blocked; no partial repair is made in that case.
Known physical ceilings and missing-confirmation blockers still apply.

Rechecked all 17 downloaded files across four nozzle sizes: the prior ASA/ASA-CF
range conflicts now yield explicit 280 -> 290 C warnings; PC-ABS yields
280 -> 285 C. No other non-thermal blockers occur among matched bases. Missing
base counts remain 3/0/2/2 for 0.25/0.4/0.6/0.8 mm respectively. No real presets
were exported or installed during this check, because hardware ceilings remain
unconfirmed. Unit suite: 114 tests, including both ends, exact and over-limit
boundaries, first-layer values, unchanged source files, report/export fidelity,
inverted ranges and physical-limit precedence.

## Bundle input and desktop review (2026-09-07)

ZIP and `.orca_filament` inputs are read without extracting files. Filament
parents resolve by declared preset name inside the same archive; missing,
ambiguous or cyclic parents block. Unsafe paths, case-insensitive collisions,
encrypted/symlink entries and oversized archives or members are rejected.
Machine/process profiles and ordinary manifest JSON are not offered as filaments.

Temperature checks now also cover effective inherited destination plate values,
so an omitted source field cannot bypass a confirmed physical ceiling. Fields
absent from the destination base receive a specific omission warning.

Using the Computer Use skill, verified the two-tab layout, installed four-size
discovery, default 0.6 HS selection, and bundle review in the running Windows GUI.
A local test bundle of all 17 downloaded Siddament JSONs loaded successfully:
15 conversion plans and two missing-base errors, with all plans correctly blocked
pending confirmed hardware ceilings. No presets were exported or installed.
Actual Anycubic configuration import remains unverified. Suite: 118 passing tests.

## User-reported hotend limits (2026-09-07)

The importer now offers an explicit hotend selection, initially unspecified.
Justin reports PTFE-lined hotends at 300 C, later all-metal and ceramic at 320 C,
and ceramic at 350 C only with a firmware settings change. These are recorded as
user-reported equipment limits, not independently verified manufacturer ratings.
Selecting a construction applies its stated ceiling when the manual nozzle limit
is blank. A lower manual limit is allowed; exceeding that construction's limit
blocks. The 350 C ceramic case requires an explicit firmware confirmation checkbox.
The app never changes firmware, machine presets or source print temperatures.
The report records construction, firmware confirmation and limit provenance.

The current fitted hotend and the bed ceiling remain unconfirmed. Bed checks are
independent and still block exports without a confirmed limit. This change does
not establish abrasive-material suitability or calibrate flow for another nozzle.

Base matching now prefers the canonical installed Anycubic preset but accepts a
single differently named discovered candidate with the exact material and nozzle.
Missing or ambiguous candidates still block; no cross-material substitution is
performed. Explicit selection among multiple bases remains pending.

## First installed Siddament batch (2026-09-07)

Justin confirmed the current setup: ceramic hotend, 0.6 mm HS, 320 C nozzle
maximum without the 350 C firmware change. He reports a 120 C hardware bed
maximum but a 110 C software limit; this batch uses the lower effective 110 C
ceiling. The reason for the software/hardware discrepancy is not established.

Generated 15 matching review presets from the 17 P1S downloads. PC-CF (source
material field PC) and PLA-CF were excluded because no matching installed 0.6 mm
base exists. Final corrected artifacts:
`reports/S1-filaments-8rbt5e9w/`, including `importable-presets.zip`, individual
JSONs, conversion report, batch audit and `installed-verification.json`.

Using the Computer Use skill, imported PETG first, then the remaining batch via
Anycubic File > Import > Import Configs. This revealed a real persistence bug:
the slicer reported imported names containing `/` but did not save those three
presets to disk. The converter now normalizes Windows-invalid characters in
the display identity as well as the export filename and records a TRANSLATE
decision. The three repaired presets were imported separately without overwrites.
The earlier `S1-filaments-w0n1kcqh` export is superseded for those three names.

All 15 final identities exist in the installed filament folder. A read-only
comparison of 35 relevant effective fields per preset against the exact base
snapshot plus generated overrides found no differences. All 15 preset JSONs
present before the batch (including the first PETG import) remain byte-identical.
PETG is visible under the 0.6 mm printer alongside normal stock/custom filaments;
its native editor shows HS 255/255 C, textured PEI 70/70 C, max flow 16 mm3/s,
destination flow ratio 0.94 and pressure advance 0.03.

No printing, firmware changes, or existing-preset overwrites occurred. Slicer
restart/reopen passed on 2026-09-07: corrected names reload, failed pre-fix names
are absent, and stock filaments remain available. A second read-only audit
verified all 15 identities and unchanged pre-existing presets after restart.
Material-specific calibration and filled-filament suitability
remain review requirements, not proven by import success.

All-size dry audit at declared HS/ceramic/320/110: matching counts 14,17,15,15
for 0.25,0.4,0.6,0.8 mm respectively. No additional sizes were installed.
Suite: 130 tests pass; source/tests/tools compile. Added repeatable corpus audit
and read-only installed comparison tools under `tools/`.

## Limited INI adapter (2026-09-07)

The tab now offers Add INI for standalone `.ini` / `.config` exports and
`[filament:name]` sections. Single local parents may be resolved within the same
file. Missing/ambiguous parents, cycles, duplicate keys, invalid numerics and
multi-extruder numeric lists are rejected; no remote parents are fetched.

Temperature, initial-layer temperature, density, diameter, cost, vendor,
material and maximum volumetric flow have explicit mappings. Bed temperatures
map only to Textured PEI and produce a visible warning. Other plates, cooling,
calibration and G-code remain destination-owned. Unknown INI fields are retained
in the audit but omitted from output. This is not full Prusa/SuperSlicer
configuration compatibility. Automated engine-to-export coverage passes;
native import of a real vendor INI conversion remains pending.

Source field semantics: [PrusaSlicer PrintConfig.cpp](https://github.com/prusa3d/PrusaSlicer/blob/master/src/libslic3r/PrintConfig.cpp).
Destination names were checked against the locally reviewed Anycubic common
filament JSON and PrintConfig.cpp. No upstream implementation was copied.
