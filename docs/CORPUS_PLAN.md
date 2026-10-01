# Local 3MF corpus plan

Inspection date: 2026-09-04. There are 120 `.3mf` files under the user's
Downloads directory. They remain outside Git and are inspected read-only.
Files should enter a public test fixture set only when their model/profile
redistribution rights are known or their contents have been independently
sanitized.

## Outcome-labelled anchors

| Role | File | Outcome | Key use |
|---|---|---|---|
| MakerWorld/Bambu source | `tools.3mf` | not supplied | Bambu A1 mini source schema |
| S1 reference | `迪士尼小城堡-Sumee1798.3mf` | printed very well | authoritative 0.4 mm S1 snapshot; multi-plate/multi-material |
| Legacy compatibility | `Flexible_Cat.3mf` | printed pretty well | Kobra 3 legacy `Slic3r_PE.config` input |
| Modern compatibility | `Helicopter_Back.3mf` | printed pretty well | Kobra 2 Pro modern project; three plates |

Successful printing is useful evidence, but the two compatibility cases must
not donate their foreign printer identities, G-code, or machine limits.

## High-value unlabelled cases

| File | SHA-256 | Observed role |
|---|---|---|
| `Poop Chute v2.3mf` | `9C3516F725D5F817ED9980AD226551EA898A46F5F3403FBF6753EB3C375B4260` | clean S1 0.4 mm brass, PLA, two plates |
| `Anycubic_ACE_Pro_RISER.3mf` | `35405BA20A9A9C4FFDDA492BD95C52E609EB8A362065F4708A777E30B608564E` | clean S1 hardened 0.4 mm, eight plates, PA/PETG/PLA/ASA |
| `Redmi Pad SE 8.7 Folio Case - TPU 90A - Kobra S1.3mf` | `C1BCA2E1D8494101BD966379CDEBECF3422DF7F1AC2C67C6AC607D09F9E2FEE2` | clean S1 0.4 mm TPU, three plates |
| `Halter+Oben_Kobra-S1_0.6_PA-CF_Tuned.3mf` | `EF5AFD46100FB89945C90E06395CA7F1449977E66C74101D09BD34533350B8B9` | 0.6 mm hardened PA/ABS; one bundle-aware conflict |
| `IroningTest_TwoColor.3mf` | `C9644C6FFB1B2AA6D0023B2239BAF85A27F8BB1D7A827FC953524F1C7AD7175B` | Bambu P1S to S1 two-colour retargeting case; 80 bundle-aware conflicts |
| `Amazing_Support_Settings.3mf` | `8FF01B6DCF49EFD0E0641EE438A7745C0A8B9D79CD9758AD049E490540EB6FB3` | clean Bambu P2S support-settings source |
| `V2+Kobra+S1+0.4+nozzle+profiles+for+speed+and+quality.3mf` | `9C8A5FDC3A2F43BBCD8E7D27E425C31A0CCEB3E17268D00885B622D5F686F57E` | user-validated community 0.4 hardened/process/filament bundle |
| `Profiles+0.2+0.6+0.8+V2.3mf` | `2925445F8DF172EB4131A883A6599A66318BFBAE2047B11AA786168B6F986DCD` | user-validated community 0.25/0.6/0.8 machine/process bundle |

The 0.6 mm local projects are useful conversion cases but are not cleaner than
the installed official 0.6 mm machine JSON. Online downloads are therefore
deferred until a missing case is identified, such as a licensed painted
multi-colour MakerWorld project or a known-good 0.25/0.8 mm S1 print.

Because the user owns every supported nozzle diameter in multiple materials
and several hotend constructions, conversion reports record the exact target
profile and a user-selected hotend/heatbreak label. Filename/profile identity
alone remains insufficient for thermal or flow calibration, so no limit is
inferred from the label.

The two community profile packages are outcome-labelled configuration bundles,
not geometry fixtures. Their internal alternative presets should be exercised
as separate target choices and deduplicated by hash.

## Selection rules

- Record SHA-256, origin URL, author, licence, slicer version, printer/nozzle,
  material, and known print outcome when available.
- Deduplicate identical hashes before analysis.
- Separate `known-good printed`, `opened/sliced only`, `downloaded`, and
  `unknown` outcomes.
- Do not infer S1 safety from filenames or a renamed preset.
- Prefer one minimal case per feature over a large indiscriminate fixture set.
