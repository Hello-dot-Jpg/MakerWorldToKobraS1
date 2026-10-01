# MakerWorld / Bambu 3MF to Kobra S1 Optimizer

A Windows desktop app and CLI for inspecting MakerWorld/Bambu 3MF projects
and producing validated, minimally retargeted Anycubic Kobra S1 project copies.
Also includes a separate filament-preset conversion, install and rollback tool.

## Quick start

**New here? [Start with the picture guide](USING_THE_APP.md).**
Short steps, big pictures, and the extra settings on a separate page.

Download the **0.4.1 beta Windows ZIP** from this repository's **Releases** page,
extract it, and run `S1Optimizer-0.4.1-beta.exe`. No Python installation needed.
Anycubic Slicer Next and its local profiles are required for profile discovery.
The executable is unsigned; follow your normal Windows security policy.

Download page: **[Windows app · 0.4.1 beta](https://github.com/Hello-dot-Jpg/MakerWorldToKobraS1/releases/tag/v0.4.1-beta)**.

1. Browse to a 3MF (or paste its path and press Enter).
2. Discover profiles and select your nozzle, machine, process and filaments.
3. Review the changes, then export a new copy. Your source is not overwritten.
4. Open it in Anycubic, check **Plate Type**, temperatures and assignments,
   slice and inspect Preview before printing.

Keep **Scale to fit S1 plate** off for dimension-critical parts unless you
intentionally want to resize them. Filament imports require confirmed physical
temperature limits and review; they are not calibrated printing profiles.

Source users can double-click `run_gui.cmd` with Python 3.11+ installed, or use
the setup instructions below. Distributed application source is MIT-licensed;
bundled runtime components retain their licences in `THIRD_PARTY_NOTICES.md`.

## Current status

Windows portable beta executable: build with
`python tools/build_windows_exe.py --build-deps .research/exe-build-deps`
after installing `pyinstaller==6.22.3` into that isolated folder. Each build
creates a new `dist/S1Optimizer-<version>-beta-*` directory containing the single
`.exe`, build log, runtime smoke evidence and SHA-256 manifest. No Python
installation is needed to run the executable; local Anycubic profiles are
still needed for discovery. This beta release is unsigned.
The remembered plate-choice limitation is accepted for beta with a warning:
always check Plate Type before slicing. Automatic selection remains a bug.

The 0.4.1 desktop refresh uses an Anycubic-inspired charcoal/blue theme with
numbered workflow cards, a scrollable settings pane, an always-visible export
area and separate source/review panes. Community bundles and hardware options
are expandable. Long forms support mouse-wheel and keyboard-focus scrolling;
controls lock while work runs and recover their readonly states afterward.

Latest release scope: [release notes](docs/RELEASE_NOTES_0.4.1.md).

Milestone 1 inspection/comparison, the Milestone 2 converter, Milestone 3
material and ACE-slot handling, and a local desktop interface are implemented.
Material-owned translations remain visibly marked `REVIEW` in every report.
The previous local software beta gate passed 12/12 representative native
fixtures; this is not physical print calibration or a blanket guarantee for
other projects. Corrected project-process identity, representative multi-plate
placement and fresh-session persistence checks have subsequently passed. See
[acceptance status](docs/ACCEPTANCE_STATUS.md) for the exact boundary.

The user has confirmed a 0.6 mm hardened-steel cupholder export opens, slices,
has satisfactory beta supports, and restores the stock-filament list. Later
import-fidelity metadata repairs have automated and representative native
coverage. See [current completion audit](docs/COMPLETION_AUDIT.md)
and [exact artifact acceptance](docs/MANUAL_ACCEPTANCE.md); acceptance of one
file is not a blanket guarantee for all nozzle/profile combinations.

Implemented commands:

```powershell
python -m s1_optimizer inspect makerworld.3mf
python -m s1_optimizer compare makerworld.3mf kobra_s1.3mf
python -m s1_optimizer inspect-profile "C:\path\to\machine-profile.json"
python -m s1_optimizer targets --nozzle 0.6 --bundle community-profiles.3mf
python -m s1_optimizer processes --target-id TARGET_ID --bundle community-profiles.3mf
python -m s1_optimizer filaments --target-id TARGET_ID --material PETG --bundle community-profiles.3mf
python -m s1_optimizer plan source.3mf --target-id TARGET_ID --bundle community-profiles.3mf
python -m s1_optimizer optimize source.3mf --target-id TARGET_ID --process-id PROCESS_ID --bundle community-profiles.3mf --dry-run
python -m s1_optimizer optimize source.3mf --target-id TARGET_ID --process-id PROCESS_ID --bundle community-profiles.3mf
python -m s1_optimizer gui
```

On Windows, double-click `run_gui.cmd` from the repository
folder to launch the interface without first installing the package.

Build plate defaults to **Textured PEI Plate**. The GUI selector or CLI
`--bed-type "Cool Plate"` selects an alternative. Exports set the project
default and clear individual plate overrides so the slicer's global selector
remains usable, without changing filament reassignment. **Known limitation:**
Anycubic may restore its remembered plate preference when opening a project.
Check the displayed Plate Type matches the requested plate and verify its
material temperature before slicing. Reports and the export notice repeat
this warning; automatic native plate-default acceptance remains unresolved.

A separate **Filament profiles - beta** tab now reviews and exports batches of
standalone Bambu/Orca JSON presets, including ZIP and `.orca_filament` bundles.
Limited Prusa-style `.ini` / `.config` input is also available through **Add INI**;
only explicitly mapped scalar material settings transfer. INI bed temperatures
apply to Textured PEI only; other plates inherit the destination base.
Choose files or a bundle, discover/select an installed
S1 printer, enter confirmed physical nozzle/bed temperature ceilings, and review
before export. It creates a new folder and never overwrites installed profiles.
An explicit hotend selector can use this project's user-reported 300/320 C
limits, or 350 C for ceramic with firmware confirmation; no hotend is assumed.
Bed limits are separate, and the app never changes firmware.
Import `importable-presets.zip` (or individual JSONs) with Anycubic's Import
Configs command, or use the tab's opt-in **Install reviewed export…** button
while the slicer is closed. Direct install detects collisions, creates a full
active-account filament backup, and supports quarantined rollback. The local
Siddament batch has 65 installed REVIEW identities across 0.25/0.4/0.6/0.8 mm;
the three unsupported 0.25 mm materials remain excluded. The earlier fifteen
Siddament 0.6 HS presets have passed native import,
identity/focused-setting checks and fresh-session reopen. A broader recheck
found imported fan/slowdown and ASA-temperature differences; investigation and
exact acceptance scopes are recorded in the filament-import documentation.
Physical print calibration remains the user's responsibility.
INI input and unmatched-material bases are supported only through the limited
review/export beta; they are not native-slicer or print-calibration proof. See
[filament import details](docs/FILAMENT_PROFILE_IMPORT.md).

The inspector validates the ZIP/3MF structure, lists every archive member,
detects JSON/XML/config files, parses JSON-formatted `project_settings.config`
and separate machine/process/filament settings configs, flattens their
settings, parses legacy comment-prefixed `Slic3r_PE.config` snapshots as
untyped strings, and applies conservative category tags.

CLI output is emitted as UTF-8 so non-English filenames, member paths, profile
names, and setting values remain inspectable on Windows.

The comparer reports settings found only on one side, settings with differing
typed values, and equal settings. Matching is intentionally strict: archive
member path plus canonical JSON path. It does not yet guess that differently
located settings are equivalent.

`inspect-profile` reads a standalone slicer machine/process/filament JSON,
reports its SHA-256 and flattened settings, and infers its scope from the
containing `machine`, `process`, or `filament` directory. It is read-only and
does not copy or modify the installed profile.

`targets` discovers exact installed Kobra S1 machine profiles and optional
community profile-bundle 3MFs. It emits stable target IDs and can filter by the
actual nozzle diameter. These IDs will be consumed by the dry-run/optimization
commands rather than inferring a target from a filename.

`processes` lists profiles compatible with an exact machine/nozzle target.
Compatibility uses explicit installed-profile metadata. Community multi-nozzle
profiles without reliable compatibility metadata are offered only when their
explicit line width gives one unambiguous nozzle match.

`filaments` lists installed and bundled filament profiles compatible with the
exact target. When a saved S1 project is selected as a reference machine, its
individual filament slots are also available with their saved material tuning.
The regular profile choices remain compatible with the
exact machine/nozzle target, optionally filtered by material family. Pass one
`--filament-id` to apply it to every same-material source slot, or repeat the
option in source-slot order. Material mismatches are refused. The selected
identity is recorded; exact material/nozzle-profile temperature, cooling,
pressure-advance, retraction, and purge values are translated with `REVIEW`
confidence. Maximum volumetric flow is only reduced, never raised. An optional
explicit hotend ceiling can only lower selected filament temperatures.

`plan` and `optimize` also accept `--hotend-type` to record the installed
PTFE-lined, all-metal, aftermarket ceramic, other, or unspecified hotend in the
change report. The label is traceability metadata only: the optimizer never
guesses a safe temperature limit from a construction label. Use the separate
explicit ceiling when one is known.

`plan` and `optimize` accept the opt-in `--nice-supports-beta` overlay; the GUI
exposes the same off-by-default checkbox. It applies a finite, reviewed subset
of support settings from the supplied `Amazing_Support_Settings.3mf`, never
copies its Bambu machine/filament settings, never increases source support
speeds, and leaves nozzle-dependent line width to the selected process. See
`docs/NICE_SUPPORTS_BETA.md` for the exact boundary and required Preview review.

The GUI Physical material selector and CLI `--physical-nozzle-type` record
the installed nozzle independently of its profile. Supported material overrides
are marked REVIEW; see [nozzle hardware](docs/NOZZLE_HARDWARE.md).

Layer height is source-owned by default. If the selected process has a
different nominal height, the exported project receives a truthful custom
process label instead of falsely claiming the preset's height. The converter
also embeds an `[Optimized]` project-local process preset and a read-only copy
of the source's process values in
`Metadata/s1optimizer_original_process_reference.json`. The source reference
is not selectable or safe to print directly on the S1; it exists for comparison
and provenance. Corrected embedded-preset behavior passed representative native
checks; this is not a guarantee for every profile combination. Add
`--use-process-layer-height` (or tick the GUI checkbox) to explicitly translate
the project and initial-layer heights to the selected process. Either policy is
checked against the selected machine's minimum and maximum layer heights.
For an independent height, use `--layer-height 0.18` or the GUI's custom-mm
field. This retains the source first-layer height and the selected process's
line widths. Custom height and selected-process height are mutually exclusive.
Explicit zero machine limits use Anycubic's automatic limits; zero actual
layer heights remain invalid.

Geometry is never scaled by default. If a source plate cannot fit the S1 bed,
the GUI's **Scale to fit S1 plate** checkbox or CLI `--scale-to-fit` measures
each plate and shrinks only those that need it, to the largest fitting 0.1%
increment. The dry-run report names the percentage for every plate. All parts
on a resized plate scale uniformly, changing their physical dimensions;
check fit-critical parts before use. The planner measures transformed mesh
vertices against the target bed and reserves requested brim clearance plus
0.5 mm. The previous explicit `--scale-percent` CLI argument remains available
for advanced use but cannot be combined with `--scale-to-fit`. Prime tower,
support and purge paths still require native Anycubic slicing and Preview
review before printing.

Exports also reconcile the project inheritance/compatibility vectors for
selected profiles and protect explicitly written values from being replaced
by installed-preset defaults during import. This preserves the export's tuning
rather than silently adopting future preset updates. See the
[project metadata audit](docs/PROJECT_INHERITANCE_AUDIT.md).

`plan` and `optimize --dry-run` resolve the selected machine and process
inheritance chains, replace verified machine-owned settings, and clamp verified
speed/acceleration values without ever increasing them. Nozzle-dependent line
widths and machine layer bounds come from the selected nozzle profile while
source layer height and other model intent stay unchanged unless the explicit
layer-height option is selected. Unknown, painting,
modifier, colour, assignment, and layout data are preserved.

`optimize` writes a new 3MF and a change report. If `--output` is omitted the
new filename includes `KobraS1` and the selected nozzle diameter. Existing
outputs/reports and the source path are never overwritten. The rebuilt archive
must pass core 3MF validation, preserve structural counts and the planned
archive inventory, and hash-match every untouched member before it is
published. For a scope explicitly retargeted by the user, a lone foreign
embedded preset snapshot may be removed only when every substantive key is
present in the flattened project settings that Anycubic applies afterward.
Unselected scopes are preserved; ambiguous or unflattened snapshots block
export.

`gui` opens a local Tk desktop interface with source and bundle pickers, exact
nozzle/machine/process choices, ordered material-matched filament selectors,
dry-run review, and an explicit validated-export action. The GUI uses the same
engine and no-overwrite rules as the CLI. Browse loads a source immediately,
and Enter loads a path typed into the source box. Each new source resets the
conversion controls, displays its embedded nozzle and useful print settings,
then profile discovery preselects the closest compatible machine, process and
filament choices. Every suggested choice can be overridden before review.

## Setup

Python 3.11 or newer is required. The runtime has no third-party dependencies.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
```

After installation, either module or console-script form works:

```powershell
python -m s1_optimizer inspect model.3mf
3mf-inspect inspect model.3mf
```

Add `--format json` to either command for machine-readable output. Add
`--show-equal` to `compare` to print unchanged settings in text output. Long
values such as machine G-code are shortened in text output; use `--verbose` or
JSON output when their complete contents are required.

Exit code `0` means the inspected inputs have valid core 3MF structure, `1`
means a readable ZIP is invalid or incomplete as a 3MF, and `2` means the input
could not be read as an archive.

## Safety rules

- Input archives are opened read-only and never extracted.
- Suspicious member paths, duplicate names, encrypted members, oversized
  structured files, malformed XML, and malformed JSON are reported.
- Unknown files and settings remain visible; nothing is silently discarded.
- Conversion edits `Metadata/project_settings.config` and, when required,
  plate nozzle metadata and `3D/3dmodel.model` build-item transforms for
  multi-plate relocation or explicitly selected uniform scaling. Mesh members
  remain unchanged. A strictly
  reconciled foreign embedded preset may be removed; every other member is
  copied and hash-verified.
- Output remains a slicer project, not ready-to-print G-code. Translated
  filament/hotend values remain reviewable, and the project must be opened and
  sliced in Anycubic Slicer Next before printing.

## Development

```powershell
python -m unittest discover -s tests -v
```

## Known limitations

- Conversion requires a modern JSON `project_settings.config`. Legacy
  `Slic3r_PE.config` projects can be inspected, but are not converted.
- Multiple embedded presets in a retargeted scope are rejected when the active
  choice cannot be established. Profile bundles can supply destination choices
  without being convertible as source projects themselves.
- Unknown vendor settings and variable-layer data are preserved with review
  warnings; byte preservation does not prove the destination slicer applies
  every feature identically. Per-object overrides may supersede project changes.
- The known undeclared `slic3rpe` text/shape prefix is supported for read-only
  model-settings inspection. Other malformed XML still fails. Zero object/part
  extruders follow reviewed default/inheritance rules; out-of-range positive
  assignments are not silently reassigned.
- Broader model/nozzle acceptance and the final visual GUI workflow remain
  incomplete. No physical print is started by this application.

See the [Project specification](docs/PROJECT_SPEC.md),
[Architecture](docs/ARCHITECTURE.md), [Roadmap](docs/ROADMAP.md),
[upstream research](docs/UPSTREAM_RESEARCH.md), and
[first real-file findings](docs/REAL_FILE_FINDINGS.md). The emerging
KEEP/CLAMP/REPLACE/TRANSLATE constraints are recorded in
[rule-engine design notes](docs/RULE_DESIGN.md). Local reference provenance is
captured in the [installed slicer snapshot](docs/LOCAL_SLICER_REFERENCE.md) and
[corpus plan](docs/CORPUS_PLAN.md). User-validated third-party choices and
their provenance are recorded in [community profile options](docs/COMMUNITY_PROFILES.md).
See [CLI usage](docs/USAGE.md) for the export workflow and
[acceptance evidence](docs/MANUAL_ACCEPTANCE.md) for completed single-slot and
four-slot slicer gates, plus pending and superseded acceptance cases.

## Before publishing to GitHub

The repository is initialized locally on the `main` branch. Before the first
public push:

1. Review the project name and package metadata.
2. Choose and add a licence; none is implied by this repository.
3. Confirm no private 3MF/profile files are staged.
4. Add sanitized real-world fixtures only when redistribution is permitted.
5. Create the remote repository, then add it as `origin` and push `main`.
