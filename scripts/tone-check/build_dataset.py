#!/usr/bin/env python3
"""Builds the tone-check training data: written seed lines, template expansions, public corpora, and
synthetic everyday messages. Nothing here is anyone's private writing.

Labels (one per message):
  neutral             ordinary messages, including direct, critical, negative, terse and apologetic-once ones
  rude                insults, profanity at a person or their work, hostility, condescension, blame, threats
  passive_aggressive  sarcasm, pointed reminders, backhanded compliments, guilt trips, fake politeness
  curt                brusque or bossy orders and brush-offs ("Not my problem.", "Just get it done.")
  over_apologetic     apologizing far beyond what the situation needs, self-deprecation that undercuts the ask

Sources (all synthetic, public or licensed for this use):
  seeds/*.txt         lines written for this project (scripts/tone-check/seeds)
  templates           TEMPLATES below, filled with synthetic objects, names and times
  everyday            dist/batches/batch-001 items written for Parzr ("written" and "corrupted" sources only;
                      Enron, LexNorm and ClueWeb lines are excluded), neutral after the AFM screen in afm-label
  paradetox           s-nlp/paradetox (OpenRAIL++): toxic side rude, neutral rewrite neutral
  politeness          Stanford Politeness Corpus (CC BY 4.0): the most polite half as neutral
  civil               google/civil_comments validation shard (CC0): toxicity >= 0.7 rude, < 0.05 neutral, <= 200 chars

The development sets (benchmarks/tone-check/dev.jsonl and dev2.jsonl) are written separately and every DEV text,
after normalization, is removed from training. Train/val split is 90/10 by a hash of the source group.

    PARZR_DIST=<main checkout>/dist python3 -I scripts/tone-check/build_dataset.py
"""
import argparse
import csv
import hashlib
import json
import pathlib
import random
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
from paths import BAKEOFF as _BAKEOFF, BATCHES, TONE  # noqa: E402

BAKEOFF = _BAKEOFF / "data"
LABELS = ["neutral", "rude", "passive_aggressive", "curt", "over_apologetic"]

OBJ = ["report", "deck", "PR", "invoice", "spec", "ticket", "budget", "roadmap", "contract", "slides", "test plan",
       "release notes", "mockup", "proposal", "timesheet", "migration plan", "schedule", "dashboard", "quote",
       "newsletter", "lesson plan", "shift roster", "purchase order", "design doc", "code review", "summary",
       "forecast", "press release", "onboarding guide", "survey results", "pitch", "estimate", "patch", "draft",
       "spreadsheet", "agenda", "meeting notes", "client email", "status update", "QA report"]
NAME = ["Priya", "Sam", "Alex", "Jordan", "Maria", "Lee", "Chen", "Omar", "Fatima", "Noah", "Aisha", "Ravi",
        "Elena", "Tom", "Grace", "Kenji", "Lucas", "Zara", "Ben", "Nina", "Arjun", "Sofia", "Marcus", "Hana"]
TIME = ["Friday", "tomorrow", "Monday", "end of day", "3pm", "next week", "the 14th", "noon", "Thursday",
        "this afternoon", "the end of the sprint", "9am", "Tuesday morning", "the 30th"]
AGO = ["last week", "on Monday", "two weeks ago", "three days ago", "yesterday", "last month", "in March"]
ORD = ["third", "fourth", "fifth", "second"]
GREET = ["Hey {n}, ", "Hi {n}, ", "{n}, ", "Hi team, ", "Hey all, ", "Hi, ", "Morning {n}. ", "@{n} ", ""]
NEUTRAL_LEAD = ["Here's the {o}.", "I looked at the {o}.", "Quick note on the {o}.", "Re the {o}:", "About the {o}.",
                "Got your message.", "Thanks for the update.", "Saw your comment."]

TEMPLATES = {
    "rude": [
        "This {o} is garbage.", "Who wrote this {bad} {o}?", "Your {o} is {insult}.", "Did you even read the {o} before sending it?",
        "{n}, this {o} is an embarrassment.", "Are you {dumb}? The {o} was due {t}.", "Stop {whine} and fix the {o}.",
        "The {o} is a disaster and it's your fault.", "Honestly, a child could have written a better {o}.",
        "What the hell is wrong with this {o}?", "I've never seen a worse {o}.", "Your {o} is a joke, like your last one.",
        "How did you manage to screw up the {o} this badly?", "This {o} is lazy, sloppy work.", "Only an idiot would send a {o} like this.",
        "Nobody can use this {bad} {o}.", "You ruined the {o}.", "Learn to write a {o} before you send one to the client.",
        "Your {o} made us look like clowns.", "The {o} is crap. Redo it.", "Who the hell approved this {o}?",
        "You clearly have no idea how to put together a {o}.", "The {o} is full of stupid mistakes, as usual.",
        "I'm sick of fixing your {bad} {o}s.", "This {o} is so bad it's insulting.", "Wow, this {o} is pathetic.",
    ],
    "passive_aggressive": [
        "Per my last email, the {o} was due {t}.", "Thanks for finally sending the {o}.", "Just a friendly reminder that I asked for the {o} {ago}.",
        "As I already mentioned, the {o} is in the shared drive.", "No worries, I'll just finish the {o} myself, as usual.",
        "Must be nice not to have to worry about the {o}.", "I'm sure you had a great reason for missing the {o} deadline.",
        "Reattaching the {o} for the {ord} time.", "Glad the {o} finally showed up, only two weeks late.",
        "As previously stated, the {o} is due {t}. Again.", "Not sure if you saw my last three messages about the {o}.",
        "Thanks for letting me know about the {o} after the meeting.", "Interesting that the {o} is only urgent now.",
        "It would be great if someone actually read the {o} for once.", "Happy to explain the {o} a fourth time.",
        "Great {o}. Shame about the numbers.", "The {o} looks good, for something done in an hour.",
        "Love that I found out about the {o} from the client.", "Gentle reminder that the {o} was due {ago}.",
        "I guess the {o} isn't a priority for some people.", "So glad we spent an hour on the {o} that was already decided.",
        "Kindly refer to my previous email about the {o}, which answers your question.", "Bumping the {o} again, since apparently nobody reads Slack.",
        "Following up on my follow-up about the {o}.", "I'll take your silence on the {o} as a yes, as usual.",
        "Wow, the {o} only took three weeks.", "Oh, so now the {o} is my problem?", "Thanks for the detailed feedback on the {o}. All one word of it.",
    ],
    "curt": [
        "{O}. Now.", "Send the {o}. Today.", "Fix the {o}. No excuses.", "Why isn't the {o} done yet?", "I don't care, just send the {o}.",
        "Not my problem. Ask {n} about the {o}.", "Just get the {o} done.", "The {o}. By {t}. Period.", "Redo the {o}.",
        "Stop asking me about the {o}.", "Figure out the {o} yourself.", "The {o} is your job, not mine.", "Don't care. Ship the {o}.",
        "I want the {o} on my desk by {t}. No excuses.", "{O} wrong. Redo it.", "Not interested in the {o}.", "Is the {o} done or not?",
        "Just send the {o} I asked for.", "Don't message me about the {o} again.", "The {o}. Today. Not tomorrow.",
        "Read the {o} yourself.", "Spare me the details, just finish the {o}.", "Done with the {o} yet?", "{O}? Hello?",
    ],
    "over_apologetic": [
        "So sorry to bother you, I'm so sorry, but could you look at the {o}? Sorry!",
        "Sorry, sorry, I messed up the {o}, I'm so sorry.",
        "I'm really sorry, this is probably a dumb question, but where is the {o}? Sorry!",
        "Sorry for asking again, I know you're busy, sorry, any update on the {o}? So sorry.",
        "I'm so sorry the {o} is late, I feel terrible, I'm really sorry, it won't happen again.",
        "Sorry, I know the {o} is probably terrible, sorry in advance, I can redo it.",
        "Sorry to be a pain, I'm sorry, could you resend the {o}? Sorry again!",
        "I apologize for the {o}, I sincerely apologize, I'm so sorry for the trouble.",
        "Sorry if this is a silly question, sorry, but is the {o} due {t}? Sorry!",
        "I'm so sorry, I think I might have made a tiny mistake in the {o}, so sorry, I'm the worst.",
        "Sorry for the spam, sorry, last question about the {o}, I promise, sorry.",
        "Here's the {o}, sorry it's so bad, sorry, I tried.",
        "I'm probably wrong, I'm not an expert, ignore me if so, but the {o} looks off? Sorry.",
        "sorry sorry sorry, sent the wrong {o}!! so sorry!!",
    ],
    "neutral": [
        "Can you send the {o} by {t}?", "The {o} is ready for review.", "Per the plan, the {o} is due {t}.", "Following up on the {o}. Any update?",
        "Sorry for the delay, here's the {o}.", "The {o} has a few issues. See my comments.", "I don't think the {o} is ready yet.",
        "Please fix the {o} before {t}.", "Just a reminder that the {o} is due {t}.", "Thanks for sending the {o}!",
        "Where's the {o}? I can't find it in the drive.", "The {o} needs to be done by {t}.", "Can we push the {o} to {t}?",
        "I'm not happy with the {o}. Let's discuss.", "Why did the {o} get rejected?", "Resending the {o} in case it got lost.",
        "Is the {o} done?", "Attached is the {o}.", "I updated the {o} with your comments.", "The {o} looks great, thanks {n}!",
        "Could you take a look at the {o} when you have a minute?", "I left a few comments on the {o}.", "The {o} is late. When can we expect it?",
        "The numbers in the {o} don't add up. Can you check them?", "I disagree with the {o}. Can we talk?", "The {o} needs another pass.",
        "Sorry, wrong {o}. Here's the right one.", "Sorry, I missed the {o}. Sending it now.", "Thanks for the reminder about the {o}.",
        "As discussed, I'll send the {o} by {t}.", "As mentioned in the meeting, the {o} is due {t}.", "Bumping the {o} in case it got buried.",
        "Checking in on the {o}. Do you need anything from me?", "No rush on the {o}.", "Please send the {o} today, the client is waiting.",
        "I need the {o} by {t}.", "Send me the {o} when it's ready.", "Fix the typo in the {o} before sending.", "Who owns the {o}?",
        "{n} is handling the {o}.", "I'll finish the {o} tonight.", "The {o} is approved.", "The client rejected the {o}.",
        "We can't approve the {o} as it is.", "The {o} is over budget.", "I made a mistake in the {o}. Fixing it now.",
        "Ugh, the {o} template is broken again.", "Great work on the {o}!", "Happy with the {o}, ship it.", "Let's discuss the {o} on {t}.",
        "Can someone own the {o} this week?", "Not sure about the {o}. Let me check.", "The {o} is in the shared folder.",
        "FYI, the {o} moved to {t}.", "Heads up: the {o} changed.", "Re-attaching the {o} since the link expired.",
        "Sorry to bother you, quick question about the {o}.", "Sorry for the late reply. The {o} looks good.",
        "If I don't hear back about the {o} by {t}, I'll go ahead.", "I'll pass on the {o} this time.",
        "No, we're not changing the {o}.", "That won't work for the {o}.", "Let's not change the {o} this late.",
    ],
}
FILL = {
    "bad": ["terrible", "awful", "useless", "sloppy", "garbage", "pathetic", "ridiculous"],
    "insult": ["a mess", "garbage", "useless", "embarrassing", "pathetic", "trash", "a disgrace"],
    "dumb": ["stupid", "blind", "incompetent", "serious", "kidding me"],
    "whine": ["whining", "complaining", "making excuses", "wasting time", "crying about it"],
}


def norm(text):
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def bucket(group):
    return "val" if int(hashlib.sha256(group.encode()).hexdigest(), 16) % 10 == 0 else "train"


def fill(template, rng):
    o = rng.choice(OBJ)
    out = template.replace("{O}", o[0].upper() + o[1:]).replace("{o}", o)
    for k, opts in FILL.items():
        out = out.replace("{" + k + "}", rng.choice(opts))
    return (out.replace("{n}", rng.choice(NAME)).replace("{t}", rng.choice(TIME))
            .replace("{ago}", rng.choice(AGO)).replace("{ord}", rng.choice(ORD)))


def chatify(text, rng):
    """Surface variation that must not change the label: case, final punctuation, a greeting."""
    r = rng.random()
    if r < 0.15:
        text = text.lower()
    elif r < 0.25:
        text = text.rstrip(".")
    if rng.random() < 0.25:
        text = rng.choice(GREET).replace("{n}", rng.choice(NAME)) + (text[0].lower() + text[1:] if text[:2] not in ("I ", "I'") else text)
    return text


def seeds(label):
    """The written lines of one class: seeds/<label>.txt, plus the round-2 files (neutral_contrast.txt, and the
    tab-separated harsh_round2.txt)."""
    lines = [l.strip() for l in open(HERE / "seeds" / f"{label}.txt", encoding="utf-8") if l.strip() and not l.startswith("#")]
    if label == "neutral":
        lines += [l.strip() for l in open(HERE / "seeds/neutral_contrast.txt", encoding="utf-8") if l.strip() and not l.startswith("#")]
    else:
        for l in open(HERE / "seeds/harsh_round2.txt", encoding="utf-8"):
            if l.strip() and not l.startswith("#"):
                lab, text = l.rstrip("\n").split("\t", 1)
                if lab == label:
                    lines.append(text.strip())
    return lines


def build(out, dev_path, seed=7):
    rng = random.Random(seed)
    rows = []

    def add(text, label, source, group):
        rows.append({"text": text, "label": label, "source": source, "group": group})

    # Seeds, each with up to two surface variants (same group: they stay in one split).
    for label in LABELS:
        for i, line in enumerate(seeds(label)):
            g = f"seed-{label}-{i}"
            add(line, label, "seed", g)
            for _ in range(2):
                v = chatify(line, rng)
                if v != line:
                    add(v, label, "seed", g)
    # Templates: about 30 fills per template; the template is the group, so val holds unseen templates.
    for label, temps in TEMPLATES.items():
        per = 40 if label == "neutral" else 30
        for ti, t in enumerate(temps):
            seen = set()
            for _ in range(per):
                text = chatify(fill(t, rng), rng)
                if text not in seen:
                    seen.add(text)
                    add(text, label, "template", f"tpl-{label}-{ti}")
    # Two-sentence messages: a neutral lead plus a line of any class takes that line's label.
    seed_lines = {l: seeds(l) for l in LABELS}
    for label in LABELS:
        for k in range(250 if label != "neutral" else 600):
            line = rng.choice(seed_lines[label])
            lead = fill(rng.choice(NEUTRAL_LEAD), rng)
            text = f"{lead} {line}" if rng.random() < 0.6 else f"{line} {fill(rng.choice(NEUTRAL_LEAD), rng)}"
            add(text, label, "combo", f"combo-{label}-{seed_lines[label].index(line)}")
    # Everyday messages written for Parzr's batches (batch-001 only; batch-002 is DEV).
    for l in open(BATCHES / "batch-001/items.jsonl", encoding="utf-8"):
        r = json.loads(l)
        if r["source"] in ("written", "corrupted"):
            add(r["expected"], "neutral", "everyday", f"b1-{r['id']}")
    # Public corpora.
    pairs = []
    with open(BAKEOFF / "dl-paradetox/s-nlp__paradetox/train.tsv", encoding="utf-8") as f:
        for k, r in enumerate(csv.DictReader(f, delimiter="\t")):
            pairs.append((k, r["en_toxic_comment"].strip(), r["en_neutral_comment"].strip()))
    rng.shuffle(pairs)
    for k, tox, neu in pairs[:1500]:
        add(tox, "rude", "paradetox", f"pdx-{k}")
        add(neu, "neutral", "paradetox", f"pdx-{k}")
    pol = []
    for name in ("wikipedia", "stack-exchange"):
        with open(BAKEOFF / f"dl-politeness/Stanford_politeness_corpus/{name}.annotated.csv", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                pol.append((name, r["Id"], r["Request"], float(r["Normalized Score"])))
    med = sorted(p[3] for p in pol)[len(pol) // 2]
    polite = [p for p in pol if p[3] >= med and "<url>" not in p[2]]
    rng.shuffle(polite)
    for name, i, text, _ in polite[:1200]:
        add(text, "neutral", "politeness", f"pol-{name}-{i}")
    import pandas as pd
    cc = pd.read_parquet(BAKEOFF / "dl-civil/data/validation-00000-of-00001.parquet")
    cc = cc[cc.text.str.len() <= 200]
    for lab, part, n in (("rude", cc[cc.toxicity >= 0.7], 600), ("neutral", cc[cc.toxicity < 0.05], 800)):
        for idx, r in part.sample(n=min(n, len(part)), random_state=seed).iterrows():
            add(r.text.strip(), lab, "civil", f"civil-{idx}")

    # Remove DEV texts (and exact duplicates), then split.
    dev = set()
    for path in (dev_path, dev_path.with_name("dev2.jsonl")):
        if path.exists():
            dev |= {norm(json.loads(l)["text"]) for l in open(path, encoding="utf-8")}
    seen, final = set(), []
    dropped_dev = 0
    for r in rows:
        k = norm(r["text"])
        if not k:
            continue
        if k in dev:
            dropped_dev += 1
            continue
        if (k, r["label"]) in seen:
            continue
        seen.add((k, r["label"]))
        r["split"] = bucket(r["group"])
        final.append(r)
    # A text with two labels is ambiguous: keep neither.
    by = {}
    for r in final:
        by.setdefault(norm(r["text"]), set()).add(r["label"])
    final = [r for r in final if len(by[norm(r["text"])]) == 1]
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "train.jsonl", "w", encoding="utf-8") as f:
        for i, r in enumerate(final):
            r["id"] = f"t{i:05d}"
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    from collections import Counter
    print("dropped (in DEV):", dropped_dev)
    print(Counter((r["split"], r["label"]) for r in final))
    print(Counter((r["source"], r["label"]) for r in final))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=pathlib.Path, default=TONE / "data")
    ap.add_argument("--dev", type=pathlib.Path, default=REPO / "benchmarks/tone-check/dev.jsonl")
    a = ap.parse_args()
    build(a.out, a.dev)
