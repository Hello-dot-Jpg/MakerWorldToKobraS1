from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import BinaryIO
import zipfile

from .archive import ThreeMFArchive
from .constants import MAX_STRUCTURED_MEMBER_BYTES
from .errors import PlanError
from .parser import decode_json, inspect_archive
from .plan import (
    ArchiveAction, ConversionPlan, _PROFILE_METADATA_KEYS,
    _is_filament_translate_key,
    _is_machine_replace_key,
)
from .plates import clear_plate_bed_types
from .plate_layout import relocate_build_items, stream_relocate_build_items


@dataclass(frozen=True, slots=True)
class WriteResult:
    output_path: str
    source_sha256: str
    output_sha256: str
    changed_members: tuple[str, ...]
    unchanged_members_verified: int
    structure_counts: dict[str, int]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _file_sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest().upper()


def _stream_sha256(stream: BinaryIO) -> str:
    digest = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(block)
    return digest.hexdigest().upper()


def _member_hashes(path: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    with zipfile.ZipFile(path, "r") as archive:
        for info in archive.infolist():
            if info.filename in hashes:
                raise PlanError(f"Refusing duplicate archive member: {info.filename}")
            with archive.open(info, "r") as stream:
                hashes[info.filename] = _stream_sha256(stream)
    return hashes


def _serialized_project(raw: bytes, project: dict[str, object]) -> bytes:
    has_bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    newline = "\r\n" if "\r\n" in text else "\n"
    trailing_newline = text.endswith(("\r", "\n"))
    rendered = json.dumps(project, ensure_ascii=False, indent=4)
    if newline != "\n":
        rendered = rendered.replace("\n", newline)
    if trailing_newline:
        rendered += newline
    encoded = rendered.encode("utf-8")
    return (b"\xef\xbb\xbf" + encoded) if has_bom else encoded


def _apply_plan(raw: bytes, plan: ConversionPlan) -> bytes:
    try:
        value = decode_json(raw)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise PlanError(f"Cannot parse project settings while writing: {exc}") from exc
    if not isinstance(value, dict):
        raise PlanError("project_settings.config root must be a JSON object")
    for action in plan.actions:
        if action.action not in {"REPLACE", "CLAMP", "TRANSLATE"}:
            raise PlanError(f"Unsupported write action: {action.action}")
        if action.setting_was_present:
            if action.setting_name not in value:
                raise PlanError(
                    f"Planned setting disappeared before writing: {action.setting_name}"
                )
            if value[action.setting_name] != action.old_value:
                raise PlanError(
                    f"Planned old value no longer matches: {action.setting_name}"
                )
        elif action.setting_name in value:
            raise PlanError(
                f"Planned new setting unexpectedly appeared before writing: "
                f"{action.setting_name}"
            )
        value[action.setting_name] = action.new_value
    return _serialized_project(raw, value)


_PROCESS_ARCHIVE_METADATA_EXCLUSIONS = _PROFILE_METADATA_KEYS | {
    "compatible_machine_expression_group",
    "compatible_process_expression_group",
    "curr_bed_type",
    "different_settings_to_system",
    "inherits_group",
    "print_compatible_printers",
}


def _is_private_or_host_key(name: str) -> bool:
    lowered = name.casefold()
    return any(part in lowered for part in (
        "host", "password", "api_key", "apikey", "secret", "token",
    ))


def _embedded_optimized_process(project: dict[str, object], plan: ConversionPlan) -> bytes:
    """Make the selected project process a real, project-local preset.

    The flattened project remains authoritative, but Anycubic also needs a
    matching embedded process identity to avoid showing these settings as an
    unsaved modification of the installed system process.
    """
    process = plan.process
    label = plan.effective_process_label
    if process is None or not label or project.get("print_settings_id") != label:
        raise PlanError("Cannot embed a process without its matching project identity")
    parent = (
        process.process.label if process.process.source_kind == "official"
        else process.process.inherits or ""
    )
    profile: dict[str, object] = {
        "type": "process",
        "from": "project",
        "name": label,
        "print_settings_id": label,
        "inherits": parent,
        "compatible_printers": list(dict.fromkeys((
            plan.effective_machine_label, plan.target.target.label,
        ))),
    }
    version = process.effective_values.get("version")
    if isinstance(version, str):
        profile["version"] = version
    # The flattened project may contain hundreds of Bambu/vendor fields that
    # are not process settings. Its difference mask is not a scope schema.
    # Only keys recognized by the selected resolved process belong in a
    # selectable process preset; the full source remains in the inert
    # original reference and the flattened project.
    names = set(process.effective_values)
    # This is a recognized process-only Anycubic setting even when the
    # selected stock process inherits its default from the slicer schema.
    # Include the preserved source value in this project-local preset so the
    # flattened project does not dirty it immediately on load.
    # Reviewed Anycubic PrintConfig process fields can be absent from an
    # installed JSON because their defaults come from the slicer schema.
    # Keep these source overrides in the embedded preset as well, otherwise
    # the flattened project immediately dirties that preset on native load.
    names.update({
        "ironing_direction", "ironing_inset", "skeleton_infill_density",
        "skeleton_infill_line_width", "skin_infill_density",
        "skin_infill_line_width", "skin_infill_depth",
        "support_ironing", "support_ironing_pattern", "support_ironing_flow",
        "support_ironing_spacing", "filename_format",
    } & project.keys())
    for name in sorted(names):
        if (name in _PROCESS_ARCHIVE_METADATA_EXCLUSIONS
                or _is_private_or_host_key(name)
                or name.startswith(("filament_", "machine_", "printer_", "extruder_"))
                or _is_machine_replace_key(name)
                or _is_filament_translate_key(name) or name not in project):
            continue
        profile[name] = project[name]
    return (json.dumps(profile, ensure_ascii=False, indent=4) + "\n").encode("utf-8")


def _original_process_reference(project: dict[str, object], plan: ConversionPlan) -> bytes:
    """Keep source process values inspectable without making them print-selectable."""
    settings = {
        name: value for name, value in project.items()
        if name not in _PROCESS_ARCHIVE_METADATA_EXCLUSIONS
        and not _is_private_or_host_key(name)
        and not _is_machine_replace_key(name)
        and not _is_filament_translate_key(name)
    }
    reference = {
        "schema": "s1optimizer-original-process-v1",
        "reference_only": True,
        "source_file": Path(plan.source_path).name,
        "source_sha256": plan.source_sha256,
        "original_print_settings_id": project.get("print_settings_id"),
        "settings": settings,
    }
    return (json.dumps(reference, ensure_ascii=False, indent=4) + "\n").encode("utf-8")


def _apply_archive_action(raw: bytes, action: ArchiveAction) -> bytes:
    if action.action == "CLEAR_PLATE_BED_TYPE":
        return clear_plate_bed_types(raw)
    if action.action == "RELOCATE_PLATES":
        return relocate_build_items(raw, action.new_value)
    try:
        value = decode_json(raw)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise PlanError(f"Cannot parse {action.source_member} while writing: {exc}") from exc
    if not isinstance(value, dict):
        raise PlanError(f"JSON root must be an object: {action.source_member}")
    if value.get(action.setting_name) != action.old_value:
        raise PlanError(
            f"Planned old value no longer matches: "
            f"{action.source_member}::{action.setting_name}"
        )
    value[action.setting_name] = action.new_value
    return _serialized_project(raw, value)


def write_optimized_archive(
    plan: ConversionPlan, output_path: str | Path
) -> WriteResult:
    source = Path(plan.source_path).resolve()
    output = Path(output_path).expanduser().resolve()
    if source == output:
        raise PlanError("Output path must not be the source file")
    if output.exists():
        raise PlanError(f"Refusing to overwrite existing output: {output}")
    if not output.parent.is_dir():
        raise PlanError(f"Output directory does not exist: {output.parent}")
    if _file_sha256(source) != plan.source_sha256:
        raise PlanError("Source file changed after the conversion plan was created")
    if plan.write_blockers:
        raise PlanError("Export blocked: " + "; ".join(plan.write_blockers))

    source_inspection = inspect_archive(str(source))
    if not source_inspection.is_valid_3mf:
        raise PlanError("Source is not a valid core 3MF archive")
    inventory = ThreeMFArchive(source).validate()
    if inventory.duplicate_names:
        raise PlanError("Cannot safely rewrite an archive with duplicate member names")
    if any(member.encrypted or member.suspicious_path for member in inventory.members):
        raise PlanError("Cannot safely rewrite encrypted or suspicious archive members")

    project_member = plan.project_member
    removal_actions = {
        item.source_member: item
        for item in plan.archive_actions
        if item.action == "REMOVE"
    }
    auxiliary_actions = {
        item.source_member: item
        for item in plan.archive_actions
        if item.action != "REMOVE"
    }
    embedded_process_member = (
        "Metadata/process_settings_1.config" if plan.process is not None else None
    )
    original_process_member = (
        "Metadata/s1optimizer_original_process_reference.json"
        if plan.process is not None else None
    )
    source_names = {member.name for member in inventory.members}
    if (embedded_process_member in source_names
            and embedded_process_member not in removal_actions):
        raise PlanError("Cannot replace an unreviewed embedded process member")
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{output.name}.", suffix=".tmp", dir=output.parent, delete=False
        ) as temp:
            temp_path = Path(temp.name)
        with zipfile.ZipFile(source, "r") as source_zip, zipfile.ZipFile(
            temp_path, "w", allowZip64=True
        ) as output_zip:
            projected_project: dict[str, object] | None = None
            for info in source_zip.infolist():
                if info.filename in removal_actions:
                    continue
                if info.filename == project_member and plan.actions:
                    raw = ThreeMFArchive(source).read_member(
                        project_member, max_bytes=MAX_STRUCTURED_MEMBER_BYTES
                    )
                    rendered = _apply_plan(raw, plan)
                    output_zip.writestr(info, rendered)
                    if embedded_process_member is not None:
                        projected_project = decode_json(rendered)
                elif info.filename in auxiliary_actions:
                    auxiliary = auxiliary_actions[info.filename]
                    if auxiliary.action == "RELOCATE_PLATES":
                        with source_zip.open(info, "r") as src, output_zip.open(
                            info, "w", force_zip64=True
                        ) as dst:
                            stream_relocate_build_items(src, dst, auxiliary.new_value)
                        continue
                    raw = ThreeMFArchive(source).read_member(
                        info.filename, max_bytes=MAX_STRUCTURED_MEMBER_BYTES
                    )
                    output_zip.writestr(
                        info, _apply_archive_action(raw, auxiliary_actions[info.filename])
                    )
                else:
                    with source_zip.open(info, "r") as src, output_zip.open(
                        info, "w", force_zip64=True
                    ) as dst:
                        shutil.copyfileobj(src, dst, length=1024 * 1024)
            if embedded_process_member is not None:
                if projected_project is None:
                    raw = ThreeMFArchive(source).read_member(
                        project_member, max_bytes=MAX_STRUCTURED_MEMBER_BYTES
                    )
                    projected_project = decode_json(raw)
                if not isinstance(projected_project, dict):
                    raise PlanError("Project settings root must be a JSON object")
                info = zipfile.ZipInfo(
                    embedded_process_member, date_time=(1980, 1, 1, 0, 0, 0)
                )
                info.compress_type = zipfile.ZIP_DEFLATED
                output_zip.writestr(
                    info, _embedded_optimized_process(projected_project, plan)
                )
                if original_process_member not in source_names:
                    source_project = decode_json(ThreeMFArchive(source).read_member(
                        project_member, max_bytes=MAX_STRUCTURED_MEMBER_BYTES
                    ))
                    if not isinstance(source_project, dict):
                        raise PlanError("Original project settings root must be a JSON object")
                    reference_info = zipfile.ZipInfo(
                        original_process_member, date_time=(1980, 1, 1, 0, 0, 0)
                    )
                    reference_info.compress_type = zipfile.ZIP_DEFLATED
                    output_zip.writestr(
                        reference_info, _original_process_reference(source_project, plan)
                    )

        output_inspection = inspect_archive(str(temp_path))
        if not output_inspection.is_valid_3mf:
            raise PlanError("Rebuilt output failed core 3MF validation")
        if source_inspection.structure_counts != output_inspection.structure_counts:
            raise PlanError("Rebuilt output changed model/object/plate structure counts")

        source_hashes = _member_hashes(source)
        output_hashes = _member_hashes(temp_path)
        added_members = {embedded_process_member} if embedded_process_member else set()
        if original_process_member and original_process_member not in source_names:
            added_members.add(original_process_member)
        expected_output_names = (set(source_hashes) - set(removal_actions)) | added_members
        if set(output_hashes) != expected_output_names:
            raise PlanError(
                "Rebuilt output changed the archive member inventory beyond planned "
                "embedded-profile removals"
            )
        changed = tuple(
            name
            for name in source_hashes
            if name in removal_actions or source_hashes[name] != output_hashes[name]
        ) + tuple(sorted(added_members - set(source_hashes)))
        expected = (
            ({project_member} if plan.actions else set())
            | set(auxiliary_actions)
            | set(removal_actions)
            | added_members
        )
        if set(changed) != expected:
            raise PlanError(
                "Rebuilt output changed an unexpected member set: "
                + ", ".join(changed)
            )
        if _file_sha256(source) != plan.source_sha256:
            raise PlanError("Source file changed during output generation")

        # Reserve the destination exclusively, then atomically replace only
        # that placeholder. This works on Windows volumes that reject links.
        placeholder_created = False
        try:
            descriptor = os.open(output, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(descriptor)
            placeholder_created = True
            os.replace(temp_path, output)
        except Exception:
            if placeholder_created:
                output.unlink(missing_ok=True)
            raise
        output_hash = _file_sha256(output)
        temp_path = None
        return WriteResult(
            output_path=str(output),
            source_sha256=plan.source_sha256,
            output_sha256=output_hash,
            changed_members=changed,
            unchanged_members_verified=sum(
                name in output_hashes and source_hashes[name] == output_hashes[name]
                for name in source_hashes
            ),
            structure_counts=output_inspection.structure_counts,
        )
    except FileExistsError as exc:
        raise PlanError(f"Refusing to overwrite existing output: {output}") from exc
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        raise PlanError(f"Cannot create optimized archive: {exc}") from exc
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
