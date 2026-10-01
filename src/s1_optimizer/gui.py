from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from typing import Callable, TypeVar

from .errors import InspectorError, PlanError, TargetDiscoveryError
from .filaments import (
    FilamentOption,
    default_filament_profile_dir,
    discover_filaments,
    resolve_filament_target,
)
from .gui_model import (
    SourceSummary,
    closest_supported_nozzle,
    suggest_filament,
    suggest_process,
    suggest_target,
    summarize_source,
)
from .plan import build_conversion_plan
from .plan import SUPPORTED_BED_TYPES
from .processes import (
    ProcessOption,
    default_process_profile_dir,
    discover_processes,
    resolve_process_target,
)
from .report import render_plan
from .resolution import ResolvedMachineTarget, resolve_machine_target
from .rules import load_rules
from .targets import TargetOption, default_machine_profile_dir, discover_targets
from .writer import write_optimized_archive


T = TypeVar("T")


def _default_bundles() -> tuple[Path, ...]:
    downloads = Path.home() / "Downloads"
    names = (
        "V2+Kobra+S1+0.4+nozzle+profiles+for+speed+and+quality.3mf",
        "Profiles+0.2+0.6+0.8+V2.3mf",
    )
    return tuple(path for name in names if (path := downloads / name).is_file())


def _display(label: str, source_kind: str, stable_id: str) -> str:
    reference = sha256(stable_id.encode("utf-8")).hexdigest()[:8]
    return f"{label}  · {source_kind.title()} · {reference}"


def _target_display(item: TargetOption) -> str:
    nozzle_type = item.nozzle_type.replace("_", " ")
    details = f"effective {item.nozzle_diameter} mm / {nozzle_type}"
    return f"{item.label}  · {details} · {item.source_kind.title()} · {item.sha256[:6]}"


def _process_display(item: ProcessOption) -> str:
    details = f"{item.layer_height or '?'} mm layer / {item.line_width or '?'} mm line"
    return f"{item.label}  · {details} · {item.source_kind.title()} · {item.sha256[:6]}"


def _shown(value: str) -> str:
    return value or "(not declared)"


def _source_overview(summary: SourceSummary | None) -> str:
    if summary is None:
        return "No project loaded\n\nOpen a 3MF to see its original printer, nozzle and print settings."
    materials = ", ".join(f"{slot.index}: {slot.material or 'unknown'}" for slot in summary.filament_slots)
    return (
        f"{Path(summary.path).name}\n\n"
        f"Nozzle  {_shown(summary.nozzle_diameter)} mm\n"
        f"Layer  {_shown(summary.layer_height)} mm  ·  Line  {_shown(summary.line_width)} mm\n"
        f"Plate  {_shown(summary.bed_type)}\n"
        f"Materials  {materials or '(not declared)'}\n\n"
        f"Printer  {_shown(summary.printer)}\nPrint profile  {_shown(summary.process)}"
    )


def _source_report(summary: SourceSummary, target_nozzle: str) -> str:
    materials = ", ".join(
        f"{slot.index}: {slot.material or 'unknown'} ({slot.profile_id or 'unnamed'})"
        for slot in summary.filament_slots
    )
    if summary.support_enabled == "1":
        support = f"enabled ({summary.support_type or 'type not declared'})"
    elif summary.support_enabled == "0":
        support = "disabled"
    else:
        support = _shown(summary.support_type)
    return (
        "SOURCE FILE SETTINGS\n"
        f"Printer profile: {_shown(summary.printer)}\n"
        f"Print profile: {_shown(summary.process)}\n"
        f"Nozzle: {_shown(summary.nozzle_diameter)} mm\n"
        f"Profile nozzle material: {_shown(summary.nozzle_type).replace('_', ' ')}\n"
        f"Layer height: {_shown(summary.layer_height)} mm\n"
        f"Initial layer height: {_shown(summary.initial_layer_height)} mm\n"
        f"Default line width: {_shown(summary.line_width)} mm\n"
        f"Wall loops: {_shown(summary.wall_loops)}\n"
        f"Infill: {_shown(summary.infill_density)} / {_shown(summary.infill_pattern)}\n"
        f"Supports: {support}\n"
        f"Build plate: {_shown(summary.bed_type)}\n"
        f"Filament slots: {materials}\n\n"
        f"Starting Kobra S1 nozzle choice: {target_nozzle} mm\n"
        "Click Discover profiles to load the closest compatible machine, process, "
        "and filament choices. Every suggestion remains editable."
    )


def _build_plan_from_selection(selection):
    (
        source_path,
        machine_dir,
        process_dir,
        filament_dir,
        target,
        process,
        filaments,
        hotend_type,
        hotend_max_temp,
        nice_supports_beta,
        use_process_layer_height,
        nozzle_hardware_type,
        layer_height_override,
        bed_type,
        scale_to_fit,
    ) = selection
    machine = resolve_machine_target(target, machine_dir=machine_dir)
    resolved_process = resolve_process_target(process, process_dir=process_dir)
    resolved_filaments = tuple(
        resolve_filament_target(item, filament_dir=filament_dir)
        for item in filaments
    )
    return build_conversion_plan(
        source_path,
        machine,
        process=resolved_process,
        filaments=resolved_filaments,
        hotend_type=hotend_type,
        max_nozzle_temperature=hotend_max_temp,
        nice_supports_beta=nice_supports_beta,
        use_process_layer_height=use_process_layer_height,
        nozzle_hardware_type=nozzle_hardware_type,
        layer_height_override=layer_height_override,
        bed_type=bed_type,
        scale_to_fit=scale_to_fit,
        rules=load_rules(),
    )


class OptimizerApp:
    def __init__(self, root) -> None:
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.ttk = ttk
        self.root = root
        self.root.title("MakerWorld to Kobra S1 Optimizer")
        self.root.minsize(900, 680)
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="s1optimizer")
        self.root.protocol("WM_DELETE_WINDOW", self._close)

        self.source_summary: SourceSummary | None = None
        self.machine_dir: Path | None = None
        self.process_dir: Path | None = None
        self.filament_dir: Path | None = None
        self.targets_by_display: dict[str, TargetOption] = {}
        self.processes_by_display: dict[str, ProcessOption] = {}
        self.filaments_by_slot: list[dict[str, FilamentOption]] = []
        self.filament_boxes: list[object] = []
        self.filament_vars: list[object] = []
        self.busy_widgets: list[object] = []

        self.source_var = tk.StringVar()
        self.nozzle_var = tk.StringVar(value="0.4")
        self.physical_nozzle_var = tk.StringVar(value="profile")
        self.target_var = tk.StringVar()
        self.process_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.hotend_type_var = tk.StringVar(value="Unspecified")
        self.hotend_max_var = tk.StringVar()
        self.nice_supports_beta_var = tk.BooleanVar(value=False)
        self.use_process_layer_height_var = tk.BooleanVar(value=False)
        self.bed_type_var = tk.StringVar(value="Textured PEI Plate")
        self.scale_to_fit_var = tk.BooleanVar(value=False)
        self.custom_layer_height_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Choose a source 3MF, then discover profiles.")

        from .ui import apply_theme, build_converter
        apply_theme(root)
        root.geometry(f"{min(1240, root.winfo_screenwidth() - 80)}x{min(820, root.winfo_screenheight() - 100)}")
        root.minsize(980, 650)
        header = ttk.Frame(root, padding=(22, 16, 22, 8))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Kobra S1 · Project optimizer", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="A considered conversion. Your models, your choices.", style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(3, 0))
        ttk.Label(header, text="LOCAL BETA", style="Badge.TLabel").grid(row=0, column=1, rowspan=2)
        notebook = ttk.Notebook(root)
        notebook.grid(row=1, column=0, sticky="nsew", padx=8)
        root.rowconfigure(1, weight=1)
        root.columnconfigure(0, weight=1)
        self.SUPPORTED_BED_TYPES = SUPPORTED_BED_TYPES
        build_converter(self, notebook, _default_bundles())
        from .preset_gui import FilamentProfileTab
        self.preset_tab = FilamentProfileTab(self, notebook)

    def _close(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=True)
        self.root.destroy()

    def _set_report(self, text: str) -> None:
        if hasattr(self, "source_overview_var"):
            self.source_overview_var.set(_source_overview(self.source_summary))
        self.report_text.configure(state="normal")
        self.report_text.delete("1.0", "end")
        self.report_text.insert("1.0", text)
        self.report_text.configure(state="disabled")

    def _bundles(self) -> tuple[str, ...]:
        return tuple(self.bundle_list.get(0, "end"))

    def _set_busy(self, busy: bool, message: str) -> None:
        self.status_var.set(message)
        from .ui import lock_controls
        if busy:
            self._busy_states = lock_controls(self.root)
            if hasattr(self, "progress"):
                self.progress.grid()
                self.progress.start(12)
        else:
            for widget, state in getattr(self, "_busy_states", {}).items():
                if widget.winfo_exists():
                    widget.configure(state=state)
            self._busy_states = {}
            if hasattr(self, "progress"):
                self.progress.stop()
                self.progress.grid_remove()

    def _run_job(
        self, message: str, function: Callable[[], T], success: Callable[[T], None]
    ) -> None:
        from tkinter import messagebox

        self._set_busy(True, message)
        future: Future[T] = self.executor.submit(function)

        def poll() -> None:
            if not future.done():
                self.root.after(100, poll)
                return
            self._set_busy(False, "Ready")
            try:
                success(future.result())
            except Exception as exc:  # Tk callback boundary
                self.status_var.set("Action failed")
                messagebox.showerror("Kobra S1 Optimizer", str(exc), parent=self.root)

        self.root.after(100, poll)

    def _browse_source(self) -> None:
        from tkinter import filedialog

        value = filedialog.askopenfilename(
            parent=self.root,
            title="Choose MakerWorld/Bambu 3MF",
            filetypes=(("3MF project", "*.3mf"), ("All files", "*.*")),
        )
        if value:
            self.source_var.set(value)
            self._load_source()

    def _source_entered(self, _event=None) -> str:
        self._load_source()
        return "break"

    def _reset_for_source_load(self) -> None:
        self.source_summary = None
        self.machine_dir = None
        self.process_dir = None
        self.filament_dir = None
        self.targets_by_display.clear()
        self.processes_by_display.clear()
        self.target_box.configure(values=())
        self.process_box.configure(values=())
        self.target_var.set("")
        self.process_var.set("")
        self.nozzle_var.set("0.4")
        self.physical_nozzle_var.set("profile")
        self.hotend_type_var.set("Unspecified")
        self.hotend_max_var.set("")
        self.nice_supports_beta_var.set(False)
        self.use_process_layer_height_var.set(False)
        self.custom_layer_height_var.set("")
        self.bed_type_var.set("Textured PEI Plate")
        self.scale_to_fit_var.set(False)
        self.output_var.set("")
        self._clear_filament_rows("Load the source, then discover profiles.")
        self._set_report("")

    def _load_source(self) -> None:
        from tkinter import messagebox

        value = self.source_var.get().strip()
        if not value:
            messagebox.showerror(
                "Kobra S1 Optimizer", "Choose a source 3MF first", parent=self.root
            )
            return

        self._reset_for_source_load()

        def loaded(summary: SourceSummary) -> None:
            self.source_summary = summary
            suggested_nozzle = closest_supported_nozzle(summary.nozzle_diameter)
            self.nozzle_var.set(suggested_nozzle)
            self._set_report(_source_report(summary, suggested_nozzle))
            self.status_var.set(
                f"Source loaded; suggested {suggested_nozzle} mm target. Discover profiles to continue"
            )

        self._run_job("Inspecting source…", lambda: summarize_source(value), loaded)

    def _add_bundle(self) -> None:
        from tkinter import filedialog

        values = filedialog.askopenfilenames(
            parent=self.root,
            title="Add profile-bundle 3MF",
            filetypes=(("3MF profile bundle", "*.3mf"), ("All files", "*.*")),
        )
        current = set(self._bundles())
        for value in values:
            resolved = str(Path(value).resolve())
            if resolved not in current:
                self.bundle_list.insert("end", resolved)
                current.add(resolved)

    def _remove_bundle(self) -> None:
        for index in reversed(self.bundle_list.curselection()):
            self.bundle_list.delete(index)

    def _discover_profiles(self) -> None:
        from tkinter import messagebox

        if self.source_summary is None:
            messagebox.showerror(
                "Kobra S1 Optimizer", "Load a source 3MF first", parent=self.root
            )
            return
        nozzle = self.nozzle_var.get()
        bundles = self._bundles()

        def work():
            machine_dir = default_machine_profile_dir()
            process_dir = default_process_profile_dir()
            filament_dir = default_filament_profile_dir()
            if machine_dir is None or process_dir is None or filament_dir is None:
                raise TargetDiscoveryError(
                    "Installed Anycubic machine/process/filament directories were not all found"
                )
            targets = discover_targets(
                machine_dir=machine_dir, bundles=bundles, nozzle=nozzle
            )
            return machine_dir, process_dir, filament_dir, targets

        def loaded(result) -> None:
            self.machine_dir, self.process_dir, self.filament_dir, targets = result
            self.targets_by_display = {
                _target_display(item): item
                for item in targets
            }
            self.target_box.configure(values=tuple(self.targets_by_display))
            self.target_var.set("")
            self.process_var.set("")
            self.process_box.configure(values=())
            self._clear_filament_rows("Select an exact machine profile.")
            if self.source_summary is None:
                return
            suggested = suggest_target(self.source_summary, targets)
            if suggested is None:
                self.status_var.set("No compatible machine profile was found")
                return
            display = next(
                label for label, item in self.targets_by_display.items()
                if item.target_id == suggested.target_id
            )
            self.target_var.set(display)
            self.status_var.set(
                f"Suggested {suggested.label}; loading compatible settings…"
            )
            self._target_changed()

        self._run_job("Discovering machine profiles…", work, loaded)

    def _selected_target(self) -> TargetOption:
        target = self.targets_by_display.get(self.target_var.get())
        if target is None:
            raise PlanError("Select an exact machine profile")
        return target

    def _target_changed(self, _event=None) -> None:
        if self.source_summary is None or self.machine_dir is None:
            return
        target = self._selected_target()
        bundles = self._bundles()
        machine_dir = self.machine_dir
        process_dir = self.process_dir
        filament_dir = self.filament_dir
        materials = tuple(slot.material for slot in self.source_summary.filament_slots)

        def work():
            if process_dir is None or filament_dir is None:
                raise TargetDiscoveryError("Installed process/filament directories are missing")
            machine = resolve_machine_target(target, machine_dir=machine_dir)
            processes = discover_processes(
                machine, process_dir=process_dir, bundles=bundles
            )
            by_material = {
                material: discover_filaments(
                    machine,
                    filament_dir=filament_dir,
                    bundles=bundles,
                    material=material,
                )
                for material in set(materials)
            }
            return machine, processes, by_material

        def loaded(result) -> None:
            _machine, processes, by_material = result
            try:
                if self._selected_target().target_id != target.target_id:
                    return
            except PlanError:
                return
            self.processes_by_display = {
                _process_display(item): item
                for item in processes
            }
            self.process_box.configure(values=tuple(self.processes_by_display))
            suggested_process = suggest_process(self.source_summary, processes)
            if suggested_process is None:
                self.process_var.set("")
            else:
                process_display = next(
                    label for label, item in self.processes_by_display.items()
                    if item.process_id == suggested_process.process_id
                )
                self.process_var.set(process_display)
            suggested_filaments = self._build_filament_rows(by_material)
            source = Path(self.source_summary.path)
            self.output_var.set(
                str(
                    source.with_name(
                        f"{source.stem}_KobraS1_{target.nozzle_diameter}mm.3mf"
                    )
                )
            )
            missing = sorted(
                material for material, choices in by_material.items() if not choices
            )
            if not processes:
                self.status_var.set("No compatible process profile was found")
            elif missing:
                self.status_var.set(
                    "No compatible filament profile for: " + ", ".join(missing)
                )
            else:
                self.status_var.set(
                    "Closest compatible profiles selected; review or override them before export"
                )
            filament_text = ", ".join(suggested_filaments) or "(no match)"
            process_text = suggested_process.label if suggested_process else "(no match)"
            self._set_report(
                _source_report(
                    self.source_summary,
                    target.nozzle_diameter,
                )
                + "\n\nSUGGESTED CONVERSION PROFILES\n"
                + f"Machine: {target.label}\n"
                + f"Process: {process_text}\n"
                + f"Filaments: {filament_text}\n"
                + "These are starting choices; use the selectors above to override them."
            )

        self._run_job("Loading compatible process and filament profiles…", work, loaded)

    def _clear_filament_rows(self, message: str | None = None) -> None:
        for child in self.filament_frame.winfo_children():
            child.destroy()
        self.filament_boxes.clear()
        self.filament_vars.clear()
        self.filaments_by_slot.clear()
        if message:
            self.ttk.Label(self.filament_frame, text=message).grid(
                row=0, column=0, columnspan=2, sticky="w"
            )

    def _build_filament_rows(
        self, by_material: dict[str, tuple[FilamentOption, ...]]
    ) -> tuple[str, ...]:
        self._clear_filament_rows()
        assert self.source_summary is not None
        selected_labels: list[str] = []
        for row, slot in enumerate(self.source_summary.filament_slots):
            choices = by_material.get(slot.material, ())
            mapping = {
                _display(
                    f"{item.label} | {item.confidence}",
                    item.source_kind,
                    item.filament_id,
                ): item
                for item in choices
            }
            variable = self.tk.StringVar()
            label = self.ttk.Label(
                self.filament_frame,
                text=f"{slot.index}  {slot.material or 'Unknown'}",
                style="Card.TLabel",
            )
            label.grid(row=row, column=0, sticky="w", padx=(0, 8), pady=2)
            box = self.ttk.Combobox(
                self.filament_frame,
                textvariable=variable,
                values=tuple(mapping),
                state="readonly",
            )
            box.grid(row=row, column=1, sticky="ew", pady=2)
            suggested = suggest_filament(slot, choices)
            if suggested is not None:
                selected_display = next(
                    display for display, item in mapping.items()
                    if item.filament_id == suggested.filament_id
                )
                variable.set(selected_display)
                selected_labels.append(f"slot {slot.index}: {suggested.label}")
            self.filament_vars.append(variable)
            self.filament_boxes.append(box)
            self.filaments_by_slot.append(mapping)
        return tuple(selected_labels)

    def _browse_output(self) -> None:
        from tkinter import filedialog

        initial = Path(self.output_var.get()) if self.output_var.get() else None
        value = filedialog.asksaveasfilename(
            parent=self.root,
            title="Choose new output 3MF",
            defaultextension=".3mf",
            initialdir=str(initial.parent) if initial else None,
            initialfile=initial.name if initial else None,
            filetypes=(("3MF project", "*.3mf"),),
        )
        if value:
            self.output_var.set(value)

    def _selection(self):
        if self.source_summary is None or self.machine_dir is None:
            raise PlanError("Load a source and discover profiles first")
        target = self._selected_target()
        process = self.processes_by_display.get(self.process_var.get())
        if process is None:
            raise PlanError("Select an exact process profile")
        if len(self.filament_vars) != len(self.source_summary.filament_slots):
            raise PlanError("Filament choices have not been loaded")
        filaments: list[FilamentOption] = []
        for slot, (variable, mapping) in enumerate(
            zip(self.filament_vars, self.filaments_by_slot, strict=True), start=1
        ):
            selected = mapping.get(variable.get())
            if selected is None:
                raise PlanError(f"Select a filament profile for slot {slot}")
            filaments.append(selected)
        return target, process, tuple(filaments)

    def _build_selected_plan(self):
        target, process, filaments = self._selection()
        assert self.source_summary is not None
        assert self.machine_dir is not None
        assert self.process_dir is not None
        assert self.filament_dir is not None
        hotend_types = {
            "Unspecified": "unspecified",
            "PTFE-lined upper section": "ptfe-lined",
            "All-metal later version": "all-metal",
            "Aftermarket ceramic": "aftermarket-ceramic",
            "Other / custom": "other",
        }
        base = (
            self.source_summary.path,
            self.machine_dir,
            self.process_dir,
            self.filament_dir,
            target,
            process,
            filaments,
            hotend_types[self.hotend_type_var.get()],
            self.hotend_max_var.get().strip() or None,
            self.nice_supports_beta_var.get(),
            self.use_process_layer_height_var.get(),
            self.physical_nozzle_var.get(),
            self.custom_layer_height_var.get().strip() or None,
        )
        return base + (
            self.bed_type_var.get(),
            self.scale_to_fit_var.get(),
        )

    def _analyze(self) -> None:
        from tkinter import messagebox

        try:
            selection = self._build_selected_plan()
        except InspectorError as exc:
            messagebox.showerror("Kobra S1 Optimizer", str(exc), parent=self.root)
            return

        def loaded(plan) -> None:
            self._set_report(render_plan(plan))
            if plan.write_blockers:
                self.status_var.set(f"Dry run complete: {len(plan.write_blockers)} export blocker(s)")
            else:
                self.status_var.set("Dry run complete; review every warning before export")

        self._run_job(
            "Building dry-run plan…",
            lambda: _build_plan_from_selection(selection),
            loaded,
        )

    def _create(self) -> None:
        from tkinter import messagebox

        output_value = self.output_var.get().strip()
        if not output_value:
            messagebox.showerror(
                "Kobra S1 Optimizer", "Choose a new output path", parent=self.root
            )
            return
        output = Path(output_value).expanduser().resolve()
        report = output.with_name(f"{output.stem}_changes.txt")
        if output.exists():
            messagebox.showerror(
                "Kobra S1 Optimizer",
                f"Refusing to overwrite existing output: {output}",
                parent=self.root,
            )
            return
        if report.exists():
            messagebox.showerror(
                "Kobra S1 Optimizer",
                f"Refusing to overwrite existing report: {report}",
                parent=self.root,
            )
            return
        try:
            selection = self._build_selected_plan()
        except InspectorError as exc:
            messagebox.showerror("Kobra S1 Optimizer", str(exc), parent=self.root)
            return

        def work():
            plan = _build_plan_from_selection(selection)
            result = write_optimized_archive(plan, output)
            text = render_plan(plan)
            text += "\n\nOUTPUT VALIDATION\n"
            text += f"- output: {result.output_path}\n"
            text += f"- output SHA-256: {result.output_sha256}\n"
            text += f"- changed members: {', '.join(result.changed_members)}\n"
            text += f"- unchanged members verified: {result.unchanged_members_verified}\n"
            try:
                with report.open("x", encoding="utf-8", newline="\n") as stream:
                    stream.write(text)
                    stream.write("\n")
            except OSError as exc:
                raise PlanError(
                    f"3MF was created, but its report could not be written: {exc}"
                ) from exc
            return result, text, report

        def loaded(value) -> None:
            result, text, report_path = value
            self._set_report(text)
            self.status_var.set("Validated output created")
            messagebox.showinfo(
                "Kobra S1 Optimizer",
                "Validated 3MF created.\n\n"
                f"Output: {result.output_path}\n"
                f"Report: {report_path}\n\n"
                "Open and slice it in Anycubic Slicer Next before printing.\n"
                f"Check Plate Type is {selection[13]}: "
                "the slicer may restore its remembered plate preference.",
                parent=self.root,
            )

        self._run_job("Creating and validating output…", work, loaded)


def main() -> int:
    try:
        import tkinter as tk
    except ImportError as exc:
        raise InspectorError("Tkinter is not available in this Python installation") from exc
    root = tk.Tk()
    OptimizerApp(root)
    root.mainloop()
    return 0
