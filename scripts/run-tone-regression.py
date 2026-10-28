#!/usr/bin/env python3
"""Tone regression set: score every item in every tone mode against its expectation and the universal invariants.

benchmarks/tone/regression.jsonl holds sentences written for this set, each with a per-mode expectation:

    {"id", "kind", "text", "casual", "modes": {"professional": SPEC, "friendly": SPEC, "concise": SPEC, "direct": SPEC}}
    SPEC = {"expect": "rewrite" | "keep" | "any", "keep_words": [...], "forbid": [...regex...]}

  rewrite  the output differs from the input and the response carries no `tone.withheld` warning (clear cases only:
           chat-speak into Professional, a rude message into Friendly, a wordy message into Concise or Direct)
  keep     the output equals the input, trailing whitespace ignored (text already in that tone)
  any      only the invariants are scored
  keep_words  every entry must appear in the output (case-insensitive, whole word; "a|b" accepts either)
  forbid   no regex may match the output

Invariants scored for every item in every mode, without being listed in a SPEC:
  error                 the response carries an `error`
  numbers, times, dates, urls, emails, handles
                        everything of that kind in the input appears in the output (times are compared as h:mm am/pm,
                        and a number written out up to 100, "3" as "three", "1st" as "first", is kept)
  question_word_dropped / question_word_added
                        every question word (who, whose, what, which, where, when, why, how) in an input question
                        appears in the output, and a question word in an output question is a word of the input
  question_mark         an input that ends in "?" still does (Direct may turn a request into an instruction)
  negation_flipped      negation (not, n't, never, no, cannot, unable ...) is present in both the input and the output or in neither
  name_dropped          capitalized names that are not at the start of a sentence stay
  concise_longer        Concise output has no more words than the input and at most 3 more characters
  stray_punctuation     no ",." ";," ".." or " ," that the input did not have
  emoji_added           no emoji is added (except one final emoji in Friendly for a chat message: the engine's design)
  chat_speak            Professional output has no u, ur, thx, lol, pls, plz, gonna, wanna, gotta, ya, omg, idk, tmrw, brb, haha, cuz
A `tone.withheld` warning (the meaning guard refused a rewrite) passes keep and any, and fails rewrite.
Spec failures are named rewrite_unchanged, rewrite_withheld, keep_changed, keep_words and forbid.

usage: run-tone-regression.py [--engine PATH] [--set FILE[,FILE]] [--output DIR] [--modes a,b] [--limit N] [--every N]
                              [--answers RESULTS.jsonl] [--min-pass-rate MODE=RATE ...] [--baseline tone-regression]

Each item is sent as the app sends a tone request (`deep`, `gec`, and `casual` from the item) to one long-lived engine,
after a warm-up. Writes results.jsonl, summary.json and summary.md to --output (default dist/qa/tone-regression). The
run exits 1 when a mode is below its --min-pass-rate, or, with --baseline, when a mode's pass rate is more than 0.5
points below benchmarks/baselines.json suites.tone-regression, or latency or peak memory exceed 1.5x the same
machine's performance baseline (scripts/quality_gates.py). --every N scores every Nth item only (CI scores a sample, as a
request takes several seconds on a runner; a sample has its own baseline). --answers re-scores the answers of an earlier
results.jsonl without running the engine, for checking a changed expectation.

    export PARZR_MODEL_RUNTIME=... PARZR_MODELS_DIR=...
    cargo build --release --manifest-path engine/Cargo.toml --bin parzr-engine
    python3 scripts/run-tone-regression.py --engine engine/target/release/parzr-engine
"""
import argparse
import collections
import json
import pathlib
import re
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import quality_gates  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODES = ["professional", "friendly", "concise", "direct"]
WITHHELD = "tone.withheld"
QUESTION_WORDS = {"who", "whose", "what", "which", "where", "when", "why", "how"}
CHAT_SPEAK = re.compile(r"(?<![\w.'’-])(?:u|ur|thx|lol|pls|plz|gonna|wanna|gotta|ya|omg|idk|tmrw|brb|haha|cuz)(?![\w.'’-])", re.I)
NEGATION = re.compile(r"\b(?:not|never|no|cannot|unable|nobody|nothing|none|dont|doesnt|didnt|isnt|arent|wasnt|werent|havent|hasnt|hadnt|"
                      r"cant|couldnt|wont|wouldnt|shouldnt)\b|n['’]t\b", re.I)
# Words that start with a capital in a greeting or a sign-off but are not names.
NOT_NAMES = {"morning", "afternoon", "evening", "i"}
EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B50\u2B55][\uFE0F\U0001F3FB-\U0001F3FF]?"
                   "(?:\u200D[\U0001F000-\U0001FAFF\u2600-\u27BF][\uFE0F]?)*")


# Punctuation marks that follow each other ("widgets,." or "later;,"), which no sentence has.
STRAY = re.compile(r"[,;:][.,;:!?]|(?<!\.)\.\.(?!\.)|\s[,;]")


def load_items(paths):
    return [json.loads(line) for path in paths.split(",") for line in open(path, encoding="utf-8") if line.strip()]


class Engine:
    def __init__(self, path):
        self.proc = subprocess.Popen([path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding="utf-8",
                                     bufsize=1, env=quality_gates.engine_env())

    def ask(self, request):
        started = time.perf_counter()
        self.proc.stdin.write(json.dumps(request, ensure_ascii=False) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError("the engine exited")
        response = json.loads(line)
        response["wall_ms"] = (time.perf_counter() - started) * 1000
        return response

    def close(self):
        """Ends the engine; returns its peak resident memory in MB."""
        self.proc.stdin.close()
        return quality_gates.reap(self.proc)


# ---- extraction of the things a rewrite must not change ---------------------------------------------------------

def _take(pattern, text, flags=0):
    """All matches of pattern in text, and the text with those spans blanked (so a later extractor skips them)."""
    found = []

    def blank(m):
        found.append(m)
        return " " * len(m.group(0))
    return found, re.sub(pattern, blank, text, flags=flags)


def facts(text):
    """{kind: set of normalized tokens} for urls, emails, handles, times, dates and numbers."""
    out = {}
    m, text = _take(r"(?:https?://|www\.)[^\s<>\"'\]]+", text, re.I)
    out["urls"] = {x.group(0).rstrip(".,;:!?)").lower() for x in m}
    m, text = _take(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", text)
    out["emails"] = {x.group(0).rstrip(".").lower() for x in m}
    m, text = _take(r"(?<![\w@])@\w+(?:\.\w+)*", text)
    out["handles"] = {x.group(0).lower() for x in m}
    times = set()

    def time_token(m):
        hour, minute, ampm = m.group("h"), m.group("m") or "00", (m.group("ap") or "").lower()
        return f"{int(hour)}:{minute}{ampm + 'm' if ampm else ''}"
    m, text = _take(r"\b(?P<h>\d{1,2})(?::(?P<m>\d{2}))?\s?(?P<ap>[ap])\.?m\b\.?", text, re.I)
    times |= {time_token(x) for x in m}
    m, text = _take(r"\b(?P<h>\d{1,2}):(?P<m>\d{2})\b(?P<ap>)", text)
    times |= {time_token(x) for x in m}
    out["times"] = times
    m, text = _take(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b", text)
    out["dates"] = {x.group(0) for x in m}
    m, text = _take(r"\d+(?:,\d{3})*(?:\.\d+)?", text)
    out["numbers"] = {x.group(0).replace(",", "") for x in m}
    return out


ONES = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen").split()
TENS = "twenty thirty forty fifty sixty seventy eighty ninety".split()
ORDINALS = ("zeroth first second third fourth fifth sixth seventh eighth ninth tenth eleventh twelfth thirteenth fourteenth fifteenth sixteenth "
            "seventeenth eighteenth nineteenth twentieth").split()


def spelled(number):
    """The words a writer may use for a whole number up to 100 (and the ordinal up to 31): "6" -> {"six", "sixth"}."""
    if not number.isdigit() or int(number) > 100:
        return set()
    n, forms = int(number), set()
    if n < 20:
        forms.add(ONES[n])
    elif n == 100:
        forms.add("hundred")
    else:
        forms.add(TENS[n // 10 - 2] + ("-" + ONES[n % 10] if n % 10 else ""))
        forms.add(TENS[n // 10 - 2] + ("" if n % 10 == 0 else " " + ONES[n % 10]))
    if n <= 20:
        forms.add(ORDINALS[n])
    elif n < 30:
        forms.add("twenty-" + ORDINALS[n - 20])
    elif n == 30:
        forms.add("thirtieth")
    elif n == 31:
        forms.add("thirty-first")
    return forms


def words(text):
    return re.findall(r"[A-Za-z][A-Za-z'’-]*", text)


def stem(word):
    """who's -> who, Amara's -> Amara."""
    word = re.sub(r"['’](?:s|ll|d|re|ve|m)$", "", word.lower())
    return "who" if word == "whom" else word


def sentences(text):
    text = re.sub(r"\b(Mr|Mrs|Ms|Dr|Prof|St|Jr|Sr)\.", r"\1", text)  # "Mr. Whitfield" does not end a sentence
    return [s for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


def question_words(text):
    found = set()
    for sentence in sentences(text):
        if re.search(r"\?\W*$", sentence):
            found |= {stem(w) for w in words(sentence)} & QUESTION_WORDS
    return found


def ends_question(text):
    # As the engine reads it: an emoji after the question mark still ends a question.
    return bool(re.search(r"\?\W*$", text))


def names(text):
    """Capitalized words that are not at the start of a sentence or line (and not I, all-caps acronyms or greeting words)."""
    found = set()
    for sentence in sentences(text):
        tokens = words(sentence)
        for i, w in enumerate(tokens):
            if i == 0 or not w[0].isupper() or w.isupper() or len(w) < 2 or w.startswith("I'") or w.startswith("I’"):
                continue
            s = stem(w)
            if s not in NOT_NAMES:
                found.add(s)
    return found


def emoji_clusters(text):
    return EMOJI.findall(text)


# ---- scoring -----------------------------------------------------------------------------------------------------

def check(item, mode, response):
    """Returns (failed checks, details) for one item and mode."""
    spec = item["modes"][mode]
    text, casual = item["text"], item.get("casual", False)
    if response.get("error"):
        return ["error"], {"error": response["error"]}
    out = response.get("text")
    if out is None:
        return ["error"], {"error": "no text in the response"}
    withheld = WITHHELD in response.get("warnings", [])
    failed, why = [], {}

    def fail(name, detail=None):
        if name not in failed:
            failed.append(name)
        if detail:
            why[name] = detail

    changed = out.rstrip() != text.rstrip()
    if spec["expect"] == "rewrite":
        if withheld:
            fail("rewrite_withheld")
        elif not changed:
            fail("rewrite_unchanged")
    elif spec["expect"] == "keep" and changed and not withheld:
        fail("keep_changed")
    before, after = facts(text), facts(out)
    lowered = out.lower()
    for kind in ("numbers", "times", "dates", "urls", "emails", "handles"):
        missing = sorted(before[kind] - after[kind])
        if kind == "numbers":
            # Writing a number out ("3 times" -> "three times", "the 1st" -> "the first") keeps it.
            missing = [n for n in missing if not any(re.search(r"\b" + re.escape(w) + r"\b", lowered) for w in spelled(n))]
        if missing:
            fail(kind, missing)
    asked, answered = question_words(text), question_words(out)
    out_stems = {stem(w) for w in words(out)}
    if asked - out_stems:
        fail("question_word_dropped", sorted(asked - out_stems))
    # An output question asks nothing the writer did not: its question words are words of the input (maybe not in a question).
    if answered - asked - {stem(w) for w in words(text)}:
        fail("question_word_added", sorted(answered - asked - {stem(w) for w in words(text)}))
    if ends_question(text) and mode != "direct" and not ends_question(out):
        fail("question_mark")
    if bool(NEGATION.search(text)) != bool(NEGATION.search(out)):
        fail("negation_flipped", "dropped" if NEGATION.search(text) else "added")
    lost = sorted(names(text) - {stem(w) for w in words(out)})
    if lost:
        fail("name_dropped", lost)
    # Concise may not grow: more words fail, and so do more than 3 extra characters (a final full stop, "u" -> "you" or
    # "can't" -> "cannot" are the engine's hygiene in every mode and are allowed).
    if mode == "concise" and (len(out.split()) > len(text.split()) or len(out.rstrip()) > len(text.rstrip()) + 3):
        fail("concise_longer", f"{len(out.rstrip())} chars, {len(out.split())} words > {len(text.rstrip())} chars, {len(text.split())} words")
    new_marks = [m.group(0) for m in STRAY.finditer(out) if m.group(0) not in text]
    if new_marks:
        fail("stray_punctuation", new_marks)
    added = len(emoji_clusters(out)) - len(emoji_clusters(text))
    # Friendly may end a chat message with one emoji (engine/src/model.rs emoji_allowed); nothing else may add one.
    if added > 0 and not (mode == "friendly" and casual and added == 1 and out.rstrip().endswith(emoji_clusters(out)[-1])):
        fail("emoji_added", added)
    if mode == "professional":
        slang = sorted({m.group(0).lower() for m in CHAT_SPEAK.finditer(out)})
        if slang:
            fail("chat_speak", slang)
    missing = [w for w in spec.get("keep_words", []) if not re.search(r"(?i)\b(?:" + w + r")\b", out)]
    if missing:
        fail("keep_words", missing)
    hit = [p for p in spec.get("forbid", []) if re.search(p, out)]
    if hit:
        fail("forbid", [re.search(p, out).group(0) for p in hit])
    return failed, why


def summarize(rows, modes, items, machine, rss, engine, sets, every):
    summary = {"engine": engine, "set": sets, "machine": machine, "items": len(items), "every": every, "modes": {}, "max_rss_mb": rss}
    for mode in modes:
        group = [r for r in rows if r["mode"] == mode]
        failures = collections.Counter(c for r in group for c in r["failed"])
        kinds = collections.defaultdict(lambda: [0, 0])
        for r in group:
            kinds[r["kind"]][0] += 1
            kinds[r["kind"]][1] += r["verdict"] == "pass"
        passed = sum(1 for r in group if r["verdict"] == "pass")
        summary["modes"][mode] = {
            "items": len(group), "passed": passed, "pass_rate": round(passed / max(1, len(group)), 4),
            "failures": dict(sorted(failures.items(), key=lambda kv: (-kv[1], kv[0]))),
            "withheld": sum(1 for r in group if r["withheld"]),
            "rewritten": sum(1 for r in group if r["output"] is not None and r["output"].rstrip() != r["input"].rstrip()),
            "kinds": {k: {"items": n, "passed": p} for k, (n, p) in sorted(kinds.items())},
            "latency": quality_gates.latency([r["elapsed_ms"] for r in group if r["elapsed_ms"] is not None]),
        }
    return summary


def markdown(summary, rows):
    modes = summary["modes"]
    lines = [f"Tone regression set: {summary['items']} items, scored in {len(modes)} modes ({summary['machine']}; peak memory {summary['max_rss_mb']} MB).", "",
             "| Mode | Items | Passed | Pass rate | Rewritten | Withheld | p50 ms | p95 ms |", "|---|---|---|---|---|---|---|---|"]
    for mode, s in modes.items():
        lines.append(f"| {mode} | {s['items']} | {s['passed']} | {s['pass_rate']:.1%} | {s['rewritten']} | {s['withheld']} | "
                     f"{s['latency']['p50_ms']:.0f} | {s['latency']['p95_ms']:.0f} |")
    lines += ["", "## Failures by check", "", "| Check | " + " | ".join(modes) + " |", "|---|" + "---|" * len(modes)]
    checks = sorted({c for s in modes.values() for c in s["failures"]})
    for c in checks:
        lines.append(f"| {c} | " + " | ".join(str(s["failures"].get(c, 0)) for s in modes.values()) + " |")
    lines += ["", "## Pass rate by kind", "", "| Kind | " + " | ".join(modes) + " |", "|---|" + "---|" * len(modes)]
    kinds = sorted({k for s in modes.values() for k in s["kinds"]})
    for k in kinds:
        cells = []
        for s in modes.values():
            d = s["kinds"].get(k)
            cells.append(f"{d['passed']}/{d['items']}" if d else "-")
        lines.append(f"| {k} | " + " | ".join(cells) + " |")
    for mode in modes:
        bad = [r for r in rows if r["mode"] == mode and r["verdict"] == "fail"]
        if not bad:
            continue
        lines += ["", f"## {mode}: failed items ({len(bad)})", ""]
        for r in bad[:80]:
            lines.append(f"- {r['id']} [{', '.join(r['failed'])}] {r['input']!r} -> {r['output']!r}")
        if len(bad) > 80:
            lines.append(f"- ... and {len(bad) - 80} more in results.jsonl")
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--engine", default=str(ROOT / "engine/target/release/parzr-engine"))
    p.add_argument("--set", default=str(ROOT / "benchmarks/tone/regression.jsonl"), help="comma-separated list of files")
    p.add_argument("--output", type=pathlib.Path, default=ROOT / "dist/qa/tone-regression")
    p.add_argument("--modes", default=",".join(MODES))
    p.add_argument("--limit", type=int, default=0, help="first N items only (development)")
    p.add_argument("--every", type=int, default=1, help="every Nth item only (CI runs a sample; its baseline is kept apart from the full set's)")
    p.add_argument("--answers", type=pathlib.Path, help="re-score the answers of an earlier results.jsonl instead of running the engine")
    p.add_argument("--min-pass-rate", action="append", default=[], metavar="MODE=RATE")
    p.add_argument("--baseline", metavar="SUITE", help="gate against this suite in benchmarks/baselines.json (tone-regression)")
    a = p.parse_args()
    items = load_items(a.set)
    items = items[::max(1, a.every)]
    if a.limit:
        items = items[:a.limit]
    modes = a.modes.split(",")
    a.output.mkdir(parents=True, exist_ok=True)
    earlier, rss = {}, None
    if a.answers:
        earlier = {(r["mode"], r["id"]): r for r in map(json.loads, open(a.answers, encoding="utf-8")) if r.get("id")}
        previous = a.answers.parent / "summary.json"
        if previous.exists():
            rss = json.loads(previous.read_text()).get("max_rss_mb")
    engine = None
    if not a.answers:
        engine = Engine(a.engine)
        # Warm the model (and each mode's prompt) so the first items do not carry the load time.
        for mode in modes:
            engine.ask({"text": "Thanks for the update.", "mode": mode, "deep": True, "gec": True})
    rows, started = [], time.time()
    with open(a.output / "results.jsonl", "w", encoding="utf-8") as results:
        for n, item in enumerate(items):
            for mode in modes:
                if a.answers:
                    old = earlier.get((mode, item["id"]))
                    if old is None:
                        sys.exit(f"{a.answers} has no answer for {mode} {item['id']}")
                    response = {"text": old["output"], "warnings": old.get("warnings", []), "wall_ms": old["elapsed_ms"]}
                    if old.get("error"):
                        response["error"] = old["error"]
                else:
                    response = engine.ask({"text": item["text"], "mode": mode, "deep": True, "gec": True, "casual": bool(item.get("casual"))})
                failed, why = check(item, mode, response)
                row = {"id": item["id"], "kind": item["kind"], "mode": mode, "expect": item["modes"][mode]["expect"], "input": item["text"],
                       "output": response.get("text"), "withheld": WITHHELD in response.get("warnings", []),
                       "warnings": response.get("warnings", []), "error": response.get("error"),
                       "verdict": "fail" if failed else "pass", "failed": failed, "why": why,
                       "elapsed_ms": round(response["wall_ms"], 1) if response.get("wall_ms") is not None else None}
                rows.append(row)
                results.write(json.dumps(row, ensure_ascii=False) + "\n")
                results.flush()
            if not a.answers and (n + 1) % 20 == 0:
                print(f"  {n + 1}/{len(items)} items ({time.time() - started:.0f} s)", file=sys.stderr)
    if engine:
        rss = engine.close()
    summary = summarize(rows, modes, items, quality_gates.machine(), rss, a.engine, a.set, max(1, a.every))
    (a.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    text = markdown(summary, rows)
    (a.output / "summary.md").write_text(text)
    for mode, s in summary["modes"].items():
        print(f"{mode}: {s['passed']}/{s['items']} = {s['pass_rate']:.1%} (p50 {s['latency']['p50_ms']:.0f} ms, p95 {s['latency']['p95_ms']:.0f} ms)")
    print(f"peak memory {rss} MB; wrote {a.output}/summary.md")
    failed = []
    for spec in a.min_pass_rate:
        mode, threshold = spec.split("=")
        if summary["modes"][mode]["pass_rate"] < float(threshold):
            failed.append(f"{mode} pass rate {summary['modes'][mode]['pass_rate']:.4f} is below the gate {threshold}")
    for f in failed:
        print(f"GATE FAILED: {f}", file=sys.stderr)
    passed = True
    if a.baseline:
        gate = quality_gates.Gate(a.baseline)
        for mode, s in summary["modes"].items():
            # A sample (--every N) has its own baseline under "samples", recorded by update-baselines.py from a sample run.
            recorded = (gate.base or {}).get("samples", {}).get(str(a.every), {}) if a.every > 1 else (gate.base or {})
            base = recorded.get("modes", {}).get(mode)
            if base is None:
                if gate.base is not None:
                    gate.failures.append(f"{a.baseline}: no baseline for mode {mode}" + (f" with --every {a.every}" if a.every > 1 else ""))
                continue
            if base["items"] != s["items"]:
                gate.failures.append(f"{a.baseline} {mode}: {s['items']} items, the baseline counted {base['items']} (set changed: update the baseline on purpose)")
                continue
            gate.rate(f"{mode} passed", s["passed"], s["items"], base["passed"], base["items"])
            gate.performance(mode, {"p50_ms": s["latency"]["p50_ms"], "p95_ms": s["latency"]["p95_ms"], "max_rss_mb": rss})
        passed = gate.finish()
    if failed or not passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
