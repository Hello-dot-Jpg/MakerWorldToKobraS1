# 0.4.1 beta

First public beta of the Kobra S1 project optimizer. Windows x64 portable
executable; unsigned, no installer, no automatic updates. Application source
is MIT-licensed. Not affiliated with Anycubic, Bambu Lab or MakerWorld.

## Included

- Safe 3MF inspection, review and no-overwrite conversion using locally
  discovered Kobra S1 machine, nozzle, process and filament profiles.
- Source settings overview, source layer-height preservation, optional custom
  height, and truthful `[Optimized]` project-local process identity.
- Original process reference retained for comparison, not a printable S1 preset.
- Multi-plate placement reconciliation and opt-in scale-to-fit (changes dimensions).
- Textured PEI default with an editable plate selector and explicit warning.
- Optional Nice supports beta overlay; painting, modifiers and colour slots preserved.
- Separate filament-preset batch conversion, reviewed installation, collision
  protection, backup and quarantined rollback while the slicer is closed.
- Refreshed charcoal/blue interface, numbered workflows, collapsible advanced
  options, source/review panels and fixed converter export controls.

## Verification and limits

216 automated tests passed before publication. Package verification, frozen
runtime initialization, source loading, discovery and scrolling passed.
Representative engine outputs passed native Anycubic open/slice checks; this
does not mean every plate, material, profile or user file was tested.

**Known issue:** Anycubic can restore its remembered plate preference instead
of the exported Textured PEI default. Check the displayed Plate Type and its
material temperature manually before slicing. The beta warning is an accepted
mitigation, not a fix for automatic plate selection.

Always review temperatures, machine/nozzle identity, colour assignments,
supports, prime tower and toolpaths in Preview. Physical calibration and safe
hardware/firmware limits are not established by a successful conversion.
No printer upload, firmware modification or print initiation is included.

The verified executable is 12,922,434 bytes. SHA-256:

```text
3a03473a1edca37d2d2b02adcf10e523a9ae677e58529930835def6fb13eda70
```

Model files, private slicer presets, local reports and upstream research
checkouts are not distributed. Community/Siddament presets must be obtained
separately by the user; their licences are not replaced by this project's MIT
licence. See [upstream research](UPSTREAM_RESEARCH.md).
