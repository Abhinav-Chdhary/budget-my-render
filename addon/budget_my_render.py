bl_info = {
    "name": "Budget My Render",
    "author": "Abhinav Chdhary",
    "version": (0, 5, 1),
    "blender": (4, 2, 0),
    "location": "3D Viewport > Sidebar > Render Budget",
    "description": "Estimate Cycles render time from opt-in local pilot renders",
    "category": "Render",
}

import json
import hashlib
import platform
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import bpy
from bpy.app.handlers import persistent


# Scene properties are saved in .blend files.  A pilot must never be reused
# after opening that file in another Blender process, even if its visible
# settings happen to match.
CALIBRATION_SESSION_ID = uuid.uuid4().hex
_CALIBRATION_IN_PROGRESS = False


@persistent
def invalidate_calibrations_on_scene_change(scene, depsgraph):
    """Invalidate rather than guess when Blender reports a render-relevant edit."""
    if _CALIBRATION_IN_PROGRESS:
        return
    # Scene updates also occur when the artist changes Max Samples. That
    # setting is deliberately excluded from calibration identity, allowing the
    # fitted pilot to be reused for a new target. Other scene settings are
    # checked by the fingerprint when the panel is drawn.
    relevant_types = {"OBJECT", "MESH", "CURVE", "CURVES", "POINTCLOUD", "VOLUME", "MATERIAL", "WORLD", "CAMERA", "LIGHT", "COLLECTION", "IMAGE", "MOVIECLIP", "CACHEFILE"}
    def affects_render(update):
        rna = getattr(getattr(update, "id", None), "bl_rna", None)
        identifier = rna.identifier.upper() if rna else ""
        return identifier in relevant_types or identifier.endswith("NODETREE")
    if any(affects_render(update) for update in depsgraph.updates):
        scene.render_budget_calibration_available = False


@persistent
def invalidate_calibrations_on_load(_unused):
    # A stored .blend can be opened with a different Blender build or device.
    for scene in bpy.data.scenes:
        scene.render_budget_calibration_available = False
        scene.render_budget_calibration_session_id = ""


def optional_setting(settings, name):
    return getattr(settings, name, None)


def reports_directory():
    if bpy.data.filepath:
        report_directory = Path(bpy.data.filepath).parent / "reports"
    else:
        report_directory = Path(tempfile.gettempdir()) / "budget-my-render"
    report_directory.mkdir(parents=True, exist_ok=True)
    return report_directory


def blend_file_name():
    """Return non-sensitive file metadata suitable for a shareable report."""
    return Path(bpy.data.filepath).name if bpy.data.filepath else None


def estimate_directory():
    return timestamped_report_directory("estimate")


def timestamped_report_directory(prefix):
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    parent = reports_directory()
    # A timestamp alone is not unique when an artist starts two estimates in a
    # second. A random suffix also avoids colliding with a restored report.
    directory = parent / f"{prefix}-{timestamp}-{uuid.uuid4().hex[:8]}"
    directory.mkdir(parents=True, exist_ok=False)
    return directory


def estimate_seconds(pilot_runs, target_samples):
    lower, upper = pilot_runs
    seconds_per_sample = (upper["elapsed_seconds"] - lower["elapsed_seconds"]) / (upper["samples"] - lower["samples"])
    setup_seconds = lower["elapsed_seconds"] - lower["samples"] * seconds_per_sample
    return max(0.0, setup_seconds + target_samples * seconds_per_sample), seconds_per_sample, setup_seconds


def format_duration(seconds):
    rounded_seconds = max(0, round(seconds))
    minutes, seconds = divmod(rounded_seconds, 60)
    return f"{minutes}m {seconds:02d}s" if minutes else f"{seconds}s"


def _stable_value(value):
    """Convert common Blender property values into JSON-safe, stable values."""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="backslashreplace")
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    try:
        return list(value)
    except TypeError:
        return str(value)


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
    return json.dumps(settings, sort_keys=True, separators=(",", ":"), default=_stable_value)


def _node_signature(node):
    inputs = {}
    for socket in node.inputs:
        if not socket.is_linked and hasattr(socket, "default_value"):
            try:
                inputs[socket.identifier] = _stable_value(socket.default_value)
            except (TypeError, ValueError):
                pass
    return {"name": node.name, "type": node.bl_idname, "mute": node.mute, "inputs": inputs}


def scene_content_fingerprint(scene):
    """An additional signature of visible content that affects Cycles work.

    Blender's depsgraph handler performs conservative in-session invalidation
    for all reported edits; this digest is a second line of defence for common
    transform, topology, visibility, camera, material, and world changes.
    """
    objects = []
    for obj in sorted(scene.objects, key=lambda item: item.name_full):
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        item = {
            "name": obj.name_full,
            "type": obj.type,
            "hide_render": obj.hide_render,
            "matrix_world": [round(value, 8) for row in obj.matrix_world for value in row],
            "modifiers": [(modifier.name, modifier.type, modifier.show_render) for modifier in obj.modifiers],
            "materials": [slot.material.name_full if slot.material else None for slot in obj.material_slots],
        }
        if hasattr(evaluated, "data") and hasattr(evaluated.data, "vertices"):
            item["evaluated_geometry"] = {
                "vertices": len(evaluated.data.vertices),
                "edges": len(evaluated.data.edges),
                "polygons": len(evaluated.data.polygons),
            }
        objects.append(item)

    materials = []
    for material in sorted((slot.material for obj in scene.objects for slot in obj.material_slots if slot.material), key=lambda item: item.name_full):
        # Repeated material entries are harmless to correctness and preserve a
        # change in which object uses which material via the object list above.
        materials.append({
            "name": material.name_full,
            "use_nodes": material.use_nodes,
            "nodes": [_node_signature(node) for node in material.node_tree.nodes] if material.use_nodes and material.node_tree else [],
        })
    world = scene.world
    payload = {
        "scene": scene.name_full,
        "frame": [scene.frame_current, scene.frame_subframe],
        "camera": scene.camera.name_full if scene.camera else None,
        "camera_matrix": [round(value, 8) for row in scene.camera.matrix_world for value in row] if scene.camera else None,
        "world": {
            "name": world.name_full if world else None,
            "use_nodes": world.use_nodes if world else None,
            "nodes": [_node_signature(node) for node in world.node_tree.nodes] if world and world.use_nodes and world.node_tree else [],
        },
        "objects": objects,
    }
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=_stable_value
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def environment_identity(scene):
    """Non-identifying local environment details used only in the JSON report."""
    cycles = scene.cycles
    device_preferences = {}
    try:
        preferences = bpy.context.preferences.addons["cycles"].preferences
        # Refresh devices before reading them: changing a GPU selection must
        # invalidate a calibration made with a different renderer device.
        preferences.get_devices()
        device_preferences = {
            "compute_device_type": getattr(preferences, "compute_device_type", None),
            "devices": [
                {"name": device.name, "type": device.type, "use": device.use}
                for device in preferences.devices
            ],
        }
    except (AttributeError, KeyError, RuntimeError):
        # Cycles preferences are not always available in background/minimal
        # builds. The remaining identity fields still keep the calibration safe.
        device_preferences = {"compute_device_type": None, "devices": []}
    return {
        "blender_version": bpy.app.version_string,
        "blender_version_tuple": list(bpy.app.version),
        "build_platform": getattr(bpy.app, "build_platform", None),
        "python_version": sys.version.split()[0],
        "operating_system": platform.system(),
        "machine_architecture": platform.machine(),
        "cycles_device": optional_setting(cycles, "device"),
        "cycles_device_preferences": device_preferences,
    }


def calibration_fingerprint(scene):
    identity = {
        "render_settings": json.loads(render_settings_fingerprint(scene)),
        "scene_content": scene_content_fingerprint(scene),
        "environment": environment_identity(scene),
    }
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":"), default=_stable_value).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def calibration_is_valid(scene):
    return bool(scene.render_budget_calibration_available) and (
        scene.render_budget_calibration_fingerprint == calibration_fingerprint(scene)
    ) and scene.render_budget_calibration_session_id == CALIBRATION_SESSION_ID


def estimate_from_calibration(scene):
    predicted_seconds = max(
        0.0,
        scene.render_budget_calibration_setup_seconds
        + scene.cycles.samples * scene.render_budget_calibration_seconds_per_sample,
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
        "blend_file_name": blend_file_name(),
        "engine": scene.render.engine,
        "resolution": {
            "width": scene.render.resolution_x,
            "height": scene.render.resolution_y,
            "percentage": scene.render.resolution_percentage,
        },
        "environment": environment_identity(scene),
        "scene_content_fingerprint": scene_content_fingerprint(scene),
        "cycles": {
            "samples": optional_setting(cycles, "samples"),
            "preview_samples": optional_setting(cycles, "preview_samples"),
            "use_adaptive_sampling": optional_setting(cycles, "use_adaptive_sampling"),
            "adaptive_threshold": optional_setting(cycles, "adaptive_threshold"),
            "use_denoising": optional_setting(cycles, "use_denoising"),
        },
    }


class RENDERBUDGET_OT_estimate_render_time(bpy.types.Operator):
    bl_idname = "render_budget.estimate_render_time"
    bl_label = "Estimate Render Time"
    bl_description = "Run two low-sample pilot renders and estimate the current Cycles Max Samples value"

    def execute(self, context):
        global _CALIBRATION_IN_PROGRESS
        scene = context.scene
        if scene.render.engine != "CYCLES":
            self.report({"WARNING"}, "Select Cycles before estimating render time")
            return {"CANCELLED"}

        cycles = scene.cycles
        target_samples = cycles.samples
        original_samples = cycles.samples
        started_at = datetime.now(timezone.utc).isoformat()
        pilot_runs = []
        report_directory = None
        _CALIBRATION_IN_PROGRESS = True

        try:
            report_directory = estimate_directory()
            for sample_count in (16, 64):
                cycles.samples = sample_count
                started = time.perf_counter()
                # Do not write an image or overwrite the artist's render
                # output; Cycles' Render Result is the only render-side effect.
                result = bpy.ops.render.render(write_still=False)
                if "FINISHED" not in result:
                    raise RuntimeError("render was cancelled")
                pilot_runs.append({
                    "samples": sample_count,
                    "elapsed_seconds": round(time.perf_counter() - started, 3),
                    "settings": build_snapshot(scene),
                })
        except (RuntimeError, OSError, ValueError, TypeError) as error:
            self.report({"ERROR"}, f"Estimate stopped: {error}")
            return {"CANCELLED"}
        finally:
            cycles.samples = original_samples
            _CALIBRATION_IN_PROGRESS = False

        if len(pilot_runs) != 2:
            self.report({"ERROR"}, "Estimate stopped before both pilot renders completed")
            return {"CANCELLED"}

        _CALIBRATION_IN_PROGRESS = True
        try:
            _, seconds_per_sample, setup_seconds = estimate_seconds(pilot_runs, target_samples)
            scene.render_budget_calibration_seconds_per_sample = seconds_per_sample
            scene.render_budget_calibration_setup_seconds = setup_seconds
            scene.render_budget_calibration_fingerprint = calibration_fingerprint(scene)
            scene.render_budget_calibration_session_id = CALIBRATION_SESSION_ID
            scene.render_budget_calibration_available = True
        finally:
            _CALIBRATION_IN_PROGRESS = False
        estimate = estimate_from_calibration(scene)
        report = {
            "schema_version": 4,
            "kind": "cycles_render_time_estimate",
            "started_at": started_at,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "blend_file_name": blend_file_name(),
            "calibration_identity": {
                "fingerprint": scene.render_budget_calibration_fingerprint,
                "scene_content_fingerprint": scene_content_fingerprint(scene),
                "environment": environment_identity(scene),
            },
            "data_handling": {
                "storage": "local JSON report beside the .blend file, or the system temporary directory for unsaved files",
                "network_upload": False,
                "machine_identity": "reports contain Blender, OS family, CPU architecture, and selected Cycles device; no hostname, account name, or full file path is collected",
            },
            "target_samples": target_samples,
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
        try:
            report_path = report_directory / "estimate.json"
            report_path.write_text(json.dumps(report, indent=2, default=_stable_value) + "\n", encoding="utf-8")
        except (OSError, TypeError, ValueError) as error:
            self.report({"WARNING"}, f"Estimated {format_duration(estimate['seconds'])}; report was not saved: {error}")
            return {"FINISHED"}
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
        layout.label(text=f"Cycles max samples: {cycles.samples}")
        estimate_box = layout.box()
        estimate_box.label(text="Estimate this render")
        if calibration_is_valid(scene):
            estimate_box.operator(RENDERBUDGET_OT_estimate_render_time.bl_idname, text="Estimate render time", icon="TIME")
            estimate = estimate_from_calibration(scene)
            estimate_box.separator()
            estimate_box.label(text=f"Estimate: ~{format_duration(estimate['seconds'])}")
            estimate_box.label(text=(
                f"Range: {format_duration(estimate['lower_seconds'])}–"
                f"{format_duration(estimate['upper_seconds'])} ({estimate['confidence']})"
            ))
        else:
            estimate_box.operator(RENDERBUDGET_OT_estimate_render_time.bl_idname, text="Estimate render time", icon="TIME")
            if scene.render_budget_calibration_available:
                estimate_box.label(text="Scene, device, or session changed — recalibrate.", icon="INFO")


classes = (RENDERBUDGET_OT_estimate_render_time, RENDERBUDGET_PT_main)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.render_budget_calibration_seconds_per_sample = bpy.props.FloatProperty(default=0.0, min=0.0)
    bpy.types.Scene.render_budget_calibration_setup_seconds = bpy.props.FloatProperty(default=0.0)
    bpy.types.Scene.render_budget_calibration_fingerprint = bpy.props.StringProperty(default="")
    bpy.types.Scene.render_budget_calibration_session_id = bpy.props.StringProperty(default="")
    bpy.types.Scene.render_budget_calibration_available = bpy.props.BoolProperty(default=False)
    if invalidate_calibrations_on_scene_change not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(invalidate_calibrations_on_scene_change)
    if invalidate_calibrations_on_load not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(invalidate_calibrations_on_load)


def unregister():
    if invalidate_calibrations_on_scene_change in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(invalidate_calibrations_on_scene_change)
    if invalidate_calibrations_on_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(invalidate_calibrations_on_load)
    del bpy.types.Scene.render_budget_calibration_seconds_per_sample
    del bpy.types.Scene.render_budget_calibration_setup_seconds
    del bpy.types.Scene.render_budget_calibration_fingerprint
    del bpy.types.Scene.render_budget_calibration_session_id
    del bpy.types.Scene.render_budget_calibration_available
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
