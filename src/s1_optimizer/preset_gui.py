"""Independent GUI tab for standalone filament presets."""
from pathlib import Path

from .errors import PlanError, TargetDiscoveryError
from .filaments import (default_filament_profile_dir, discover_filaments,
                        resolve_filament_target, load_standalone_filament_base)
from .preset_conversion import convert_preset, export_presets, read_source, scalar, render_preset_review
from .resolution import resolve_machine_target
from .targets import default_machine_profile_dir, discover_targets
from .preset_sources import ArchivePreset, list_bundle_presets
from .preset_ini import IniPreset, list_ini_presets
from .preset_matching import match_filament_option
from .preset_install import active_filament_store, install_export, rollback_install, _read_candidates


class FilamentProfileTab:
    def __init__(self, app, notebook):
        import tkinter as tk
        from tkinter import ttk
        self.app, self.tk = app, tk
        self.paths = []
        self.machine_options = {}
        self.explicit_base = tk.StringVar()
        self.accept_base_material = tk.BooleanVar(value=False)
        self.physical_nozzle = tk.StringVar(value="hardened-steel")
        self.nozzle_max = tk.StringVar()
        self.bed_max = tk.StringVar()
        self.hotend = tk.StringVar(value="unspecified")
        self.ceramic_firmware = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="Separate workflow: does not change 3MF filament reassignment.")
        from .ui import build_preset_tab
        build_preset_tab(self, app, notebook)

    def install_reviewed(self):
        from tkinter import filedialog, messagebox
        folder = filedialog.askdirectory(parent=self.app.root, title="Select a reviewed S1-filaments export folder")
        if not folder:
            return
        try:
            candidates = _read_candidates(Path(folder))
            store = active_filament_store()
        except (OSError, ValueError, PlanError) as exc:
            messagebox.showerror("Filament install", str(exc), parent=self.app.root)
            return
        backup_parent = filedialog.askdirectory(parent=self.app.root, title="Select existing folder for a NEW complete preset backup")
        if not backup_parent:
            return
        if not messagebox.askyesno("Confirm direct filament install",
                f"Install {len(candidates)} REVIEW presets into:\n{store}\n\n"
                f"Create a complete backup under:\n{backup_parent}\n\n"
                "Existing names will never be overwritten. Close Anycubic Slicer Next first.",
                parent=self.app.root):
            return
        def done(manifest):
            self.status.set(f"Installed {len(candidates)} REVIEW presets. Backup and rollback manifest: {manifest}")
        self.app._run_job("Backing up and installing filament presets…",
                          lambda: install_export(Path(folder), Path(backup_parent)), done)

    def rollback_reviewed(self):
        from tkinter import filedialog, messagebox
        manifest = filedialog.askopenfilename(parent=self.app.root, title="Select install-manifest.json from backup",
                                              filetypes=[("Install manifest", "*.json")])
        if not manifest:
            return
        if not messagebox.askyesno("Confirm rollback", "Close Anycubic Slicer Next first. Move this installation's presets into the backup quarantine? Any presets tuned since installation will be preserved there, not deleted.", parent=self.app.root):
            return
        self.app._run_job("Rolling back filament install…", lambda: rollback_install(Path(manifest), preserve_modified=True),
                          lambda quarantine: self.status.set(f"Installation rolled back. Removed presets preserved at {quarantine}"))

    def choose_base(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(parent=self.app.root,
            title="Choose standalone destination base (exact material and printer/nozzle required)",
            filetypes=[("Standalone filament base", "*.json")])
        if path:
            self.explicit_base.set(str(Path(path).resolve()))

    def clear(self):
        self.paths.clear()
        self.files.delete(0, "end")

    def add(self, paths):
        for path in paths:
            path = path if isinstance(path, (ArchivePreset, IniPreset)) else Path(path).resolve()
            if path not in self.paths:
                self.paths.append(path)
                self.files.insert("end", str(path))
        self.files.selection_set(0, "end")

    def add_files(self):
        from tkinter import filedialog
        self.add(filedialog.askopenfilenames(parent=self.app.root, filetypes=[("Filament JSON", "*.json")]))

    def add_folder(self):
        from tkinter import filedialog
        folder = filedialog.askdirectory(parent=self.app.root)
        if folder:
            self.add(sorted(Path(folder).glob("*.json")))

    def add_ini(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(parent=self.app.root,
            filetypes=[("Filament INI / config", "*.ini *.config")])
        if path:
            def done(presets):
                self.add(presets)
                self.status.set(f"Found {len(presets)} INI filament sections. Limited scalar mapping; review warnings before export.")
            self.app._run_job("Reading filament INI…", lambda: list_ini_presets(path), done)

    def add_bundle(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(parent=self.app.root,
            filetypes=[("Filament bundle", "*.zip *.orca_filament")])
        if path:
            def done(presets):
                self.add(presets)
                self.status.set(f"Found {len(presets)} filament presets in bundle; no files extracted.")
            self.app._run_job("Reading filament bundle…", lambda: list_bundle_presets(path), done)

    def discover(self):
        def done(options):
            self.machine_options = {o.label: o for o in options}
            self.machine_box.delete(0, "end")
            for index, label in enumerate(self.machine_options):
                self.machine_box.insert("end", label)
                if label == "Anycubic Kobra S1 0.6 nozzle":
                    self.machine_box.selection_set(index)
            self.status.set(f"Found {len(options)} installed S1 printer profiles. Select one or multiple nozzle sizes.")
        self.app._run_job("Discovering filament-import targets…",
                          lambda: discover_targets(machine_dir=default_machine_profile_dir()), done)

    def run(self, exporting):
        from tkinter import filedialog, messagebox
        selected = tuple(self.paths[i] for i in self.files.curselection())
        targets = tuple(self.machine_options[self.machine_box.get(i)] for i in self.machine_box.curselection())
        if not selected or not targets:
            messagebox.showerror("Filament profiles", "Select source presets and a destination printer.", parent=self.app.root)
            return
        nozzle_max, bed_max = self.nozzle_max.get().strip(), self.bed_max.get().strip()
        physical_nozzle = self.physical_nozzle.get()
        hotend, firmware_confirmed = self.hotend.get(), self.ceramic_firmware.get()
        explicit_base = self.explicit_base.get()
        accept_base_material = self.accept_base_material.get()
        if accept_base_material and not explicit_base:
            messagebox.showerror("Filament profiles", "Material correction requires an explicit REVIEW base.", parent=self.app.root)
            return
        parent = filedialog.askdirectory(parent=self.app.root, title="Choose parent folder for a NEW preset export folder") if exporting else None
        if exporting and not parent:
            return

        def work():
            directory = default_filament_profile_dir()
            plans, errors = [], []
            for target in targets:
                machine = resolve_machine_target(target, machine_dir=default_machine_profile_dir())
                options = () if explicit_base else discover_filaments(machine, filament_dir=directory)
                for source in selected:
                    try:
                        values, _ = read_source(source)
                        material = scalar(values.get("filament_type", ""))
                        if explicit_base:
                            base = load_standalone_filament_base(explicit_base, machine)
                        else:
                            choice = match_filament_option(options, material=material,
                                                           nozzle_diameter=target.nozzle_diameter)
                            base = resolve_filament_target(choice, filament_dir=directory)
                        plans.append(convert_preset(source, machine, base,
                                                    max_nozzle_temp=nozzle_max, max_bed_temp=bed_max,
                                                    nozzle_material=physical_nozzle, hotend=hotend,
                                                    ceramic_firmware_confirmed=firmware_confirmed,
                                                    accept_base_material=accept_base_material))
                    except (OSError, ValueError, PlanError, TargetDiscoveryError) as exc:
                        errors.append(f"{source.name} / {target.nozzle_diameter} mm: {exc}")
            blocked = errors or any(p.blockers for p in plans)
            folder = export_presets(plans, Path(parent)) if exporting and not blocked else None
            return plans, errors, folder

        def done(result):
            plans, errors, folder = result
            report = render_preset_review(plans, errors)
            self.report.configure(state="normal")
            self.report.delete("1.0", "end")
            self.report.insert("1.0", report)
            self.report.configure(state="disabled")
            count = len(errors) + sum(bool(p.blockers) for p in plans)
            self.status.set(f"Exported to {folder}. Not installed; import the ZIP or JSONs in Anycubic." if folder else
                            f"Reviewed {len(plans)} presets; {count} blocked. No installed files changed.")
        self.app._run_job("Reviewing standalone filament presets…", work, done)
