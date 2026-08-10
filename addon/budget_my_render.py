bl_info = {
    "name": "Budget My Render",
    "author": "Abhinav Chdhary",
    "version": (0, 1, 0),
    "blender": (4, 2, 0),
    "location": "3D Viewport > Sidebar > Render Budget",
    "description": "Capture the active Cycles render budget as a JSON snapshot",
    "category": "Render",
}

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import bpy


def optional_setting(settings, name):
    return getattr(settings, name, None)


def snapshot_path():
    if bpy.data.filepath:
        report_directory = Path(bpy.data.filepath).parent / "reports"
    else:
        report_directory = Path(tempfile.gettempdir()) / "budget-my-render"
    report_directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return report_directory / f"render-settings-{timestamp}.json"


def build_snapshot(scene):
    cycles = scene.cycles
    return {
        "schema_version": 1,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "blend_file": bpy.data.filepath or None,
        "engine": scene.render.engine,
        "resolution": {
            "width": scene.render.resolution_x,
            "height": scene.render.resolution_y,
            "percentage": scene.render.resolution_percentage,
        },
        "cycles": {
            "samples": optional_setting(cycles, "samples"),
            "preview_samples": optional_setting(cycles, "preview_samples"),
            "use_adaptive_sampling": optional_setting(cycles, "use_adaptive_sampling"),
            "adaptive_threshold": optional_setting(cycles, "adaptive_threshold"),
            "use_denoising": optional_setting(cycles, "use_denoising"),
        },
    }


class RENDERBUDGET_OT_capture_settings(bpy.types.Operator):
    bl_idname = "render_budget.capture_settings"
    bl_label = "Capture Settings Snapshot"
    bl_description = "Write the current Cycles render settings to a JSON report"

    def execute(self, context):
        scene = context.scene
        if scene.render.engine != "CYCLES":
            self.report({"WARNING"}, "Select Cycles before capturing a render budget")
            return {"CANCELLED"}

        output_path = snapshot_path()
        output_path.write_text(json.dumps(build_snapshot(scene), indent=2) + "\n", encoding="utf-8")
        self.report({"INFO"}, f"Saved snapshot: {output_path.name}")
        return {"FINISHED"}


class RENDERBUDGET_PT_main(bpy.types.Panel):
    bl_label = "Budget My Render"
    bl_idname = "RENDERBUDGET_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Budget"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        if scene.render.engine != "CYCLES":
            layout.label(text="Select Cycles to begin.", icon="INFO")
            return

        cycles = scene.cycles
        layout.label(text=f"Resolution: {scene.render.resolution_x} × {scene.render.resolution_y}")
        layout.label(text=f"Samples: {cycles.samples}")
        layout.operator(RENDERBUDGET_OT_capture_settings.bl_idname, icon="FILE_TICK")


classes = (RENDERBUDGET_OT_capture_settings, RENDERBUDGET_PT_main)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
