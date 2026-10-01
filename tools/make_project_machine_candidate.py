"""Experimental project-local printer scope; never install or overwrite presets."""
import json
from pathlib import Path
import shutil
import sys
import zipfile

from s1_optimizer.plan import _is_machine_replace_key
from s1_optimizer.resolution import resolve_machine_target
from s1_optimizer.targets import discover_targets, default_machine_profile_dir


def main(source: Path, output: Path, target_id: str):
    target = resolve_machine_target(
        next(t for t in discover_targets() if t.target_id == target_id),
        machine_dir=default_machine_profile_dir(),
    )
    with zipfile.ZipFile(source) as original:
        project = json.loads(original.read("Metadata/project_settings.config"))
        label = "[Project beta] " + target.target.label + " - " + source.stem
        project["printer_settings_id"] = label
        project["print_compatible_printers"] = [label, target.target.label]
        names = set(target.effective_values) | {k for k in project if _is_machine_replace_key(k)}
        machine = {k: project[k] for k in names if k in project
                   and not any(v in k.casefold() for v in ("host", "password", "secret", "token", "api_key"))}
        machine.update(type="machine", **{"from": "project", "name": label,
                                        "printer_settings_id": label, "inherits": target.target.label})
        with zipfile.ZipFile(output, "x") as destination:
            for info in original.infolist():
                if info.filename.startswith("Metadata/machine_settings_"):
                    raise ValueError("Refusing to replace an existing embedded machine")
                if info.filename == "Metadata/project_settings.config":
                    destination.writestr(info, json.dumps(project).encode())
                elif info.filename.startswith("Metadata/process_settings_"):
                    process = json.loads(original.read(info))
                    process["compatible_printers"] = [label, target.target.label]
                    destination.writestr(info, json.dumps(process).encode())
                else:
                    with original.open(info) as src, destination.open(info, "w", force_zip64=True) as dst:
                        shutil.copyfileobj(src, dst, length=1024 * 1024)
            destination.writestr("Metadata/machine_settings_1.config", json.dumps(machine).encode())
    print(output)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3])
