import torch
import numpy as np
from sam2.build_sam import build_sam2
from sam2.sam2_image_predictor import SAM2ImagePredictor

checkpoint = "checkpoints/sam2_hiera_tiny.pt"
model_cfg = "configs/sam2.1/sam2.1_hiera_t.yaml"

model = build_sam2(checkpoint=checkpoint, model_cfg=model_cfg)
predictor = SAM2ImagePredictor(model)
print("Model loaded successfully.")