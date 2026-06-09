import numpy as np
from PIL import Image

## 1. Your frame is shape (H, W, 3) — RGB. Your mask is shape (H, W) — 0s and 1s. What shape does the output RGBA image need to be?
##2. You need to create an alpha channel from your mask. The mask has values 0 and 1. But alpha needs values 0 and 255. How do you convert from one to the other? (Hint: one multiplication)
##3. You have R, G, B from the frame and A from the mask. How do you combine four separate arrays into one (H, W, 4) array? Search: numpy stack arrays along axis

def create_rgba_image(frame, mask):
    # Step 1: Create the alpha channel from the mask
    alpha_channel = mask * 255  # Convert 0s and 1s to 0s and 255s

    # Step 2: Stack the R, G, B channels from the frame with the alpha channel
    rgba_image = np.dstack((frame, alpha_channel))  # Combine into (H, W, 4)

    return rgba_image

def save_png(rgba_array, output_path):
    # Convert the RGBA array to a PIL Image and save as PNG
    image = Image.fromarray(rgba_array.astype('uint8'), 'RGBA')
    image.save(output_path)
    print(f"Saved RGBA image to {output_path}")