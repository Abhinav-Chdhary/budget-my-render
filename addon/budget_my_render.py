bl_info = {
    "name": "Budget My Render",
    "author": "Abhinav Chdhary",
    "version": (0, 4, 0),
    "blender": (4, 2, 0),
    "location": "3D Viewport > Sidebar > Render Budget",
    "description": "Estimate Cycles render time from opt-in local pilot renders",
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
    return timestamped_report_directory("benchmark")


def estimate_directory():
    return timestamped_report_directory("estimate")


def timestamped_report_directory(prefix):
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    directory = reports_directory() / f"{prefix}-{timestamp}"
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


def parse_pilot_sample_counts(value):
    sample_counts = parse_sample_counts(value)
    if len(sample_counts) != 2 or len(set(sample_counts)) != 2:
        raise ValueError("Pilot samples must contain exactly two different values.")
    return sorted(sample_counts)


def estimate_seconds(pilot_runs, target_samples):
    lower, upper = pilot_runs
    seconds_per_sample = (upper["elapsed_seconds"] - lower["elapsed_seconds"]) / (upper["samples"] - lower["samples"])
    setup_seconds = lower["elapsed_seconds"] - lower["samples"] * seconds_per_sample
    return max(0.0, setup_seconds + target_samples * seconds_per_sample), seconds_per_sample, setup_seconds


def format_duration(seconds):
    rounded_seconds = max(0, round(seconds))
    minutes, seconds = divmod(rounded_seconds, 60)
    return f"{minutes}m {seconds:02d}s" if minutes else f"{seconds}s"


def render_settings_fingerprint(scene):
    cycles = scene.cycles
    settings = {
        "engine": scene.render.engine,
        "resolution": [scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage],
        "device": optional_setting(cycles, "device"),
        "adaptive_sampling": optional_setting(cycles, "use_adaptive_sampling"),
        "adaptive_threshold": optional_setting(cycles, "adaptive_threshold"),
        "denoising": optional_setting(cycles, "use_denoising"),
        "bounces": {
            name: optional_setting(cycles, name)
            for name in ("max_bounces", "diffuse_bounces", "glossy_bounces", "transmission_bounces", "volume_bounces", "transparent_max_bounces")
        },
    }
    return json.dumps(settings, sort_keys=True, separators=(",", ":"))


def calibration_is_valid(scene):
    return bool(scene.render_budget_calibration_available) and (
        scene.render_budget_calibration_fingerprint == render_settings_fingerprint(scene)
    )


def estimate_from_calibration(scene):
    predicted_seconds = max(
        0.0,
        scene.render_budget_calibration_setup_seconds
        + scene.render_budget_target_samples * scene.render_budget_calibration_seconds_per_sample,
    )
    adaptive_sampling = bool(optional_setting(scene.cycles, "use_adaptive_sampling"))
    uncertainty = 0.5 if adaptive_sampling else 0.25
    return {
        "seconds": predicted_seconds,
        "lower_seconds": max(0.0, predicted_seconds * (1 - uncertainty)),
        "upper_seconds": predicted_seconds * (1 + uncertainty),
        "confidence": "low" if adaptive_sampling else "medium",
        "adaptive_sampling": adaptive_sampling,
    }


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


class RENDERBUDGET_OT_estimate_render_time(bpy.types.Operator):
    bl_idname = "render_budget.estimate_render_time"
    bl_label = "Estimate Render Time"
    bl_description = "Run two low-sample pilot renders and estimate the selected Cycles sample count"

    def execute(self, context):
        scene = context.scene
        if scene.render.engine != "CYCLES":
            self.report({"WARNING"}, "Select Cycles before estimating render time")
            return {"CANCELLED"}

        try:
            pilot_samples = parse_pilot_sample_counts(scene.render_budget_pilot_samples)
        except ValueError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}

        cycles = scene.cycles
        original_samples = cycles.samples
        started_at = datetime.now(timezone.utc).isoformat()
        report_directory = estimate_directory()
        pilot_runs = []

        try:
            for sample_count in pilot_samples:
                cycles.samples = sample_count
                started = time.perf_counter()
                bpy.ops.render.render()
                pilot_runs.append({
                    "samples": sample_count,
                    "elapsed_seconds": round(time.perf_counter() - started, 3),
                    "settings": build_snapshot(scene),
                })
        except RuntimeError as error:
            self.report({"ERROR"}, f"Estimate stopped: {error}")
            return {"CANCELLED"}
        finally:
            cycles.samples = original_samples

        _, seconds_per_sample, setup_seconds = estimate_seconds(pilot_runs, scene.render_budget_target_samples)
        scene.render_budget_calibration_seconds_per_sample = seconds_per_sample
        scene.render_budget_calibration_setup_seconds = setup_seconds
        scene.render_budget_calibration_fingerprint = render_settings_fingerprint(scene)
        scene.render_budget_calibration_available = True
        estimate = estimate_from_calibration(scene)
        report = {
            "schema_version": 3,
            "kind": "cycles_render_time_estimate",
            "started_at": started_at,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "blend_file": bpy.data.filepath or None,
            "target_samples": scene.render_budget_target_samples,
            "pilot_runs": pilot_runs,
            "model": {
                "kind": "two_point_linear_extrapolation",
                "seconds_per_sample": round(seconds_per_sample, 6),
                "setup_seconds": round(setup_seconds, 3),
            },
            "estimate": {
                "seconds": round(estimate["seconds"], 3),
                "range_seconds": [round(estimate["lower_seconds"], 3), round(estimate["upper_seconds"], 3)],
                "confidence": estimate["confidence"],
                "adaptive_sampling": estimate["adaptive_sampling"],
            },
        }
        report_path = report_directory / "estimate.json"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        self.report({"INFO"}, f"Estimated render time: {format_duration(estimate['seconds'])}")
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
        layout.separator()
        estimate_box = layout.box()
        estimate_box.label(text="Estimate final render")
        estimate_box.prop(scene, "render_budget_target_samples")
        estimate_box.prop(scene, "render_budget_pilot_samples")
        estimate_box.label(text="Pilot renders use CPU/GPU.", icon="INFO")
        if calibration_is_valid(scene):
            estimate_box.operator(RENDERBUDGET_OT_estimate_render_time.bl_idname, text="Refresh calibration", icon="TIME")
            estimate = estimate_from_calibration(scene)
            estimate_box.separator()
            estimate_box.label(text=f"Estimate: ~{format_duration(estimate['seconds'])}")
            estimate_box.label(text=(
                f"Range: {format_duration(estimate['lower_seconds'])}–"
                f"{format_duration(estimate['upper_seconds'])} ({estimate['confidence']})"
            ))
        else:
            estimate_box.operator(RENDERBUDGET_OT_estimate_render_time.bl_idname, icon="TIME")
            if scene.render_budget_calibration_available:
                estimate_box.label(text="Core settings changed — recalibrate.", icon="INFO")


classes = (
    RENDERBUDGET_OT_capture_settings,
    RENDERBUDGET_OT_run_benchmark,
    RENDERBUDGET_OT_estimate_render_time,
    RENDERBUDGET_PT_main,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.render_budget_sample_counts = bpy.props.StringProperty(
        name="Max samples",
        description="Comma-separated Cycles max sample counts to render",
        default="16, 64, 256, 1024",
    )
    bpy.types.Scene.render_budget_target_samples = bpy.props.IntProperty(
        name="Target max samples",
        description="Cycles max samples to estimate",
        default=256,
        min=1,
    )
    bpy.types.Scene.render_budget_pilot_samples = bpy.props.StringProperty(
        name="Pilot samples",
        description="Exactly two comma-separated Cycles max sample counts used for calibration",
        default="16, 64",
    )
    bpy.types.Scene.render_budget_calibration_seconds_per_sample = bpy.props.FloatProperty(default=0.0, min=0.0)
    bpy.types.Scene.render_budget_calibration_setup_seconds = bpy.props.FloatProperty(default=0.0)
    bpy.types.Scene.render_budget_calibration_fingerprint = bpy.props.StringProperty(default="")
    bpy.types.Scene.render_budget_calibration_available = bpy.props.BoolProperty(default=False)


def unregister():
    del bpy.types.Scene.render_budget_sample_counts
    del bpy.types.Scene.render_budget_target_samples
    del bpy.types.Scene.render_budget_pilot_samples
    del bpy.types.Scene.render_budget_calibration_seconds_per_sample
    del bpy.types.Scene.render_budget_calibration_setup_seconds
    del bpy.types.Scene.render_budget_calibration_fingerprint
    del bpy.types.Scene.render_budget_calibration_available
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
