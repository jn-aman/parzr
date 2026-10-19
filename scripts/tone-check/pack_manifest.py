#!/usr/bin/env python3
"""Writes the "tone" pack entry of engine/models.json from a converted pack folder (convert_coreml.py output).

Every file is pinned by size and SHA-256 under the release tag models-tone-<version>. Nothing is uploaded: the
owner publishes the release with `python3 scripts/model-pack.py stage --from-dir <pack> --pack tone` and
`python3 scripts/model-pack.py publish --pack tone` (see docs/releases.md, "Model packs").

    python3 -I scripts/tone-check/pack_manifest.py "$PARZR_DIST/tone-check/models/v1-minilm6/pack"
"""
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "engine/models.json"
VERSION = "2"
TAG = f"models-tone-{VERSION}"
SOURCE = "sentence-transformers/all-MiniLM-L6-v2@1110a243fdf4706b3f48f1d95db1a4f5529b4d41, fine-tuned (scripts/tone-check), Core ML 8-bit"


def main(pack_dir):
    pack_dir = pathlib.Path(pack_dir)
    files = []
    for path in sorted(p for p in pack_dir.rglob("*") if p.is_file()):
        rel = str(path.relative_to(pack_dir))
        data = path.read_bytes()
        name = {"tone/vocab.txt": "Tone check vocabulary (BERT uncased WordPiece)", "tone/tone-config.json": "Tone check settings"}.get(rel, "Tone check classifier (Core ML 8-bit)")
        files.append({"path": rel, "url": f"https://github.com/jn-aman/parzr/releases/download/{TAG}/{rel.replace('/', '.')}",
                      "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "name": name, "version": SOURCE,
                      "license": "Apache-2.0", "purpose": "Tone check: flags messages that may read as rude, passive-aggressive, curt or overly apologetic"})
    pack = {"id": "tone", "version": VERSION, "title": "Tone check",
            "purpose": "A small classifier that flags a message that may read as rude, passive-aggressive, curt or overly apologetic, before you send it. Downloaded only when Tone check is on.",
            "license": "Apache-2.0 (fine-tuned from all-MiniLM-L6-v2, Apache-2.0; training data synthetic or openly licensed, see scripts/tone-check)",
            "provides": {"tone_model": "tone"}, "files": files}
    manifest = json.loads(MANIFEST.read_text())
    manifest["packs"] = [p for p in manifest["packs"] if p["id"] != "tone"] + [pack]
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(f"tone pack: {len(files)} files, {sum(f['bytes'] for f in files) / 1e6:.1f} MB")


if __name__ == "__main__":
    main(sys.argv[1])
