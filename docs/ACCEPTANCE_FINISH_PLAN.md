# Efficient remaining acceptance plan

Prepared 2026-09-09. Planning only; unchecked items are not acceptance evidence.
Start with CHECKPOINT.md and observe current native state before input.

## Working rules

- Do local validation first. Reserve desktop calls for actual import, visibility,
  editor, save/reopen and slice behaviour that cannot be established from files.
- Reuse existing fixtures; preserve original downloads and previous evidence.
  Regenerate only cases affected by code changes, to fresh output paths. In
  particular, old exports do not test the latest machine load-time fix.
- Group native cases by nozzle to avoid repeated printer switches. Import each
  necessary batch once and do one restart/persistence audit after that batch.
- Take pre-import hashes. Avoid duplicate imports and overwriting existing
  presets; cleaned engineering replacements need a checked collision strategy.
- User permits discarding known task-generated temporary changes during goal
  work. Protect unrelated unsaved work; do not suppress future warnings globally.
- Never print, change firmware or publish as part of acceptance. Keep effective
  320 C nozzle / 110 C bed limits. Slicing is not physical calibration.
- One low-compute agent may independently audit reports/tests while the main
  agent operates the desktop. No second desktop operator or duplicate reviews.

## Execution order

1. **Prepare one small test manifest locally.** Map each pending feature to its
   existing fixture, expected nozzle/layer/width/material/plate values and exact
   required native check. Include source/output hashes and preservation checks.
   Use MANUAL_ACCEPTANCE.md and ACTIVE_FEATURE_COVERAGE.md; retain prior passes.
   Add one fresh regression artifact for target load/unload/tool-change times.

2. **Finish the 0.6 filament workflow first.** Current recorded slicer state is
   an empty plate, S1 0.6, PC-CF selected; reobserve rather than assuming it.
   Confirm corrected PC-CF editor values, then slice a small single-material
   fixture with PC-CF and PLA-CF. Reuse the fixture for the six engineering
   material families, checking each actual preset and warnings. No mixed-material
   scraper as an engineering acceptance stand-in. Record unsupported cases as
   failures, not silent substitutions.

3. **Test converter GUI and INI in one session.** Start the current converter;
   exercise automatic base, explicit REVIEW base and opt-in material correction.
   Check JSON/ZIP/INI selection and one representative blocked input. Use the
   already-converted real BIBO/Prusament PETG INI fixture. Export to fresh folders,
   inspect the audit, import only needed new presets, then restart once and
   verify persistence plus unchanged pre-existing preset hashes. Resolve any
   cleaned engineering-preset collisions before importing replacements.

4. **Complete the nozzle matrix.** Work through 0.25, 0.4 and 0.8 with the
   existing current-official-*-hs-petg-review.3mf fixtures, retaining 0.6 evidence
   where applicable. For each, check nozzle identity, chosen layer height/width,
   Textured PEI, stock filament list and successful Preview. Include the custom
   community profile path: stock profiles alone do not prove that regression.

5. **Do complex projects together on 0.4.** Cover painted manual supports,
   variable layers, multi-plate coasters, ironing, custom castle reference and
   ASA/ABS with existing fixtures. Inspect all plate metadata locally; slice
   representative distinct plates first, then remaining plates required by the
   manifest. Record the exact tested plate subset; do not claim all-plate slicing
   from one plate. Keep the scraper floating-cantilever warning explicit.

6. **Close out once.** Fix any failures with focused regression tests and rerun
   affected native cases only. Then run the full test suite and release verifier
   once against final source. Reconcile the acceptance matrix and handoff, review
   publishable files/licensing/privacy, and leave GitHub publication deferred.
   A standalone EXE is optional, not a prerequisite for completing beta acceptance.

## Evidence and interruption protocol

After each batch update CHECKPOINT.md with: passed/failed/not-run cases, exact
artifact/report paths, app/project/modal state, unsaved changes, next single
action and any real approval required. Record warnings verbatim where useful.
Save native round-trips under new names and compare metadata/archive contents.
Do not repeat a completed batch after an interruption unless source changed.

Final handoff separates automated checks, native acceptance, user-confirmed
prints and uncalibrated REVIEW presets. User-only remaining items are physical
material/nozzle calibration and publication name/visibility/licence decisions.
