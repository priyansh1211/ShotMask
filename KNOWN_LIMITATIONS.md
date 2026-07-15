# Known Limitations

ShotMask handles the core rotoscoping pipeline end-to-end. The following
edge cases are identified but not yet handled, in rough priority order.

## Tracking Robustness
- **Subject occlusion/exit**: If the tracked subject leaves the frame
  entirely or is fully occluded for multiple frames, SAM 2's behavior on
  re-entry has not been tested. May require re-clicking to re-establish
  tracking.
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
