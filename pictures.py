import bpy
import json
import math
import os
import mathutils
import glob

# ================== PARAMÈTRES ==================
N =6
RADIUS = 0.5

OUT_DIR = "24"
NAME_PIC = "patatoide"
USE_NORMAL = True


MAIN_PATH = bpy.path.abspath("//")

BASE_PATH = os.path.join(MAIN_PATH, "images-blender")
os.makedirs(BASE_PATH, exist_ok=True)

if USE_NORMAL:
    OBJ_PATH = os.path.join(MAIN_PATH, "model", "Patatoide_lisse.obj")
else:
    OBJ_PATH = os.path.join(MAIN_PATH, "model", "Patatoide_details.obj")

NORM_DIR = os.path.join(BASE_PATH, "sigma", OUT_DIR)

os.makedirs(NORM_DIR, exist_ok=True)

normal_map_path = os.path.join(BASE_PATH, "normal_merged.png")

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
        
    for obj in bpy.data.objects:
        if obj.type == 'LIGHT':
            bpy.data.objects.remove(obj, do_unlink=True)


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

def apply_white_material(obj, normal_map_path):
    mat = bpy.data.materials.new(name="WhiteMaterial")
    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # === Nodes ===
    tex_normal = nodes.new(type="ShaderNodeTexImage")
    tex_normal.image = bpy.data.images.load(normal_map_path)
    tex_normal.image.colorspace_settings.name = 'Non-Color'
    tex_normal.location = (-600, 0)
    
    normal_map = nodes.new(type="ShaderNodeNormalMap")
    normal_map.inputs["Strength"].default_value = 1.0
    normal_map.space = 'WORLD'
    normal_map.location = (-300, 0)
    
    bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.5, 0.5, 0.5, 1)
    bsdf.inputs["Roughness"].default_value = 0.5
    bsdf.location = (0, 0)

    output = nodes.new(type="ShaderNodeOutputMaterial")
    output.location = (300, 0)

    # === Links ===
    links.new(tex_normal.outputs["Color"], normal_map.inputs["Color"])
    if USE_NORMAL:
        links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

    # === Assign material ===
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)


def add_full_studio_lighting(
    strength=100,
    size=5.0,
    radius=3.0
):
    lights = []
    positions = [
        ( radius,  0,  0),
        (-radius,  0,  0),
        ( 0,  radius,  0),
        ( 0, -radius,  0)
    ]

    for i, pos in enumerate(positions):
        bpy.ops.object.light_add(type='AREA', location=pos)
        light = bpy.context.active_object
        light.name = f"StudioLight_{i}"

        light.data.energy = strength
        light.data.shape = 'SQUARE'
        light.data.size = size

        direction = mathutils.Vector((0, 0, 0)) - light.location
        light.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

        lights.append(light)

    return lights



# ================== MAIN ==================
def run_synthetic_data_gen():
    clear_scene()
    import_obj(OBJ_PATH)
    
    obj = bpy.context.selected_objects[0]
    apply_white_material(obj, normal_map_path)
    
    cam = add_camera()
    
    scene = bpy.context.scene

    # ================== WORLD NOIR SANS LUMIÈRE ==================
    if scene.world is None:
        scene.world = bpy.data.worlds.new("BlackWorld")

    scene.world.use_nodes = True
    world_nodes = scene.world.node_tree.nodes
    world_links = scene.world.node_tree.links

    world_nodes.clear()

    bg = world_nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (0, 0, 0, 1)
    bg.inputs["Strength"].default_value = 0.0

    out = world_nodes.new("ShaderNodeOutputWorld")
    world_links.new(bg.outputs["Background"], out.inputs["Surface"])
    
    bpy.context.scene.render.film_transparent = True
    
    
    # =================== SOLEIL ===================
    add_full_studio_lighting()
    
    
    # ================== GPU / CUDA ==================
    scene.render.engine = 'CYCLES'

    prefs = bpy.context.preferences
    cycles_prefs = prefs.addons['cycles'].preferences

    cycles_prefs.compute_device_type = 'CUDA'

    # Active uniquement le GPU
    for device in cycles_prefs.devices:
        device.use = (device.type == 'CUDA')

    scene.cycles.device = 'GPU'
    scene.cycles.samples = 256
    scene.cycles.use_denoising = False
    scene.cycles.max_bounces = 1
    scene.cycles.diffuse_bounces = 1
    scene.cycles.glossy_bounces = 1
    scene.cycles.transparent_max_bounces = 1
    scene.cycles.use_adaptive_sampling = False
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = 'OPENIMAGEDENOISE'
    
    # ================== RÉSOLUTION 4K ==================
    scene.render.resolution_x = 1024
    scene.render.resolution_y = 1024
    scene.render.resolution_percentage = 100

    
    scene.render.film_transparent = True
    
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'

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

        scene.render.filepath = os.path.join(
            NORM_DIR, NAME_PIC + f"_{i}.png"
        )
        bpy.ops.render.render(write_still=True)

        print(f"Picture {i} générée.")


    print("Extraction terminée.")

# ================== RUN ==================

run_synthetic_data_gen()