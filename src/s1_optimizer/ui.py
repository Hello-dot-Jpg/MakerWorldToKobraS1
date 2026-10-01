"""Shared desktop presentation; no conversion or preset-install decisions."""
import tkinter as tk
from tkinter import ttk

BG = "#171b22"
PANEL = "#222832"
FIELD = "#2c3441"
TEXT = "#edf2f8"
MUTED = "#b0bdce"
BLUE = "#0074d9"


def lock_controls(root):
    """Restore original readonly/disabled states rather than making all editable."""
    states = {}
    def visit(parent):
        for widget in parent.winfo_children():
            if isinstance(widget, (ttk.Entry, ttk.Combobox, ttk.Button, ttk.Checkbutton, tk.Listbox)):
                states[widget] = widget.cget("state")
                widget.configure(state="disabled")
            visit(widget)
    visit(root)
    return states


def apply_theme(root):
    root.configure(background=BG)
    root.option_add("*TCombobox*Listbox.background", FIELD)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", BLUE)
    root.option_add("*TCombobox*Listbox.selectForeground", "white")
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", background=PANEL, foreground=TEXT, font=("Segoe UI", 10))
    style.configure("TFrame", background=BG)
    style.configure("Card.TFrame", background=PANEL)
    style.configure("TLabel", background=BG, foreground=TEXT)
    style.configure("Card.TLabel", background=PANEL)
    style.configure("Muted.TLabel", foreground=MUTED)
    style.configure("Hint.TLabel", foreground=MUTED, background=PANEL, font=("Segoe UI", 9))
    style.configure("Title.TLabel", font=("Segoe UI", 21, "bold"))
    style.configure("Section.TLabel", background=PANEL, font=("Segoe UI", 11, "bold"))
    style.configure("Badge.TLabel", background=BLUE, foreground="white", padding=(10, 5))
    style.configure("TButton", background=FIELD, foreground=TEXT, padding=(12, 7), borderwidth=0)
    style.map("TButton", background=[("active", "#3b485b"), ("disabled", PANEL)],
              foreground=[("disabled", "#8995a5")])
    style.configure("Primary.TButton", background=BLUE, foreground="white")
    style.map("Primary.TButton", background=[("disabled", "#30425a"), ("active", "#0062ba")])
    style.configure("TEntry", fieldbackground=FIELD, foreground=TEXT, insertcolor=TEXT, padding=6,
                    bordercolor="#536176", lightcolor=FIELD, darkcolor=FIELD)
    style.map("TEntry", bordercolor=[("focus", BLUE)])
    style.configure("TCombobox", fieldbackground=FIELD, background=FIELD, foreground=TEXT,
                    arrowcolor=TEXT, padding=5, bordercolor="#536176", lightcolor=FIELD, darkcolor=FIELD)
    style.map("TCombobox", fieldbackground=[("readonly", FIELD), ("disabled", PANEL)],
              foreground=[("disabled", "#8995a5"), ("readonly", TEXT)],
              selectbackground=[("readonly", FIELD)], selectforeground=[("readonly", TEXT)])
    style.configure("TCheckbutton", background=PANEL, foreground=TEXT, padding=(0, 5))
    style.map("TCheckbutton", background=[("active", PANEL)], foreground=[("disabled", "#8995a5")])
    style.configure("TLabelframe", background=PANEL, bordercolor=FIELD, relief="flat")
    style.configure("TLabelframe.Label", background=PANEL, foreground=TEXT, font=("Segoe UI", 11, "bold"))
    style.configure("TNotebook", background=BG, borderwidth=0, bordercolor=BG, lightcolor=BG, darkcolor=BG, tabmargins=(0, 8, 0, 8))
    style.configure("TNotebook.Tab", background=PANEL, foreground=MUTED, padding=(22, 10))
    style.map("TNotebook.Tab", background=[("selected", BLUE)], foreground=[("selected", "white")],
              padding=[("selected", (22, 10))], lightcolor=[("selected", BLUE), ("!selected", PANEL)])
    style.configure("TPanedwindow", background=BG)
    style.configure("Vertical.TScrollbar", background=FIELD, troughcolor=BG, arrowcolor=MUTED, borderwidth=0)
    style.configure("Horizontal.TProgressbar", background=BLUE, troughcolor=BG, borderwidth=0)


def list_style(widget):
    widget.configure(background=FIELD, foreground=TEXT, selectbackground=BLUE,
                     selectforeground="white", highlightthickness=0, borderwidth=0,
                     relief="flat", activestyle="none", font=("Segoe UI", 9))


def report_widget(parent):
    parent.rowconfigure(0, weight=1)
    parent.columnconfigure(0, weight=1)
    widget = tk.Text(parent, wrap="word", state="disabled", background=PANEL,
                     foreground=TEXT, selectbackground=BLUE, insertbackground=TEXT,
                     relief="flat", borderwidth=0, padx=14, pady=12,
                     font=("Segoe UI", 10), spacing1=2, spacing3=3, width=40, height=12)
    scroll = ttk.Scrollbar(parent, command=widget.yview)
    widget.configure(yscrollcommand=scroll.set)
    widget.grid(row=0, column=0, sticky="nsew")
    scroll.grid(row=0, column=1, sticky="ns")
    return widget


class ScrollForm(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, background=BG, highlightthickness=0, width=565)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(self, command=self.canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.body = ttk.Frame(self.canvas)
        self.body.columnconfigure(0, weight=1)
        item = self.canvas.create_window(0, 0, window=self.body, anchor="nw")
        self.body.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(item, width=e.width))
        self.bind_id = self.winfo_toplevel().bind("<MouseWheel>", self._wheel, add="+")
        # Scroll after keyboard focus changes, never on mouse-down: moving a
        # button between mouse-down/up can cancel the user's click.
        self.winfo_toplevel().bind("<KeyRelease-Tab>", self._reveal_focus, add="+")

    def _contains(self, widget):
        while widget is not None:
            if widget is self:
                return True
            widget = getattr(widget, "master", None)
        return False

    def _reveal_focus(self, event):
        if not self._contains(event.widget) or event.widget is self.canvas:
            return
        y = event.widget.winfo_rooty() - self.body.winfo_rooty()
        visible_top = self.canvas.canvasy(0)
        if y < visible_top or y + event.widget.winfo_height() > visible_top + self.canvas.winfo_height():
            self.canvas.yview_moveto(max(0, y - 12) / max(1, self.body.winfo_height()))

    def _wheel(self, event):
        # Only scroll this form; leave report/list/dropdown wheel behavior alone.
        if isinstance(event.widget, (tk.Text, tk.Listbox, ttk.Combobox)):
            return
        if self._contains(event.widget) and event.delta:
            steps = max(1, int(abs(event.delta) / 120))
            self.canvas.yview_scroll(-steps if event.delta > 0 else steps, "units")
            return "break"


def card(parent, row, title, hint=None):
    frame = ttk.Frame(parent, style="Card.TFrame", padding=16)
    frame.grid(row=row, column=0, sticky="ew", pady=(0, 10))
    frame.columnconfigure(0, weight=1)
    ttk.Label(frame, text=title, style="Section.TLabel").grid(row=0, column=0, sticky="w")
    if hint:
        ttk.Label(frame, text=hint, style="Hint.TLabel", wraplength=510).grid(row=1, column=0, sticky="w", pady=(3, 8))
    body = ttk.Frame(frame, style="Card.TFrame")
    body.grid(row=2, column=0, sticky="ew", pady=(8, 0))
    body.columnconfigure(0, weight=1)
    return body


def disclosure(parent, row, title):
    frame = ttk.Frame(parent, style="Card.TFrame", padding=12)
    frame.grid(row=row, column=0, sticky="ew", pady=(0, 10))
    frame.columnconfigure(0, weight=1)
    body = ttk.Frame(frame, style="Card.TFrame")
    body.columnconfigure(0, weight=1)
    button = ttk.Button(frame, text=f"+  {title}")
    button.grid(row=0, column=0, sticky="ew")
    def toggle():
        if body.winfo_manager():
            body.grid_remove()
            button.configure(text=f"+  {title}")
        else:
            body.grid(row=1, column=0, sticky="ew", pady=(12, 0))
            button.configure(text=f"−  {title}")
    button.configure(command=toggle)
    return body


def field(parent, row, label, variable, *, values=None, width=None):
    ttk.Label(parent, text=label, style="Card.TLabel").grid(row=row * 2, column=0, sticky="w", pady=(6, 4))
    options = {"textvariable": variable}
    if width:
        options["width"] = width
    widget = ttk.Entry(parent, **options) if values is None else ttk.Combobox(parent, values=values, state="readonly", **options)
    widget.grid(row=row * 2 + 1, column=0, sticky="ew", pady=(0, 5))
    return widget


def workspace(notebook, title):
    tab = ttk.Frame(notebook, padding=(14, 6, 14, 12))
    notebook.add(tab, text=title)
    tab.rowconfigure(0, weight=1)
    tab.columnconfigure(0, weight=1)
    panes = ttk.Panedwindow(tab, orient="horizontal")
    panes.grid(row=0, column=0, sticky="nsew")
    form = ScrollForm(panes)
    right = ttk.Frame(panes, padding=(16, 0, 0, 0))
    panes.add(form, weight=3)
    panes.add(right, weight=2)
    right.columnconfigure(0, weight=1)
    return tab, form.body, right


def build_converter(app, notebook, bundles):
    tab, form, right = workspace(notebook, "3MF projects")
    source = card(form, 0, "1  Open a project", "Your original file stays untouched. Browse, or paste a path and press Enter.")
    app.source_entry = ttk.Entry(source, textvariable=app.source_var)
    app.source_entry.grid(row=0, column=0, sticky="ew", pady=(0, 8))
    app.source_entry.bind("<Return>", app._source_entered)
    app.source_browse_button = ttk.Button(source, text="Browse 3MF…", command=app._browse_source)
    app.source_browse_button.grid(row=1, column=0, sticky="w")
    app.busy_widgets.extend((app.source_entry, app.source_browse_button))

    settings = card(form, 1, "2  Choose your S1 setup", "Discover profiles to suggest the closest match. You can change every choice.")
    split = ttk.Frame(settings, style="Card.TFrame")
    split.grid(row=0, column=0, sticky="ew")
    split.columnconfigure((0, 1), weight=1)
    for col, title, var, values in (
        (0, "Nozzle size (mm)", app.nozzle_var, ("0.25", "0.4", "0.6", "0.8")),
        (1, "Nozzle material", app.physical_nozzle_var, ("profile", "brass", "hardened-steel", "stainless-steel", "bimetal", "other")),
    ):
        group = ttk.Frame(split, style="Card.TFrame", padding=(0, 0, 10 if col == 0 else 0, 0))
        group.grid(row=0, column=col, sticky="ew")
        group.columnconfigure(0, weight=1)
        box = field(group, 0, title, var, values=values, width=16)
        if col == 0:
            app.nozzle_box = box
    discover = ttk.Button(settings, text="Discover matching profiles", command=app._discover_profiles)
    discover.grid(row=1, column=0, sticky="ew", pady=(6, 8))
    app.busy_widgets.append(discover)
    app.target_box = field(settings, 1, "Printer profile", app.target_var, values=())
    app.target_box.bind("<<ComboboxSelected>>", app._target_changed)
    app.process_box = field(settings, 2, "Print profile", app.process_var, values=())
    layer = ttk.Frame(settings, style="Card.TFrame")
    layer.grid(row=6, column=0, sticky="ew", pady=6)
    app.use_process_layer_height_box = ttk.Checkbutton(layer, text="Use print profile's layer height", variable=app.use_process_layer_height_var)
    app.use_process_layer_height_box.pack(anchor="w")
    ttk.Label(layer, text="Otherwise keep the source layer height. A custom value overrides both.", style="Hint.TLabel", wraplength=490).pack(anchor="w")
    custom = ttk.Frame(layer, style="Card.TFrame")
    custom.pack(fill="x", pady=(6, 0))
    ttk.Label(custom, text="Custom layer height (mm)", style="Card.TLabel").pack(side="left")
    ttk.Entry(custom, textvariable=app.custom_layer_height_var, width=8).pack(side="left", padx=10)
    app.busy_widgets.append(app.use_process_layer_height_box)
    app.filament_frame = ttk.LabelFrame(settings, text="Filament assignments", padding=10)
    app.filament_frame.grid(row=7, column=0, sticky="ew", pady=(8, 0))
    app.filament_frame.columnconfigure(1, weight=1)
    ttk.Label(app.filament_frame, text="Load a project and discover profiles.", style="Hint.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")

    options = card(form, 2, "3  Adjust the conversion")
    field(options, 0, "Build plate", app.bed_type_var, values=app.SUPPORTED_BED_TYPES)
    ttk.Label(options, text="Check Plate Type again in the slicer: it may restore its last-used choice.", style="Hint.TLabel", wraplength=490).grid(row=2, column=0, sticky="w", pady=(0, 8))
    app.nice_supports_beta_box = ttk.Checkbutton(options, text="Nice supports - beta", variable=app.nice_supports_beta_var)
    app.nice_supports_beta_box.grid(row=3, column=0, sticky="w")
    ttk.Label(options, text="Use the reviewed tree-support settings. Check supports in Preview.", style="Hint.TLabel", wraplength=490).grid(row=4, column=0, sticky="w")
    app.scale_to_fit_box = ttk.Checkbutton(options, text="Scale to fit S1 plate", variable=app.scale_to_fit_var)
    app.scale_to_fit_box.grid(row=5, column=0, sticky="w", pady=(6, 0))
    ttk.Label(options, text="Shrink oversized plates only. This changes part dimensions; review each scale in the report.", style="Hint.TLabel", wraplength=490).grid(row=6, column=0, sticky="w")
    app.busy_widgets.extend((app.nice_supports_beta_box, app.scale_to_fit_box))

    hardware = disclosure(form, 3, "Advanced · hotend limits")
    app.hotend_type_box = field(hardware, 0, "Hotend / heatbreak", app.hotend_type_var, values=("Unspecified", "PTFE-lined upper section", "All-metal later version", "Aftermarket ceramic", "Other / custom"))
    field(hardware, 1, "Confirmed safe nozzle temperature (°C, optional)", app.hotend_max_var)
    ttk.Label(hardware, text="Hotend choice is recorded only. A confirmed limit can lower selected filament temperatures; no physical limit is guessed.", style="Hint.TLabel", wraplength=490).grid(row=4, column=0, sticky="w")
    bundle = disclosure(form, 4, "Advanced · community profile bundles")
    app.bundle_list = tk.Listbox(bundle, height=3, selectmode="extended", exportselection=False)
    list_style(app.bundle_list)
    app.bundle_list.grid(row=0, column=0, sticky="ew")
    for path in bundles:
        app.bundle_list.insert("end", str(path))
    buttons = ttk.Frame(bundle, style="Card.TFrame")
    buttons.grid(row=1, column=0, sticky="ew", pady=(8, 0))
    ttk.Button(buttons, text="Add bundle…", command=app._add_bundle).pack(side="left")
    ttk.Button(buttons, text="Remove selected", command=app._remove_bundle).pack(side="left", padx=8)

    export = card(right, 4, "4  Export a reviewed project", "Save a new copy. Existing files are never overwritten.")
    ttk.Entry(export, textvariable=app.output_var).grid(row=0, column=0, sticky="ew")
    ttk.Button(export, text="Choose output…", command=app._browse_output).grid(row=1, column=0, sticky="w", pady=8)
    actions = ttk.Frame(export, style="Card.TFrame")
    actions.grid(row=2, column=0, sticky="ew")
    analyze = ttk.Button(actions, text="Review changes", command=app._analyze)
    create = ttk.Button(actions, text="Export 3MF", command=app._create, style="Primary.TButton")
    analyze.pack(side="left", padx=(0, 8))
    create.pack(side="left")
    app.busy_widgets.extend((analyze, create))

    right.rowconfigure(3, weight=1)
    app.source_overview_var = tk.StringVar(value="No project loaded\n\nOpen a 3MF to see its original printer, nozzle and print settings.")
    ttk.Label(right, text="Original project", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w", pady=(4, 8))
    overview = ttk.Frame(right, style="Card.TFrame")
    overview.grid(row=1, column=0, sticky="ew", pady=(0, 16))
    app.source_overview_text = report_widget(overview)
    app.source_overview_text.configure(height=7)
    def update_overview(*_):
        app.source_overview_text.configure(state="normal")
        app.source_overview_text.delete("1.0", "end")
        app.source_overview_text.insert("1.0", app.source_overview_var.get())
        app.source_overview_text.configure(state="disabled")
    app.source_overview_var.trace_add("write", update_overview)
    update_overview()
    ttk.Label(right, text="Review & change report", font=("Segoe UI", 12, "bold")).grid(row=2, column=0, sticky="w", pady=(0, 8))
    report = ttk.Frame(right, style="Card.TFrame")
    report.grid(row=3, column=0, sticky="nsew")
    app.report_text = report_widget(report)
    app._set_report("Your review will appear here.\n\n1. Open a project.\n2. Discover profiles and choose your setup.\n3. Review changes before exporting.\n\nConversion never starts a print or changes your installed presets.")
    ttk.Label(tab, textvariable=app.status_var, style="Muted.TLabel", wraplength=1080).grid(row=1, column=0, sticky="ew", pady=(10, 0))
    app.progress = ttk.Progressbar(tab, mode="indeterminate")
    app.progress.grid(row=2, column=0, sticky="ew", pady=(6, 0))
    app.progress.grid_remove()


def build_preset_tab(tab, app, notebook):
    _, form, right = workspace(notebook, "Filament library · beta")
    sources = card(form, 0, "1  Add filament presets", "Convert standalone presets without changing a 3MF's filament assignments.")
    buttons = ttk.Frame(sources, style="Card.TFrame")
    buttons.grid(row=0, column=0, sticky="ew", pady=(0, 8))
    for index, (label, command) in enumerate((("JSON files…", tab.add_files), ("Folder…", tab.add_folder), ("Bundle…", tab.add_bundle), ("INI file…", tab.add_ini), ("Clear list", tab.clear))):
        button = ttk.Button(buttons, text=label, command=command)
        button.grid(row=index // 3, column=index % 3, sticky="ew", padx=(0, 6), pady=(0, 6))
        buttons.columnconfigure(index % 3, weight=1)
        app.busy_widgets.append(button)
    tab.files = tk.Listbox(sources, selectmode="extended", exportselection=False, height=5)
    list_style(tab.files)
    tab.files.grid(row=1, column=0, sticky="ew")
    ttk.Label(sources, text="Ctrl / Shift selects multiple presets. All added presets are selected initially.", style="Hint.TLabel", wraplength=490).grid(row=2, column=0, sticky="w", pady=(6, 0))

    setup = card(form, 1, "2  Choose destination & limits", "Select one or several nozzle sizes. Hardware limits are checked before export.")
    discover = ttk.Button(setup, text="Find installed S1 printers", command=tab.discover)
    discover.grid(row=0, column=0, sticky="ew", pady=(0, 8))
    app.busy_widgets.append(discover)
    tab.machine_box = tk.Listbox(setup, selectmode="extended", exportselection=False, height=4)
    list_style(tab.machine_box)
    tab.machine_box.grid(row=1, column=0, sticky="ew")
    ttk.Label(setup, text="Ctrl / Shift selects multiple nozzle sizes.", style="Hint.TLabel").grid(row=2, column=0, sticky="w", pady=6)
    field(setup, 2, "Nozzle material", tab.physical_nozzle, values=("profile", "hardened-steel", "brass", "stainless-steel", "bimetal"))
    field(setup, 3, "Hotend", tab.hotend, values=("unspecified", "ptfe-lined", "all-metal", "ceramic"))
    limits = ttk.Frame(setup, style="Card.TFrame")
    limits.grid(row=8, column=0, sticky="ew")
    limits.columnconfigure((0, 1), weight=1)
    for column, label, variable in ((0, "Nozzle ceiling (°C)", tab.nozzle_max), (1, "Bed ceiling (°C)", tab.bed_max)):
        group = ttk.Frame(limits, style="Card.TFrame", padding=(0, 0, 10 if column == 0 else 0, 0))
        group.grid(row=0, column=column, sticky="ew")
        group.columnconfigure(0, weight=1)
        field(group, 0, label, variable, width=12)
    ttk.Label(setup, text="Blank nozzle ceiling uses your hotend choice: PTFE 300°C; all-metal / ceramic 320°C. Confirm the bed limit separately.", style="Hint.TLabel", wraplength=490).grid(row=9, column=0, sticky="w", pady=6)

    advanced = disclosure(form, 2, "Advanced · base material & firmware")
    for row, label, command in ((0, "Choose destination base JSON…", tab.choose_base), (1, "Return to automatic matching", lambda: tab.explicit_base.set(""))):
        button = ttk.Button(advanced, text=label, command=command)
        button.grid(row=row, column=0, sticky="ew", pady=(0, 6))
        app.busy_widgets.append(button)
    ttk.Label(advanced, textvariable=tab.explicit_base, style="Hint.TLabel", wraplength=490).grid(row=2, column=0, sticky="w")
    ttk.Checkbutton(advanced, text="Correct material to the selected base (verify spool)", variable=tab.accept_base_material).grid(row=3, column=0, sticky="w")
    ttk.Checkbutton(advanced, text="Ceramic 350°C firmware change confirmed", variable=tab.ceramic_firmware).grid(row=4, column=0, sticky="w")
    ttk.Label(advanced, text="No firmware changes are made by this app. Unknown material bases or hardware limits block export.", style="Hint.TLabel", wraplength=490).grid(row=5, column=0, sticky="w")

    actions = card(form, 3, "3  Review & export", "Export creates a new folder of JSON / ZIP presets; it does not install them.")
    for row, label, command, style in ((0, "Review selected presets", lambda: tab.run(False), "TButton"), (1, "Export presets…", lambda: tab.run(True), "Primary.TButton")):
        button = ttk.Button(actions, text=label, command=command, style=style)
        button.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        app.busy_widgets.append(button)
    install = disclosure(form, 4, "Install or restore reviewed presets")
    ttk.Label(install, text="Close Anycubic first. Installation creates a complete preset backup; existing names are never overwritten.", style="Hint.TLabel", wraplength=490).grid(row=0, column=0, sticky="w", pady=(0, 8))
    for row, label, command in ((1, "Install reviewed export…", tab.install_reviewed), (2, "Restore an installation…", tab.rollback_reviewed)):
        button = ttk.Button(install, text=label, command=command)
        button.grid(row=row, column=0, sticky="ew", pady=(0, 6))
        app.busy_widgets.append(button)

    right.rowconfigure(2, weight=1)
    ttk.Label(right, text="Preset review", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w", pady=(4, 8))
    ttk.Label(right, text="Review the changes, warnings and blocked materials before importing. These are starting presets, not physical calibration.", style="Muted.TLabel", wraplength=360).grid(row=1, column=0, sticky="ew", pady=(0, 12))
    report = ttk.Frame(right, style="Card.TFrame")
    report.grid(row=2, column=0, sticky="nsew")
    tab.report = report_widget(report)
    tab.report.configure(state="normal")
    tab.report.insert("1.0", "Start with the filament presets you want to import.\n\nChoose the destination nozzle sizes and confirm hardware limits, then select Review.\n\nExport and installation are separate steps. Review never changes installed presets.")
    tab.report.configure(state="disabled")
    ttk.Label(right, textvariable=tab.status, style="Muted.TLabel", wraplength=360).grid(row=3, column=0, sticky="ew", pady=(12, 0))
