import bpy
import os
import math
import mathutils


# ===============================
# PARAMÈTRES
# ===============================

OBJ_NAME = "Patatoide_lisse.obj"

BASE_DIR = os.path.join(
    os.path.expanduser("~"),
    "Documents", "Github", "Normal-map-grouping-on-smooth-model"
)

OBJ_DIR = os.path.join(BASE_DIR, "model")
IMAGE_DIR = os.path.join(BASE_DIR, "images", "patatoide_textures")
BAKE_DIR = os.path.join(BASE_DIR, "images", "patatoide_baked")

TEXTURE_RES = 4096

SEUIL_ANGLE = 0.95

os.makedirs(BAKE_DIR, exist_ok=True)

CAM_LOCATION = (0, 0, -2)     # mettres
CAM_ROTATION = (180, 0, -68)  # degrés


# ===============================
# RESET SCÈNE
# ===============================

scene = bpy.context.scene

# Supprimer tous les objets
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)


# ===============================
# IMPORT OBJ (Blender 4.x)
# ===============================

obj_path = os.path.join(OBJ_DIR, OBJ_NAME)

bpy.ops.wm.obj_import(filepath=obj_path)

obj = bpy.context.selected_objects[0]
obj.name = "Patatoide"
scene.view_layers[0].objects.active = obj


# ===============================
# CAMÉRA
# ===============================

cam_data = bpy.data.cameras.new("ProjectionCamera")
cam = bpy.data.objects.new("ProjectionCamera", cam_data)
scene.collection.objects.link(cam)

cam.location = CAM_LOCATION
cam.rotation_euler = [math.radians(a) for a in CAM_ROTATION]

scene.camera = cam


# ===============================
# UV PROJECTION
# ===============================

# Trouver une zone VIEW_3D valide
area_3d = next((area for area in bpy.context.window.screen.areas if area.type == 'VIEW_3D'), None)
if area_3d is None:
    raise RuntimeError("Aucune zone VIEW_3D trouvée")
region_3d = next((region for region in area_3d.regions if region.type == 'WINDOW'), None)
if region_3d is None:
    raise RuntimeError("Aucune région WINDOW dans VIEW_3D trouvée")

override = {
    "window": bpy.context.window,
    "screen": bpy.context.window.screen,
    "area": area_3d,
    "region": region_3d,
    "scene": bpy.context.scene,
    "active_object": obj,
    "edit_object": obj
}

# Passer à la vue de la caméra
with bpy.context.temp_override(**override):
    bpy.ops.view3d.view_camera()

uv_layer_name = "CameraUV" # nom de la couche UV
uv_layer = obj.data.uv_layers.get(uv_layer_name)

if uv_layer is None:
    uv_layer = obj.data.uv_layers.new(name=uv_layer_name)
obj.data.uv_layers.active = uv_layer

# Passer en EDIT mode
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')

# Projeter les UV
with bpy.context.temp_override(**override):
    bpy.ops.uv.project_from_view(
        camera_bounds=True,
        correct_aspect=True,
        scale_to_bounds=True
    )

bpy.ops.object.mode_set(mode='OBJECT')


# ===============================
# TEXTURE
# ===============================

image_files = [
    f for f in os.listdir(IMAGE_DIR)
    if f.lower().endswith((".png", ".jpg", ".jpeg"))
]
if not image_files:
    raise RuntimeError("Aucune image trouvée")

image_name = image_files[0]

img_path = os.path.join(IMAGE_DIR, image_name)


# ===============================
# MATÉRIAU
# ===============================

mat = bpy.data.materials.new("ProjectionMaterial")
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links
nodes.clear()

# Les nœuds pour le shadeur
uv_map_node = nodes.new("ShaderNodeUVMap")
uv_map_node.location = (-400, 0)
uv_map_node.uv_map = uv_layer_name

tex_node = nodes.new("ShaderNodeTexImage")
tex_node.location = (-200, 0)
tex_node.image = bpy.data.images.load(img_path)

bsdf = nodes.new("ShaderNodeBsdfPrincipled")
bsdf.location = (100, 0)

bsdf_black = nodes.new("ShaderNodeBsdfPrincipled")
bsdf_black.location = (100, -400)
bsdf_black.inputs["Base Color"].default_value = (0, 0, 0, 1)

mix_shader = nodes.new("ShaderNodeMixShader")
mix_shader.location = (400, 0)

geometry = nodes.new("ShaderNodeNewGeometry")
geometry.location = (-400, 300)

dot = nodes.new("ShaderNodeVectorMath")
dot.operation = 'DOT_PRODUCT'
dot.location = (0, 300)

cam_vec_node = nodes.new("ShaderNodeCombineXYZ")
cam_norm = mathutils.Vector(CAM_LOCATION).normalized()
cam_vec_node.inputs[0].default_value = cam_norm[0]
cam_vec_node.inputs[1].default_value = cam_norm[1]
cam_vec_node.inputs[2].default_value = cam_norm[2]
cam_vec_node.location = (-200, 200)

greater_than = nodes.new("ShaderNodeMath")
greater_than.operation = 'GREATER_THAN'
greater_than.inputs[1].default_value = SEUIL_ANGLE
greater_than.location = (200, 300)

output = nodes.new("ShaderNodeOutputMaterial")
output.location = (600, 0)

# Connexion : UV Map -> Texture -> BSDF
links.new(uv_map_node.outputs["UV"], tex_node.inputs["Vector"])
links.new(tex_node.outputs["Color"], bsdf.inputs["Base Color"])

# Connexion du masque caméra
links.new(geometry.outputs["Normal"], dot.inputs[0])
links.new(cam_vec_node.outputs[0], dot.inputs[1])
links.new(dot.outputs["Value"], greater_than.inputs[0])
links.new(greater_than.outputs[0], mix_shader.inputs["Fac"])

# Mix visible / invisible
links.new(bsdf.outputs["BSDF"], mix_shader.inputs[2])
links.new(bsdf_black.outputs["BSDF"], mix_shader.inputs[1])
links.new(mix_shader.outputs["Shader"], output.inputs["Surface"])

# Appliquer le matériau
obj.data.materials.clear()
obj.data.materials.append(mat)


# ===============================
# BAKE SUR L'UV ORIGINALE
# ===============================

# Activer la UV “originale” (celle de l'OBJ)
original_uv_name = "UVMap"  # remplace par le nom de l'UV de ton OBJ si différent
obj.data.uv_layers.active = obj.data.uv_layers[original_uv_name]

# Créer l'image pour le bake
bake_img = bpy.data.images.new(
    name="BakedTexture",
    width=TEXTURE_RES,
    height=TEXTURE_RES,
    alpha=False,
    float_buffer=False
)

# Créer un nœud TexImage qui va recevoir le bake
bake_tex_node = nodes.new("ShaderNodeTexImage")
bake_tex_node.image = bake_img
bake_tex_node.location = (800, 0)
bake_tex_node.select = True
nodes.active = bake_tex_node

# Paramètres Blender pour le bake
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.cycles.device = 'GPU'

# Lancer le bake (diffuse color seulement)
bpy.ops.object.bake(
    type='DIFFUSE',
    pass_filter={'COLOR'},
    use_clear=True,
    margin=16,
    use_selected_to_active=False
)

# Sauvegarder l'image bake
image_name = image_name.replace(".png", "")
bake_path = os.path.join(BAKE_DIR, image_name + "_baked.png")
bake_img.filepath_raw = bake_path
bake_img.file_format = 'PNG'
bake_img.save()