"""Generate local S1 engineering REVIEW presets; never install them."""
import argparse
from pathlib import Path

from s1_optimizer.engineering_presets import MATERIALS, plan_engineering_preset
from s1_optimizer.filaments import default_filament_profile_dir
from s1_optimizer.preset_conversion import export_presets, render_preset_review


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_parent", type=Path)
    parser.add_argument("--nozzle", choices=("0.4", "0.6", "0.8"), default="0.6")
    parser.add_argument("--profile-dir", type=Path, default=default_filament_profile_dir())
    parser.add_argument("--export-ready", action="store_true", help="Explicitly export only unblocked plans; record all blocked cases in batch audit")
    args = parser.parse_args()
    plans = [plan_engineering_preset(args.profile_dir, material, args.nozzle) for material in MATERIALS]
    print(render_preset_review(plans))
    selected = [p for p in plans if not p.blockers] if args.export_ready else plans
    folder = export_presets(selected, args.output_parent)
    with (folder / "batch-audit.txt").open("x", encoding="utf-8") as stream:
        stream.write(render_preset_review(plans))
    print(folder)


if __name__ == "__main__":
    main()
