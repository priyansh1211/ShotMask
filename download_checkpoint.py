"""
Downloads the SAM 2.1 (Hiera-Tiny) checkpoint on first run.

checkpoints/ is gitignored on purpose (large binary), so a fresh clone —
or a fresh HF Space build — has nothing to load until this runs once.

Usage:
    python download_checkpoint.py          # run manually
    from download_checkpoint import ensure_checkpoint  # or import from app.py
"""

import os
from huggingface_hub import hf_hub_download

CHECKPOINT_DIR = "checkpoints"
CHECKPOINT_FILENAME = "sam2.1_hiera_tiny.pt"
CHECKPOINT_PATH = os.path.join(CHECKPOINT_DIR, CHECKPOINT_FILENAME)

# NOTE: verify this repo_id/filename against the current listing at
# https://huggingface.co/facebook — Meta occasionally reorganizes SAM 2.1
# checkpoint repos. If this 404s, search "sam2.1 hiera tiny" on HF and
# swap in the exact repo_id/filename shown on that model card.
HF_REPO_ID = "facebook/sam2.1-hiera-tiny"


def ensure_checkpoint() -> str:
    """Download the checkpoint if it isn't already on disk. Returns the local path."""
    if os.path.exists(CHECKPOINT_PATH):
        return CHECKPOINT_PATH

    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    print(f"Checkpoint not found locally — downloading {CHECKPOINT_FILENAME} from {HF_REPO_ID}...")
    hf_hub_download(
        repo_id=HF_REPO_ID,
        filename=CHECKPOINT_FILENAME,
        local_dir=CHECKPOINT_DIR,
    )
    print(f"Checkpoint saved to {CHECKPOINT_PATH}")
    return CHECKPOINT_PATH


if __name__ == "__main__":
    ensure_checkpoint()
