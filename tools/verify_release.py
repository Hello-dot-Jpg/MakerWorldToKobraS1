"""Build twice offline, compare wheels, and smoke-test an isolated installation.

Requires local pip, setuptools and wheel. Creates only a new report directory;
does not install into the active interpreter or publish anything.
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
import zipfile


def run(command, cwd, env):
    result = subprocess.run(command, cwd=cwd, env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f"Command failed: {command!r}\n{result.stdout}")
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_parent", type=Path)
    parser.add_argument("--build-deps", type=Path, help="Optional local pip --target build dependencies")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    args.output_parent.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="release-check-", dir=args.output_parent.resolve()))
    evidence = {"status": "incomplete", "python": sys.version, "checks": []}
    try:
        env = {**os.environ, "SOURCE_DATE_EPOCH": "1704067200", "PYTHONHASHSEED": "0",
               "PIP_NO_INDEX": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1"}
        env.pop("PYTHONPATH", None)
        if args.build_deps:
            env["PYTHONPATH"] = str(args.build_deps.resolve())
        evidence["build_tools"] = run([sys.executable, "-c",
            "import setuptools,wheel; print('setuptools='+setuptools.__version__+' wheel='+wheel.__version__)"], repo, env).strip()
        wheels = []
        with tempfile.TemporaryDirectory(prefix="s1-release-") as temporary:
            work = Path(temporary)
            for index in range(2):
                stage = work / f"source-{index}"
                stage.mkdir()
                for name in ("pyproject.toml", "README.md", "LICENSE"):
                    shutil.copy2(repo / name, stage / name)
                shutil.copytree(repo / "src", stage / "src",
                                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info"))
                destination = output / f"build-{index}"
                run([sys.executable, "-m", "pip", "wheel", ".", "--no-deps",
                     "--no-build-isolation", "--no-index", "--wheel-dir", str(destination)], stage, env)
                found = list(destination.glob("*.whl"))
                if len(found) != 1:
                    raise RuntimeError("Expected exactly one built wheel")
                wheels.append(found[0])
            hashes = [hashlib.sha256(w.read_bytes()).hexdigest() for w in wheels]
            evidence["wheel_sha256"] = hashes
            if hashes[0] != hashes[1]:
                raise RuntimeError("Independent wheel builds differ")
            evidence["checks"].append("byte-identical independent wheel builds")
            with zipfile.ZipFile(wheels[0]) as archive:
                members = archive.namelist()
                if archive.testzip() is not None or any(not (
                    name.startswith("s1_optimizer/") or ".dist-info/" in name
                ) for name in members):
                    raise RuntimeError("Unexpected or corrupt package members")
                evidence["wheel_members"] = members
            installed = work / "installed"
            run([sys.executable, "-m", "pip", "install", "--no-deps", "--no-index",
                 "--target", str(installed), str(wheels[0])], work, env)
            isolated = {**env, "PYTHONPATH": str(installed), "PYTHONNOUSERSITE": "1"}
            probe = "import pathlib,s1_optimizer; p=pathlib.Path(s1_optimizer.__file__).resolve(); assert p.is_relative_to(pathlib.Path(__import__('sys').argv[1]).resolve()),p; import s1_optimizer.gui,s1_optimizer.preset_gui; print('isolated package and GUI imports OK')"
            run([sys.executable, "-c", probe, str(installed)], work, isolated)
            help_text = run([sys.executable, "-m", "s1_optimizer", "--help"], work, isolated)
            if "optimize" not in help_text or "inspect" not in help_text:
                raise RuntimeError("Installed CLI help is incomplete")
            evidence["checks"].extend(["isolated package origin", "GUI module imports", "installed CLI help"])
        evidence["status"] = "passed"
    except Exception as exc:
        evidence["error"] = str(exc)
    with (output / "verification.json").open("x", encoding="utf-8") as stream:
        json.dump(evidence, stream, indent=2)
    print(f"{evidence['status']}: {output}")
    return int(evidence["status"] != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
