import json
import math
import os

# Paramètres
N = 20
RADIUS = 5.0  # Distance de la caméra par rapport au centre
OUTPUT_FILE = "camera_data.json"

def generate_sphere_points(n, radius):
    points = []
    golden_angle = math.pi * (3 - math.sqrt(5))  # Angle d'or en radians

    for i in range(n):
        # Calcul de la position Z (de 1 à -1)
        z = 1 - (i / float(n - 1)) * 2
        # Rayon à la hauteur z
        radius_at_z = math.sqrt(1 - z * z)
        
        # Angle horizontal
        theta = golden_angle * i
        
        x = math.cos(theta) * radius_at_z * radius
        y = math.sin(theta) * radius_at_z * radius
        z_pos = z * radius
        
        # Calcul de la rotation pour regarder vers le centre (0,0,0)
        # Dans Blender, la caméra pointe par défaut vers -Z.
        # On calcule les angles d'Euler (en radians)
        direction = (-x, -y, -z_pos)
        # Rotation X : inclinaison (tangage)
        rot_x = math.atan2(math.sqrt(x**2 + y**2), z_pos)
        # Rotation Z : lacet
        rot_z = math.atan2(y, x) + math.pi / 2
        
        points.append({
            "id": i,
            "position": {"x": x, "y": y, "z": z_pos},
            "rotation_euler": {"x": rot_x, "y": 0.0, "z": rot_z}
        })
    
    return points

camera_data = generate_sphere_points(N, RADIUS)

# Export en JSON
output_path = os.path.join(os.path.expanduser("~"), "Desktop", OUTPUT_FILE)
with open(output_path, 'w') as f:
    json.dump(camera_data, f, indent=4)

print(f"Terminé ! {N} points générés dans {output_path}")