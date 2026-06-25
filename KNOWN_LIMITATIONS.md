# Known Limitations

ShotMask is a working prototype focused on the core rotoscoping 
pipeline. The following edge cases are identified but not yet 
handled, in order of priority for future work:

## Tracking Robustness
- **Subject occlusion/exit**: If the tracked subject leaves the 
  frame entirely or is fully occluded for multiple frames, SAM 2's 
  behavior on re-entry has not been tested. May require re-clicking 
  to re-establish tracking.
- **Multiple subjects**: Currently supports tracking one subject 
  (obj_id) per run. Multi-subject tracking would require calling 
  `add_click` with multiple obj_ids before `track()`.

## Input Constraints
- **Single-frame videos**: Behavior with a 1-frame "video" is untested.
- **Resolution**: Frames above ~1080p risk GPU out-of-memory errors 
  on free-tier Colab (T4, 15GB VRAM) during `track()`, since the 
  video predictor holds all frames in memory simultaneously (unlike 
  the image predictor, which processes one frame at a time).
- **Frame rate / video length**: No hard limit enforced beyond a 
  soft warning above 500 frames; very long videos will be slow on 
  free-tier GPUs.

## Click Quality
- **Ambiguous clicks**: A single click can occasionally select a 
  sub-part of the subject (e.g. clothing) rather than the whole 
  object, due to inherent click ambiguity in SAM 2. The current 
  implementation supports only a single positive click per object; 
  refining with additional clicks (positive/negative) is supported 
  by SAM 2's API but not yet exposed in `add_click`.

## Error Handling
- **GPU OOM during tracking**: Partially handled — see `track()` 
  for the explicit `OutOfMemoryError` catch, but recovery (e.g. 
  automatic downscaling) is not implemented.