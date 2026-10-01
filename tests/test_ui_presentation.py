"""Presentation regressions without opening a native window."""
import unittest
from unittest.mock import Mock, patch

from s1_optimizer.gui import OptimizerApp, _source_overview, _display
from tests import test_gui_model as model_fixtures


class PresentationTests(unittest.TestCase):
    def test_same_named_filaments_from_different_bundles_stay_distinguishable(self):
        a = _display("Generic PETG", "community", "community:aaa:generic-petg")
        b = _display("Generic PETG", "community", "community:bbb:generic-petg")
        self.assertNotEqual(a, b)
        self.assertNotIn("community:aaa", a)
        self.assertIn("Community", a)

    def test_source_overview_keeps_source_values_and_order(self):
        # Access the helper through its module to avoid unittest rediscovery.
        summary = model_fixtures.GuiModelTests._summary(nozzle_diameter="0.6", layer_height="0.18")
        text = _source_overview(summary)
        self.assertIn("Nozzle  0.6 mm", text)
        self.assertIn("Layer  0.18 mm", text)
        self.assertIn("Materials  1: PETG", text)
        self.assertNotIn("0.20 mm", text)
        self.assertIn("No project loaded", _source_overview(None))

    def test_busy_restores_each_original_control_state(self):
        app = Mock()
        app._busy_states = {}
        controls = {Mock(): "readonly", Mock(): "normal", Mock(): "disabled"}
        for widget in controls:
            widget.winfo_exists.return_value = True
        with patch("s1_optimizer.ui.lock_controls", return_value=controls):
            OptimizerApp._set_busy(app, True, "Working")
        app.progress.start.assert_called_once()
        OptimizerApp._set_busy(app, False, "Ready")
        for widget, state in controls.items():
            widget.configure.assert_called_once_with(state=state)
        app.progress.stop.assert_called_once()

    def test_report_updates_overview_without_changing_report_text(self):
        app = Mock()
        app.source_summary = None
        OptimizerApp._set_report(app, "Original review wording")
        app.source_overview_var.set.assert_called_once_with(_source_overview(None))
        app.report_text.insert.assert_called_once_with("1.0", "Original review wording")
