import os
import PIL.Image as Image
import numpy as np


def laod_images(folder):
    images = []

    for filename in os.listdir(folder):
        img_path = os.path.join(folder, filename)
        img = Image.open(img_path).convert('RGB')
        images.append(np.array(img))
    
    return images

def change_R(images, R):
    changed_images = []
    for img in images:
        img_copy = img.copy()
        img_copy[:, :, 0] = R * img[:, :, R[0]*2 + R[1]*1 + R[2]*0]
        img_copy[:, :, 1] = img[:, :, R[3]*2 + R[4]*1 + R[5]*0]
        img_copy[:, :, 2] = img[:, :, R[6]*2 + R[7]*1 + R[8]*0]
        changed_images.append(img_copy.astype(np.uint8))
    return changed_images

if __name__ == "__main__":
    
    folder_path = "./images/test"
    images = laod_images(folder_path)
    # Matrice de rotation de R360 degrees
    R = [0, 1, 0,
         1, 0, 0,
         0, 0, 1]