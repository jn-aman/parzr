#!/usr/bin/env python3
"""Writes Hugging Face's token ids for every DEV and DEV2 text (plus some awkward strings) so the Swift tokenizer
test can compare: PARZR_TONE_PARITY=<out> PARZR_TONE_DIR=<pack>/tone swift test --filter ToneCheckTests

    venv/bin/python -I scripts/tone-check/token_parity.py <run dir> <out.jsonl>
"""
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
EXTRA = ["Caf\u00e9 na\u00efve r\u00e9sum\u00e9", "I'm  done!!! :)", "\u201cQuoted\u201d \u2014 dash\u2026 ellipsis", "\u65e5\u672c\u8a9e text",
         "emoji \U0001F44D\U0001F3FD ok", "e-mail @sam #ops $5.00", "ALL CAPS SHOUTING", "tab\tand\nnewline", "x" * 120,
         "url https://example.com/a?b=c", "\u00dcn\u00efc\u00f6d\u00e9 \u00dftra\u00dfe", "a\u200bzero width"]


def main(run, out):
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(run)
    texts = EXTRA[:]
    for name in ("dev", "dev2"):
        texts += [json.loads(l)["text"] for l in open(REPO / f"benchmarks/tone-check/{name}.jsonl", encoding="utf-8")]
    with open(out, "w", encoding="utf-8") as f:
        for t in texts:
            ids = tok(t, padding="max_length", truncation=True, max_length=64)["input_ids"]
            f.write(json.dumps({"text": t, "ids": ids}, ensure_ascii=False) + "\n")
    print(len(texts), "texts")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
