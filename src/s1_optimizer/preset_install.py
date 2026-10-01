"""Opt-in, collision-safe installation of reviewed standalone filament presets.

The active Anycubic account is read from its configuration; neither the default
account nor the first directory found is silently selected. Keep the slicer
closed: it can rewrite preset files while running.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

from .errors import PlanError


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def slicer_running() -> bool:
    if os.name != "nt":
        return False
    try:
        import subprocess
        result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq AnycubicSlicerNext.exe", "/FO", "CSV", "/NH"],
                                capture_output=True, text=True, check=True)
        return "AnycubicSlicerNext.exe" in result.stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise PlanError("Cannot confirm Anycubic Slicer Next is closed") from exc


def active_filament_store(appdata: Path | None = None) -> Path:
    root = Path(appdata or os.environ["APPDATA"]).resolve() / "AnycubicSlicerNext"
    config = root / "AnycubicSlicerNext.conf"
    try:
        raw = config.read_text(encoding="utf-8")
        settings, end = json.JSONDecoder().raw_decode(raw)
        if not re.fullmatch(r"\s*(?:# MD5 checksum [0-9A-Fa-f]{32}\s*)?", raw[end:]):
            raise ValueError("Unexpected trailing slicer configuration data")
    except (OSError, ValueError) as exc:
        raise PlanError(f"Cannot read Anycubic configuration: {config}") from exc
    # Current app versions put this setting in the app section.
    account = settings.get("app", {}).get("preset_folder")
    if not isinstance(account, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", account) or account == "default":
        raise PlanError("No unique active Anycubic account preset folder in configuration")
    store = (root / "user" / account / "filament").resolve()
    if not store.is_dir() or store.parent.parent != (root / "user").resolve():
        raise PlanError(f"Active filament folder does not exist: {store}")
    return store


def _read_candidates(folder: Path) -> list[tuple[str, Path, str]]:
    found = []
    for source in sorted(folder.glob("S1_*.json")):
        try:
            raw = source.read_bytes()
            data = json.loads(raw)
        except (OSError, ValueError) as exc:
            raise PlanError(f"Invalid preset JSON: {source}") from exc
        name = data.get("name")
        if (not isinstance(name, str) or not name or name.strip(" .") != name
                or any(c in name for c in '<>:"/\\|?*\x00\x7f')
                or any(ord(c) < 32 for c in name)):
            raise PlanError(f"Unsafe Anycubic preset name in {source}")
        if (data.get("type") != "filament" or data.get("from") != "User"
                or data.get("inherits") != "" or str(data.get("is_custom_defined")) != "1"
                or data.get("filament_settings_id") != [name]
                or not data.get("compatible_printers")
                or not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", str(data.get("version", "")))):
            raise PlanError(f"Not a detached reviewed filament preset: {source}")
        found.append((name, source, hashlib.sha256(raw).hexdigest()))
    if not found:
        raise PlanError("No reviewed filament JSON files in selected export folder")
    names = [item[0].casefold() for item in found]
    if len(set(names)) != len(names):
        raise PlanError("Duplicate destination preset identities")
    return found


def _existing_names(store: Path) -> set[str]:
    # Anycubic loads filament/base before the top-level user presets. A name
    # already present there silently shadows an otherwise successful install.
    return {p.stem.casefold() for folder in (store / "base", store) if folder.is_dir()
            for p in folder.iterdir() if p.is_file() and p.suffix.lower() in {".json", ".info"}}


def install_export(folder: Path, backup_parent: Path, *, store: Path | None = None) -> Path:
    return install_exports([folder], backup_parent, store=store)


def install_exports(folders: list[Path], backup_parent: Path, *, store: Path | None = None) -> Path:
    """Install reviewed exports, never overwriting an existing JSON or info.

    Returns a manifest path. If an installation write fails, only files this
    invocation created are removed; the complete pre-install backup remains.
    """
    if slicer_running():
        raise PlanError("Close Anycubic Slicer Next before installing presets")
    store = Path(store).resolve() if store else active_filament_store()
    if not store.is_dir():
        raise PlanError("Destination filament folder does not exist")
    candidates = [item for folder in folders for item in _read_candidates(Path(folder).resolve())]
    if len({name.casefold() for name, _, _ in candidates}) != len(candidates):
        raise PlanError("Duplicate destination identities across selected exports")
    collisions = _existing_names(store) & {name.casefold() for name, _, _ in candidates}
    if collisions:
        raise PlanError(f"Existing preset collision; no files installed: {', '.join(sorted(collisions))}")
    backup_parent = Path(backup_parent).resolve()
    if not backup_parent.is_dir() or backup_parent == store or backup_parent.is_relative_to(store):
        raise PlanError("Choose an existing backup folder outside the live filament store")
    backup = Path(tempfile.mkdtemp(prefix="S1-preset-backup-", dir=backup_parent))
    original = backup / "original-filament"
    shutil.copytree(store, original)
    manifest = {"schema": 1, "store": str(store), "backup": str(original),
                "before": {str(p.relative_to(store)): _sha(p) for p in store.rglob("*") if p.is_file()},
                "installed": [], "status": "installing"}
    manifest_path = backup / "install-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    created: list[Path] = []
    try:
        for name, source, digest in candidates:
            destination = store / (name + ".json")
            payload = source.read_bytes()
            if hashlib.sha256(payload).hexdigest() != digest:
                raise PlanError(f"Source changed after review: {source}")
            with destination.open("xb") as stream:
                stream.write(payload)
            created.append(destination)
            manifest["installed"].append({"name": name, "source": str(source),
                                           "source_sha256": digest, "file": destination.name,
                                           "installed_sha256": _sha(destination)})
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        manifest["status"] = "installed"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    except Exception:
        for path in created:
            if path.is_file() and path.name not in manifest["before"]:
                path.unlink()
        manifest["status"] = "failed-rolled-back"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        raise
    return manifest_path


def rollback_install(manifest_path: Path, *, preserve_modified: bool = False) -> Path:
    """Move this install's presets aside, preserving any changed files in quarantine.

    Modified presets require explicit opt-in, since the user may have tuned them
    since installation. Nothing is permanently deleted.
    """
    if slicer_running():
        raise PlanError("Close Anycubic Slicer Next before rolling back presets")
    manifest_path = Path(manifest_path).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != 1 or manifest.get("status") != "installed":
        raise PlanError("Manifest does not describe an active installation")
    store = Path(manifest["store"]).resolve()
    if store != active_filament_store():
        raise PlanError("Active Anycubic account changed; refusing rollback")
    entries = manifest["installed"]
    if not entries or len({e["file"].casefold() for e in entries}) != len(entries):
        raise PlanError("Invalid rollback manifest")
    for entry in entries:
        path = store / entry["file"]
        if (path.parent != store or not path.is_file()
                or path.stem != entry["name"]
                or entry["file"] in manifest["before"]):
            raise PlanError(f"Installed preset changed or missing; rollback stopped: {entry['file']}")
        if not preserve_modified and _sha(path) != entry["installed_sha256"]:
            raise PlanError(f"Installed preset changed since install; rollback stopped: {entry['file']}")
    quarantine = manifest_path.parent / "rolled-back-files"
    quarantine.mkdir(exist_ok=False)
    for entry in entries:
        path = store / entry["file"]
        shutil.move(str(path), str(quarantine / path.name))
        info = path.with_suffix(".info")
        if info.is_file() and info.name not in manifest["before"]:
            shutil.move(str(info), str(quarantine / info.name))
    manifest["status"] = "rolled-back"
    manifest["quarantine"] = str(quarantine)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return quarantine
