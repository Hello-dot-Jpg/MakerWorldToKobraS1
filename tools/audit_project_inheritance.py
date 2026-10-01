"""Read-only, bounded project-inheritance audit; emits local filenames to stdout."""
import argparse
from collections import Counter
import json
from pathlib import Path
import zipfile

from s1_optimizer.plan import _machine_inherits_group
from s1_optimizer.errors import PlanError


def audit(root):
    counts = Counter()
    findings = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() != ".3mf":
            continue
        counts["files"] += 1
        try:
            with zipfile.ZipFile(path) as archive:
                members = [i for i in archive.infolist()
                           if i.filename.lower() == "metadata/project_settings.config"]
                if not members:
                    counts["no_modern_project"] += 1
                    continue
                if len(members) != 1 or members[0].file_size > 16 * 1024 * 1024:
                    raise ValueError("ambiguous or oversized project config")
                project = json.loads(archive.read(members[0]))
            counts["modern_projects"] += 1
            group = project.get("inherits_group", [])
            repaired = _machine_inherits_group(project, "AUDIT_TARGET")
            assert repaired[-1] == "AUDIT_TARGET"
            if group:
                assert repaired[:-1][:min(len(group), len(repaired)-1)] == group[:len(repaired)-1]
                counts["existing_nonempty_group"] += 1
            else:
                counts["absent_or_empty_group"] += 1
            if project.get("filament_colour") is None:
                counts["missing_filament_colour"] += 1
            for key in ("print_compatible_printers", "compatible_machine_expression_group",
                        "compatible_process_expression_group", "different_settings_to_system"):
                if project.get(key):
                    counts[key] += 1
            counts["machine_repair_preserves_other_scopes"] += 1
        except (OSError, ValueError, KeyError, PlanError, zipfile.BadZipFile) as error:
            counts["errors"] += 1
            findings.append({"file": str(path), "error": str(error)})
    return {"counts": dict(counts), "findings": findings}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.root), indent=2))
