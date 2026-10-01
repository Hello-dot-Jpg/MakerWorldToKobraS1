"""Frozen GUI entry point and opt-in, non-installing runtime smoke check."""
from pathlib import Path
import json
import sys

from s1_optimizer.gui import OptimizerApp, main


def smoke_test(report_path: Path) -> int:
    import tkinter as tk
    from s1_optimizer.rules import load_rules
    from s1_optimizer import cli, preset_gui, stream_geometry, preset_install

    result = {"status": "failed", "frozen": bool(getattr(sys, "frozen", False)),
              "python": sys.version, "checks": []}
    root = None
    try:
        assert result["frozen"], "Smoke check must run inside the executable"
        assert load_rules().clamp
        result["checks"].append("bundled application modules and default rules")
        root = tk.Tk()
        root.withdraw()
        app = OptimizerApp(root)
        root.update_idletasks()
        assert app.bed_type_var.get() == "Textured PEI Plate"
        assert not app.scale_to_fit_var.get()
        assert str(app.target_box.cget("state")) == "readonly", "Initial profile selector must be readonly"
        assert not root.bind("<FocusIn>"), "Mouse focus must not auto-scroll the form"
        assert root.bind("<KeyRelease-Tab>"), "Keyboard navigation should reveal controls"
        assert not app.progress.winfo_manager(), "Idle progress must be hidden"
        app._set_busy(True, "Smoke check")
        assert str(app.target_box.cget("state")) == "disabled", "Profile selector must lock during a job"
        assert app.progress.winfo_manager() == "grid", "Busy progress must be visible"
        app._set_busy(False, "Ready")
        assert str(app.target_box.cget("state")) == "readonly", "Profile selector must restore readonly state"
        assert not app.progress.winfo_manager(), "Finished progress must be hidden"
        result["checks"].append("busy controls restore readonly state")
        result["checks"].append("Tk runtime and both application tabs initialize")
        result["status"] = "passed"
    except Exception as exc:
        result["error"] = repr(exc)
    finally:
        if root is not None:
            root.destroy()
    with report_path.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--smoke-test":
        raise SystemExit(smoke_test(Path(sys.argv[2])))
    raise SystemExit(main())
