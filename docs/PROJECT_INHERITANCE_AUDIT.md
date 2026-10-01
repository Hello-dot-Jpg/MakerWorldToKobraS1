# Project inheritance audit — 2026-09-06

## 2026-09-15 Downloads rerun - PASS

The read-only audit at `reports/download-inheritance-audit-2026-09-15.txt`
covered 137 files / 129 modern projects and reported zero findings. All modern
projects expose `print_compatible_printers`; machine-repair preservation passed
for all 129.

The user's screenshots established that the prior cupholder export did not
restore stock-filament visibility. Successful opening and slicing did not prove
that compatibility metadata survived import.

## Loader evidence and repair

Reviewed local Anycubic source in
`.research/AnycubicSlicerNext/src/libslic3r/PresetBundle.cpp` (around lines
2429–2521) extracts `inherits_group`, resizes it to the number of filament
colours plus two, then assigns each entry to plain `inherits` while loading
the respective preset. Order: process, ordered filament slots, printer.
`Preset.cpp` (around lines 603–644) accepts a non-system printer's immediate
parent when evaluating a filament's compatible-printer list.

The converter now sets the printer entry to the matching official selectable
machine parent. Previously it changed only plain `inherits`, which the loader
overwrites. Other scope entries remain unchanged. Short groups are padded;
malformed or oversized groups are rejected rather than silently losing entries.
An official target uses its selectable leaf name, not an internal base profile.

## Read-only Downloads audit

Command: `python tools/audit_project_inheritance.py C:\Users\USER\Downloads`

- 128 files scanned; 120 modern project configs, eight without one.
- 54 modern projects have nonempty inheritance groups; 66 have absent/empty groups.
- All 120 passed the machine-entry repair and other-scope preservation check.
- No malformed/oversized groups or missing filament-colour arrays were found.
- All 120 also contain `print_compatible_printers`; 102 contain
  `different_settings_to_system`; four each contain machine/process expression
  groups. These are separate loader metadata and are not fixed by changing the
  printer inheritance entry.

This proves array alignment and preservation on this corpus, not destination
UI visibility or semantic fidelity. Follow-up: audit retargeted process/filament
scope metadata and difference masks against the loader before claiming full
profile identity fidelity. Unselected scopes must remain source-owned.

The cupholder inheritance repair differs from the earlier export only
in `inherits_group`. The user confirmed opening, slicing and no missing filaments;
see MANUAL_ACCEPTANCE.md. No slicer UI, installed settings, or source archives
were modified by this audit.

## Difference-mask finding and repair

`Preset.cpp`, `PresetCollection::load_external_preset` (around lines 1900–1939),
refreshes options absent from `different_settings_list` using an installed
parent or matching system preset. `PresetBundle.cpp` always inserts identity
keys into this list, so merely deleting/emptying the serialized masks would
not disable the refresh. The cupholder's old machine mask was empty and its
process mask contained only five source overrides. This cannot protect all
converted machine tuning, downward clamps, and source-owned KEEP settings.

The converter now emits a mask containing every explicitly written setting
name in each scope. The loader filters by each preset's own keys, making a
shared superset valid. Absent settings are not materialized or protected;
installed defaults can still fill those. Names containing delimiter/escape
characters are rejected instead of generating ambiguous masks. This freezes
the exported explicit values for fidelity rather than opting into future
installed-preset default changes on import.

Regression tests exercise KEEP and changed-value retention under the reviewed
refresh rule and check masks in a writer round trip. A new cupholder export
differs from the accepted filament-fix artifact only in these masks. Actual
installed-slicer import fidelity remains to be checked. Retargeted process
and filament inheritance/expression metadata still needs its separate audit.

## Process compatibility follow-up

The loader copies `print_compatible_printers` to the loaded process's
`compatible_printers` before loading that preset (PresetBundle.cpp around
2501). All 120 modern corpus files contain the serialized field; the cupholder
still named Bambu A1 mini after its machine was retargeted. The converter now
replaces this list only when an explicit destination process is selected, using
the effective destination machine and its official compatibility parent.
Machine-only plans leave source process compatibility alone.

Difference masks also protect loader-renamed compatibility keys, not just their
serialized project names. A writer regression verifies the exact custom/official
machine pair, and unit tests cover renamed-key mask protection. These changes
are not yet represented by the earlier import-fidelity review artifact.

## Selected-scope reconciliation

The planner now reconciles process and ordered filament entries of
`inherits_group` and their machine/process expression vectors from explicitly
selected profiles. Official selections use their selectable leaf identities;
community selections use their declared parents. Unselected scopes retain
their original entries. Saved project process references use scope zero,
never the reference project's plain machine `inherits`. Malformed/oversized
expression vectors and filament-count mismatches are rejected.

Tests cover single-filament broadcasting, source immutability, unselected
process retention, reference process scope selection and malformed vectors.
The consolidated cupholder output has all seven correct destination inheritance
entries, target process compatibility, and explicit-value masks. Compared with
the accepted filament-list repair, only those five metadata fields change;
all print-setting values and other archive members remain identical.

Reference filament discovery now extracts each slot's inheritance and both
compatibility expressions with the loader's correct vector offsets. It pads
missing entries with empty strings like the loader, rejects malformed/oversized
vectors, and never uses the reference project's plain machine `inherits` for
a filament. An export regression verifies distinct parents/expressions for two
otherwise identically named reference filaments, with malformed-vector checks.
All 86 tests pass. Installed-slicer acceptance of reference-profile exports
and of the consolidated cupholder output remains pending.
