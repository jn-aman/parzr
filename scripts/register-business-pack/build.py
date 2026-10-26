#!/usr/bin/env python3
"""Writes engine/rules/packs/register-business.json and docs/rule-packs/register-business.md.
usage: python3 scripts/register-business-pack/build.py"""
import json, pathlib, sys
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parent.parent
import core, fam_wordy, fam_verbs, fam_email, fam_signoff, coverage
def build():
    for m in (fam_wordy, fam_verbs, fam_email, fam_signoff):
        m.build()
    rules = core.RULES
    ids = [r["id"] for r in rules]
    assert len(ids) == len(set(ids)), "duplicate ids"
    out = [{k: v for k, v in r.items() if not k.startswith("_")} for r in rules]
    (ROOT / "engine/rules/packs/register-business.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (ROOT / "docs/rule-packs/register-business.md").write_text(coverage.render(rules), encoding="utf-8")
    print(f"{len(out)} rules")
if __name__ == "__main__":
    build()
