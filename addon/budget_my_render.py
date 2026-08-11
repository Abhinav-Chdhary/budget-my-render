bl_info = {
    "name": "Budget My Render",
    "author": "Abhinav Chdhary",
    "version": (0, 2, 0),
    "blender": (4, 2, 0),
    "location": "3D Viewport > Sidebar > Render Budget",
    "description": "Benchmark Cycles sample counts and save reproducible reports",
    "category": "Render",
}

import json
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import bpy


def optional_setting(settings, name):
    return getattr(settings, name, None)


def snapshot_path():
    report_directory = reports_directory()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return report_directory / f"render-settings-{timestamp}.json"


def reports_directory():
    if bpy.data.filepath:
        report_directory = Path(bpy.data.filepath).parent / "reports"
    else:
        report_directory = Path(tempfile.gettempdir()) / "budget-my-render"
    report_directory.mkdir(parents=True, exist_ok=True)
    return report_directory


def benchmark_directory():
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    directory = reports_directory() / f"benchmark-{timestamp}"
    directory.mkdir(parents=True, exist_ok=False)
    return directory


def parse_sample_counts(value):
    try:
        sample_counts = [int(item.strip()) for item in value.split(",") if item.strip()]
    except ValueError as error:
        raise ValueError("Sample counts must be comma-separated whole numbers.") from error
    if not sample_counts or any(sample_count < 1 for sample_count in sample_counts):
        raise ValueError("Enter at least one sample count greater than zero.")
    return sample_counts


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


class RENDERBUDGET_OT_run_benchmark(bpy.types.Operator):
    bl_idname = "render_budget.run_benchmark"
    bl_label = "Run Sample Benchmark"
    bl_description = "Render each sample count, save images, and write timings to a JSON report"

    def execute(self, context):
        scene = context.scene
        if scene.render.engine != "CYCLES":
            self.report({"WARNING"}, "Select Cycles before running a benchmark")
            return {"CANCELLED"}

        try:
            sample_counts = parse_sample_counts(scene.render_budget_sample_counts)
        except ValueError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}

        cycles = scene.cycles
        original_samples = cycles.samples
        original_filepath = scene.render.filepath
        run_directory = benchmark_directory()
        started_at = datetime.now(timezone.utc).isoformat()
        runs = []

        try:
            for sample_count in sample_counts:
                cycles.samples = sample_count
                scene.render.filepath = str(run_directory / f"{sample_count}-samples")
                started = time.perf_counter()
                bpy.ops.render.render(write_still=True)
                elapsed_seconds = time.perf_counter() - started
                runs.append({
                    "samples": sample_count,
                    "elapsed_seconds": round(elapsed_seconds, 3),
                    "image_path": f"{sample_count}-samples",
                    "image_format": scene.render.image_settings.file_format,
                    "settings": build_snapshot(scene),
                })
        except RuntimeError as error:
            self.report({"ERROR"}, f"Benchmark stopped: {error}")
            return {"CANCELLED"}
        finally:
            cycles.samples = original_samples
            scene.render.filepath = original_filepath

        report = {
            "schema_version": 2,
            "kind": "cycles_sample_benchmark",
            "started_at": started_at,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "blend_file": bpy.data.filepath or None,
            "sample_counts": sample_counts,
            "runs": runs,
        }
        report_path = run_directory / "benchmark.json"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        self.report({"INFO"}, f"Completed {len(runs)} renders: {report_path.name}")
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
        layout.label(text=f"Current max samples: {cycles.samples}")
        layout.operator(RENDERBUDGET_OT_capture_settings.bl_idname, icon="FILE_TICK")
        layout.separator()
        layout.prop(scene, "render_budget_sample_counts")
        layout.label(text="Renders run one at a time.", icon="INFO")
        layout.operator(RENDERBUDGET_OT_run_benchmark.bl_idname, icon="RENDER_STILL")


classes = (RENDERBUDGET_OT_capture_settings, RENDERBUDGET_OT_run_benchmark, RENDERBUDGET_PT_main)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.render_budget_sample_counts = bpy.props.StringProperty(
        name="Max samples",
        description="Comma-separated Cycles max sample counts to render",
        default="16, 64, 256, 1024",
    )


def unregister():
    del bpy.types.Scene.render_budget_sample_counts
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
