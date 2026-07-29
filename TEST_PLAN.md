# Test Plan

Reconstructed from the project's testing history. The original
`TEST_PLAN.md` was lost (never committed to GitHub), so entries from
before this conversation are reconstructed from what's documented in
`KNOWN_LIMITATIONS.md`, commit history, and prior session notes — exact
original wording/numbering for those isn't recoverable, but the
functional outcomes are accurate. Entries from this conversation are
logged in full detail, including raw error output where relevant.

Categories: **Happy path**, **GPU/memory limits**, **VFX edge cases**,
**UI state transitions**, **Repo/deployment hygiene**.

---

## Happy path

### HP-1 — Single subject, clean 1080p clip, full pipeline
**Input**: `7187078-hd_1920_1080_24fps.mp4` — athlete running, 1920×1080,
24fps, 172 frames.
**Steps**: Load frames → click subject (5 points) → track across clip →
scrub → export ZIP.
**Result**: FAILED on first run — see BUG-1 below. Root cause was frame
contamination, not the core pipeline; tracking itself succeeded
(`Tracking completed. Generated masks for 533 frames.`) before the crash
in compositing.
**Status**: Retest blocked on BUG-1 fix being applied to the live
`app.py` (still not applied as of this writing — see Open Items).

### HP-2 — Multi-click accuracy on ambiguous subject
**Result**: RESOLVED (pre-dates this conversation). Early version only
supported a single positive click per object, which sometimes selected a
sub-part of the subject (e.g. clothing) instead of the whole body.
Fixed by accumulating multiple clicks per object with
`clear_old_points=True` on the first click only, `False` after — see
`on_track()` in `app.py`. Documented in `KNOWN_LIMITATIONS.md` under
"Ambiguous clicks — resolved."

### HP-3 — Export produces a usable RGBA PNG sequence
**Result**: PASSED (pre-dates this conversation). Original implementation
double-compressed (PNG compression + ZIP DEFLATE on already-compressed
bytes). Replaced with streaming `ZIP_STORED` + `compress_level=3` PNG
encoding + per-frame `gc.collect()` every 50 frames — see `export_zip()`
in `app.py`. This is reflected in the current live code.

---

## VFX edge cases

### VFX-1 — Full-body occlusion mid-track
**Input**: `8402088-hd_1920_1080_30fps.mp4` — person jumping, 1920×1080,
30fps, 541 frames. A car passes in front of the subject, fully occluding
them for ~70 frames (~frames 430–500, ~2.3s at 30fps).
**Expected**: Mask should not "stick" to the occluding object, and should
reattach to the subject on reappearance, ideally without a re-click.
**Result**: PASSED. Mask disappeared cleanly during the occlusion and
reattached correctly with no re-click needed.
**Status**: Confirmed passing, logged in `KNOWN_LIMITATIONS.md`.
Untested beyond ~70 frames of occlusion, and the case of the subject
fully exiting frame bounds (vs. being blocked by an object).

### VFX-2 — Two subjects, single click set
**Input**: Two people talking close together in frame (test clip via
image upload, not saved to repo).
**Steps**: Clicked points scattered across both people's heads/torsos as
one set of clicks (single `obj_id`).
**Result**: Both people appeared cut out in the tracked mask preview.
**Caveat — not yet fully verified**: this is very likely **one merged
mask** treating both people as a single blob (since they're close/
overlapping in frame), not true independent multi-subject tracking.
`KNOWN_LIMITATIONS.md` still correctly states multi-subject tracking
(separate `obj_id`s) isn't exposed in the UI. Don't upgrade this to a
"multi-subject" claim in the README without a dedicated test — e.g. two
subjects who cross paths or separate, checked frame-by-frame to confirm
whether the mask ever splits into two disconnected regions vs. staying
one blob.
**Status**: Logged as a passing "adjacent subjects, single blob" result;
not a substitute for a real multi-subject test.

### VFX-6 — Two distant, dissimilar objects, single click set ("candlelit dinner")
**Input**: `10811234-hd_1080_1918_30fps.mp4` — candlelit dinner table,
1080×1918 (portrait), 30fps. Flowers in a vase and a lit candle, roughly
2ft apart in frame, both static.
**Steps**: Clicked points on both the flowers and the candle as one set
(single `obj_id`), then ran a full "Track across clip" (not just a
frame-0 preview).
**Expected**: Either a clean merged mask (as in VFX-2) or a clear,
obvious failure to select one/both objects.
**Actual**: FAILED — neither object got a clean mask. Flower petals came
out with ragged, fragmented edges (disconnected orange fragments outside
the main petal boundary). The candle showed a black drippy/streaky
artifact running down its lower half, as if the alpha boundary was
bleeding or breaking down partway along the object.
**Analysis**: This is a different, and arguably more concerning, failure
mode than VFX-2. VFX-2's two-adjacent-subjects case produced one clean
(if merged) result. This case produced **poor quality on both regions
independently** — not a clean merge, not a clean failure, but degraded
boundaries throughout. Two confounded variables here that need
untangling: (1) the objects are far apart and dissimilar (unlike VFX-2's
adjacent, similar-context subjects), and (2) both objects individually
have fine/organic/reflective detail (curled petals, specular candle wax)
that may be a segmentation weak point on its own, independent of the
multi-object clicking.
**Status**: Logged as a real quality bug, not yet root-caused. Documented
in `KNOWN_LIMITATIONS.md`. Needs a targeted follow-up test with each
object tracked *individually* (its own single-object run) to isolate
whether this is a multi-object-clicking problem, a fine-detail
segmentation limitation, or both.

**Follow-up — candle isolated, retested alone**: Same clip
(`10811234-hd_1080_1918_30fps.mp4`, 221 frames), candle only, single
`obj_id`, full track across clip. Result: PASSED — clean boundary
throughout the scrub range (0–221), no drippy/streaky artifact. This
strongly points the root cause of VFX-6 toward the **multi-object
clicking itself** (points spanning two dissimilar, disconnected regions
confusing the single mask) rather than a fine-detail segmentation limit
on the candle's specular wax highlights. Still open: retest the flowers
alone to confirm they're similarly clean in isolation — if so, VFX-6
is fully explained by the multi-object confound, not a segmentation
quality limit on either object individually.

**Follow-up — vase + flowers isolated, retested alone**: Same clip,
clicks on the vase body/stem (not the petals directly), single `obj_id`,
full track across clip. Result: PASSED — both flower heads (SAM 2 pulled
in the second head automatically via stem proximity, same grouping
behavior as VFX-2) and the vase came out with clean, well-defined
boundaries — no ragged/fragmented petal edges like the original VFX-6
failure. **Minor new observation**: a small cluster of dark speckle
artifacts appears right where the stems enter the vase neck — same
character (though far smaller in extent) as the candle's original
drippy artifact. Both occur at a thin dark structure near a bright
highlight/background area, which may be a recurring weak point worth
watching for in future tests, though not severe enough here to fail the
test.

**Conclusion**: VFX-6 is now fully explained. Both objects are clean
when tracked individually; the original ragged/drippy failure only
appeared when clicks spanned both dissimilar, disconnected objects under
one `obj_id`. This is a genuine multi-object-clicking limitation, not a
fine-detail segmentation weakness. Correctly scoped as "don't combine
distant, dissimilar objects in one click set" rather than "SAM 2 can't
handle organic/reflective detail" — the latter would have been a much
bigger concern for VFX use cases and isn't supported by this data.

### VFX-3 — Long-take propagation (600+ frames)
**Result**: PASSED, with a performance caveat (pre-dates this
conversation). Runs correctly but slow — ~2+ it/s, ~5+ minutes total on
free-tier Colab T4. Documented in `KNOWN_LIMITATIONS.md` as a soft
performance limit, not a correctness bug.

### VFX-4 — Portrait orientation
**Result**: PASSED (pre-dates this conversation, referred to as "Test
#14" in earlier notes). No further detail recoverable on exact input
used — worth re-running and logging properly if this needs to be citable.

### VFX-5 — 4K resolution (3840×2160)
**Result**: Not a pass/fail test — identified as a hardware ceiling, not
a bug. SAM 2's video predictor holds encoded features for every frame
simultaneously; at 4K this risks OOM on free-tier Colab's T4. Resolution
warning added in `on_extract()` for anything above 1920px on the long
edge. Documented in `KNOWN_LIMITATIONS.md`.
**Side effect discovered this conversation**: leftover frames from a 4K
test session are the likely origin of BUG-1 below (see root cause).

---

## GPU / memory limits

### GPU-1 — ZeroGPU decorator gating
**Result**: RESOLVED (pre-dates this conversation). `@spaces.GPU` is
gated on the `SPACE_ID` env var so it doesn't silently hang when run
locally in Colab (where `SPACE_ID` isn't set). **Still not verified in
an actual deployed HF Space** — this is the one path that's only ever
been reasoned about, never run for real. See Open Items.

### GPU-2 — OOM during tracking
**Result**: Partially handled (pre-dates this conversation). `track()`
has an explicit `OutOfMemoryError` catch, but automatic recovery (e.g.
downscaling and retrying) is not implemented. Documented as a known
limitation, not a bug.

---

## UI state transitions

### UI-1 — Session/connection drop after successful export
**Result**: BUG FOUND (pre-dates this conversation, referred to as "Test
#21" in earlier notes). After a successful backend export, the Gradio UI
reset to blank with no download link following a Colab session
reconnect — Gradio's file output references are session-bound and don't
survive a runtime reconnect. Recovery path at the time: Colab's Files
pane sidebar. A patch for session-independent export links was drafted
but **never confirmed applied** — status unknown, should be re-verified
before relying on this being fixed.

---

## Bugs found this conversation

### BUG-1 — Stale frame contamination across sessions
**Symptom**:
```
Total frames: 172
Extracted 172 frames to examples/Frames
...
Video initialized successfully with 533 frames.
...
IndexError: boolean index did not match indexed array along axis 0;
size of axis is 1080 but size of corresponding boolean axis is 2160
```
**Root cause**: `FRAMES_DIR` (`examples/Frames`) is a fixed path, never
cleared between runs. `extract_frames()` only overwrites filenames up to
its own frame count, so leftover frames from a prior, larger session
(almost certainly the earlier 4K OOM test — 2160 is exactly the height
of a 3840×2160 clip) remained on disk. `init_video()` in
`src/video_predictor.py` lists every JPG present rather than just the
current run's, so SAM 2 initialized on a mixed-resolution frame set.
**Fix**: Clear `FRAMES_DIR` (and the derived `_numeric` folder) at the
start of every `on_extract()` call, before writing new frames.
**Status**: Fix written and verified working in a sandbox clone.
**NOT YET applied to the actual GitHub `app.py`** — confirmed still
missing as of the latest pasted version of the file. This is the
top-priority open item.
**Broader implication**: `FRAMES_DIR` being a fixed, non-session-scoped
path is also a multi-user risk on a real HF Spaces deployment — two
concurrent users would contaminate each other's frames. Worth a
dedicated multi-user isolation test once the app is actually deployed.

### BUG-2 — Leaked GitHub PAT in commit history
Not a code bug, but a real finding from this project: `PAT.txt`
containing a live-looking GitHub Personal Access Token was committed
2026-05-22 and deleted (but not purged from history) 2026-05-29,
remaining publicly exposed in git history for ~2 months.
**Resolution**: Token revoked on GitHub. History rewritten with
`git filter-repo` to remove `PAT.txt`, `examples/Frames/`, and
`examples/sample.mp4` from all commits. Verified via: empty
`git log --all -- PAT.txt`, GitHub code search for "PAT" returning zero
results, and fresh-clone size dropping from 150MB+ to 1.39MB. Force-pushed
to `main`.
**Status**: Resolved and verified.

---

## Open items (blocking a "ready for public/HF launch" status)

- [ ] **Apply BUG-1 fix to the live `app.py` on GitHub** — currently
      only exists in a sandbox clone, not committed or pushed
- [ ] Retest HP-1 (athlete clip) after the fix lands, confirm frame count
      matches extraction count exactly
- [ ] Run a dedicated stale-frame **regression** test: load Video A, then
      Video B (different frame count/resolution) in the same session
      without restarting, confirm B's frame count is never contaminated
      by A
- [ ] Re-verify UI-1's session-independent export link patch was ever
      actually applied — status unknown
- [ ] Deploy to a real HF Space and verify GPU-1 (`@spaces.GPU` +
      `SPACE_ID` gating) works outside of Colab — never tested live
- [ ] Run a real multi-subject test (VFX-2) — two people who separate or
      cross paths, checked frame-by-frame for whether the mask splits
- [x] Isolate the VFX-6 boundary-quality bug — RESOLVED: both objects
      confirmed clean when tracked individually; root cause was the
      multi-object clicking, not a fine-detail segmentation limit
- [ ] Fresh-clone + fresh `pip install` in a clean environment (no cached
      Colab packages) to confirm no hidden dependencies
- [ ] Decide what test footage, if any, ships in `examples/` going
      forward, given the stock-footage redistribution concern that came
      up during the git history cleanup