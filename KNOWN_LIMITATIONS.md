# Known Limitations

ShotMask handles the core rotoscoping pipeline end-to-end. The following
edge cases are identified but not yet handled, in rough priority order.

## Tracking Robustness
- **Subject occlusion/exit — tested, passes**: A full-body occlusion
  (car passing in front of the subject) lasting ~70 frames (frames
  ~430–500 of 541, 30fps, ~2.3s) was tested on real footage. Mask
  disappeared cleanly during the occlusion (did not stick to the
  occluding object) and reattached to the subject on reappearance with
  no re-click needed. Untested beyond this: occlusions longer than ~70
  frames, and the subject fully exiting frame bounds (rather than being
  blocked by an object) before returning.
- **Multiple subjects**: Currently supports tracking one subject (`obj_id`)
  per run. Multi-subject tracking would require calling `add_click` with
  multiple `obj_id`s before `track()` — the underlying SAM 2 API supports
  this, it's just not exposed in the UI yet.

## Input Constraints
- **Single-frame videos**: Behavior with a 1-frame "video" is untested.
- **Resolution**: Frames above ~1080p risk GPU out-of-memory errors on
  free-tier Colab (T4, 15GB VRAM) during `track()`, since the video
  predictor holds all frames in memory simultaneously (unlike the image
  predictor, which processes one frame at a time).
- **Frame rate / video length**: No hard limit enforced beyond a soft
  warning above 500 frames; very long videos will be slow on free-tier
  GPUs.

## Click Quality
- **Ambiguous clicks — resolved**: Earlier versions only supported a single
  positive click per object, which could occasionally select a sub-part of
  the subject (e.g. clothing) rather than the whole object. The UI now
  accumulates multiple clicks per object (forehead, chest, legs, etc.),
  which resolves most of this ambiguity in practice.
- **Negative clicks**: Only positive (foreground) clicks are exposed in the
  UI. SAM 2's API supports negative clicks to exclude regions; not yet
  wired up.

## Error Handling
- **GPU OOM during tracking**: Partially handled — see `track()` for the
  explicit `OutOfMemoryError` catch, but recovery (e.g. automatic
  downscaling) is not implemented.