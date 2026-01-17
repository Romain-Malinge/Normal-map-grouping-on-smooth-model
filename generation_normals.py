import bpy
import json
import math
import os
import mathutils

N = 10 # nombre de takes
RADIUS = 1.0 # rayon de la sphère sur laquelle on prend les takes
BASE_PATH = "./BlenderOutput" 
JSON_NAME = "camera_pos.json"

RGB_DIR = os.path.join(BASE_PATH, "rgb")
NORM_DIR = os.path.join(BASE_PATH, "normals")

for d in [RGB_DIR, NORM_DIR]:
    if not os.path.exists(d):
        os.makedirs(d)

def setup_compositor():
    """ Configure les nodes pour extraire la carte des normales """
    bpy.context.scene.use_nodes = True
    tree = bpy.context.scene.node_tree
    for node in tree.nodes: 
        tree.nodes.remove(node)
        
    render_layers = tree.nodes.new('CompositorNodeRLayers')
    file_output = tree.nodes.new('CompositorNodeOutputFile')
    file_output.base_path = NORM_DIR
    file_output.file_slots[0].path = "temp_norm_"
    
    bpy.context.view_layer.use_pass_normal = True
    
    mult = tree.nodes.new('CompositorNodeMixRGB')
    mult.blend_type = 'MULTIPLY'
    mult.inputs[2].default_value = (0.5, 0.5, 0.5, 1)
    
    add = tree.nodes.new('CompositorNodeMixRGB')
    add.blend_type = 'ADD'
    add.inputs[2].default_value = (0.5, 0.5, 0.5, 1)
    
    tree.links.new(render_layers.outputs['Normal'], mult.inputs[1])
    tree.links.new(mult.outputs[0], add.inputs[1])
    tree.links.new(add.outputs[0], file_output.inputs[0])
    
    return file_output

def run_synthetic_data_gen():
    cam = bpy.data.objects.get("Camera")
    if not cam: return

    norm_node = setup_compositor()
    camera_log = []
    golden_angle = math.pi*(3-math.sqrt(5))

    for i in range(N):
        z_ratio = 1-(i/float(N-1))*2
        r_at_z = math.sqrt(1 - z_ratio * z_ratio)
        theta = golden_angle*i
        
        pos_x = math.cos(theta)*r_at_z*RADIUS
        pos_y = math.sin(theta)*r_at_z*RADIUS
        pos_z = z_ratio*RADIUS
        
        cam.location = (pos_x, pos_y, pos_z)
        direction = mathutils.Vector((0, 0, 0)) - cam.location
        cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
        
        file_id = f"{i}"
        rgb_filename = f"color_{file_id}.png"
        norm_filename = f"normal_{file_id}.png"
        
        bpy.context.scene.render.filepath = os.path.join(RGB_DIR, rgb_filename)
        norm_node.file_slots[0].path = f"temp_norm_{file_id}"
        
        bpy.ops.render.render(write_still=True)
        
        temp_name = f"temp_norm_{file_id}{bpy.context.scene.frame_current:04d}.png"
        temp_path = os.path.join(NORM_DIR, temp_name)
        final_norm_path = os.path.join(NORM_DIR, norm_filename)
        
        if os.path.exists(temp_path):
            if os.path.exists(final_norm_path): os.remove(final_norm_path)
            os.rename(temp_path, final_norm_path)

        camera_log.append({
            "id": i,
            "image_rgb": f"rgb/{rgb_filename}",
            "image_normal": f"normals/{norm_filename}",
            "position": {"x": float(pos_x), "y": float(pos_y), "z": float(pos_z)},
            "rotation_euler": {"x": float(cam.rotation_euler.x), "y": float(cam.rotation_euler.y), "z": float(cam.rotation_euler.z)}
        })
        print(f"Rendu {i+1}/{N} terminé.")

    with open(os.path.join(BASE_PATH, JSON_NAME), 'w') as f:
        json.dump(camera_log, f, indent=4)

run_synthetic_data_gen()