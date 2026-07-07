"""
ShotMask — Gradio front end

Uses the pipeline already in src/ (preprocess, video_predictor, alpha_exporter):
upload a shot, click the object once on frame 0, SAM 2's memory attention
tracks it across the clip, scrub to check quality, export the RGBA PNG
sequence for Nuke / After Effects.
"""

import os
import shutil

import numpy as np
import gradio as gr
from PIL import Image

from src.preprocess import extract_frames
from src.video_predictor import SAM2VideoPredictor
from src.alpha_exporter import create_rgba_image, save_png

# ---------------------------------------------------------------------------
# CONFIG — swap these if you change checkpoint size
# ---------------------------------------------------------------------------
CHECKPOINT_PATH = "checkpoints/sam2.1_hiera_tiny.pt"
MODEL_CFG = "configs/sam2.1/sam2.1_hiera_t.yaml"

FRAMES_DIR = "examples/Frames"
MASKS_DIR = "examples/Masks"
OBJ_ID = 1

# Load the model once at startup so clicking "Track" doesn't reload it every time
predictor = SAM2VideoPredictor(CHECKPOINT_PATH, MODEL_CFG)


def composite_on_checker(frame, mask, tile=16):
    """Show the cutout over a checkerboard so transparency is actually visible."""
    h, w = frame.shape[:2]
    checker = np.zeros((h, w, 3), dtype=np.uint8)
    for yy in range(0, h, tile):
        for xx in range(0, w, tile):
            shade = 200 if ((yy // tile) + (xx // tile)) % 2 == 0 else 120
            checker[yy:yy + tile, xx:xx + tile] = shade

    mask_bool = mask.astype(bool)
    out = checker.copy()
    out[mask_bool] = frame[mask_bool]
    return out


def list_frames():
    return sorted(f for f in os.listdir(FRAMES_DIR) if f.lower().endswith((".jpg", ".jpeg")))


def on_extract(video_path):
    if video_path is None:
        raise gr.Error("Upload a video first.")

    extract_frames(video_path, FRAMES_DIR)
    frames = list_frames()
    if not frames:
        raise gr.Error("No frames were extracted from that video.")

    first_frame_img = Image.open(os.path.join(FRAMES_DIR, frames[0]))
    frame_w, frame_h = first_frame_img.size
    first_frame = np.array(first_frame_img)

    # init_video() also handles renaming frames to SAM2's required numeric
    # filenames internally (see src/video_predictor.py) and resets any prior state.
    inference_state = predictor.init_video(FRAMES_DIR)

    # display, reset click point, clean copy for redraw-on-reset, inference_state, (w, h)
    return first_frame, None, first_frame, inference_state, (frame_w, frame_h)


def on_click(first_frame, evt: gr.SelectData):
    """Draw a marker at the click and remember the coordinates."""
    x, y = evt.index
    vis = first_frame.copy()
    y0, y1 = max(0, y - 4), min(vis.shape[0], y + 4)
    x0, x1 = max(0, x - 4), min(vis.shape[1], x + 4)
    vis[y0:y1, x0:x1] = [255, 0, 0]
    return vis, (x, y)


def on_reset(first_frame):
    return first_frame, None


def on_track(click_point, inference_state, frame_size, progress=gr.Progress()):
    if click_point is None:
        raise gr.Error("Click on the object in frame 0 first.")
    if inference_state is None:
        raise gr.Error("Load frames first.")

    x, y = click_point
    frame_w, frame_h = frame_size

    progress(0, desc="Tracking object across the clip (SAM2 memory attention)...")
    predictor.add_click(inference_state, obj_id=OBJ_ID, x=x, y=y,
                         frame_width=frame_w, frame_height=frame_h)
    video_segments = predictor.track(inference_state)

    if not video_segments:
        raise gr.Error("Tracking produced no masks — check the console log.")

    frames = list_frames()
    first_frame = np.array(Image.open(os.path.join(FRAMES_DIR, frames[0])))
    first_mask = video_segments[0][OBJ_ID].squeeze()
    first_preview = composite_on_checker(first_frame, first_mask)

    slider_update = gr.Slider(
        minimum=0, maximum=max(len(frames) - 1, 0), value=0, step=1,
        visible=True, label=f"Scrub tracked mask (0–{len(frames) - 1})",
    )
    return video_segments, first_preview, slider_update


def show_frame_preview(frame_idx, video_segments):
    if not video_segments:
        raise gr.Error("Track the object first.")

    frames = list_frames()
    frame_idx = int(frame_idx)
    frame = np.array(Image.open(os.path.join(FRAMES_DIR, frames[frame_idx])))

    obj_masks = video_segments.get(frame_idx)
    if not obj_masks:
        return frame  # object wasn't tracked on this frame
    mask = obj_masks[OBJ_ID].squeeze()
    return composite_on_checker(frame, mask)


def export_zip(video_segments):
    if not video_segments:
        raise gr.Error("Track the object first — nothing to export yet.")

    if os.path.isdir(MASKS_DIR):
        shutil.rmtree(MASKS_DIR)
    os.makedirs(MASKS_DIR, exist_ok=True)

    frames = list_frames()

    for frame_idx, obj_masks in video_segments.items():
        mask = obj_masks[OBJ_ID].squeeze()
        frame_path = os.path.join(FRAMES_DIR, frames[frame_idx])
        frame_array = np.array(Image.open(frame_path).convert("RGB"))

        rgba_image = create_rgba_image(frame_array, mask)
        save_png(rgba_image, os.path.join(MASKS_DIR, f"mask_{frame_idx:04d}.png"))

    zip_path = shutil.make_archive("shotmask_export", "zip", MASKS_DIR)
    return zip_path


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
with gr.Blocks(title="ShotMask — AI Rotoscoping") as demo:
    gr.Markdown(
        "# 🎬 ShotMask\n"
        "Click the object once on frame 0 — SAM 2's memory attention tracks it "
        "across the whole clip. Export an RGBA PNG sequence for Nuke / After Effects."
    )

    click_point_state = gr.State(None)
    first_frame_state = gr.State(None)
    inference_state_holder = gr.State(None)
    frame_size_state = gr.State((0, 0))
    video_segments_state = gr.State({})

    with gr.Row():
        with gr.Column():
            video_input = gr.Video(label="1. Upload shot")
            extract_btn = gr.Button("Load frames", variant="primary")
            frame_display = gr.Image(label="2. Click the object (frame 0)")
            reset_btn = gr.Button("Reset point")
            track_btn = gr.Button("3. Track across clip", variant="primary")

        with gr.Column():
            scrub_slider = gr.Slider(minimum=0, maximum=1, value=0, step=1,
                                      label="Scrub tracked mask", visible=False)
            scrub_preview = gr.Image(label="Tracked mask preview (checkerboard = transparent)")
            export_btn = gr.Button("4. Export PNG sequence (.zip)", variant="primary")
            export_file = gr.File(label="Download")

    extract_btn.click(
        on_extract,
        inputs=[video_input],
        outputs=[frame_display, click_point_state, first_frame_state,
                 inference_state_holder, frame_size_state],
    )

    frame_display.select(
        on_click,
        inputs=[first_frame_state],
        outputs=[frame_display, click_point_state],
    )

    reset_btn.click(
        on_reset,
        inputs=[first_frame_state],
        outputs=[frame_display, click_point_state],
    )

    track_btn.click(
        on_track,
        inputs=[click_point_state, inference_state_holder, frame_size_state],
        outputs=[video_segments_state, scrub_preview, scrub_slider],
    )

    scrub_slider.change(
        show_frame_preview,
        inputs=[scrub_slider, video_segments_state],
        outputs=[scrub_preview],
    )

    export_btn.click(
        export_zip,
        inputs=[video_segments_state],
        outputs=[export_file],
    )

if __name__ == "__main__":
    demo.launch()