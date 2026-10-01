# Upstream research

Third-party repositories are cloned only under the Git-ignored `.research/`
directory. This document records the reviewed commit and separates reusable
ideas from code/data whose licence is unclear.

## Primary references

### myles1663/3mf-Sanitizer

- Upstream: <https://github.com/myles1663/3mf-Sanitizer>
- Reviewed commit: `8e47a26e7da2eac3d6a29d76b5b97ff97e1f0118`
- Licence: MIT.
- Useful evidence: `sanitizer.py` identifies two concrete MakerWorld values
  rejected by some downstream slicers: `raft_first_layer_expansion = -1` and
  `tree_support_wall_count = -1`. Its narrow parameter-specific fixes are a
  better model than generic numeric rewriting.
- Ideas to retain: only write when something changes; name each changed member
  and key; treat unknown content as untouched.
- Patterns not to copy: `extractall`, rewriting the input path, wholesale ZIP
  reconstruction, regex editing without schema context, and continuing after
  individual member errors.

### FJ-Oekstrahay/bambu-3mf-maker-with-settings

- Upstream: <https://github.com/FJ-Oekstrahay/bambu-3mf-maker-with-settings>
- Reviewed commit: `7a677f37fe0af5cdebf10d3760a34fb95d9280a1`
- Licence: MIT.
- Useful evidence: `make_bambu_3mf.py` contains a deliberately finite
  `SETTING_KEY_MAP` for quality, strength, speed, acceleration, and filament
  keys. It treats many slicer values as strings or arrays of strings rather
  than coercing them to numbers immediately.
- Architecture to study: deep-copy configuration before edits, preserve array
  slot counts, keep per-plate `process_settings_N.config`, preserve object IDs
  and filament maps in `model_settings.config`, and verify output geometry and
  metadata after writing.
- Constraint: its generated preset identities and assumptions are Bambu/A1
  oriented; they are not Kobra S1 machine definitions.

### prma85/anycubic-profiles

- Upstream: <https://github.com/prma85/anycubic-profiles>
- Reviewed commit: `c78b7174811f9c1621178201c120f525a16a98ab`
- Licence: none found. Do not copy code, JSON, or prose without permission.
- Research value: documents a machine → filament → process inheritance model,
  Bambu-only fan/AMS key removal, Anycubic G-code preservation, and explicit
  Kobra S1 material/process caps.
- Examples requiring validation rather than blind adoption: PLA Basic maximum
  volumetric speed 16 mm³/s, PLA Matte 14 mm³/s, PETG high-quality default
  acceleration 4000 mm/s², outer acceleration 2000 mm/s², outer speed 60–80
  mm/s, and travel acceleration 5000–7000 mm/s².
- Important principle: pressure advance, flow, retraction, and maximum
  volumetric speed remain material/nozzle/printer calibration concerns and
  should be TRANSLATE/REVIEW, not unconditional replacement.

## Adoption policy

- Facts, file-format observations, and public interfaces may guide independent
  implementation.
- MIT code may be reused only when doing so is better than a clean local
  implementation and the required notice is preserved.
- Unlicensed profile data remains research-only.
- Every candidate limit must be checked against the user's supplied reference
  and, where conflicts exist, verified in Anycubic Slicer Next before it becomes
  a conversion rule.

## Secondary references

### MPC561/Anycubic-Kobra-S1-Orcaslicer-Profiles

- Upstream: <https://github.com/MPC561/Anycubic-Kobra-S1-Orcaslicer-Profiles>
- Reviewed commit: `3af7b09f0f1141b643db929633f0fe02a9632018`.
- Licence: none found. Treat profiles as research-only.
- Machine values in the reviewed 0.4 mm profile include X/Y maximum speed 600
  mm/s, Z 15 mm/s, E 80 mm/s, 20,000/10,000 mm/s² X/Y limit arrays, 500
  mm/s² Z, and Klipper flavour. These resemble values in the supplied Kobra
  candidate but are not proof of safe process acceleration.
- The author distinguishes ringing-prone Standard profiles from lower-speed
  Structural profiles and describes 5,000 mm/s² as measured capability. That
  supports saved Conservative/Structural targets rather than one universal
  limit.
- The custom "Startcode 2.0" assumes an enhanced nozzle wiper, special purge
  moves, and coordinates beyond the nominal 250 mm Y area. It must never be
  copied into a general Kobra reference.
- Claimed PETG/ABS flow tests and filament temperatures are material-specific
  anecdotes, not default TRANSLATE rules.

### hansonxyz/Bambu-Labs-Orcaslicer-Generator

- Upstream: <https://github.com/hansonxyz/Bambu-Labs-Orcaslicer-Generator>
- Reviewed commit: `7dbb8afe9c3bf3b65fa92532be32bf72a44fc6e1`.
- Licence: CC BY-SA 4.0. Copied/adapted code or data requires attribution,
  change notice, licence linking, and ShareAlike distribution. Prefer an
  independent implementation of general architectural ideas.
- The generator models Kobra S1 as enclosed CoreXY and mirrors selected X1C
  behavior, but its machine profile is intentionally minimal and inherits the
  installed OrcaSlicer `Anycubic Kobra S1 0.4 nozzle` system preset.
- It does not bundle Kobra machine G-code. This is useful evidence that a clean
  reference can inherit a slicer-owned machine profile instead of embedding a
  foreign custom machine snapshot.
- Its deterministic layering—universal values, printer-group deltas, material,
  nozzle, mode, and hard caps—is a useful future TRANSLATE architecture.
- Its temperatures and X1C mirroring remain opinionated profile data and must
  not override the user's known-good Kobra reference.

### ANYCUBIC-3D/AnycubicSlicerNext

- Upstream: <https://github.com/ANYCUBIC-3D/AnycubicSlicerNext>
- Reviewed commit: `6103ed8b511609658d00d0538cc7f0609cdb57da`.
- Licence: GNU AGPL v3. Use source behavior as research unless the project
  deliberately adopts AGPL-compatible code/licensing.
- `GCodeProcessor.hpp` defines machine time modes as Normal index 0 and Stealth
  index 1. `Tab.cpp` exposes two machine-limit fields only when `silent_mode`
  is enabled, and `GCodeProcessor.cpp` looks up axis speed/acceleration by that
  mode index.
- The reviewed upstream Kobra S1 profile uses two slots. This does not fully
  describe the installed Anycubic Slicer Next 2.0.0.2 data, documented below,
  so it cannot justify rejecting or warning about a third slot.

### Installed Anycubic Slicer Next 2.0.0.2

- Executable: `C:\Program Files\AnycubicSlicerNext\AnycubicSlicerNext.exe`;
  file/product version `2.0.0.2`, build marker `20260902193307`.
- Bundled machine profiles are under
  `C:\Program Files\AnycubicSlicerNext\resources\profiles\Anycubic\machine`;
  the OTA cache mirrors them under the user's roaming profile.
- The bundled Kobra S1 model advertises 0.25, 0.4, 0.6, and 0.8 mm variants.
  Their default process heights are 0.08, 0.20, 0.30, and 0.40 mm
  respectively, and all use machine setting ID `GM001`.
- Every bundled Kobra S1 nozzle profile contains three machine-limit entries,
  including X/Y speed `600, 300, 780`. This matches the clean printed castle
  project and proves that three entries are normal current Anycubic profile
  data, even though the reviewed public estimator code exposes only Normal and
  Stealth modes.
- Until current semantics are proven, preserve or replace these arrays as
  complete versioned values. Do not infer a third mode or operate on one slot.
- No separate local slicer CLI or documented headless project-export command
  was found. GUI-generated empty reference projects remain optional because
  the installed profile JSONs are a cleaner machine source of truth.
