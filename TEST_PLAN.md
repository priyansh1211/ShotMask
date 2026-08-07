# Test Plan

Manual test coverage for ShotMask's core pipeline: frame extraction,
subject selection, SAM 2 tracking, and RGBA export.

**Status key**: Pass &nbsp;·&nbsp; Bug found, fixed and verified &nbsp;·&nbsp;
Known limitation (by design or unresolved) &nbsp;·&nbsp; Not yet tested

---

## 1. Happy Path

| ID | Scenario | Input | Status |
|----|----------|-------|--------|
| HP-1 | Full pipeline: load → click → track → scrub → export | 1920×1080, 24fps, 318 frames | Pass |
| HP-2 | Multi-click subject selection accuracy | Any subject with multiple click points | Pass |
| HP-3 | RGBA PNG sequence export quality/speed | Any tracked clip | Pass |

**HP-1 detail** — Originally failed due to BUG-1 (below). After the fix,
retested end-to-end on a fresh 318-frame clip: extraction, tracking,
scrub preview, and full ZIP export all completed correctly, with the
reported frame count matching the actual clip exactly.

**HP-2 detail** — The UI accumulates multiple click points per subject
(e.g. forehead, chest, legs) rather than only accepting one, which
resolved earlier cases where a single click would sometimes select only
part of the subject (e.g. clothing instead of the whole body).

**HP-3 detail** — Export uses uncompressed ZIP storage (`ZIP_STORED`)
since PNG bytes are already compressed, plus a slightly lower PNG
compression level, meaningfully reducing export time on large frame
counts with negligible file size cost.

---

## 2. VFX Edge Cases

| ID | Scenario | Input | Status |
|----|----------|-------|--------|
| VFX-1 | Full-body occlusion mid-track | 1920×1080, 30fps, 541 frames — car blocks subject for ~70 frames | Pass |
| VFX-2 | Two adjacent subjects, one click set | Two people close together in frame | Pass (as one merged mask) |
| VFX-3 | Long-take propagation (600+ frames) | 600+ frame clip | Pass (slow: ~2 it/s on free-tier Colab) |
| VFX-4 | Portrait orientation | Portrait-aspect clip | Pass |
| VFX-5 | 4K resolution (3840×2160) | 3840×2160, 502 frames | Works, but risks OOM on free-tier Colab — UI warns above 1080p |
| VFX-6 | Two distant, dissimilar objects, one click set | Flowers + candle, ~2ft apart | Fixed (see below) |

**VFX-1 detail** — Mask disappeared cleanly during the occlusion (did
not stick to the occluding object) and reattached to the subject on
reappearance with no re-click needed. Untested beyond ~70 frames of
occlusion.

**VFX-2 detail** — Clicking points across two people standing close
together produces one merged mask covering both, not two independently
tracked subjects. This is expected given the current single-object
architecture (see Section 5, "Not yet supported").

**VFX-6 detail** — Initially produced ragged, fragmented mask edges on
both objects when clicked together in a single click set. Isolated by
retesting each object individually: both came out completely clean on
their own. Root cause confirmed as the combined clicking spanning two
distant, dissimilar objects — not a fine-detail segmentation limitation.
Minor residual note: a small dark-speckle artifact can appear where a
thin structure (e.g. a stem) meets a bright highlight; not severe enough
to fail a test, worth watching for in future fine-detail cases.

---

## 3. GPU / Memory

| ID | Scenario | Status |
|----|----------|--------|
| GPU-1 | `@spaces.GPU` decorator gated on `SPACE_ID` | Implemented — not yet verified on an actual HF Space |
| GPU-2 | OOM handling during tracking | Partial — clean error message on OOM, no automatic recovery (e.g. downscale + retry) |

---

## 4. UI / State Handling

| ID | Scenario | Status |
|----|----------|--------|
| UI-1 | Export delivery after a long-running job | Confirmed bug, not yet fixed |
| UI-2 | "Reset points" clears prior tracking state | Fixed (see below) |
| UI-3 | Frame count visible in the UI after extraction | Added |

**UI-1 detail** — On a long export (502-frame, 4K clip), the backend
completed the entire pipeline successfully (confirmed via console log),
but the browser lost its connection partway through and the Download
button never produced a working link. The completed file is still
retrievable directly from disk (e.g. Colab's file browser) — the
computation isn't lost, only the in-app delivery fails. Root cause:
Gradio's live connection isn't designed to stay open for multi-minute
jobs. **Fix not yet implemented** — the correct approach is to run the
export as a background task and let the UI poll for completion instead
of holding one connection open the whole time. This should be verified
specifically on HF Spaces before launch, since Spaces' networking may
behave differently than a local Colab tunnel, and Spaces users won't
have a file-browser fallback the way Colab does.

**UI-2 detail** — Clicking "Reset points" only cleared the on-screen
click markers, not SAM 2's internal tracking memory. Selecting a new
subject after a previous full track would still silently produce the
*old* subject's mask. Fixed by clearing SAM 2's internal state (not just
the UI) whenever points are reset. Verified live: reset points, click a
different subject, and the newly-selected subject tracks correctly.

**UI-3 detail** — The extracted frame count and resolution are now shown
directly under "Load frames" (e.g. "502 frames extracted · 3840×2160"),
so this information doesn't require checking the console log.

---

## 5. Known Limitations (by design, not bugs)

- **Single subject per run**: The UI supports one subject at a time.
  SAM 2 itself supports multiple independently-tracked subjects, but
  this isn't exposed in the interface yet.
- **Negative clicks**: Only positive (foreground) clicks are exposed in
  the UI; SAM 2 supports excluding regions, not yet wired up.
- **Single-frame videos**: Untested.
- **Resolution ceiling**: Clips above ~1080p risk GPU out-of-memory
  errors on free-tier Colab, since the video predictor holds every
  frame's features in memory simultaneously. The UI warns above 1080p.

---

## 6. Open Items

- [ ] Deploy to an actual HF Space and verify GPU gating + export
      delivery there — this is the only path never tested outside Colab
- [ ] Decide on a fix for UI-1 (background task + polling), or confirm
      the failure mode doesn't reproduce on Spaces before deciding it's
      necessary
- [ ] Decide what, if any, sample footage ships in `examples/`