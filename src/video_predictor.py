import os
import numpy as np
import torch
from sam2.build_sam import build_sam2_video_predictor
import shutil
class SAM2VideoPredictor:

    def __init__(self, checkpoint_path, model_cfg):
        """
        Load SAM2 model from checkpoint for video prediction.
        IN: path to .pt file, model config name
        OUT: None — model stored in self.predictor
        """
        try:
            model = build_sam2_video_predictor(config_file=model_cfg, ckpt_path=checkpoint_path)
        except Exception as e:
            raise RuntimeError(f"Failed to load SAM2 video model: {e}")
        self.predictor = model
        self._click_added = False
        print("Video model loaded successfully.")

    def _prepare_numeric_frames(self, frames_folder):
        """
        SAM2's Video predictor requires purely numeric frame filenames. 
        This function renames frames in the folder to a numeric sequence if necessary.
        IN: frames_folder - original folder (e.g. frames_0000.jpg style)
        OUT: path to a folder with SAM2 compatible numeric filenames
        """
        frames = sorted([f for f in os.listdir(frames_folder) if f.lower().endswith(('.jpg', '.jpeg'))])
        try:
            int(os.path.splitext(frames[0])[0])
            return frames_folder
        except ValueError:
            pass
        numeric_folder = frames_folder.rstrip('/\\') + "_numeric"
        
        if os.path.exists(numeric_folder):
            shutil.rmtree(numeric_folder)
        os.makedirs(numeric_folder)
        
        for i,frame in enumerate(frames):
            shutil.copy(os.path.join(frames_folder, frame), os.path.join(numeric_folder, f"{i}.jpg"))
        return numeric_folder        
   
    def init_video(self, video_path):
        """
        Initialize SAM 2 video tracking on a folder of frames.
        IN: video_path — folder of extracted JPG frames
        OUT: inference_state — needed by add_click and track
        """
        if not os.path.isdir(video_path):
            raise FileNotFoundError(f"Video frames folder not found: {video_path}")
        frames = [f for f in os.listdir(video_path) if f.lower().endswith(('.jpg', '.jpeg'))]
        
        if len(frames) == 0:
            raise ValueError(f"No JPEG frames found in {video_path}")
        # Ensure frame filenames are SAM2-compatible (purely numeric)
        video_path = self._prepare_numeric_frames(video_path)
        
        inference_state = self.predictor.init_state(video_path=video_path)
        
        self.predictor.reset_state(inference_state)
        
        print(f"Video initialized successfully with {len(frames)} frames.")
        return inference_state

    def add_click(self, inference_state, obj_id, x, y, frame_width=None, frame_height=None):
        """
        Add a click point on frame 0 to select the subject to track.
        IN: inference_state — from init_video
            obj_id — positive integer ID for this subject
            x, y — artist's click coordinates
            frame_width, frame_height — optional, for bounds checking
        OUT: None (the click is registered internally for tracking)
        """
        obj_id, x, y = int(obj_id), int(x), int(y)

        if obj_id < 1:
            raise ValueError("obj_id must be a positive integer")

        if frame_width is not None and frame_height is not None:
            if not (0 <= x < frame_width and 0 <= y < frame_height):
                raise ValueError(
                    f"Coordinates ({x}, {y}) are out of bounds for frame size ({frame_width}x{frame_height})"
                )

        points = np.array([[x, y]], dtype=np.float32)
        labels = np.array([1], dtype=np.int32)

        self.predictor.add_new_points_or_box(
            inference_state=inference_state,
            frame_idx=0,
            obj_id=obj_id,
            points=points,
            labels=labels
        )
        self._click_added = True
        print(f"Click added successfully for object ID {obj_id} at coordinates ({x}, {y}).")

    def track(self, inference_state):
        """
        Propagate the clicked subject across all frames in the video.
        IN: inference_state — from init_video, after add_click was called
        OUT: video_segments — dict mapping frame_idx -> {obj_id: binary_mask}
        """
        if not self._click_added:
            raise RuntimeError("No click added. Call add_click() before track().")

        video_segments = {}
        try:
            for out_frame_idx, out_obj_ids, out_mask_logits in self.predictor.propagate_in_video(inference_state):
                video_segments[out_frame_idx] = {
                obj_id: (out_mask_logits[i] > 0.0).cpu().numpy()
                for i, obj_id in enumerate(out_obj_ids)
            }
        except torch.cuda.OutOfMemoryError:
            raise RuntimeError(
            "GPU ran out of memory during tracking. Try a shorter video or lower resolution frames."
        )
        print(f"Tracking completed. Generated masks for {len(video_segments)} frames.")
        return video_segments