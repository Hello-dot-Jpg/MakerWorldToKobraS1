# Local release verification

## 2026-09-24 rerun - PASS

Python 3.13 `tools/verify_release.py` passed at
`reports/release-check-gbc2c8fx/verification.json`. The two independent wheels
were byte-identical (SHA-256
`d0a3af331bf49955d2efedd8ade5478a2dfee4e31c437e885665733b1c70bbba`),
and isolated package-origin, GUI imports and installed CLI help passed. The
documented `unittest discover` command passes 185 tests. No package was
published or installed into the user's Python environment. Native slicer
acceptance remains incomplete.

## Python 3.12 rerun - PASS (2026-09-15)

The bundled offline dependencies also pass under Python 3.12 at
`reports/release-check-xotwvj3v/verification.json`, including independent
wheel reproducibility, isolated package origin, GUI imports and CLI help.


## 2026-09-15 rerun - PASS

Using the repository-bundled offline dependencies in `.research/build-deps`,
`tools/verify_release.py` passed at
`reports/release-check-pr83cf7w/verification.json`. It confirmed
byte-identical independent wheels, isolated package origin, GUI imports and
CLI help. Wheel SHA-256:
`0fba86d57c48925f7a1e369b8a54805b4c22e552d0b32e1022d710f83ce3f38f`.

No publishing or global installation is performed. Python 3.11+ with Tk is
required to run the GUI; this wheel is not a standalone Windows executable.

Prepare local build dependencies (once, network access required):

```powershell
python -m pip install --target .research/build-deps setuptools==84.0.0 wheel==0.48.0 packaging==26.3
```

Run tests, then verify the package:

```powershell
python -m unittest discover -s tests
python tools/verify_release.py reports --build-deps .research/build-deps
```

The verifier builds from two separate temporary copies with a fixed archive
timestamp, compares SHA-256 hashes, checks wheel contents, installs into a
temporary target, confirms the imported package originates there and tests
CLI help and GUI module imports. It records tool versions and results in a
new `reports/release-check-*/verification.json`, retaining both wheels.
Temporary staging/installation directories are cleaned up automatically.

Builds are offline after dependency preparation. Byte-identical builds prove
reproducibility in the recorded environment, not across arbitrary tool versions
or operating systems. Module import is not GUI visual acceptance. This check
does not replace native slicing, calibration, licensing or publication review.

Only package source, README and project metadata enter build staging. Local
models, presets, research and acceptance reports are excluded. The wheel member
list is recorded for review. Keep GitHub publication deferred until the user
chooses visibility/name/licence and the remaining acceptance work is complete.
