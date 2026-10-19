"""Where the tone-check scripts read inputs and write outputs: PARZR_DIST (default: the repository's dist/,
which git ignores). A worktree points it at the main checkout's dist/."""
import os
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]
DIST = pathlib.Path(os.environ.get("PARZR_DIST") or REPO / "dist")
TONE = DIST / "tone-check"
BAKEOFF = DIST / "model-bakeoff2"
BATCHES = DIST / "batches"
