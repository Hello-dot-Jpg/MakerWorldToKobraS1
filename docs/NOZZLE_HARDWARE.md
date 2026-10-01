# Physical nozzle selection

Use `--physical-nozzle-type` in `plan` or `optimize`, or the GUI's Physical
material selector. `profile` is the default and follows the chosen machine.
Explicit choices are brass, hardened-steel, stainless-steel, bimetal and other.
Diameter continues to come from the exact machine target.

For a supported type differing from the profile, the converter writes that
nozzle type and a distinct machine identity with REVIEW confidence. It records
the profile parent and resets `nozzle_hrc` to 0, allowing the slicer's type-based
hardness lookup. This hardware declaration is not a calibrated thermal profile.
Temperatures, cooling, retraction and flow still follow the selected profile
rules and need review for that hardware.

Bimetal and other have no exact enum in the reviewed Anycubic source. They are
recorded in reports, while the export retains the chosen profile's slicer type.
Actual wear resistance cannot be inferred from those names.

## Hardness evidence

Reviewed Anycubic source `src/libslic3r/Print.cpp`, function
`Print::get_hrc_by_nozzle_type`, reads `resources/info/nozzle_info.json`.
The installed file maps hardened steel to 55, stainless steel to 20, brass to
2, and undefined to 0. These are slicer compatibility values, not measurements
of the user's nozzle. `GCodeProcessor.cpp` compares required filament HRC
against nozzle HRC, falling back to this type lookup when nozzle HRC is zero.
Discovery and conversion now honor a positive explicit profile HRC before the
type lookup. The target hardness is written even when the source omitted it,
so the report and exported configuration use the same rating. Unsupported
physical material names still require independent review.

Many installed ordinary filament profiles require HRC 3. Brass (2) versus
requirement 3 therefore produces a warning under the slicer's rules; this alone
does not establish that the filament contains abrasive filler. Reports describe
the numeric mismatch instead of implying every nonzero requirement demands
hardened steel.

## Verification

Tests cover threshold comparisons and archive export with an explicit material
override, parent identity, reset hardness, unchanged painting and unchanged
input target. Bimetal report-only behavior is also checked. Installed-slicer
acceptance of the new control and output identity remains pending.
