import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path


ADDON_PATH = Path(__file__).resolve().parents[1] / "addon" / "budget_my_render.py"


def load_addon_module():
    handlers = types.ModuleType("bpy.app.handlers")
    handlers.persistent = lambda function: function
    handlers.depsgraph_update_post = []
    handlers.load_post = []

    app = types.ModuleType("bpy.app")
    app.handlers = handlers
    app.version_string = "4.2.0"
    app.version = (4, 2, 0)

    bpy = types.ModuleType("bpy")
    bpy.app = app
    bpy.data = types.SimpleNamespace(filepath="", scenes=[])
    bpy.context = types.SimpleNamespace()
    bpy.types = types.SimpleNamespace(Operator=object, Panel=object, Scene=object)
    bpy.utils = types.SimpleNamespace(register_class=lambda _class: None, unregister_class=lambda _class: None)
    bpy.props = types.SimpleNamespace(FloatProperty=lambda **_kwargs: None, StringProperty=lambda **_kwargs: None, BoolProperty=lambda **_kwargs: None)

    original_modules = {name: sys.modules.get(name) for name in ("bpy", "bpy.app", "bpy.app.handlers")}
    sys.modules.update({"bpy": bpy, "bpy.app": app, "bpy.app.handlers": handlers})
    try:
        spec = importlib.util.spec_from_file_location("budget_my_render_test", ADDON_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module, bpy
    finally:
        for name, original in original_modules.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


class AddonLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.addon, cls.bpy = load_addon_module()

    def test_two_point_estimate_includes_setup_cost(self):
        estimate, per_sample, setup = self.addon.estimate_seconds(
            [{"samples": 16, "elapsed_seconds": 5.257}, {"samples": 64, "elapsed_seconds": 19.195}],
            256,
        )
        self.assertAlmostEqual(per_sample, 0.290375)
        self.assertAlmostEqual(setup, 0.611)
        self.assertAlmostEqual(estimate, 74.947)

    def test_report_directories_are_unique_within_one_second(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            original_reports_directory = self.addon.reports_directory
            self.addon.reports_directory = lambda: Path(temporary_directory)
            try:
                first = self.addon.timestamped_report_directory("estimate")
                second = self.addon.timestamped_report_directory("estimate")
            finally:
                self.addon.reports_directory = original_reports_directory
        self.assertNotEqual(first, second)
        self.assertTrue(first.name.startswith("estimate-"))

    def test_calibration_requires_current_session_and_fingerprint(self):
        scene = types.SimpleNamespace(
            render_budget_calibration_available=True,
            render_budget_calibration_fingerprint="current",
            render_budget_calibration_session_id=self.addon.CALIBRATION_SESSION_ID,
        )
        original_fingerprint = self.addon.calibration_fingerprint
        self.addon.calibration_fingerprint = lambda _scene: "current"
        try:
            self.assertTrue(self.addon.calibration_is_valid(scene))
            scene.render_budget_calibration_session_id = "previous-session"
            self.assertFalse(self.addon.calibration_is_valid(scene))
        finally:
            self.addon.calibration_fingerprint = original_fingerprint

    def test_scene_updates_do_not_invalidate_target_sample_reuse(self):
        scene = types.SimpleNamespace(render_budget_calibration_available=True)
        update = types.SimpleNamespace(id=types.SimpleNamespace(bl_rna=types.SimpleNamespace(identifier="Scene")))
        self.addon.invalidate_calibrations_on_scene_change(scene, types.SimpleNamespace(updates=[update]))
        self.assertTrue(scene.render_budget_calibration_available)

    def test_object_updates_invalidate_calibration(self):
        scene = types.SimpleNamespace(render_budget_calibration_available=True)
        update = types.SimpleNamespace(id=types.SimpleNamespace(bl_rna=types.SimpleNamespace(identifier="Object")))
        self.addon.invalidate_calibrations_on_scene_change(scene, types.SimpleNamespace(updates=[update]))
        self.assertFalse(scene.render_budget_calibration_available)

    def test_report_uses_basename_not_private_blend_path(self):
        self.bpy.data.filepath = "/Users/example-user/private-project/shot.blend"
        self.assertEqual(self.addon.blend_file_name(), "shot.blend")


if __name__ == "__main__":
    unittest.main()
