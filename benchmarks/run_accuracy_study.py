"""Run from Blender's Text Editor in a normal desktop session.

This creates temporary Cycles fixtures, measures 16/64-sample pilots and a
256-sample reference, then writes raw JSON beside the saved .blend file (or to
Blender's temporary directory). It never writes render images.
"""

import json
import platform
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


PILOT_SAMPLES = (16, 64)
REFERENCE_SAMPLES = 256
REPEATS = 2
RESOLUTION = 512


def add_mesh(scene, name, operation, location=(0, 0, 0), scale=(1, 1, 1), material=None):
    mesh = bpy.data.meshes.new(name)
    mesh_builder = bmesh.new()
    operation(mesh_builder)
    mesh_builder.to_mesh(mesh)
    mesh_builder.free()
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    obj.location, obj.scale = location, scale
    if material:
        obj.data.materials.append(material)
    return obj


def cube(scene, name, **kwargs):
    return add_mesh(scene, name, lambda mesh: bmesh.ops.create_cube(mesh, size=2), **kwargs)


def sphere(scene, name, **kwargs):
    return add_mesh(scene, name, lambda mesh: bmesh.ops.create_uvsphere(mesh, u_segments=32, v_segments=16, radius=1), **kwargs)


def material(name, base_color, metallic=0, roughness=0.5, transmission=0):
    value = bpy.data.materials.new(name)
    value.use_nodes = True
    shader = value.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*base_color, 1)
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Roughness"].default_value = roughness
    transmission_input = shader.inputs.get("Transmission Weight") or shader.inputs.get("Transmission")
    if transmission_input:
        transmission_input.default_value = transmission
    return value


def add_camera(scene):
    camera_data = bpy.data.cameras.new("Study Camera")
    camera = bpy.data.objects.new("Study Camera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = (7, -9, 6)
    camera.rotation_euler = (Vector((0, 0, 1.5)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = camera


def add_area_light(scene, location, energy, size):
    data = bpy.data.lights.new("Study Area", "AREA")
    data.energy, data.shape, data.size = energy, "DISK", size
    light = bpy.data.objects.new("Study Area", data)
    scene.collection.objects.link(light)
    light.location = location
    light.rotation_euler = (Vector((0, 0, 1)) - light.location).to_track_quat("-Z", "Y").to_euler()


def configure(scene):
    scene.render.engine = "CYCLES"
    scene.render.resolution_x = RESOLUTION
    scene.render.resolution_y = RESOLUTION
    scene.render.resolution_percentage = 100
    scene.cycles.use_adaptive_sampling = False
    scene.cycles.use_denoising = False
    scene.render.film_transparent = False
    scene.world = bpy.data.worlds.new("Accuracy Study World")
    scene.world.color = (0.025, 0.025, 0.025)
    add_camera(scene)
    add_area_light(scene, (3, -4, 7), 1200, 5)


def fixture_scene(name):
    scene = bpy.data.scenes.new(f"Accuracy Study — {name}")
    configure(scene)
    floor = material("Floor", (0.2, 0.2, 0.2), roughness=0.65)
    cube(scene, "Floor", location=(0, 0, -1.1), scale=(6, 6, 0.1), material=floor)
    if name == "interior":
        wall = material("Wall", (0.55, 0.45, 0.35), roughness=0.9)
        cube(scene, "Back Wall", location=(0, 3, 2), scale=(6, 0.1, 3), material=wall)
        for x in (-2, 0, 2):
            cube(scene, f"Interior Block {x}", location=(x, 0.5, 0), scale=(0.8, 0.8, 1), material=wall)
    elif name == "glossy":
        glossy = material("Glossy", (0.06, 0.3, 0.8), metallic=0.85, roughness=0.08)
        for x in (-2, 0, 2):
            sphere(scene, f"Glossy Sphere {x}", location=(x, 0, 0), material=glossy)
    elif name == "transparent":
        glass = material("Glass", (0.8, 0.95, 1.0), roughness=0.08, transmission=1)
        for x in (-1.5, 0, 1.5):
            sphere(scene, f"Glass Sphere {x}", location=(x, 0, 0), material=glass)
    elif name == "volume":
        volume = bpy.data.materials.new("Volume")
        volume.use_nodes = True
        nodes = volume.node_tree.nodes
        nodes.clear()
        output = nodes.new("ShaderNodeOutputMaterial")
        shader = nodes.new("ShaderNodeVolumePrincipled")
        shader.inputs["Density"].default_value = 0.18
        volume.node_tree.links.new(shader.outputs["Volume"], output.inputs["Volume"])
        cube(scene, "Volume Cube", location=(0, 0, 0.8), scale=(2.2, 2.2, 2.2), material=volume)
    elif name == "hair":
        hair = material("Hair", (0.08, 0.025, 0.01), roughness=0.35)
        data = bpy.data.curves.new("Hair Strands", "CURVE")
        data.dimensions, data.bevel_depth, data.bevel_resolution = "3D", 0.012, 2
        for index in range(350):
            x = (index % 25 - 12) * 0.08
            y = (index // 25 - 7) * 0.09
            spline = data.splines.new("BEZIER")
            spline.bezier_points.add(2)
            for point_index, point in enumerate(spline.bezier_points):
                point.co = (x + point_index * 0.05, y, -0.8 + point_index * 0.8)
                point.handle_left_type = point.handle_right_type = "AUTO"
        strands = bpy.data.objects.new("Hair Strands", data)
        scene.collection.objects.link(strands)
        data.materials.append(hair)
    else:
        raise ValueError(name)
    return scene


def render_seconds(scene, samples):
    scene.cycles.samples = samples
    started = time.perf_counter()
    result = bpy.ops.render.render(write_still=False)
    if "FINISHED" not in result:
        raise RuntimeError("render was cancelled")
    return round(time.perf_counter() - started, 3)


def estimate(lower, upper, target):
    slope = (upper["seconds"] - lower["seconds"]) / (upper["samples"] - lower["samples"])
    return lower["seconds"] + (target - lower["samples"]) * slope


def report_directory():
    root = Path(bpy.data.filepath).parent if bpy.data.filepath else Path(tempfile.gettempdir()) / "budget-my-render"
    root.mkdir(parents=True, exist_ok=True)
    return root


def run():
    original_scene = bpy.context.window.scene
    created_scenes, results = [], []
    try:
        for fixture in ("interior", "glossy", "transparent", "volume", "hair"):
            for repeat in range(1, REPEATS + 1):
                scene = fixture_scene(fixture)
                created_scenes.append(scene)
                bpy.context.window.scene = scene
                pilots = [{"samples": samples, "seconds": render_seconds(scene, samples)} for samples in PILOT_SAMPLES]
                predicted = estimate(pilots[0], pilots[1], REFERENCE_SAMPLES)
                actual = render_seconds(scene, REFERENCE_SAMPLES)
                results.append({
                    "status": "completed", "fixture": fixture, "repeat": repeat,
                    "pilot_runs": pilots, "target_samples": REFERENCE_SAMPLES,
                    "predicted_seconds": round(predicted, 3), "actual_seconds": actual,
                    "absolute_percentage_error": round(abs(predicted - actual) / actual * 100, 2),
                })
    finally:
        bpy.context.window.scene = original_scene
        for scene in created_scenes:
            bpy.data.scenes.remove(scene)
    report = {
        "schema_version": 1, "kind": "cycles_accuracy_study",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "blender_version": bpy.app.version_string, "platform": platform.platform(),
        "pilot_samples": list(PILOT_SAMPLES), "reference_samples": REFERENCE_SAMPLES,
        "resolution": [RESOLUTION, RESOLUTION], "adaptive_sampling": False,
        "results": results,
    }
    path = report_directory() / f"accuracy-study-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Budget My Render accuracy study: {path}")


run()
