import json
import math
import os

N = 10
RADIUS = 1.0 
OUTPUT_FILE = "camera_pos_degrees.json"

def generate_camera_data(n, radius):
    camera_log = []
    golden_angle = math.pi * (3 - math.sqrt(5))

    for i in range(n):
        z_ratio = 1 - (i / float(n - 1)) * 2 if n > 1 else 1.0
        r_at_z = math.sqrt(max(0.0, 1 - z_ratio * z_ratio))
        theta = golden_angle * i
        
        pos_x = math.cos(theta) * r_at_z * radius
        pos_y = math.sin(theta) * r_at_z * radius
        pos_z = z_ratio * radius
        
        dist_xy = math.sqrt(pos_x**2 + pos_y**2)
        rot_x_rad = math.atan2(dist_xy, pos_z)
        
        if dist_xy < 1e-6:
            rot_z_rad = 0.0 
        else:
            rot_z_rad = math.atan2(pos_y, pos_x) + (math.pi / 2)
            if rot_z_rad > math.pi: rot_z_rad -= 2 * math.pi
            
        if i == 0 and dist_xy < 1e-6:
            rot_z_rad = 0.0

        camera_log.append({
            "id": i,
            "image_normal": f"normals/normal_{i}.png",
            "position": {
                "x": round(pos_x, 6),
                "y": round(pos_y, 6),
                "z": round(pos_z, 6)
            },
            "rotation_degrees": {
                "x": round(math.degrees(rot_x_rad), 2),
                "y": 0.0,
                "z": round(math.degrees(rot_z_rad), 2)
            }
        })
        
    return camera_log

data = generate_camera_data(N, RADIUS)
with open(OUTPUT_FILE, 'w') as f:
    json.dump(data, f, indent=4)

print(f"Fichier généré.")