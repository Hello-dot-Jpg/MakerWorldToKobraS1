# Local Anycubic Slicer reference

Inspection date: 2026-09-04. This is a read-only snapshot of the locally
installed Anycubic Slicer Next resources. No application preferences, profiles,
or printer/cloud state were changed.

## Installation

- Executable: `C:\Program Files\AnycubicSlicerNext\AnycubicSlicerNext.exe`
- File/product version: `2.0.0.2`
- Build marker: `20260902193307`
- Bundled profiles:
  `C:\Program Files\AnycubicSlicerNext\resources\profiles`
- OTA profile cache:
  `C:\Users\USER\AppData\Roaming\AnycubicSlicerNext\ota\profiles`

The bundled and OTA-cache Kobra S1 machine files had identical SHA-256 hashes
at inspection time.

## Official Kobra S1 nozzle variants

| Nozzle | Default process | Machine profile SHA-256 |
|---:|---|---|
| 0.25 mm | `0.08mm Standard @Anycubic Kobra S1 0.25 nozzle` | `F53DC4578BA841C980EDFEE89515D4EDEF1CEE555BBB96FDA2816AF45D4D3C21` |
| 0.4 mm | `0.20mm Standard @Anycubic Kobra S1 0.4 nozzle` | `EE017EE3C2398FB9F0F3DA48ED0B1762D1ECE77A4190AF49089AFC599EE090DC` |
| 0.6 mm | `0.30mm Standard @Anycubic Kobra S1 0.6 nozzle` | `2A7A7A43808A18E67B9B375032C4BE86ADBEF582A130BCA3CFCCF99063EE2535` |
| 0.8 mm | `0.40mm Standard @Anycubic Kobra S1 0.8 nozzle` | `5E24E3EACFE17B5F6DA793D3E66995D1E61FBC17FC00900F2F0E7F6091BAB903` |

All four identify `Anycubic Kobra S1`, use setting ID `GM001`, Klipper G-code,
a 250 x 250 x 250 mm printable volume, and profile version `1.3.2512.26`.
They are not interchangeable: nozzle-specific differences include layer-height
ranges, retraction, default process/filament selection, and—in the 0.25 mm
profile—additional motion limits. The implemented target loader selects the
exact nozzle variant rather than scaling the 0.4 mm profile.

The installed profiles label 0.25 and 0.4 mm as brass, and 0.6 and 0.8 mm as
hardened steel. All report `nozzle_hrc = 0`; this field cannot be treated as a
reliable material-hardness measurement. The profiles do not encode whether the
physical hotend is PTFE-lined, all-metal, or an aftermarket ceramic assembly.

## User hardware inventory

The user reports owning 0.25, 0.4, 0.6, and 0.8 mm nozzles in both common
material variants, plus bimetal hardware. They also own:

- the early hotend with PTFE in its upper section;
- the later all-metal hotend;
- an aftermarket ceramic hotend.

Hardened-steel nozzles are used most often across the hotends. Consequently,
the installed preset name alone cannot identify the actual target hardware.
Nozzle diameter, nozzle material, and hotend construction must be explicit,
independent selections in the optimizer.

## Known-good community 0.4 mm hardened-steel overlay

The user confirmed that the community
`Anycubic Kobra S1 0.4 nozzle Hardened Steel -` profile works very well. Its
current local machine JSON has SHA-256
`CB31A97B2ED023D43A62B4010B8203B77AEAA54A6152B63EF1165546D9E07613`.

This is a thin seven-key user overlay, not an independent copied machine
definition. It inherits `Anycubic Kobra S1 0.4 nozzle` and changes:

- source/identity fields;
- `nozzle_type` from brass to hardened steel;
- the default process to `0.28mm ExtraDraft @AC KS1`.

Machine limits, printable volume, and Kobra-specific G-code continue to come
from the official installed 0.4 mm profile. The associated community process
set contains selective inherited profiles from 0.08 through 0.28 mm. The
known-good castle used its 0.28 mm ExtraDraft process.

No equivalent community machine overlays were found locally for 0.25, 0.6, or
0.8 mm in the slicer's saved-user directory. The separately downloaded V2
profile-bundle 3MF does contain user-validated community overlays for those
sizes, documented in `COMMUNITY_PROFILES.md`. Their source declaration inherits
the 0.4 mm machine, but exported compatibility variants now link the unchanged
community leaf overlay to the matching-diameter official parent. That deliberate
rebase is shown in the plan/report and still needs installed-slicer acceptance.

## Three-entry machine limits

Every current Kobra S1 nozzle profile contains three entries for machine-limit
arrays. For example, X/Y maximum speed is `600, 300, 780`; the 0.4/0.6/0.8 mm
Z maximum is `15, 7.5, 19.5` and X/Y maximum acceleration is
`20000, 20000, 20000`.

The reviewed public slicer source exposes Normal and Stealth estimator modes,
but does not explain the third current profile entry. The application must:

- preserve these arrays without a schema warning;
- source the whole array from the exact installed/reference machine profile;
- avoid selecting or transforming one array position based on an assumed mode.

## Castle cross-check

The known-good printed `迪士尼小城堡-Sumee1798.3mf` project exactly matches the
installed 0.4 mm profile for printer model, G-code flavour, nozzle diameter,
printable area/height, sampled machine speed/acceleration arrays, and the full
start, end, before-layer, and filament-change G-code strings.

Its intentional differences are the custom hardened-steel nozzle type and
printer preset ID. This makes it good evidence that the project contains a
genuine current S1 machine snapshot rather than a merely renamed foreign
profile.

## Default 3MF exports

No separate slicer CLI or documented headless project-export command was found.
Native GUI control was unavailable in this Codex environment, so empty default
3MF projects were not fabricated. They are not required for machine defaults:
the versioned installed JSON profiles are more direct and can later be loaded
read-only. GUI exports may still be useful for testing project serialization
once native app control is available.
