"""Save a non-overwriting hash inventory before native preset import."""
import argparse
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("installed", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
if not args.installed.is_dir():
    parser.error("Installed preset directory is missing")
hashes = {}
paths = [*args.installed.glob("*.json"), *(args.installed / "base").glob("*.json")]
for path in sorted(paths):
    with path.open("rb") as stream:
        hashes[path.relative_to(args.installed).as_posix()] = hashlib.file_digest(stream, "sha256").hexdigest()
with args.output.open("x", encoding="utf-8") as stream:
    json.dump(hashes, stream, indent=2)
print(f"Recorded {len(hashes)} preset hashes; no installed files changed")
