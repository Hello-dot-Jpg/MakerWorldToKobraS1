# Using the Kobra S1 Optimizer

You give it a 3MF file. It makes a new copy set up for your Kobra S1.
Your original file stays as it is. You still slice and print with Anycubic
Slicer Next as usual.

## Run the Windows executable

1. On this GitHub page, click **Releases**, then **0.4.1 beta**.
2. Under **Assets**, click `S1Optimizer-0.4.1-beta-windows-x64.zip`.
   Ignore the two downloads called **Source code**; those are not the app.
3. Right-click the downloaded ZIP, choose **Extract All**, and open the extracted
   folder. Keep its licence files with the app.
4. Double-click `S1Optimizer-0.4.1-beta.exe`.

You do not need Python or an installer. The app is unsigned; follow your normal
Windows security policy if Windows displays a warning. Install and set up
Anycubic Slicer Next on the same PC first, so the app can find its S1 profiles.
This app does not start prints, change firmware or send models to a printer.

## The normal job: convert a file

You do not need to understand every setting. Start with these steps:

1. Click **Browse 3MF…** and choose the file you downloaded.
2. Pick the **Nozzle size (mm)** that is actually in your printer. For example,
   choose **0.4** for a 0.4 mm nozzle. Under **Nozzle material**, choose
   **hardened-steel** if that is what you have fitted.
3. Click **Discover matching profiles** and wait for it to finish. A profile
   is just a saved set of print settings. Check **Printer profile** says Kobra
   S1 with your nozzle size. Choose the **Print profile** you want to use.
4. Under **Filament assignments**, choose what you are printing with, such as
   PLA or PETG. If there is more than one row, check each row.
5. Leave the extra options alone for your first conversion. Click
   **Review changes** and read the messages on the right. If it says something
   is blocked, stop; do not guess a way around it.
6. Click **Choose output…** to pick where the new file goes, then
   **Export 3MF**. Give it a new name, such as `my_model_S1.3mf`.
7. Open that new file in Anycubic Slicer Next. Check the nozzle, filament and
   **Plate Type**, then slice. Look at **Preview** before printing.

**Check the plate every time.** For the normal textured plate, it should say
**Textured PEI Plate** in Anycubic. The slicer sometimes switches it back to
your last-used plate, even though the converter requested PEI.

That is the basic workflow. The sections below are only for extra choices.

## More options and things to check

Use the project-converter tab. The settings area on the left scrolls; the source
summary, change report and export controls remain on the right.

1. **Open your file.** Click **Browse 3MF…** and select the original project.
   Alternatively, paste its full path into the source box and press **Enter**.
   Check **Original project** for the source nozzle, layer height and materials.
   Loading another file resets the conversion settings; recheck your choices.
2. **Choose your setup.** Select your physical **Nozzle size (mm)** and
   **Nozzle material**, then click **Discover matching profiles**. Check the
   suggested printer and print profile. Select a community profile if you have
   it available; selecting hardened steel alone does not install or create a
   community-tuned preset. Expand the community-bundle section to add a profile
   3MF you obtained separately, then discover again.
3. **Check filaments.** Assign a compatible filament to each source slot.
   Each row is one filament/colour in the original file. Choose the material
   you will actually print, not just a similarly named preset.
4. **Choose optional changes.**
   - Layer height stays as in the source by default. Tick **Use print profile's
     layer height** to adopt the selected profile's height, or enter a custom
     height in mm. Clear a custom height when you no longer want it.
   - **Plate Type** defaults to **Textured PEI Plate**; choose another if needed.
   - **Nice supports - beta** applies the reviewed support overlay. It is off
     by default; inspect supports in the slicer's Preview.
   - **Scale to fit S1 plate** shrinks oversized plates only. It changes part
     dimensions, so leave it off for parts whose size must stay exact.
   - Advanced hotend settings record the hardware choice. Only enter a
     temperature ceiling you have confirmed for your hardware and firmware.
5. Click **Review changes**. Read warnings and any blockers in the report.
   Review does not create a converted project or modify installed presets.
6. Check the output path or click **Choose output…**, then **Export 3MF**.
   The app creates a new project and a change report. It never overwrites your
   source or an existing output; choose a new filename if one already exists.
7. Open the new file in Anycubic Slicer Next. Confirm the printer, nozzle,
   process height, materials and colour assignments. Check every plate you
   intend to print, slice it, and inspect supports, prime tower and toolpaths
   in Preview before printing.

**Important plate warning:** Anycubic may restore its remembered plate choice
instead of the exported choice. Always check **Plate Type** in the slicer and
the resulting bed temperature. The converter's warning is not a fix for this
slicer behavior.

The exported `[Optimized]` process is project-local. The original process is
kept as a reference for comparison, not as a safe selectable S1 print preset.
Successful conversion or slicing is not physical material calibration.

## Import standalone filament presets

Use **Filament library · beta**. This is separate from assigning filaments in
a converted 3MF; it does not change a 3MF's assignments.

1. Obtain the filament presets separately (for example, from Siddament).
   Add them with **JSON files…**, **Folder…**, **Bundle…** or **INI file…**.
   All added presets are initially selected; Ctrl/Shift changes the selection.
2. Click **Find installed S1 printers**. Select the destination nozzle size(s)
   with Ctrl/Shift, then choose nozzle material and hotend.
3. Confirm **Nozzle ceiling (°C)** and **Bed ceiling (°C)** for your actual
   setup. Do not copy another person's hardware limits blindly. The firmware
   confirmation option is only for a change you have already made; this app
   never changes firmware. Unknown limits or unmatched material bases can
   block export.
4. Click **Review selected presets**, read the warnings, and then
   **Export presets…** to create a new folder of reviewed JSON/ZIP presets.
   These are starting settings: you will still need to test and tune them
   for your filament.
5. To install with the app, **close Anycubic Slicer Next first**. Expand the
   install/restore section, click **Install reviewed export…**, select the
   reviewed export and read the confirmation. Installation checks collisions
   and creates an active-account filament backup. Keep the installation
   record file (`install-manifest.json`) and backup folder so you can undo it.
6. Alternatively, import `importable-presets.zip` or the individual JSONs via
   Anycubic's **Import Configs** command. This manual method is not covered by
   the app's installation rollback.
7. Restart the slicer and check the new profiles under each intended nozzle.
   Check the temperatures and material are right before use. Test a small
   print before trusting a new filament's settings on a long print.

To undo an app-managed installation, close the slicer, choose
**Restore an installation…** and select its installation manifest. Read the
confirmation and result; rollback is quarantined and may refuse unsafe
collisions or changed files. Do not manually overwrite live preset folders.

## If something does not work

- **No profiles found:** set up an S1 printer in Anycubic Slicer Next, then
  retry discovery. A community bundle does not replace the required installed
  machine/process/filament directories.
- **A part is outside the bed:** inspect the report. Use scale-to-fit only if
  changing dimensions is acceptable; otherwise rearrange/split the project.
- **Export blocked or an unexpected slicer warning:** stop and read the exact
  message. Do not approve unexplained machine G-code or raise temperature
  limits just to make the warning disappear.
- **Want to report a bug:** include the app version, chosen nozzle/profile,
  exact message and change report. Remove private paths or settings first;
  do not upload someone else's model without permission.

For source users with Python 3.11+, double-click `run_gui.cmd` from the cloned
repository. CLI/setup details are in [README.md](README.md) and
[docs/USAGE.md](docs/USAGE.md).
