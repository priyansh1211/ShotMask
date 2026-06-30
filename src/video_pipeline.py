import os
import shutil
import numpy as np
from PIL import Image

from src.preprocess import extract_frames
from src.video_predictor import SAM2VideoPredictor
from src.alpha_exporter import create_rgba_image, save_png

def run_shotmask_pipeline(video_path, x, y, work_dir, checkpoint_path, model_cfg, obj_id =1):
    """
    Full ShotMask pipeline: Video -> tracked masks -> ZIP download.
    IN: video_path: path to video file
        x, y: coordinates of the object to track
        work_dir: working directory for intermediate files
        checkpoint_path: path to SAM model checkpoint
        model_cfg: configuration for the SAM model
        obj_id: ID of the object to track (default is 1)
    OUT: path to final ZIP file containing the tracked masks
    """
    # Create working directory if it doesn't exist
    os.makedirs(work_dir, exist_ok=True)

    # Step 1: Extract frames from the video
    frames_dir = os.path.join(work_dir, "frames")
    extract_frames(video_path, output_folder = frames_dir)

    if len(os.listdir(frames_dir)) == 0:
        raise RuntimeError(f"No frames extracted from video: {video_path}. Check the video file and ensure it is a valid format.")

    #step 2: Get frame dimensions from first frame (for bounds checking)
    first_frame_path = os.path.join(frames_dir, sorted(os.listdir(frames_dir))[0])
    with Image.open(first_frame_path) as img:
        frame_width, frame_height = img.size
    
    #step 3: Initialize the SAM2VideoPredictor with the provided checkpoint and model configuration
    predictor = SAM2VideoPredictor(checkpoint_path, model_cfg=model_cfg)

    #step 4: Run the 3-method flow - init_video, add_click, track
    inference_state = predictor.init_video(frames_dir)
    predictor.add_click(
        inference_state, 
        obj_id=obj_id, 
        x=x, 
        y=y, 
        frame_width=frame_width, 
        frame_height=frame_height
    )
    video_segments = predictor.track(inference_state)

    #step 5: export each frame as RGBA and save as PNG
    masks_dir = os.path.join(work_dir, "masks")
    os.makedirs(masks_dir, exist_ok=True)
    
    numeric_frames_dir = frames_dir.rstrip('/\\') + "_numeric"
    actual_frames_dir = numeric_frames_dir if os.path.isdir(numeric_frames_dir) else frames_dir

    frame_files = sorted(
        os.listdir(actual_frames_dir),
        key = lambda f: int(os.path.splitext(f)[0])
    )
    
    for frame_idx, obj_masks in video_segments.items():
        mask = obj_masks[obj_id].squeeze()  # Assuming obj_masks[obj_id] is a 3D array (H, W, 1)
        frame_path = os.path.join(actual_frames_dir, frame_files[frame_idx])
        frame_array = np.array(Image.open(frame_path).convert("RGB"))  # Convert to RGB array

        rgba_image = create_rgba_image(frame_array,mask)
        save_png(rgba_image, os.path.join(masks_dir, f"mask_{frame_idx:04d}.png"))
    
    #step 6: Create a ZIP file of the masks directory
    zip_path = os.path.join(work_dir, "tracked_masks.zip")
    shutil.make_archive(base_name=zip_path.replace('.zip', ''), format='zip', root_dir=masks_dir)
    return zip_path