import bpy
import json
import math
import os
import mathutils
import glob

N = 10
RADIUS = 1.0
BASE_PATH = "./BlenderOutput" 
JSON_NAME = "camera_pos.json"

NORM_DIR = os.path.join(BASE_PATH, "normals")
if not os.path.exists(NORM_DIR): os.makedirs(NORM_DIR)

def setup_compositor():
    """ Configure les normales pour qu'elles utilisent le canal Alpha (transparence) """
    bpy.context.scene.use_nodes = True
    tree = bpy.context.scene.node_tree
    for node in tree.nodes: tree.nodes.remove(node)
        
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

def run_synthetic_data_gen():
    cam = bpy.data.objects.get("Camera")
    if not cam: return

    bpy.context.scene.render.film_transparent = True
    bpy.context.scene.render.engine = 'CYCLES'
    
    bpy.context.scene.render.use_compositing = True
    
    norm_node = setup_compositor()
    camera_log = []
    golden_angle = math.pi * (3 - math.sqrt(5))

    for i in range(N):
        z_ratio = 1 - (i / float(N - 1)) * 2
        r_at_z = math.sqrt(1 - z_ratio * z_ratio)
        theta = golden_angle * i
        pos_x, pos_y, pos_z = math.cos(theta)*r_at_z*RADIUS, math.sin(theta)*r_at_z*RADIUS, z_ratio*RADIUS
        
        cam.location = (pos_x, pos_y, pos_z)
        direction = mathutils.Vector((0, 0, 0)) - cam.location
        cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
        
        file_id = f"{i}"
        norm_node.file_slots[0].path = f"temp_norm_{file_id}_"
        
        bpy.ops.render.render(write_still=False)
        
        search_pattern = os.path.join(NORM_DIR, f"temp_norm_{file_id}_*.png")
        found_files = glob.glob(search_pattern)
        if found_files:
            final_path = os.path.join(NORM_DIR, f"normal_{file_id}.png")
            if os.path.exists(final_path): os.remove(final_path)
            os.rename(found_files[0], final_path)

        camera_log.append({
            "id": i,
            "image_normal": f"normals/normal_{file_id}.png",
            "position": {"x": float(pos_x), "y": float(pos_y), "z": float(pos_z)},
            "rotation_euler": {"x": float(cam.rotation_euler.x), "y": float(cam.rotation_euler.y), "z": float(cam.rotation_euler.z)}
        })
        print(f"Normal Map {i} générée avec transparence.")

    with open(os.path.join(BASE_PATH, JSON_NAME), 'w') as f:
        json.dump(camera_log, f, indent=4)
    print(f"Extraction terminée ! Fichier créé : {os.path.join(BASE_PATH, JSON_NAME)}")

run_synthetic_data_gen()