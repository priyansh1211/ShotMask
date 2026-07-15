import cv2 as cv
import os
import argparse

def extract_frames(video_path, output_folder, target_fps=None):
    """
    Extract frames from a video file.
    IN: path to video, path to output folder,
        target_fps — optional. Leave as None for production use (rotoscoping
        needs a mask for every original frame, or the exported PNG sequence
        won't line up with the source footage in Nuke/AE). Only pass a value
        here for your own dev/testing iteration, where you want a quick
        smoke test without re-processing 500 frames every run.
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

    # Native FPS unless a lower target_fps is explicitly requested. Frame
    # skipping is computed as a stride, not a hard frame count, so the
    # output stays evenly spaced regardless of the source's actual FPS.
    if target_fps is not None and fps > target_fps:
        frame_stride = round(fps / target_fps)
    else:
        frame_stride = 1

    i = 0
    saved = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if i % frame_stride == 0:
            cv.imwrite(
                os.path.join(output_folder, f'frame_{saved:04d}.jpg'),
                frame
            )
            saved += 1
        i += 1

    cap.release()
    print(f"Extracted {saved} frames to {output_folder}"
          + (f" (downsampled from {fps:.1f}fps to ~{target_fps}fps for testing)"
             if frame_stride > 1 else ""))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--video', required=True, help='Path to input video')
    parser.add_argument('--output', default='examples/Frames', help='Output folder')
    parser.add_argument('--target-fps', type=float, default=None,
                         help='Downsample to this FPS for fast dev iteration. '
                              'Omit for production (native FPS, every frame).')
    args = parser.parse_args()
    
    extract_frames(args.video, args.output, target_fps=args.target_fps)