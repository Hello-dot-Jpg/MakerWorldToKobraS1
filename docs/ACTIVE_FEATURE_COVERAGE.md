# Active-feature evidence — 2026-09-06

This inventory distinguishes active assignments/overrides from unused profile
slots. It uses local metadata, not filenames as proof of a feature.

| Case | Evidence in source | Current automated evidence | Destination evidence |
| --- | --- | --- | --- |
| Painted colour | scraper (2) has nonempty paint_color triangle data (`1C`) in Schaber.stl_1.model | Painted model member byte-identical; 15 untouched members; source colours and 0.17 mm layer height retained | Pending |
| Painted supports | Bucket wider/longer source has nonempty paint_supports triangle data and enabled tree(manual) supports | Painted model member byte-identical; 19 untouched members; manual support mode retained | Pending |
| ASA | Heat bed clamps assigns its object to slot 2, whose material is ASA | Exact ordered stock PETG/ASA/PETG/PETG translation; zero blockers; 13 untouched members | Pending |
| ABS/PETG | HoseHolder_260309_2 assigns objects to slots 1 and 2, PETG and ABS | Exact ordered stock PETG/ABS/PLA translation; zero blockers; 220 untouched members; 34 plates retained | Pending |
| Modifier | Original gimballed cupholder has modifier part 4, Generic-Cylinder, with wall_loops=4 | Model-settings member retained byte-for-byte in cupholder exports | User accepted opening/slicing/supports and filament availability; effective modifier wall count not separately checked |
| Local ironing / negative volumes | IroningTest_TwoColor (1) has 54 local topmost-ironing overrides and 60 negative parts; global ironing is disabled | Current 0.4 HS export preserves all 54 overrides and 60 negative parts, with exact reviewed PLA / PLA+ / PLA destinations | Pending native open/slice |
| Variable layers | Beer Buoy P2S has a 20,444-byte layer_heights_profile.txt; Anti Vibration Feet has 2,624 bytes | Numeric profile audit implemented; bounds checked without flattening | Pending |

Do not count `poop chute` as active ABS evidence: its ABS slot is unused by
the inspected explicit assignments (slot 3 is PLA). Likewise, Anti Vibration
Feet's explicit assignment uses PA6-GF slot 1, not its unused ABS slot.

## New material regression artifacts

Both exports use the official 0.4 mm machine and 0.20 mm Standard process,
source heights retained, explicit hardened-steel hardware override (REVIEW),
and exact matching stock material profiles. They are review projects, not
independently calibrated thermal presets or physically validated prints.

- `reports/asa-heat-bed-clamps-current-04hs-review.3mf`:
  `769417A6E8EABA20E79E7F479DDE6D6D5A30A185E2C00AE6CBECA40FCD9F9EB2`.
- `reports/abs-petg-hose-holder-current-04hs-review.3mf`:
  `0DB2AD8938A41B69E4CB3F9D43A1500D2F4AF9D1DD4B6601DF7B027D791BEAB9`.

Only project settings changed in these exports. Source materials, slot order,
assignments and the existing model layout were not replaced with a simpler
single-material case. The hose-holder source is a 34-plate project, not a
single-plate acceptance fixture.

The current default-plate replacement is
`reports/asa-heat-bed-clamps-textured-04hs-review.3mf`
(`91879873DC9EF08AC8E36D54BE3BC62D4BAC7126779396DE696916CDBBC5C1E8`).
It retains the object's active slot-2 ASA assignment and sets both global and
per-plate metadata to Textured PEI Plate. The older High Temp Plate artifact is
retained only as historical warning evidence.

The refreshed local-ironing fixture is
`reports/ironing-negative-volume-current-04hs-review.3mf`
(`541763F98309786128DCF77E09AD9F2E7D7BB698A6BB9E12C9C6DCF2340DD1B9`).
It has zero write blockers, uses the official 0.20 mm process and exact
PLA / PLA+ / PLA stock destinations, and preserves all 54 local topmost-ironing
overrides and 60 negative parts. Native interpretation is still pending.

## Variable-layer validation

Reviewed `Format/bbs_3mf.cpp::_extract_layer_heights_profile_config_from_archive`
and `Slicing.cpp` establish one object per line, `object_id=N|z;height;...`,
with more than four numeric entries and paired z/height values. Repeated z
positions are valid transitions. The planner now checks this known member
format, positive finite heights, nonnegative/nondecreasing z, unique positive
object ids, the selected machine bounds, linkage to a unique direct-mesh
resource, and profile endpoint versus that mesh's streamed Z extent.
Out-of-range, missing/ambiguous linkage, or endpoint-overrun profiles block
export rather than being flattened or silently clamped. A profile ending more
than one selected maximum layer height below its mesh is retained with an
explicit Preview warning because partial control curves can be legitimate.
Unknown variable-layer formats still receive a preservation/review warning,
not a claim of validation. Unit and real-file tests cover these paths.

Successful real-file path: `S1 Flexi Baby Triceratops Dinosaur.3mf` exported
with the official 0.4 mm brass / 0.20 mm Standard machine/process and matching
stock PETG, preserving source heights. Its object-1 profile has 175 z/height
pairs spanning 0.090744–0.200000 mm. The entire variable-layer member is
byte-identical in `reports/triceratops-variable-layers-04-petg-review.3mf`.
Zero blockers; 16 untouched members verified; output SHA-256
`71486BBDE8A39BCA996511EA5A80BA413B845FBA607E22F20586CA33148B147D`.
Installed-slicer acceptance remains pending.

The attempted Beer Buoy 0.6 mm regression correctly blocked before writing:
four profiles contain 0.08 mm layers below that target's minimum, despite its
0.42 mm maximum accommodating the other two profiles. A larger nozzle is not
automatically compatible with a variable-layer project. No Beer Buoy review
archive was generated by that attempt.

## Painted-feature regression artifacts

Anycubic's `Format/bbs_3mf.cpp` reads `paint_supports` and `paint_color` on
triangles into support and multi-material facet data (around lines 3605–3607,
4770–4782). The two selected sources contain nonempty, nonzero encoded values,
not merely empty/default attribute names. This proves painting data is present;
it does not substitute for checking rendered colour/support interpretation.

Exports use official 0.4 mm / 0.20 mm Standard settings with exact ordered
stock materials. Nice supports beta is OFF here so the source's manual support
painting mode is not replaced. Source layer height, filament colours, support
enable/type and ironing type were checked unchanged. The scraper also has
active topmost ironing; the bucket retains both plates.

- `reports/painted-colour-scraper-current-04-review.3mf`:
  `F610AD50F4F1678F903AC38619B084C7D6A9A8CECB04A431E5A459EB294231AE`.
- `reports/painted-support-bucket-current-04-review.3mf`:
  `541BD3975F0035FA7DDF685CB19CBA73FC93FB53ACB5740AC9349BC6E47D9E98`.

Both exported with zero blockers and only project-settings changes. Original
paint-bearing model members were directly compared byte-for-byte after export.
No desktop/slicer interaction was used; installed-slicer checks remain pending.

## Source-speed retention

The current painted scraper export was directly compared with its source for
all 18 positive scalar values in the default CLAMP allowlist. None increased.
Examples retained exactly: inner-wall speed 70, outer-wall speed 60, top-surface
speed 55 and travel speed 175 mm/s; inner-wall acceleration remains 4000 and
outer-wall acceleration 2000 mm/s². Initial-layer infill speed decreased from
100 to 80 mm/s. This is concrete source-tuning retention evidence, not a claim
that we know why the model author chose each speed. Destination import still
needs to preserve these values; archive comparison alone does not establish it.
