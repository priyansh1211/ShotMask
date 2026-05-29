import torch
import numpy as np

class SAM2Predictor:
    
    def __init__(self, checkpoint_path, model_cfg):
        """
        Load SAM 2 model from checkpoint.
        IN: path to .pt file, model config name
        OUT: nothing — model stored in self.predictor
        """
        pass
    
    def set_frame(self, frame):
        """
        Give SAM 2 a frame to work with.
        IN: numpy array (height × width × 3)
        OUT: nothing — SAM 2 stores it internally
        """
        pass
    
    def predict_mask(self, x, y):
        """
        Generate mask for subject at click point.
        IN: x coordinate, y coordinate (artist's click)
        OUT: mask (height × width) — binary array
             score — confidence (0 to 1)
        """
        pass