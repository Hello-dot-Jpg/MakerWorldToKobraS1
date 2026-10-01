"""Build a portable Windows beta executable in a new, non-overwriting folder.

Install PyInstaller into an isolated build dependency folder first:
python -m pip install --target .research/exe-build-deps pyinstaller==6.22.3
python tools/build_windows_exe.py --build-deps .research/exe-build-deps
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-deps", type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("Build on Windows for a Windows executable")
    repo = Path(__file__).resolve().parents[1]
    version = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    parent = repo / "dist"
    parent.mkdir(exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix=f"S1Optimizer-{version}-beta-", dir=parent))
    env = {**os.environ, "PYTHONPATH": str(args.build_deps.resolve()),
           "PYTHONNOUSERSITE": "1"}
    name = f"S1Optimizer-{version}-beta"
    command = [sys.executable, "-m", "PyInstaller", "--onefile", "--windowed",
               "--noupx", "--name", name, "--paths", str(repo / "src"),
               "--collect-submodules", "s1_optimizer", "--distpath", str(output),
               "--workpath", str(output / "build"), "--specpath", str(output / "build"),
               str(repo / "tools" / "release_entry.py")]
    with (output / "build.log").open("x", encoding="utf-8") as log:
        subprocess.run(command, cwd=repo, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    executable = output / f"{name}.exe"
    # A different working directory and no PYTHONPATH prevent accidental source imports.
    with tempfile.TemporaryDirectory(prefix="s1-frozen-smoke-") as isolated:
        runtime_env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
        subprocess.run([str(executable), "--smoke-test", str(output / "smoke-test.json")],
                       cwd=isolated, env=runtime_env, timeout=90, check=True)
    evidence = {"version": version, "status": "beta", "signed": False,
                "sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
                "size_bytes": executable.stat().st_size,
                "runtime_smoke": json.loads((output / "smoke-test.json").read_text()),
                "limitations": ["Check Plate Type before slicing; remembered slicer preferences may override it",
                                "Requires local Anycubic profiles for profile discovery",
                                "Not physically calibrated or signed; not published"]}
    with (output / "release-manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(evidence, stream, indent=2)
    shutil.copy2(repo / "README.md", output / "README.md")
    print(executable)


if __name__ == "__main__":
    main()
