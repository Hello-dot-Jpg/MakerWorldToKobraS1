from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from s1_optimizer.errors import TargetDiscoveryError
from s1_optimizer.preset_gui import FilamentProfileTab


class PresetGuiTests(unittest.TestCase):
    def _tab(self, explicit_base=""):
        tab = object.__new__(FilamentProfileTab)
        tab.paths = [SimpleNamespace(name="source.json")]
        tab.machine_options = {"target": SimpleNamespace(nozzle_diameter="0.6")}
        tab.files = SimpleNamespace(curselection=lambda: [0])
        tab.machine_box = SimpleNamespace(curselection=lambda: [0], get=lambda i: "target")
        values = {"nozzle_max": "", "bed_max": "100", "physical_nozzle": "hardened-steel",
                  "hotend": "unspecified", "ceramic_firmware": False, "explicit_base": explicit_base, "accept_base_material": False}
        for name, value in values.items():
            setattr(tab, name, SimpleNamespace(get=Mock(return_value=value)))
        tab.app = SimpleNamespace(_run_job=Mock(), root=None)
        return tab

    def test_worker_snapshots_hotend_and_firmware_without_touching_tk(self):
        tab = object.__new__(FilamentProfileTab)
        tab.paths = [SimpleNamespace(name="test.json")]
        target = SimpleNamespace(nozzle_diameter="0.6")
        tab.machine_options = {"target": target}
        tab.files = SimpleNamespace(curselection=lambda: [0])
        tab.machine_box = SimpleNamespace(curselection=lambda: [0], get=lambda i: "target")
        variables = {"nozzle_max": "", "bed_max": "100", "physical_nozzle": "hardened-steel",
                     "hotend": "ceramic", "ceramic_firmware": True, "explicit_base": "", "accept_base_material": False}
        for name, value in variables.items():
            setattr(tab, name, SimpleNamespace(get=Mock(return_value=value)))
        tab.app = SimpleNamespace(_run_job=Mock())
        tab.run(False)
        worker = tab.app._run_job.call_args.args[1]
        for name in variables:
            getattr(tab, name).get.side_effect = AssertionError("Worker accessed live Tk state")
        plan = SimpleNamespace(blockers=[])
        with patch("s1_optimizer.preset_gui.default_filament_profile_dir"), \
             patch("s1_optimizer.preset_gui.default_machine_profile_dir"), \
             patch("s1_optimizer.preset_gui.resolve_machine_target"), \
             patch("s1_optimizer.preset_gui.discover_filaments"), \
             patch("s1_optimizer.preset_gui.read_source", return_value=({"filament_type": ["PETG"]}, [])), \
             patch("s1_optimizer.preset_gui.match_filament_option"), \
             patch("s1_optimizer.preset_gui.resolve_filament_target"), \
             patch("s1_optimizer.preset_gui.convert_preset", return_value=plan) as convert:
            self.assertEqual(worker(), ([plan], [], None))
        self.assertEqual(convert.call_args.kwargs, {
            "max_nozzle_temp": "", "max_bed_temp": "100", "nozzle_material": "hardened-steel",
            "hotend": "ceramic", "ceramic_firmware_confirmed": True, "accept_base_material": False})

    def test_nonempty_explicit_base_is_snapshotted_and_loaded_without_matching(self):
        tab = self._tab("C:/review/base.json")
        tab.run(False)
        worker = tab.app._run_job.call_args.args[1]
        tab.explicit_base.get.side_effect = AssertionError("Worker accessed live Tk state")
        plan, errors, folder = SimpleNamespace(blockers=[]), [], None
        with patch("s1_optimizer.preset_gui.default_filament_profile_dir"), \
             patch("s1_optimizer.preset_gui.default_machine_profile_dir"), \
             patch("s1_optimizer.preset_gui.resolve_machine_target", return_value=SimpleNamespace()), \
             patch("s1_optimizer.preset_gui.discover_filaments", side_effect=AssertionError("Explicit base must not require automatic discovery")), \
             patch("s1_optimizer.preset_gui.read_source", return_value=({"filament_type": ["PETG"]}, [])), \
             patch("s1_optimizer.preset_gui.load_standalone_filament_base", return_value="loaded-base") as load, \
             patch("s1_optimizer.preset_gui.match_filament_option") as match, \
             patch("s1_optimizer.preset_gui.convert_preset", return_value=plan) as convert:
            self.assertEqual(worker(), ([plan], errors, folder))
        load.assert_called_once_with("C:/review/base.json", unittest.mock.ANY)
        match.assert_not_called()
        self.assertIs(convert.call_args.args[2], "loaded-base")

    def test_target_discovery_error_is_per_source_error_and_blocks_export(self):
        tab = self._tab("C:/review/bad.json")
        with patch("tkinter.filedialog.askdirectory", return_value="C:/exports"):
            tab.run(True)
        worker = tab.app._run_job.call_args.args[1]
        failure = TargetDiscoveryError("invalid explicit base")
        with patch("s1_optimizer.preset_gui.default_filament_profile_dir"), \
             patch("s1_optimizer.preset_gui.default_machine_profile_dir"), \
             patch("s1_optimizer.preset_gui.resolve_machine_target", return_value=SimpleNamespace()), \
             patch("s1_optimizer.preset_gui.discover_filaments", return_value=[]), \
             patch("s1_optimizer.preset_gui.read_source", return_value=({"filament_type": ["PETG"]}, [])), \
             patch("s1_optimizer.preset_gui.load_standalone_filament_base", side_effect=failure), \
             patch("s1_optimizer.preset_gui.export_presets") as export:
            plans, errors, folder = worker()
        self.assertEqual(plans, [])
        self.assertEqual(errors, ["source.json / 0.6 mm: invalid explicit base"])
        self.assertIsNone(folder)
        export.assert_not_called()

    def test_material_correction_without_explicit_base_rejects_before_worker_or_folder_picker(self):
        tab = self._tab()
        tab.accept_base_material = SimpleNamespace(get=Mock(return_value=True))
        with patch("tkinter.messagebox.showerror") as showerror, \
             patch("tkinter.filedialog.askdirectory") as askdirectory:
            tab.run(True)
        showerror.assert_called_once()
        askdirectory.assert_not_called()
        tab.app._run_job.assert_not_called()

    def test_missing_source_or_target_rejects_before_worker(self):
        for missing in ("source", "target"):
            tab = self._tab()
            if missing == "source":
                tab.files = SimpleNamespace(curselection=lambda: [])
            else:
                tab.machine_box = SimpleNamespace(curselection=lambda: [], get=lambda i: "target")
            with patch("tkinter.messagebox.showerror") as showerror, \
                 patch("tkinter.filedialog.askdirectory") as askdirectory:
                tab.run(True)
            showerror.assert_called_once()
            askdirectory.assert_not_called()
            tab.app._run_job.assert_not_called()

    def test_canceled_export_starts_no_worker(self):
        tab = self._tab()
        with patch("tkinter.filedialog.askdirectory", return_value="") as askdirectory:
            tab.run(True)
        askdirectory.assert_called_once()
        tab.app._run_job.assert_not_called()
