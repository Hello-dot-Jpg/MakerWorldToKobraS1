# Third-party runtime notices

The application's own source is licensed under MIT (see LICENSE). That licence
does not replace the terms for bundled runtime components or imported profiles.
The Windows portable executable contains unmodified Python 3.13.5, Tcl/Tk
8.6.15, and PyInstaller 6.22.3 bootloader/runtime components.

Preserve this file and the `licenses/` directory when redistributing the ZIP.

- Python and Windows build conditions: `licenses/PYTHON.txt`.
- Python component notices (including OpenSSL, Expat, zlib and other standard
  library components): `licenses/PYTHON-COMPONENTS.html`, from the documentation
  shipped with the build interpreter. The document can be opened in a browser.
- Tcl: `licenses/TCL.txt`, from the matching upstream 8.6.15 source.
- Tk: `licenses/TK.txt`, from the build interpreter's Tk distribution.
- PyInstaller: `licenses/PYINSTALLER.txt`, from the exact build dependency.
  This includes its bootloader exception and Apache-2.0 runtime-hook terms.

The Windows binary also contains Microsoft runtime/distributable components.
The additional Windows build conditions in `licenses/PYTHON.txt` apply to
these components, not to the MIT application source. Redistribution must
retain their notices and comply with those conditions; the included runtime
is for Microsoft Windows only. No endorsement by Microsoft is implied.

Build-only tools are not bundled as separate applications. Local Anycubic,
community and Siddament presets, downloaded models, and third-party research
checkouts are not included. Their respective authors retain their rights.
The converter discovers user-supplied/installed profiles at runtime.

Research provenance and the independent-implementation policy are recorded
in `docs/UPSTREAM_RESEARCH.md`; the project is not a redistributed code fork
of the referenced converters or slicers.

Source references:

- https://www.python.org/downloads/release/python-3135/
- https://docs.python.org/3.13/license.html
- https://github.com/tcltk/tcl/blob/core-8-6-15/license.terms
- https://github.com/tcltk/tk/blob/core-8-6-15/license.terms
- https://github.com/pyinstaller/pyinstaller/blob/v6.22.3/COPYING.txt
