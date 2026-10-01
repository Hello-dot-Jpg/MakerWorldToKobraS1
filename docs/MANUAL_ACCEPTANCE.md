# Anycubic Slicer Next acceptance evidence

## Latest native feature evidence (2026-10-01)

Exact hashes and session details are in CHECKPOINT.md.

- `reports/routine-tracker-autofit-process-fix-20261001.3mf`: clean optimized
  process; both plates freshly sliced,212.22g/6h55m and7.37g/20m25s.
- `reports/tools-06hs-018-selected-naming-20261001.3mf`: clean optimized0.18,
  first layer0.30, widths0.62; slice74.50g/3h27m. Fresh-process reopen passes.
- `reports/SYNTHETIC-tools-two-plates-S1-06HS-20261001.3mf`: representative
  >25MiB streamed multi-plate open/slice PASS; individually inspected plates
  30.15g/1h21m and38.48g/1h39m, supports/brim, no bounds error.
- `reports/gui-routine-autofit-smoke-20261001.3mf`: native GUI Enter-load,
  discovery, auto-fit/export and new-source reset PASS. This specific GUI
  artifact was opened but not freshly sliced; no inherited slice claim.
- `reports/EXPERIMENTAL-routine-project-machine-PEI-20261001.3mf`: unique
  embedded machine loaded, but remembered Cool Plate still overrides exported
  PEI. FAIL automatic default. Editable selector manually returns to PEI.
  Candidate slicing/filament-menu gates stopped; no production promotion.

Historical artifact evidence below remains specific to its named files.


## Current-artifact qualification (2026-09-15)

The regenerated `reports/coasters-current-reconciled.3mf` remains archive-
validated but has not been opened in Anycubic. The native three-plate result
recorded later in this document applies to the separately named review
artifact and is not silently transferred to this regenerated file. The same
distinction applies to other artifacts explicitly labelled automated or
historical below.

## Xiaomi side-suction user-requested export (automated, 2026-09-06)

`reports/xiaomi-side-suction-KobraS1-06HS-PETG-nice-supports.3mf` was generated
from the user's `小米吸尘器+侧吸+v1.3mf` with the community 0.6 mm hardened-steel
machine and community 0.30 mm process settings, stock 0.6 mm Anycubic PETG,
and Nice supports beta enabled. Source 0.20 mm layer/first-layer heights remain;
main and support line widths are 0.62 mm. Every beta overlay value was checked
in the written config. Only project settings changed; 19 untouched members
were hash-verified. Output SHA-256:
`A19F1BCBC99CE3A9B2FBCDC73BB552E9B9552CFAA9E5774E7FD2F7A82B3E4DCA`.
The user confirmed it sliced, printed, and came out great on 2026-09-06.
They reported the printer selector showed
the default Anycubic 0.6 profile rather than the community hardened-steel name.
The delivered archive still contains the community printer identity, the
official 0.6 compatibility parent, hardened_steel nozzle type, community
retraction overlay and explicit-value preservation masks. Reviewed loader
code can select an installed parent while applying imported settings, so the
display name alone does not establish loss of tuning. Effective imported
settings were subsequently verified from the separate slicer-saved
`reports/xiaomi-anycubic-import-roundtrip.3mf`: hardened steel, 0.6 mm nozzle,
community 1 mm retraction, 0.20 mm layers, 0.62 mm widths, 100/150 mm/s outer/inner
walls, tree(auto) supports, 150/80 mm/s support/interface speeds and PETG at
230 C all survived. This confirms those effective values despite the parent
display name; it is not a claim that every vendor-specific option survived.
The selected plate became Cool Plate despite the original global Textured PEI
setting. The user used physical textured PEI and requested an explicit default
and selector. The successful adhesion does not validate a mismatched plate.

After the user closed Anycubic, read-only inspection confirmed the Xiaomi
export is its most recent project. The configured last-recovery folder no
longer exists and the day's model recovery directory is empty. No newly saved
user JSON/3MF/config files were found for that session; the available warning
log does not expose effective imported tuning. Therefore the closed-session
files cannot establish whether the displayed parent retained all community
overrides. No slicer settings or recovery files were changed during inspection.

## Current Nice supports review artifact

### Saved-reference regression (automated, 2026-09-06)

`reports/tools-castle-reference-04-review.3mf` uses the user's saved castle as
the machine/process reference and its PETG slot 2, converting `tools.3mf`.
The written project has a 0.4 mm hardened-steel machine, retained 0.20 mm source
layers, 0.42 mm widths, and the reference's 230 °C PETG temperature. Its process,
filament and machine inheritance entries point to the correct respective
official 0.4 mm parents. Eight objects and one plate remain; zero blockers;
23 untouched members verified. Output SHA-256:
`150E6B306FB1718827FF93E8B2C4479616CFB4427F6D61B2EF99A901619D15B8`.
This is reference-import/export evidence only; installed-slicer acceptance is
pending. No changes were made to the user's reference or Xiaomi output.

### Cupholder beta-support artifact

`reports/cupholder-06hs-018-nice-supports-review.3mf` was exported with the
community 0.6 mm hardened-steel target, official 0.24 mm process widths,
custom 0.18 mm layer height, source 0.20 mm first layer, four stock PETG slots
and one stock TPU slot. Every finite beta support setting was checked in the
written project. Main/support widths are 0.62 mm, support speed 100 mm/s and
interface speed 80 mm/s. There were zero blockers and 28 untouched archive
members were hash-verified. SHA-256:
`C6C61002FC95DA1FC22BD7175F245F6CF9BC702FDAF8D0BC90EBC78E574CE505`.

On 2026-09-06, the user confirmed this exact export opened without errors,
then confirmed that slicing and supports were also OK. These are user-reported
installed-slicer acceptance results, obtained without desktop automation.
The user subsequently supplied screenshots confirming stock-filament visibility
FAILED: only PETG appeared under system presets, versus the normal material
list. This does not establish a
physical print result or acceptance for other exports/nozzle sizes.

### Filament-list repair candidate (2026-09-06)

`reports/cupholder-06hs-018-nice-supports-filament-fix.3mf` was regenerated by
the converter with identical selections. Compared with the accepted review
artifact, only `Metadata/project_settings.config` differs, and its only changed
setting is `inherits_group`: six empty scope entries followed by
`Anycubic Kobra S1 0.6 nozzle` at machine index 6 (five filament slots + 1).
The original review artifact is retained. On 2026-09-06 the user confirmed
this repair opens without errors, slices OK, and has no missing filaments.
Stock-filament visibility is therefore passed for this exact 0.6 mm artifact.

### Explicit-value import fidelity candidate (2026-09-06)

`reports/cupholder-06hs-018-import-fidelity-review.3mf` adds the separate
difference-mask repair described in PROJECT_INHERITANCE_AUDIT.md. Compared
with the accepted filament-fix artifact, only `different_settings_to_system`
changes; seven scope masks protect all explicitly written project keys. Every
other archive member is byte-identical. Output hash:
`598A58A058B3FC89C74703147DE9577B4B21AA367BDAF7E60696653E04F4C35A`.
The writer verified 28 untouched members. This newer candidate does not yet
have user-reported installed-slicer acceptance.

### Consolidated metadata review (2026-09-06)

Use `reports/cupholder-06hs-018-consolidated-review.3mf` for the next check;
it supersedes the intermediate import-fidelity review candidate. SHA-256:
`537A7E55EEE25E0C6037EBE090C5DCE9E6FF3EC9743AC8197A20D316CA1C1D84`.
All changes relative to the user-accepted filament-fix artifact are confined
to five profile metadata fields: inheritance, machine/process expression
groups, process-compatible printers, and difference masks. All other project
values and archive members are identical; the writer verified 28 untouched
members. No installed-slicer result is claimed yet. Check open/slice/filament
list plus effective 0.18 mm height, 0.62 mm width, hardened-steel nozzle and
the intended support settings.

The historical checks below were completed locally in Anycubic Slicer Next
2.0.0.2. No print was started by the agent.

## Single-material 0.6 mm hardened/PETG

Artifact (locally ignored):

```text
C:\Projects\MakerWorldToKobraS1\.research\tools_KobraS1_06_Hardened_test_v3.3mf
```

Generated from `C:\Users\USER\Downloads\tools.3mf` with:

- machine `AC KS1 0.6 nozzle Hardened Steel`;
- process ceiling `0.30mm @AC KS1 0.6 mm Nozzle`;
- filament `Anycubic PETG @Anycubic Kobra S1 0.6 nozzle`.

Observed in the slicer:

- no compatibility-repair, corrupt-project, or missing-profile error;
- correct 0.6 mm hardened machine and PETG profile;
- source 0.20 mm layer height preserved;
- nozzle-dependent displayed line widths translated to 0.62 mm;
- all eight objects and one plate retained;
- slice completed successfully with an estimated 3 h 38 min.

Automated evidence: valid ZIP/3MF, zero write blockers, eight checked extruder
assignments using slot 1, unchanged source hash, unchanged member inventory,
unchanged structural counts, and 22 untouched members SHA-256-identical.

## Four-slot 0.4 mm hardened/PLA

Artifact (locally ignored):

```text
C:\Projects\MakerWorldToKobraS1\.research\crocs_KS1_04_Hardened_test.3mf
```

Generated from `C:\Users\USER\Downloads\Crocs+Strap+Pin+with+Brim.3mf` with
ordered profiles: Anycubic PLA Matte, then three Generic PLA community slots.

Observed in the slicer:

- correct 0.4 mm hardened machine;
- all four ordered filament slots displayed;
- all four objects retained their source assignment to slot 4;
- slice completed successfully with an estimated 10 min.

Automated evidence: source and output filament colours were identical
(`#9B9EA0,#FFFFFF,#DCDCDC,#161616`), `model_settings.config` was SHA-256
identical, four assignments were validated against four slots, and model,
object, part, plate, assembly, and archive-member counts were unchanged.

## Three-plate embedded-profile reconciliation

Current automated export (locally ignored):

```text
C:\Projects\MakerWorldToKobraS1\reports\coasters-current-reconciled.3mf
```

This was regenerated from the same three-plate source with the community
0.4 mm hardened-steel target, its 0.28 mm ExtraDraft process, and the official
0.4 mm Anycubic PLA profile repeated over all four source slots. It uses the
reviewed Anycubic precedence rule: the complete project config is applied after
embedded presets, so one embedded snapshot is removed only for each explicitly
retargeted scope and only when every substantive key is flattened.

The current converter reported zero blockers and removed one machine, one
process, and one filament snapshot. ZIP/3MF validation completed without
warnings; 45 untouched members were hash-verified. Structural validation
retained 13 assembly/build/model instances, eight mesh objects, 13
model-settings objects and parts, three plates, and 21 resource objects. Output
SHA-256:
`5DC969BACBAC2B869570FB210AF9770DEAE04A8198467293A951755F1F8BC173`.

This regenerated artifact has not yet been opened or sliced in the installed
slicer. The following older result is retained only as historical UI evidence.
It was generated by an earlier key-presence check and must not be used as a
validated print project.

Artifact (locally ignored):

```text
C:\Projects\MakerWorldToKobraS1\.research\coasters_embedded_reconciled_test.3mf
```

Generated from
`C:\Users\USER\Downloads\Modern+coasters+-+different+designs+-+3+colors+mix.3mf`
with the 0.4 mm hardened-steel community target, the 0.28 mm ExtraDraft
process, and four ordered Anycubic PLA/PLA Silk profiles.

Observed in the slicer:

- the project opened without a repair, corrupt-project, or missing-profile
  error;
- all three plates and all four ordered filament slots were present;
- the effective Printer Settings showed a 0.4 mm `Hardened steel` nozzle;
- Anycubic Slicer represented the flattened overlay as an asterisked modified
  base preset in the top-level machine selector;
- plate 1 sliced successfully with an estimated 1 h 10 min.

Historical automated evidence: the lone foreign machine, process, and filament
snapshots were removed after checking key presence, which did not prove value
equivalence. Thirteen assignments were validated against four slots using
slots 2, 3, and 4. Structural validation retained 13 assembly/build/model
instances, eight mesh objects, 13 model-settings objects and parts, three
plates, and 21 resource objects; 45 untouched members were SHA-256-identical.

## Download-audit qualification (2026-09-05)

The subsequent 122-file audit found additional numeric scalar-array mismatches
beyond the visible overhang warning. Earlier exports in this document predate
those fixes. Preserve their open/slice results as historical observations, but
regenerate before further acceptance testing or printing; successful slicing
alone did not prove every setting was interpreted correctly. See
DOWNLOAD_SETTINGS_AUDIT.md. No desktop interaction was used for this audit.

## Cupholder 0.6 mm regression (automated only, 2026-09-05)

The current converter produced the locally ignored
`reports/cupholder-06hs-024-preserve-validated-v2.3mf` from the five-slot
PETG/PETG/PETG/PETG/TPU cupholder source. It used the community 0.6 mm
hardened-steel machine, the official 0.24 mm process, four stock 0.6 mm PETG
slots, and one stock 0.6 mm TPU slot.

Archive validation completed with no write blockers, 28 untouched members were
hash-verified, and the output SHA-256 is
`4400C7DC73EF01B9AA089A07C7EFC96F60A12AAAAC9B049CEF0EB83DF644413E`.
The written project retains 0.20 mm project/initial layers, uses 0.62 mm main,
outer-wall, and support widths, links to the official 0.6 mm machine parent,
replaces all stale Bambu filament identities, and normalizes both known invalid
support sentinels to 0 under the documented safe conditions.

This is not installed-slicer acceptance. It was deliberately performed without
desktop automation; profile visibility, Preview, and slicing remain pending.

## Nozzle-extreme regressions (automated only, 2026-09-05)

### Current official-profile matrix (2026-09-06)

The current converter exported `tools.3mf` with each installed official nozzle
target, exact Standard process below, matching stock Anycubic PETG, and explicit
hardened-steel hardware selection. Selected-process layer heights were enabled
for this matrix; it is not a test of default source-height preservation. All
four plans had zero blockers. The written machine inheritance points to the
correct official nozzle, and each written nozzle type is `hardened_steel`.
The 0.25/0.4 cases are REVIEW hardware overrides, not independently calibrated
hardened-steel community presets. No thermal tuning was invented.

| Review file in `reports/` | Layer / line width (mm) | Untouched members |
| --- | --- | ---: |
| `current-official-0.25-hs-petg-review.3mf` | 0.10 / 0.27 | 22 |
| `current-official-0.4-hs-petg-review.3mf` | 0.20 / 0.42 | 23 |
| `current-official-0.6-hs-petg-review.3mf` | 0.24 / 0.62 | 22 |
| `current-official-0.8-hs-petg-review.3mf` | 0.40 / 0.82 | 22 |

Hashes in the same order:

```text
7B0EA2B70207DB70F19B713DCB8F70E503BB0E22E658C473AC87BC896971BAEE
DC02B6C13B103747AD968C49522258E06BE4E935635F9C62AEDC0C627F321BA2
0FFD47F46D43135C3355F56362FFA3F72B51CFC560D4D501558B7B953AB660A3
7E2E19A0643186250922434244C92B5871A6AF5671B04E2F624F4A73919EAF81
```

These include the current metadata fixes, unlike the historical community
outputs below. None of these four current matrix files has installed-slicer
acceptance yet. The extra untouched member at 0.4 mm is expected: no plate
nozzle metadata change is needed when the diameter stays the same.

### Historical community outputs

The current converter also produced two locally ignored PETG projects from
`tools.3mf` using the additional community bundle:

- `reports/tools-025-brass-010-validated.3mf`: effective 0.25 mm brass target,
  0.10 mm selected process height, 0.22 mm line widths, and the stock 0.25 mm
  Anycubic PETG filament. SHA-256
  `BA56DF79EE0749481746DB5838918B15DE94A9001C6122BFC27B150B75D5513A`.
  The report deliberately warns that the bundle calls this target `0.2`, that
  its 0.22 mm line width is narrower than the actual 0.25 mm nozzle, and that
  its filament requires nozzle-hardness review.
- `reports/tools-08hs-040-validated.3mf`: effective 0.8 mm hardened-steel
  target, 0.40 mm selected process height, 0.82 mm line widths, and stock
  0.8 mm Anycubic PETG. SHA-256
  `E79BD0D12BD7F7ED45EA07CC0720044ADB825DCF4EF75EFA7ECE72D0FF0E3456`.

Both outputs passed ZIP/core-3MF validation with zero blockers, updated only
the project config and plate nozzle metadata, and hash-verified 22 untouched
members. Neither has been opened or sliced in the installed slicer.

## Support-heavy P2S project (2026-09-05, pre-audit artifact)

Source: `C:\Users\USER\Downloads\Amazing_Support_Settings.3mf`.
Historical artifact: `.research/support_settings_KS1_04_Hardened_test_v2.3mf`.
Target: community 0.4 mm hardened steel, official 0.20 mm Standard process,
and Anycubic PLA Silk.

The first output triggered an Anycubic repair that disabled overhang slowdown
when Bambu's boolean array was read as `1,1`. The corrected output translates
agreeing source booleans to a single switch and opened without that repair.
Mixed source switches block export. Source support, ironing, and seam values
remain unchanged; 23 untouched archive members are hash-identical. Slicing
completed in Anycubic Slicer Next with an estimated 50 min 3 sec total time,
visible support/support-interface and overhang toolpaths, two retained objects,
and the selected 0.4 mm hardened-steel machine. No print was started.
