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
        smoke test without re-processing 500 frames every run. When set, the output FPS is approximate (see stride note below)
    OUT: PNG frames saved to output folder
    """
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    cap = cv.VideoCapture(video_path)
    
    if not cap.isOpened():  ##cap.isOpened() is a method used to check whether a cv2.VideoCapture object has successfully initialized and connected to a video source. It returns True if the video file, image sequence, or camera stream was successfully opened, and False otherwise
        raise RuntimeError(f"Cannot open video {video_path}")
    
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
    
    # The above code calculates how many frames to skip forward to downsample a high-framerate video to a lower target framerate, and it uses a mathematical rounding trick. The resulting FPS is approximate: stride is a whole number, so only source/n values are reachable (e.g. 30 fps with target 24 gives stride 1, no downsampling).
    # It divides the original FPS by the target FPS and rounds it to the nearest whole number. This number is your stride. 
    
    i = 0
    saved = 0
    try:
        while True:
            ret, frame = cap.read()  # cap.read() is a method used to read the next frame from a video file or camera stream. It returns two values: ret and frame. ret is a boolean indicating whether the frame was successfully read (True) or if the end of the video has been reached (False). frame is the actual image data of the frame that was read, typically represented as a NumPy array.
            if not ret:
                break
            if i % frame_stride == 0:
                out_path = os.path.join(output_folder, f'frame_{saved:04d}.png')
                ok = cv.imwrite(out_path, frame)
                if not ok:
                    raise RuntimeError(f"cv.imwrite failed for {out_path} — frame not written to disk")
                saved += 1
            i += 1
    finally:
        cap.release()

    if frame_stride == 1 and saved != total_frames:
        print(f"WARNING: saved {saved} frames, but expected {total_frames} — verify the sequence length against the source")
    
    print(f"Extracted {saved} frames to {output_folder}"
          + (f" (downsampled from {fps:.1f}fps to ~{target_fps}fps for testing)"
             if frame_stride > 1 else ""))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()  # this initializes an ArgumentParser object, which is used to handle command-line arguments in Python scripts. It provides a way to define what arguments the script expects, parse those arguments when the script is run, and access their values within the code.
    parser.add_argument('--video', required=True, help='Path to input video') # this is a mandatory argument that specifies the path to the input video file. The script will not run without this argument being provided, i.e., the user must supply a valid video file path when executing the script.
    parser.add_argument('--output', default='examples/Frames', help='Output folder') # this argument specifies the directory where the extracted frames will be saved. If the user does not provide a value for this argument, it defaults to 'examples/Frames'. The script will create this folder if it does not already exist.
    parser.add_argument('--target-fps', type=float, default=None,
                         help='Downsample to this FPS for fast dev iteration. '
                              'Omit for production (native FPS, every frame).') # this argument allows the user to specify a target frames-per-second (FPS) value for downsampling the video during frame extraction. If provided, the script will extract frames at this lower FPS, which can be useful for quick development and testing. If omitted, the script will extract frames at the video's native FPS, ensuring that every frame is captured for production use. 
    args = parser.parse_args() # this line processes the command-line arguments provided by the user when running the script. It reads the arguments defined earlier (video, output, target-fps) and stores their values in the 'args' object, which can then be accessed throughout the script to control its behavior based on user input.
    
    extract_frames(args.video, args.output, target_fps=args.target_fps) # this line calls the extract_frames function, passing in the values of the command-line arguments that were parsed earlier. It uses args.video for the input video path, args.output for the output folder where frames will be saved, and args.target_fps for the optional downsampling FPS. This effectively initiates the frame extraction process based on the user's specified parameters.