import torch
import numpy as np
from sam2.build_sam import build_sam2
from sam2.sam2_image_predictor import SAM2ImagePredictor

checkpoint = "checkpoints/sam2.1_hiera_tiny.pt"  ## Model weights
model_cfg = "configs/sam2.1/sam2.1_hiera_t.yaml" ##the model configuration file

model = build_sam2(config_file=model_cfg, ckpt_path=checkpoint) ## build the model and it returns a model
predictor = SAM2ImagePredictor(model) ## build the predictor and it returns a predictor
print("Model loaded successfully.")

def set_frame(self,frame):
    """
    Give SAM 2 a frame to work with.
    Input: frame: a numpy array of shape (H, W, 3) representing the image frame.
    Output: None (SAM 2 stores it internally for later use in prediction).
    """
    with torch.inference_mode():
        self.predictor.model.set_image(frame) ## Set the image for the predictor to work with. This is necessary before making any predictions.