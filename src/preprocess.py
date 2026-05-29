import cv2 as cv
import os
import argparse

def extract_frames(video_path, output_folder):
    """
    Extract frames from a video file.
    IN: path to video, path to output folder
    OUT: JPG frames saved to output folder
    """
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    cap = cv.VideoCapture(video_path)
    
    if not cap.isOpened():
        print(f"Error: Cannot open video {video_path}")
        return
    
    # Store metadata
    fps = cap.get(cv.CAP_PROP_FPS)
    total_frames = int(cap.get(cv.CAP_PROP_FRAME_COUNT))
    print(f"FPS: {fps}")
    print(f"Total frames: {total_frames}")
    
    i = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        cv.imwrite(
            os.path.join(output_folder, f'frame_{i:04d}.jpg'), 
            frame
        )
        i += 1
    
    cap.release()
    print(f"Extracted {i} frames to {output_folder}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--video', required=True, help='Path to input video')
    parser.add_argument('--output', default='examples/Frames', help='Output folder')
    args = parser.parse_args()
    
    extract_frames(args.video, args.output)