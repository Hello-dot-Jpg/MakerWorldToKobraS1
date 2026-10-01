# Filament change timing investigation - 2026-09-09

Native acceptance 2026-09-14: fresh timing fixture opened and sliced with no
visible warning, 133 layers / 31.98 mm / 76.61 g total. Saved separately as
`reports/timing-acceptance-dgbiwl02/tools-06hs-petg-timing-native-review.3mf`.
Native saved JSON retains load 126.423, unload 0 and tool-change 0 exactly.
0.6 HS, .24 layer, .62 width and textured PEI also retained. Reopen still pending;
this single-material slice does not measure real ACE/tool-change duration.

User noticed 126.423 in the old-value column of Anycubic's preset dialog.
All four installed official S1 machine JSONs specify
`machine_load_filament_time: "126.423"` (line 76). This is not an accidental
temperature, feed rate or converter-generated value.

Reviewed local Anycubic source: `src/libslic3r/PrintConfig.cpp` around line 2034
labels this field Filament load time, units seconds, and explicitly describes
it as statistics-only. `GCode/GCodeProcessor.cpp` around line 4002 adds the
load/unload/tool-change allowances to simulated tool-change time. No command
to wait 126.423 seconds is implied by this setting.

The scraper review archive contains zero for both load and unload. Investigation
found the converter's machine replacement allowlist omitted these timing keys.
It now replaces all three from the chosen target, including adding target
values absent in the source. Missing target values follow the existing warning/
preservation policy; no duration is guessed. Community/reference targets retain
their own effective timing values, not hard-coded official values.

158 tests pass, including source-zero replacement and missing-source addition.
Existing saved exports and installed presets were NOT rewritten. Regenerate
relevant exports to receive this fix. Earlier native slice results remain
historical acceptance and do not verify the newly changed timing values.

The exact reason for Anycubic's 126.423 precision is unverified. It is a
126.423-second estimate (about 2 minutes 6 seconds), not proof of actual ACE
load duration. No firmware changes or physical print commands were made.
