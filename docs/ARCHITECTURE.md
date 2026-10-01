# Architecture

## Milestone 1 data flow

```text
CLI
  -> ThreeMFArchive validates and inventories without extraction
  -> parser discovers modern JSON and legacy Slic3r settings snapshots
  -> settings flattens JSON into typed Setting records
  -> classifier applies conservative, non-exclusive category tags
  -> report renders deterministic text or JSON
```

`Setting.identity` is the exact archive member name plus a canonical,
type-preserving JSON segment path. A separate friendly dotted/bracketed path is
shown to people. This prevents accidental merging of unrelated settings with
the same leaf name or keys containing punctuation. Array indices are retained,
duplicate object keys are rejected with a warning, and JSON types are not
coerced.

Comparison has two layers. The primary human report groups exact leaf names
and compares their sets of typed values, so array-versus-scalar schema changes
do not hide a shared setting. Every occurrence and source location remains in
the group. JSON output also retains the stricter member-plus-canonical-path
diff for forensic review.

## Modules

- `archive.py`: read-only archive validation and member inventory.
- `parser.py`: content detection plus modern JSON and legacy Slic3r settings
  loading.
- `settings.py`: immutable setting records and deterministic JSON flattening.
- `classifier.py`: heuristic category tags; it does not make optimization
  decisions.
- `compare.py`: exact typed comparison and structured diff records.
- `report.py`: text and JSON presentation.
- `targets.py`: installed/community machine-target discovery, actual-diameter
  filtering, provenance hashes, stable IDs, and exact selection.
- `processes.py`: installed/community process discovery, compatibility
  filtering, inheritance resolution, and stable process IDs.
- `filaments.py`: material/nozzle-compatible filament discovery, inheritance,
  hardness risk labels, and ordered slot selection.
- `rules.py`: conservative default CLAMP names and optional strict JSON
  overrides.
- `plan.py`: machine REPLACE and process-ceiling CLAMP planning; exact
  filament/nozzle translation and assignment validation; no write side effects.
- `validation.py`: one-based model/object filament-assignment validation against
  the selected slot count.
- `writer.py`: new-path-only archive rebuild, planned embedded-snapshot
  removals, plus member-hash and structural round-trip validation.
- `cli.py`: argument parsing and exit-code handling.

## Deliberate limitations

- JSON-formatted `project_settings.config` and recognized separate
  machine/process/filament settings configs are parsed into settings.
- Legacy comment-prefixed `Slic3r_PE.config` snapshots are parsed as strings;
  their setting-specific lists and expressions are deliberately not guessed.
- XML is checked for well-formedness but not flattened into settings.
- Duplicate ZIP member names are reported and are not parsed, because lookup
  by name would be ambiguous.
- Settings in different member paths are not treated as equivalent.
- Machine/process conversion, exact filament/material translation, ACE-slot
  validation, and archive rewriting are implemented. G-code generation is not;
  output intentionally remains a slicer project.

These constraints keep the first real-file comparison evidential rather than
speculative. Schema-specific normalization belongs after that review.

Target resolution has two layers: an exact installed/versioned Anycubic
machine JSON supplies machine identity, geometry, limits, and G-code, while a
known-good printed 3MF supplies project/process/material evidence. A foreign or
custom project snapshot must not silently override the selected machine JSON.

Recognized settings files are also checked for same-name values that disagree
across members. Inspection reports those conflicts without guessing. Reviewed
Anycubic source registers embedded presets before applying the complete
`project_settings.config`, so the latter is authoritative for keys it contains.
During conversion, only a scope explicitly retargeted by the user is eligible
for removal of one foreign embedded snapshot, and only when every substantive
snapshot key is present in the flattened project config. Unselected scopes are
preserved; multiple candidates, excess selected filament snapshots, or any
unflattened key remain write blockers. Printer identity, G-code flavour, and
nozzle conflicts receive explicit warnings.

When a 3MF bundles several separately identified machine/process/filament
profiles, the parser classifies each member as selected, alternative, or
unresolved. Alternative profiles and multi-slot filament selections remain
visible but are excluded from contradiction counts. A lone unmatched profile,
such as the retained Creality machine definition, remains unresolved and is
still checked against the project snapshot.

XML is streamed and counted rather than loaded wholesale. Core model resource,
mesh, and build-item counts plus model-settings object, part, instance, plate,
and assembly counts are enforced as structural invariants by the writer.
