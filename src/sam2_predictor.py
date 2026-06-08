import torch
import numpy as np
from sam2.build_sam import build_sam2
from sam2.sam2_image_predictor import SAM2ImagePredictor


class SAM2Predictor:
    def __init__(self,checkpoint_path,model_cfg):
        """
        Load SAM2 model from checkpoint
        IN: path to .pt file, model config name
        OUT: None (SAM 2 model is loaded and ready for prediction) Model is stored in self.predictor 
        """
        model = build_sam2(config_file=model_cfg, ckpt_path=checkpoint_path) ## build the model and it returns a model
        self.predictor = SAM2ImagePredictor(model) ## build the predictor and it returns a predictor
        print("Model loaded successfully.")
        
    def set_frame(self,frame):
        """
        Give SAM 2 a frame to work with.
        Input: frame: a numpy array of shape (H, W, 3) representing the image frame.
        Output: None (SAM 2 stores it internally for later use in prediction).
        """
        with torch.inference_mode():
            self.predictor.set_image(frame) ## Set the image for the predictor to work with. This is necessary before making any predictions.
        print("Frame set successfully.")
    
    def predict_mask(self,x,y):
        """
        Generate a mask for the object at the given point (x, y).
        Predict a mask given a point (x, y).
        Input: x: x-coordinate of the point, y: y-coordinate of the point. (Artist's click)
        Output: A binary mask of shape (H, W) where pixels belonging to the predicted object are 1 and others are 0.
        """
        input_point = np.array([[x, y]]) ## Create an array for the input point
        input_label = np.array([1]) ## Create an array for the input label (1 for foreground)
        with torch.inference_mode():
            masks, scores, _ = self.predictor.predict(
                point_coords=input_point, 
                point_labels=input_label,
                multimask_output=True
            ) ## Predict the mask using the predictor
        best_mask = masks[np.argmax(scores)] ## Select the mask with the highest score
        return best_mask, scores[np.argmax(scores)] ## Return the best mask and its score