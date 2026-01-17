import bpy
import json
import math
import os
import mathutils
import glob

# ================== PARAMÈTRES ==================
N = 100
RADIUS = 1.0

MAIN_PATH = bpy.path.abspath("//")

BASE_PATH = os.path.join(MAIN_PATH, "images-blender")
OBJ_PATH = os.path.join(MAIN_PATH, "model", "Patatoide_details.obj")

JSON_NAME = "camera_pos_degrees.json"
NORM_DIR = os.path.join(BASE_PATH, "normals")

os.makedirs(NORM_DIR, exist_ok=True)

# ================== UTILITAIRES ==================
def clear_scene():
    """Supprime absolument tout de la scène"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

    for block in bpy.data.meshes:
        bpy.data.meshes.remove(block)
    for block in bpy.data.cameras:
        bpy.data.cameras.remove(block)
    for block in bpy.data.lights:
        bpy.data.lights.remove(block)

def import_obj(path):
    path = os.path.abspath(path)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"OBJ introuvable : {path}")

    bpy.ops.wm.obj_import(filepath=path)

def add_camera():
    """Ajoute une caméra et la définit comme active"""
    bpy.ops.object.camera_add(location=(0, 0, RADIUS))
    cam = bpy.context.active_object
    bpy.context.scene.camera = cam
    return cam

def setup_compositor():
    """Configure l'export des normales avec alpha"""
    scene = bpy.context.scene
    scene.use_nodes = True
    tree = scene.node_tree
    tree.nodes.clear()

    render_layers = tree.nodes.new('CompositorNodeRLayers')

    file_output = tree.nodes.new('CompositorNodeOutputFile')
    file_output.base_path = NORM_DIR
    file_output.format.file_format = 'PNG'
    file_output.format.color_mode = 'RGBA'
    file_output.file_slots[0].path = "temp_norm_"

    bpy.context.view_layer.use_pass_normal = True

    mult = tree.nodes.new('CompositorNodeMixRGB')
    mult.blend_type = 'MULTIPLY'
    mult.inputs[2].default_value = (0.5, 0.5, 0.5, 1)

    add = tree.nodes.new('CompositorNodeMixRGB')
    add.blend_type = 'ADD'
    add.inputs[2].default_value = (0.5, 0.5, 0.5, 1)

    set_alpha = tree.nodes.new('CompositorNodeSetAlpha')

    tree.links.new(render_layers.outputs['Normal'], mult.inputs[1])
    tree.links.new(mult.outputs[0], add.inputs[1])
    tree.links.new(add.outputs[0], set_alpha.inputs['Image'])
    tree.links.new(render_layers.outputs['Alpha'], set_alpha.inputs['Alpha'])
    tree.links.new(set_alpha.outputs['Image'], file_output.inputs[0])

    return file_output

# ================== MAIN ==================
def run_synthetic_data_gen():
    clear_scene()
    import_obj(OBJ_PATH)
    cam = add_camera()

    # ================== GPU / CUDA ==================
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'

    prefs = bpy.context.preferences
    cycles_prefs = prefs.addons['cycles'].preferences

    cycles_prefs.compute_device_type = 'CUDA'

    # Active uniquement le GPU
    for device in cycles_prefs.devices:
        device.use = (device.type == 'CUDA')

    scene.cycles.device = 'GPU'
    scene.cycles.samples = 64
    scene.cycles.use_denoising = False
    scene.cycles.max_bounces = 1
    scene.cycles.diffuse_bounces = 1
    scene.cycles.glossy_bounces = 1
    scene.cycles.transparent_max_bounces = 1
    scene.cycles.use_adaptive_sampling = False
    
    # ================== RÉSOLUTION 4K ==================
    scene.render.resolution_x = 4096
    scene.render.resolution_y = 4096
    scene.render.resolution_percentage = 100

    
    scene.render.film_transparent = True
    scene.render.use_compositing = True

    norm_node = setup_compositor()

    camera_log = []
    golden_angle = math.pi * (3 - math.sqrt(5))

    for i in range(N):
        z_ratio = 1 - (i / float(N - 1)) * 2
        r_at_z = math.sqrt(1 - z_ratio ** 2)
        theta = golden_angle * i

        pos_x = math.cos(theta) * r_at_z * RADIUS
        pos_y = math.sin(theta) * r_at_z * RADIUS
        pos_z = z_ratio * RADIUS

        cam.location = (pos_x, pos_y, pos_z)

        direction = mathutils.Vector((0, 0, 0)) - cam.location
        cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

        file_id = f"{i}"
        norm_node.file_slots[0].path = f"temp_norm_{file_id}_"

        bpy.ops.render.render(write_still=False)

        found = glob.glob(os.path.join(NORM_DIR, f"temp_norm_{file_id}_*.png"))
        if found:
            final_path = os.path.join(NORM_DIR, f"normal_{file_id}.png")
            if os.path.exists(final_path):
                os.remove(final_path)
            os.rename(found[0], final_path)

        camera_log.append({
            "id": i,
            "image_normal": f"normals/normal_{file_id}.png",
            "position": {
                "x": float(pos_x),
                "y": float(pos_y),
                "z": float(pos_z)
            },
            "rotation_euler_deg": {
                "x": math.degrees(cam.rotation_euler.x),
                "y": math.degrees(cam.rotation_euler.y),
                "z": math.degrees(cam.rotation_euler.z)
            }
        })

        print(f"Normal map {i} générée.")

    with open(os.path.join(BASE_PATH, JSON_NAME), 'w') as f:
        json.dump(camera_log, f, indent=4)

    print("Extraction terminée.")

# ================== RUN ==================

run_synthetic_data_gen()