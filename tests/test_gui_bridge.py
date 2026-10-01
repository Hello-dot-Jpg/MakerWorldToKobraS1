"""GUI control-to-worker contract tests without a display or installed slicer."""
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

from s1_optimizer.gui import OptimizerApp, _build_plan_from_selection
from s1_optimizer.gui_model import SourceFilamentSlot, SourceSummary
from s1_optimizer.errors import PlanError


class GuiBridgeTests(unittest.TestCase):
    @staticmethod
    def _var(value=None):
        state = {"value": value}
        return SimpleNamespace(
            get=lambda: state["value"],
            set=lambda new_value: state.__setitem__("value", new_value),
        )

    def test_new_source_reset_clears_every_conversion_choice(self):
        app = SimpleNamespace(
            source_summary=object(), machine_dir=Path("machines"),
            process_dir=Path("processes"), filament_dir=Path("filaments"),
            targets_by_display={"old": object()}, processes_by_display={"old": object()},
            target_box=Mock(), process_box=Mock(),
            target_var=self._var("old"), process_var=self._var("old"),
            nozzle_var=self._var("0.8"), physical_nozzle_var=self._var("bimetal"),
            hotend_type_var=self._var("Aftermarket ceramic"), hotend_max_var=self._var("320"),
            nice_supports_beta_var=self._var(True), use_process_layer_height_var=self._var(True),
            custom_layer_height_var=self._var("0.3"), bed_type_var=self._var("Cool Plate"),
            scale_to_fit_var=self._var(True),
            output_var=self._var("old-output.3mf"), _clear_filament_rows=Mock(),
            _set_report=Mock(),
        )
        OptimizerApp._reset_for_source_load(app)
        self.assertIsNone(app.source_summary)
        self.assertIsNone(app.machine_dir)
        self.assertEqual(app.targets_by_display, {})
        self.assertEqual(app.processes_by_display, {})
        self.assertEqual(app.target_var.get(), "")
        self.assertEqual(app.process_var.get(), "")
        self.assertEqual(app.nozzle_var.get(), "0.4")
        self.assertEqual(app.physical_nozzle_var.get(), "profile")
        self.assertEqual(app.hotend_type_var.get(), "Unspecified")
        self.assertEqual(app.hotend_max_var.get(), "")
        self.assertFalse(app.nice_supports_beta_var.get())
        self.assertFalse(app.use_process_layer_height_var.get())
        self.assertEqual(app.custom_layer_height_var.get(), "")
        self.assertEqual(app.bed_type_var.get(), "Textured PEI Plate")
        self.assertFalse(app.scale_to_fit_var.get())
        self.assertEqual(app.output_var.get(), "")
        app._clear_filament_rows.assert_called_once()

    def test_enter_in_source_box_runs_the_single_load_action(self):
        app = SimpleNamespace(_load_source=Mock())
        self.assertEqual(OptimizerApp._source_entered(app), "break")
        app._load_source.assert_called_once_with()

    def test_source_load_resets_before_inspection_and_suggests_nozzle(self):
        summary = SourceSummary(
            "source.3mf", "Printer", "0.20 Standard", "0.6", "hardened_steel",
            "0.2", "0.24", "0.62", "3", "20%", "gyroid", "1",
            "tree(auto)", "Textured PEI Plate",
            (SourceFilamentSlot(1, "Generic PETG", "PETG"),),
        )
        reset = Mock()
        report = Mock()
        status = self._var()
        nozzle = self._var("0.4")

        def run(_message, work, loaded):
            self.assertTrue(reset.called)
            loaded(work())

        app = SimpleNamespace(
            root=None, source_var=self._var("source.3mf"),
            _reset_for_source_load=reset, _run_job=run,
            source_summary=None, nozzle_var=nozzle, _set_report=report,
            status_var=status,
        )
        with patch("s1_optimizer.gui.summarize_source", return_value=summary):
            OptimizerApp._load_source(app)
        self.assertIs(app.source_summary, summary)
        self.assertEqual(nozzle.get(), "0.6")
        self.assertIn("suggested 0.6 mm", status.get())
        self.assertIn("Layer height: 0.2 mm", report.call_args.args[0])
    def test_existing_output_or_report_prevents_any_export_job(self):
        with tempfile.TemporaryDirectory() as directory:
            for existing_kind in ("output", "report"):
                with self.subTest(existing_kind=existing_kind):
                    output = Path(directory) / f"{existing_kind}.3mf"
                    report = output.with_name(f"{output.stem}_changes.txt")
                    existing = output if existing_kind == "output" else report
                    existing.write_bytes(b"user-owned content")
                    app = SimpleNamespace(root=None, output_var=SimpleNamespace(get=lambda: str(output)),
                                          _run_job=Mock(), _build_selected_plan=Mock())
                    with patch("tkinter.messagebox.showerror") as error:
                        OptimizerApp._create(app)
                    error.assert_called_once()
                    app._run_job.assert_not_called()
                    app._build_selected_plan.assert_not_called()
                    self.assertEqual(existing.read_bytes(), b"user-owned content")

    def test_invalid_selection_does_not_queue_export(self):
        with tempfile.TemporaryDirectory() as directory:
            app = SimpleNamespace(root=None,
                                  output_var=SimpleNamespace(get=lambda: str(Path(directory) / "new.3mf")),
                                  _run_job=Mock(),
                                  _build_selected_plan=Mock(side_effect=PlanError("Select a filament")))
            with patch("tkinter.messagebox.showerror") as error:
                OptimizerApp._create(app)
            self.assertIn("Select a filament", error.call_args.args[1])
            app._run_job.assert_not_called()

    def test_export_notice_uses_captured_plate_choice(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "new.3mf"
            selected = (None,) * 13 + ("Textured PEI Plate", False)
            app = SimpleNamespace(
                root=None, output_var=self._var(str(output)),
                bed_type_var=self._var("Textured PEI Plate"),
                _build_selected_plan=lambda: selected,
                _set_report=Mock(), status_var=self._var(),
            )
            def execute(_message, work, loaded):
                app.bed_type_var.set("Cool Plate")
                loaded(work())
            app._run_job = execute
            result = SimpleNamespace(
                output_path=str(output), output_sha256="hash",
                changed_members=("Metadata/project_settings.config",),
                unchanged_members_verified=3,
            )
            with patch("s1_optimizer.gui._build_plan_from_selection", return_value="plan"), \
                 patch("s1_optimizer.gui.write_optimized_archive", return_value=result), \
                 patch("s1_optimizer.gui.render_plan", return_value="report"), \
                 patch("tkinter.messagebox.showinfo") as notice:
                OptimizerApp._create(app)
            message = notice.call_args.args[1]
            self.assertIn("Check Plate Type is Textured PEI Plate", message)
            self.assertIn("remembered plate preference", message)
            self.assertNotIn("Check Plate Type is Cool Plate", message)
            self.assertEqual(app.status_var.get(), "Validated output created")

    def test_report_race_is_explicit_and_does_not_overwrite_existing_report(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "new.3mf"
            report = output.with_name("new_changes.txt")
            def execute(_message, work, _loaded):
                # Another process creates the report after the GUI preflight.
                report.write_text("keep this", encoding="utf-8")
                work()
            app = SimpleNamespace(root=None, output_var=SimpleNamespace(get=lambda: str(output)),
                                  _build_selected_plan=lambda: (), _run_job=execute)
            result = SimpleNamespace(output_path=str(output), output_sha256="hash",
                                     changed_members=("Metadata/project_settings.config",),
                                     unchanged_members_verified=3)
            with patch("s1_optimizer.gui._build_plan_from_selection", return_value="plan"), \
                 patch("s1_optimizer.gui.write_optimized_archive", return_value=result), \
                 patch("s1_optimizer.gui.render_plan", return_value="report"), \
                 self.assertRaisesRegex(PlanError, "3MF was created, but its report"):
                OptimizerApp._create(app)
            self.assertEqual(report.read_text(encoding="utf-8"), "keep this")

    def test_gui_snapshot_reaches_planner_without_losing_options_or_slot_order(self):
        def var(value):
            return SimpleNamespace(get=lambda: value)

        for label, hotend in (("Unspecified", "unspecified"),
                              ("PTFE-lined upper section", "ptfe-lined"),
                              ("All-metal later version", "all-metal"),
                              ("Aftermarket ceramic", "aftermarket-ceramic"),
                              ("Other / custom", "other")):
            with self.subTest(hotend=label):
                app = SimpleNamespace(
                    _selection=lambda: ("machine choice", "process choice", ("PETG slot", "TPU slot")),
                    source_summary=SimpleNamespace(path="source.3mf"),
                    machine_dir=Path("machines"), process_dir=Path("processes"), filament_dir=Path("filaments"),
                    hotend_type_var=var(label), hotend_max_var=var(" 270 "),
                    nice_supports_beta_var=var(True), use_process_layer_height_var=var(False),
                    physical_nozzle_var=var("hardened-steel"), custom_layer_height_var=var(" 0.18 "),
                    bed_type_var=var("Textured PEI Plate"),
                    scale_to_fit_var=var(True),
                )
                snapshot = OptimizerApp._build_selected_plan(app)
                # Edits after clicking must not alter the queued request.
                app.custom_layer_height_var = var("0.4")
                app.bed_type_var = var("Cool Plate")
                with patch("s1_optimizer.gui.resolve_machine_target", return_value="machine") as machine, \
                     patch("s1_optimizer.gui.resolve_process_target", return_value="process") as process, \
                     patch("s1_optimizer.gui.resolve_filament_target", side_effect=["PETG", "TPU"]) as filament, \
                     patch("s1_optimizer.gui.load_rules", return_value="rules"), \
                     patch("s1_optimizer.gui.build_conversion_plan", return_value="result") as planner:
                    self.assertEqual(_build_plan_from_selection(snapshot), "result")
                    machine.assert_called_once_with("machine choice", machine_dir=Path("machines"))
                    process.assert_called_once_with("process choice", process_dir=Path("processes"))
                    self.assertEqual([call.args[0] for call in filament.call_args_list], ["PETG slot", "TPU slot"])
                    planner.assert_called_once_with(
                        "source.3mf", "machine", process="process", filaments=("PETG", "TPU"),
                        hotend_type=hotend, max_nozzle_temperature="270", nice_supports_beta=True,
                        use_process_layer_height=False, nozzle_hardware_type="hardened-steel",
                        layer_height_override="0.18", bed_type="Textured PEI Plate", rules="rules",
                        scale_to_fit=True,
                    )
