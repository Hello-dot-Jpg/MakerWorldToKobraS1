"""Package an already verified executable with user instructions and notices.

Creates a new directory and does not modify or rebuild the input executable.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import tomllib
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build", type=Path, help="Verified build directory")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    version = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    name = f"S1Optimizer-{version}-beta"
    executable = args.build / f"{name}.exe"
    manifest = json.loads((args.build / "release-manifest.json").read_text(encoding="utf-8"))
    digest = hashlib.sha256(executable.read_bytes()).hexdigest()
    if (manifest["version"] != version or manifest["sha256"] != digest
            or manifest["size_bytes"] != executable.stat().st_size
            or manifest["runtime_smoke"]["status"] != "passed"):
        raise SystemExit("Build manifest/hash/runtime verification failed")
    # Publication changes distribution status, not the original verification evidence.
    manifest["limitations"] = [entry.replace("; not published", "")
                               for entry in manifest["limitations"]]
    parent = repo / "dist"
    parent.mkdir(exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix=f"publish-{version}-", dir=parent))
    archive = output / f"{name}-windows-x64.zip"
    notices = sorted((repo / "licenses").glob("*"))
    if not notices or any(not path.is_file() for path in notices):
        raise SystemExit("Runtime license files missing or invalid")
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.write(executable, executable.name)
        for filename in ("README.md", "USING_THE_APP.md", "LICENSE", "THIRD_PARTY_NOTICES.md"):
            bundle.write(repo / filename, filename)
        for path in notices:
            bundle.write(path, f"licenses/{path.name}")
        # Include the public documentation linked from README/user instructions.
        # The machine-specific operational checkpoint is deliberately local-only.
        for path in sorted((repo / "docs").glob("*.md")):
            if path.name != "CHECKPOINT.md":
                bundle.write(path, f"docs/{path.name}")
        bundle.write(repo / "docs" / f"RELEASE_NOTES_{version}.md", "RELEASE_NOTES.md")
        bundle.writestr("release-manifest.json", json.dumps(manifest, indent=2) + "\n")
    with zipfile.ZipFile(archive) as bundle:
        if bundle.testzip() is not None:
            raise SystemExit("Release ZIP CRC verification failed")
        if hashlib.sha256(bundle.read(executable.name)).hexdigest() != digest:
            raise SystemExit("Packaged executable hash differs from verified build")
    archive_digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksums = f"{archive_digest}  {archive.name}\n{digest}  {executable.name}\n"
    (output / "SHA256SUMS.txt").write_text(checksums, encoding="utf-8")
    print(output)
    print(checksums, end="")


if __name__ == "__main__":
    main()
