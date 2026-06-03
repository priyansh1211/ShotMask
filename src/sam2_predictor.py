import torch
import numpy as np
from sam2.build_sam import build_sam2
from sam2.sam2_image_predictor import SAM2ImagePredictor

checkpoint = "checkpoints/sam2.1_hiera_tiny.pt"  ## Model weights
model_cfg = "configs/sam2.1/sam2.1_hiera_t.yaml" ##the model configuration file

model = build_sam2(config_file=model_cfg, ckpt_path=checkpoint) ## build the model and it returns a model
predictor = SAM2ImagePredictor(model) ## build the predictor and it returns a predictor
print("Model loaded successfully.")