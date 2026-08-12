"""
ShotMask — Gradio front end

Uses the pipeline in src/ (preprocess, video_predictor, alpha_exporter):
upload a shot, click a few spots on the object across frame 0, SAM 2's
memory attention tracks it across the clip, scrub to check quality, export
the RGBA PNG sequence for Nuke / After Effects.
"""

import os
import gc
import io
import shutil
import zipfile
import numpy as np
import gradio as gr
from PIL import Image

from src.preprocess import extract_frames
from src.video_predictor import SAM2VideoPredictor
from src.alpha_exporter import create_rgba_image
from download_checkpoint import ensure_checkpoint

# ZeroGPU Spaces only grant GPU access inside functions wrapped in
# @spaces.GPU — without this, SAM2's CUDA calls either fail or silently
# run on CPU (extremely slow for 500+ frame propagation). The `spaces`
# package only exists in the HF Spaces runtime, and importing it outside
# a Space (e.g. in Colab) causes issues even though HF's docs describe it
# as a safe no-op elsewhere — so gate the import itself on SPACE_ID, not
# just the decorator's behavior.
if os.environ.get("SPACE_ID"):
    import spaces
    gpu_task = spaces.GPU
else:
    def gpu_task(*args, **kwargs):
        # Support both @gpu_task and @gpu_task(duration=...) usage,
        # matching spaces.GPU's actual call signature, so the same
        # decorator syntax works identically whether or not this is
        # running on a Space.
        if len(args) == 1 and callable(args[0]) and not kwargs:
            return args[0]
        def decorator(func):
            return func
        return decorator

MODEL_CFG = "configs/sam2.1/sam2.1_hiera_t.yaml"
FRAMES_DIR = "examples/Frames"
OBJ_ID = 1

# Load the model once at startup so clicking "Track" doesn't reload it every time.
# ensure_checkpoint() downloads the .pt file on first run (checkpoints/ is gitignored).
CHECKPOINT_PATH = ensure_checkpoint()
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


@gpu_task(duration=90)
def on_extract(video_path, test_mode, progress=gr.Progress()):
    if video_path is None:
        raise gr.Error("Upload a video first.")

    progress(0, desc="Extracting frames...")
    # Wipe any frames left behind by a prior video/session before writing
    # this one. Without this, extract_frames() only overwrites filenames
    # up to its own frame count — leftover frames from a longer or
    # differently-sized previous clip stay in the folder and get pulled
    # into init_video()'s frame listing, silently corrupting this run
    # (mismatched resolutions across "one video's" frames).
    
    if os.path.exists(FRAMES_DIR):
        shutil.rmtree(FRAMES_DIR)
    numeric_dir = FRAMES_DIR.rstrip("/\\") + "_numeric"
    if os.path.exists(numeric_dir):
        shutil.rmtree(numeric_dir)

    # test_mode downsamples to 5fps for fast dev iteration only — leave
    # unchecked for anything you intend to actually export, since
    # rotoscoping needs a mask per original frame to line up in Nuke/AE.

    extract_frames(video_path, FRAMES_DIR, target_fps=5 if test_mode else None)
    frames = list_frames()
    if not frames:
        raise gr.Error("No frames were extracted from that video.")

    first_frame_img = Image.open(os.path.join(FRAMES_DIR, frames[0]))
    frame_w, frame_h = first_frame_img.size
    first_frame = np.array(first_frame_img)

    # SAM2's video predictor holds encoded features for every frame at once —
    # at 4K that's ~4x the memory of 1080p, and free-tier Colab (T4 + limited
    # system RAM) genuinely can't hold that for a 500+ frame clip. This isn't
    # fixable in code; it's a hardware ceiling. Warn now, not 3 minutes into
    # a track() call.
    if max(frame_w, frame_h) > 1920:
        gr.Warning(
            f"This clip is {frame_w}x{frame_h} — above 1080p. On free-tier "
            "Colab (T4), tracking a clip this large is likely to exhaust "
            "RAM partway through. Consider testing with a 1080p-or-smaller "
            "clip, or downscale this one before uploading."
        )

    # Show the frame immediately — don't make the artist stare at a blank box
    # while SAM2 encodes every frame in the background.
    frame_count_text = f"**{len(frames)} frames** extracted · {frame_w}×{frame_h}"
    yield first_frame, [], first_frame, None, (frame_w, frame_h), gr.Markdown(frame_count_text, visible=True)

    progress(0.4, desc="Encoding frames for tracking (this is the slow part)...")
    inference_state = predictor.init_video(FRAMES_DIR)
    yield first_frame, [], first_frame, inference_state, (frame_w, frame_h), gr.Markdown(frame_count_text, visible=True)


def on_click(first_frame, points, evt: gr.SelectData):
    """Accumulate clicks instead of overwriting — click a few spots to cover the whole subject."""
    x, y = evt.index
    points = points + [(x, y)]
    vis = first_frame.copy()
    for px, py in points:
        y0, y1 = max(0, py - 4), min(vis.shape[0], py + 4)
        x0, x1 = max(0, px - 4), min(vis.shape[1], px + 4)
        vis[y0:y1, x0:x1] = [255, 0, 0]
    return vis, points


def on_reset(first_frame, inference_state):
    if inference_state is not None:
        predictor.reset(inference_state)
    return first_frame, []


@gpu_task(duration=300)
def on_track(points, inference_state, frame_size, progress=gr.Progress()):
    if not points:
        raise gr.Error("Click a few spots on the object in frame 0 first (e.g. face, chest, legs).")
    if inference_state is None:
        raise gr.Error("Load frames first.")

    frame_w, frame_h = frame_size
    progress(0, desc=f"Registering {len(points)} click(s)...")
    # clear_old_points=True on the first click only — SAM2 wipes all prior
    # points for this object every call unless told not to, so calling this
    # with the default for every point would silently discard everything
    # except whichever click happens to run last.
    for i, (x, y) in enumerate(points):
        predictor.add_click(inference_state, obj_id=OBJ_ID, x=x, y=y,
                             frame_width=frame_w, frame_height=frame_h,
                             clear_old_points=(i == 0))

    progress(0.3, desc="Tracking object across the clip (SAM2 memory attention)...")
    video_segments = predictor.track(inference_state)
    if not video_segments:
        raise gr.Error("Tracking produced no masks — check the console log.")

    frames = list_frames()
    first_frame = np.array(Image.open(os.path.join(FRAMES_DIR, frames[0])))
    first_mask = video_segments[0][OBJ_ID].squeeze()
    first_preview = composite_on_checker(first_frame, first_mask)

    slider_update = gr.Slider(minimum=0, maximum=max(len(frames) - 1, 1), value=0, step=1,
                               visible=True, label=f"Scrub tracked mask (0–{len(frames) - 1})")
    return video_segments, first_preview, slider_update


def show_frame_preview(frame_idx, video_segments):
    if not video_segments:
        raise gr.Error("Track the object first.")
    frames = list_frames()
    frame_idx = int(frame_idx)
    frame = np.array(Image.open(os.path.join(FRAMES_DIR, frames[frame_idx])))
    obj_masks = video_segments.get(frame_idx)
    if not obj_masks:
        return frame
    mask = obj_masks[OBJ_ID].squeeze()
    return composite_on_checker(frame, mask)


def export_zip(video_segments, progress=gr.Progress()):
    if not video_segments:
        raise gr.Error("Track the object first — nothing to export yet.")

    frames = list_frames()
    zip_path = "shotmask_export.zip"
    frame_indices = sorted(video_segments.keys())
    total = len(frame_indices)

    # ZIP_STORED (no compression), not ZIP_DEFLATED — PNG bytes are already
    # compressed, so DEFLATE was burning CPU trying to shrink data that
    # barely shrinks further. At 4K x 500 frames this was a meaningful
    # chunk of the export time for near-zero size benefit.
    #
    # compress_level=3 on the PNG itself (Pillow default is 6) trades a
    # little file size for meaningfully faster encoding — worth it for an
    # intermediate export artifact, not a final deliverable.
    #
    # print() every frame, not just every 50 via gr.Progress — if the
    # installed Gradio version doesn't match what progress() expects, the
    # UI bar can silently stop rendering while work continues in the
    # background. The console log should never go quiet during a long export.
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as zf:
        for i, frame_idx in enumerate(frame_indices):
            obj_masks = video_segments[frame_idx]
            mask = obj_masks[OBJ_ID].squeeze()
            frame_path = os.path.join(FRAMES_DIR, frames[frame_idx])
            frame_array = np.array(Image.open(frame_path).convert("RGB"))
            rgba_image = create_rgba_image(frame_array, mask)

            buf = io.BytesIO()
            Image.fromarray(rgba_image.astype("uint8")).save(
                buf, format="PNG", compress_level=3
            )
            zf.writestr(f"mask_{frame_idx:04d}.png", buf.getvalue())

            del frame_array, rgba_image, buf
            print(f"Exported frame {i + 1}/{total}")
            if i % 50 == 0:
                gc.collect()
                progress((i + 1) / total, desc=f"Exporting frame {i + 1}/{total}")

    print(f"Export complete: {total} frames written to {zip_path}")
    return zip_path


CUSTOM_CSS = """
.section-card { border: 1px solid var(--border-color-primary); border-radius: 14px; padding: 16px; }
.section-title { margin-bottom: 4px !important; }
.section-subtitle { color: var(--body-text-color-subdued); margin-bottom: 14px !important; font-size: 0.9em; }
"""

with gr.Blocks(
    title="ShotMask — AI Rotoscoping",
    theme=gr.themes.Soft(primary_hue="indigo", secondary_hue="purple"),
    css=CUSTOM_CSS,
) as demo:
    click_points_state = gr.State([])
    first_frame_state = gr.State(None)
    inference_state_holder = gr.State(None)
    frame_size_state = gr.State((0, 0))
    video_segments_state = gr.State({})

    with gr.Row():
        with gr.Column(elem_classes="section-card"):
            gr.Markdown("### Step 1 · Select your subject", elem_classes="section-title")
            gr.Markdown(
                "Upload your shot, then click a few spots on the subject "
                "(e.g. forehead, chest, legs) so the AI knows what to cut out.",
                elem_classes="section-subtitle",
            )
            video_input = gr.Video(label="Upload shot")
            test_mode_toggle = gr.Checkbox(
                label="Dev/test mode (downsample to 5fps for faster iteration — don't use this for a real export)",
                value=False,
            )
            extract_btn = gr.Button("Load frames", variant="primary", interactive=False)
            frame_count_display = gr.Markdown(visible=False)
            frame_display = gr.Image(label="Click the subject on frame 0")
            reset_btn = gr.Button("Reset points")

        with gr.Column(elem_classes="section-card"):
            gr.Markdown("### Step 2 · Track & export", elem_classes="section-title")
            gr.Markdown(
                "The AI follows your subject across every frame. Scrub through "
                "to check the result, then export a PNG sequence with alpha "
                "channel — ready to drop into Nuke or After Effects.",
                elem_classes="section-subtitle",
            )
            track_btn = gr.Button("Track across clip", variant="primary")
            scrub_slider = gr.Slider(minimum=0, maximum=1, value=0, step=1,
                                      label="Scrub tracked mask", visible=False)
            scrub_preview = gr.Image(label="Tracked mask preview (checkerboard = transparent)")
            export_btn = gr.Button("Export PNG sequence (.zip)", variant="primary")
            export_file = gr.File(label="Download")

    # extract_btn starts disabled (see the gr.Button definition above) so a
    # click can't fire before the video is actually on the server. Without
    # this, clicking "Load frames" while the file is still mid-upload
    # queues a call to on_extract() against an incomplete/empty video
    # value — the UI shows a pending "processing" state indefinitely
    # (indistinguishable from a hang) since there's nothing for the
    # backend to act on until the *next* click after the upload finishes.
    video_input.upload(
        lambda: gr.Button(interactive=True), outputs=extract_btn,
    )
    video_input.clear(
        lambda: gr.Button(interactive=False), outputs=extract_btn,
    )

    extract_btn.click(
        on_extract, inputs=[video_input, test_mode_toggle],
        outputs=[frame_display, click_points_state, first_frame_state,
                 inference_state_holder, frame_size_state, frame_count_display],
    )
    frame_display.select(
        on_click, inputs=[first_frame_state, click_points_state],
        outputs=[frame_display, click_points_state],
    )
    reset_btn.click(
        on_reset, inputs=[first_frame_state, inference_state_holder],
        outputs=[frame_display, click_points_state],
    )
    track_btn.click(
        on_track, inputs=[click_points_state, inference_state_holder, frame_size_state],
        outputs=[video_segments_state, scrub_preview, scrub_slider],
    )
    scrub_slider.change(
        show_frame_preview, inputs=[scrub_slider, video_segments_state],
        outputs=[scrub_preview],
    )
    export_btn.click(
        export_zip, inputs=[video_segments_state],
        outputs=[export_file],
    )

if __name__ == "__main__":
    demo.launch()