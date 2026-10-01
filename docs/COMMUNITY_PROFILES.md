# Community profile options

Inspection date: 2026-09-04.

## Provenance

- Source: [Version 2 of optimized 0.4mm Profiles for Kobra S1 - Faster,
  Smoother, Quieter!](https://www.makeronline.com/en/model/Version%202%20of%20optimized%200.4mm%20Profiles%20for%20Kobra%20S1%20-%20Faster,%20Smoother,%20Quieter!/167680.html)
- MakerOnline creator: `@Manethon_Sega_3814903`
- The source describes selective process/filament overrides, a hardened-steel
  0.4 mm option, and testing on the creator's Kobra S1. It also says the
  profiles are provided as-is and results vary with filament and environment.
- A redistributable licence was not verified. The project records provenance
  and reads the user's local copies; it does not vendor or republish them.

Tracking parameters from the user-provided URL are deliberately omitted.

## Local packages

| Package | SHA-256 | Contents |
|---|---|---|
| `V2+Kobra+S1+0.4+nozzle+profiles+for+speed+and+quality.3mf` | `9C8A5FDC3A2F43BBCD8E7D27E425C31A0CCEB3E17268D00885B622D5F686F57E` | 0.4 mm hardened machine overlay, 10 process profiles, 4 filament profiles |
| `Profiles+0.2+0.6+0.8+V2.3mf` | `2925445F8DF172EB4131A883A6599A66318BFBAE2047B11AA786168B6F986DCD` | five machine overlays and three matching process profiles |

The plus-named 0.4 package is byte-identical to the earlier space-named local
copy. Duplicate hashes must be analysed only once.

## 0.4 mm V2 pack

The bundled hardened-steel machine preset is a six-key overlay inheriting
`Anycubic Kobra S1 0.4 nozzle`; the slicer-created local copy adds the trailing
dash recommended by the creator and selects the community ExtraDraft default.
Official Anycubic machine limits, volume, and G-code remain inherited.

The pack provides process presets at 0.08, 0.12, 0.16, 0.20, 0.24, and
0.28 mm, including quality, optimal, standard, quiet, draft, and ExtraDraft
variants. It also includes inherited PLA, PLA+, normal PETG, and high-speed PETG
filament overrides. The known-good castle used the 0.28 mm ExtraDraft process.

## Additional nozzle pack

| Display identity | Actual diameter/type | Machine overlay highlights | Process |
|---|---|---|---|
| `AC KS1 0.2 nozzle Brass` | 0.25 mm brass | 0.04-0.14 mm layers; 0.4 mm retraction | 0.10 mm HighQuality |
| `AC KS1 0.6 nozzle Brass` | 0.6 mm brass | 0.12-0.42 mm layers; 1.0 mm retraction | 0.30 mm |
| `AC KS1 0.6 nozzle Hardened Steel` | 0.6 mm hardened steel | brass overlay plus hardened type | 0.30 mm |
| `AC KS1 0.8 nozzle Brass` | 0.8 mm brass | 0.16-0.56 mm layers; 1.0 mm retraction | 0.40 mm |
| `AC KS1 0.8 nozzle Hardened Steel` | 0.8 mm hardened steel | brass overlay plus hardened type | 0.40 mm |

Despite the first preset's `0.2` display name, its actual
`nozzle_diameter` is 0.25 mm. The UI must display the actual diameter and may
show the original preset name secondarily. The target dropdown now shows both.

All five machine overlays inherit the official 0.4 mm profile rather than the
newer matching-diameter Anycubic profiles. The user reports that these options
work well, so they are valid `USER-VALIDATED COMMUNITY` choices. Their original
leaf overrides and provenance are preserved. To repair stock-filament/process
compatibility, the optimizer explicitly links each exported overlay to the
matching-diameter official parent and reports both the declared and effective
parent. This creates a derived combination rather than an unchanged copy of the
user-validated profile, so installed-slicer visibility and slicing acceptance
remain required.

## Application presentation

Target selection should distinguish:

1. `OFFICIAL ANYCUBIC`: exact installed, versioned profile;
2. `USER-VALIDATED COMMUNITY`: exact community inheritance chain and local
   hash, including these V2 packs;
3. `CUSTOM`: user-selected profile requiring review.

A profile-bundle 3MF contains alternative `machine_settings_N`,
`process_settings_N`, and `filament_settings_N` members. They are choices, not
simultaneously active contradictions. The inspector now reports their selected,
alternative, or unresolved state separately from genuine cross-file conflicts.
