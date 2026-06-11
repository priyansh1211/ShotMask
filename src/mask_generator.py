import os
import numpy as np
from PIL import Image

# Import our own modules
from src.alpha_exporter import create_rgba_image, save_png
from src.sam2_predictor import SAM2Predictor

def generate_masks(frames_folder,output_folder, checkpoint_path, model_cfg,x,y):
    """
    Generate masks for all frames in a folder using SAM2 predictor.
    IN: frames_folder: path to extracted JPG frames
        output_folder: path to save PNG masks
        checkpoint_path: path to SAM2 checkpoint
        model_cfg: SAM2 model configuration
        x, y: VFX Artist's click coordinates for SAM2 mask generation
    OUT: Saves RGBA PNG masks in the output folder
    """
    
    ##Create output folder if it does not exist
    os.makedirs(output_folder, exist_ok=True)

    # Load SAM2Predictor
    predictor = SAM2Predictor(checkpoint_path,model_cfg)

    # Get list of all frames, sorted by name
    frames = sorted([f for f in os.listdir(frames_folder) if f.endswith('.jpg')])

    total = len(frames)
    if total == 0:
        print("No frames found in the specified folder.")
        return
    if total>500:
        print(f"Warning: Found {total} frames. Processing may take a long time.")
    print(f"Found {total} frames. Starting mask generation...")

    # Validate coordinates are within frame dimensions
    sample_frame = np.array(Image.open(
        os.path.join(frames_folder, frames[0])
    ))

    h,w = sample_frame.shape[:2]
    
    if not (0 <= x < w and 0 <= y < h):
        print(f"Error: Coordinates (x={x}, y={y}) are out of bounds for frame dimensions (width={w}, height={h}).")
        return

    # Loop through every frame, load frame as numpy array, set frame in predcitor, predict mask using X,Y, Create RGBA Image, Save as PNG, print the progress
    for i,frame in enumerate(frames):
        try:
            frame_path = os.path.join(frames_folder, frame)
            output_path = os.path.join(output_folder, frame.replace('.jpg', '.png'))
            
            # Load frame as numpy array
            frame_array = np.array(Image.open(frame_path).convert('RGB'))
            
            # Set frame in predictor
            predictor.set_frame(frame_array)
            
            # Predict mask using X,Y
            mask, score = predictor.predict_mask(x,y)
            
            if score < 0.3:
                print(f"Warning:[{i+1}/{total}] Low mask confidence ({score:.4f}) for {frame}. Mask may be inaccurate.")
            
            # Create RGBA Image
            rgba_image = create_rgba_image(frame_array, mask)
            
            # Save as PNG
            save_png(rgba_image, output_path)
            
            print(f"[{i+1}/{total}] Processed {frame} - Mask Score: {score:.4f}")

        except Exception as e:
            print(f"Error processing frame {frame}: {e}")
            continue