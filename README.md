---
title: ShotMask
emoji: 🎬
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: 5.9.1
app_file: app.py
pinned: false
license: apache-2.0
---

# ShotMask

AI-powered rotoscoping tool that automates VFX masking workflows using
Meta's SAM 2.1. Click a few points on a subject in frame 0, and SAM 2's
memory-attention tracks it across the whole clip — export a PNG sequence
with alpha channel ready to drop into Nuke or After Effects.

## Status
Working end-to-end pipeline — June 2026

- [x] Frame extraction pipeline (OpenCV)
- [x] SAM 2.1 video tracking via memory attention (`propagate_in_video`)
- [x] Multi-click subject selection (not just single-point)
- [x] Gradio UI — upload, click, track, scrub, export
- [x] Alpha channel PNG sequence export (zip)
- [ ] Hugging Face Spaces deployment (ZeroGPU)
- [ ] Multi-subject tracking (multiple `obj_id`s in one pass)

## What It Does
Upload a shot → click a few points on the subject (forehead, chest, legs) →
SAM 2.1 tracks it across every frame using memory attention → scrub through
to check quality → export as a PNG sequence with alpha channel.

## Tech Stack
- **SAM 2.1** (Meta) — promptable video object segmentation
- **PyTorch** — model inference on GPU
- **OpenCV** — video → frame extraction
- **Pillow** — RGBA PNG export
- **Gradio** — UI

## Project Structure
```
ShotMask/
├── src/
│   ├── preprocess.py        # Video → frames extraction
│   ├── video_predictor.py   # SAM2VideoPredictor wrapper (init/click/track)
│   ├── alpha_exporter.py    # Mask → PNG with alpha
│   └── sam2_predictor.py    # Single-image SAM 2 wrapper (used internally)
├── app.py                   # Gradio UI
├── download_checkpoint.py   # Fetches the SAM 2.1 tiny checkpoint on first run
├── notebooks/
│   └── 01_sam2_test.ipynb   # Development notebook
└── examples/                # Test footage and results
```

## Running Locally
```bash
pip install -r requirements.txt
python download_checkpoint.py   # first run only — fetches the checkpoint
python app.py
```

## Known Limitations
See [KNOWN_LIMITATIONS.md](./KNOWN_LIMITATIONS.md).

## License
Apache 2.0 (matches the SAM 2 license). See [LICENSE](./LICENSE).
