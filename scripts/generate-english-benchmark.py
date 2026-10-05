#!/usr/bin/env python3
"""Build an independent synthetic English challenge set and invertible error spans."""
import argparse
import hashlib
import json
import pathlib
import random
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Correct paragraphs and deliberately incorrect forms are authored separately from
# the checker. They span linguistic structures, not its implemented rule IDs.
FAMILIES = [
    ("past_narrative", "Yesterday, I went to the {place} and bought some {goods}. The shopkeeper was busy, so I waited by the entrance. My friends were ready to leave before the store closed.", [("went", "goes"), ("bought", "buyer"), ("friends were", "friends was")]),
    ("subject_agreement", "{name} writes a careful {report} every morning. Her colleagues review the details before the meeting begins. The {plural} are ready for the {topic}.", [("writes", "write"), ("colleagues review", "colleagues reviews"), ("{plural} are", "{plural} is")]),
    ("modal_verbs", "We should send the {report} before the meeting starts. {name} can finish the remaining work today. The team must check the dates for the {topic}.", [("should send", "should sends"), ("can finish", "can finished"), ("must check", "must checks")]),
    ("perfect_tenses", "{name} has written the {report} for the {topic}. We have completed the first review already. The manager had seen the latest version before the meeting began.", [("has written", "has wrote"), ("have completed", "have complete"), ("had seen", "had saw")]),
    ("passive_voice", "The {report} is supposed to be checked before the meeting. The {plural} were delivered to the office this morning. The final version was approved for the {topic}.", [("is supposed", "is suppose"), ("were delivered", "were deliver"), ("was approved", "was approve")]),
    ("articles", "{name} ate an apple before leaving for the {topic}. A university nearby offered to help with the event. We spent an hour discussing the {report} with its director.", [("an apple", "a apple"), ("A university", "An university"), ("an hour", "a hour")]),
    ("conditionals", "If {name} had prepared the {report} earlier, she would have finished on time. If the weather improves, we will attend the {topic}. We would have helped if someone had called us.", [("had prepared", "has prepare"), ("would have finished", "will had finished"), ("weather improves", "weather improve")]),
    ("comparisons", "This {report} is better than the previous version. It contains fewer mistakes and explains the {topic} clearly. The new procedure is the easiest one for the team to follow.", [("better than", "more better then"), ("fewer mistakes", "less mistakes"), ("the easiest", "the most easiest")]),
    ("pronouns_possessives", "I think you're going to enjoy the {topic}. The organizers brought their {plural} to the office. Each folder has its label attached to the front cover.", [("you're going", "your going"), ("their {plural}", "there {plural}"), ("its label", "it's label")]),
    ("uncountable_nouns", "The information is useful for the {topic}. {name}'s advice was helpful when we revised the {report}. The equipment is ready for the presentation tomorrow.", [("information is", "informations are"), ("advice was", "advices were"), ("equipment is", "equipments are")]),
    ("gerunds_infinitives", "{name} enjoys reading the {report} on the train. We look forward to meeting the organizers of the {topic}. Our colleagues suggested going to the {place} after lunch.", [("enjoys reading", "enjoys to read"), ("forward to meeting", "forward to meet"), ("suggested going", "suggested to go")]),
    ("prepositions", "The team is interested in the {topic}. Its success depends on careful planning and a clear {report}. We will discuss the arrangements during the meeting tomorrow.", [("interested in", "interested on"), ("depends on", "depends of"), ("discuss the", "discuss about the")]),
    ("auxiliary_do", "{name} did not know that the {report} was ready. The printer does not work when the battery is empty. Why did she call the organizers of the {topic} yesterday?", [("did not know", "did not knew"), ("does not work", "does not works"), ("did she call", "did she called")]),
    ("standard_negation", "We did not buy anything for the {topic} yesterday. {name} has never seen anyone revise a {report} so quickly. I cannot find any spare folders in the office.", [("did not buy anything", "did not buy nothing"), ("never seen anyone", "never seen no one"), ("cannot find any", "cannot find no")]),
    ("relative_clauses", "The person who handles the {report} is away today. The people who work on the {topic} need an updated schedule. Each of the files is stored in a separate folder.", [("person who handles", "person who handle"), ("people who work", "people who works"), ("files is", "files are")]),
    ("inversion", "Rarely have I seen a {report} with such clear explanations. Not only did {name} write the introduction, but she also checked every reference. Never have we completed the {topic} so quickly.", [("Rarely have I seen", "Rarely I have seen"), ("Not only did {name} write", "Not only {name} did write"), ("Never have we completed", "Never we have completed")]),
    ("future_forms", "Tomorrow, we will discuss the {report} at the office. By Friday, {name} will have finished the plans for the {topic}. The deadline is approaching, so the team needs a final decision.", [("will discuss", "will discussed"), ("will have finished", "will have finish"), ("deadline is", "deadline are")]),
    ("tense_consistency", "Yesterday, {name} visited the {place} to collect some {goods}. Last week, we finished the {report} for the {topic}. The manager thanked everyone after the work was complete.", [("visited", "visits"), ("we finished", "we finishes"), ("manager thanked", "manager thank")]),
    ("real_word_confusions", "Please accept the revised {report} for the {topic}. Its effect on the schedule should be clear to everyone. We will lose valuable time if we delay the next meeting.", [("Please accept", "Please except"), ("Its effect", "Its affect"), ("will lose", "will loose")]),
    ("questions", "Where did {name} put the {report} after the meeting? Why is the office closed during the {topic}? When does she arrive at the {place} to collect the remaining {goods}?", [("did {name} put", "did {name} puts"), ("Why is", "Why are"), ("does she arrive", "do she arrives")]),
]
TOPICS = [
    dict(name="Maya", topic="library renovation", report="report", plural="reports", place="market", goods="vegetables"),
    dict(name="Elena", topic="community workshop", report="proposal", plural="proposals", place="bookshop", goods="books"),
    dict(name="Priya", topic="garden project", report="schedule", plural="schedules", place="garden center", goods="plants"),
    dict(name="Sofia", topic="school exhibition", report="application", plural="applications", place="stationery shop", goods="supplies"),
    dict(name="Clara", topic="museum event", report="summary", plural="summaries", place="museum shop", goods="gifts"),
]
COMBINATIONS = [
    ("grammar_only", 3, 0, 0, 0, 0),
    ("spelling_only", 0, 3, 0, 0, 0),
    ("punctuation_only", 0, 0, 2, 0, 0),
    ("grammar_spelling", 2, 2, 0, 0, 0),
    ("grammar_punctuation", 2, 0, 2, 0, 0),
    ("spelling_punctuation", 0, 2, 2, 0, 0),
    ("grammar_spelling_punctuation", 3, 2, 2, 0, 0),
    ("short_word_spelling", 0, 0, 0, 3, 0),
    ("word_boundaries", 0, 1, 0, 0, 2),
    ("dense_combination", 3, 3, 2, 2, 1),
]
SHORT = {"the": "teh", "and": "adn", "not": "nto", "to": "ot", "was": "wsa", "had": "hda", "for": "fro", "can": "cna", "has": "hsa", "will": "wlil", "with": "wiht", "we": "ew"}


def utf16(text):
    return len(text.encode("utf-16-le")) // 2


def corrupt(correct, grammar, combination, rng, known):
    _, ng, ns, np, nshort, njoins = combination
    changes = []

    def add(start, end, wrong, category):
        if any(start < b and end > a for a, b, *_ in changes):
            return False
        assert correct[start:end] != wrong
        changes.append((start, end, wrong, category))
        return True

    for old, wrong in grammar[:ng]:
        matches = list(re.finditer(re.escape(old), correct))
        assert matches, old
        m = matches[0]
        assert add(m.start(), m.end(), wrong, "grammar")

    words = list(re.finditer(r"\b[a-z]{5,}\b", correct))
    rng.shuffle(words)
    found = 0
    for m in words:
        word = m.group()
        i = rng.randrange(1, len(word) - 1)
        op = rng.randrange(4)
        wrong = [word[:i] + "m" + word[i:], word[:i] + word[i + 1:], word[:i] + word[i + 1] + word[i] + word[i + 2:], word[:i] + "z" + word[i + 1:]][op]
        if wrong == word or wrong.lower() in known:
            continue
        if found < ns and add(m.start(), m.end(), wrong, "spelling"):
            found += 1
    assert found == ns, (found, ns, correct)

    punctuation = list(re.finditer(r"[.?] (?=[A-Z])", correct))
    rng.shuffle(punctuation)
    found = 0
    for m in punctuation:
        if found < np and add(m.start(), m.end(), " ", "missing_sentence_punctuation"):
            found += 1
    assert found == np

    short = [m for m in re.finditer(r"\b[a-z]+\b", correct) if m.group() in SHORT]
    rng.shuffle(short)
    found = 0
    for m in short:
        if found < nshort and add(m.start(), m.end(), SHORT[m.group()], "short_word_spelling"):
            found += 1
    assert found == nshort, (found, nshort, correct)

    joins = list(re.finditer(r"\b[a-z]+ [a-z]+\b", correct))
    rng.shuffle(joins)
    found = 0
    for m in joins:
        if found < njoins and add(m.start(), m.end(), m.group().replace(" ", ""), "missing_word_space"):
            found += 1
    assert found == njoins, (found, njoins, correct)

    output, annotations, cursor = "", [], 0
    for start, end, wrong, category in sorted(changes):
        output += correct[cursor:start]
        annotations.append(dict(start_utf16=utf16(output), end_utf16=utf16(output) + utf16(wrong), original=wrong, replacement=correct[start:end], category=category))
        output += wrong
        cursor = end
    output += correct[cursor:]
    restored = output.encode("utf-16-le")
    for a in reversed(annotations):
        restored = restored[:a["start_utf16"] * 2] + a["replacement"].encode("utf-16-le") + restored[a["end_utf16"] * 2:]
    assert restored.decode("utf-16-le") == correct
    return output, annotations


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=pathlib.Path, default=ROOT / "benchmarks/english-1000.jsonl")
    parser.add_argument("--seed", type=int, default=61004)
    args = parser.parse_args()
    known = dict(json.loads((ROOT / "engine/rules/lexicon.json").read_text()))
    cases, controls = [], []
    for family_index, (family, template, mistakes) in enumerate(FAMILIES):
        for topic_index, topic in enumerate(TOPICS):
            base_id = f"base-{family_index * 5 + topic_index + 1:03}"
            correct = template.format(**topic).replace("a application", "an application")
            grammar = [(a.format(**topic), b.format(**topic)) for a, b in mistakes]
            controls.append(dict(id=base_id, family=family, input=correct, expected=correct, kind="clean_control"))
            for index, combination in enumerate(COMBINATIONS):
                rng = random.Random(args.seed + family_index * 1000 + topic_index * 100 + index)
                text, annotations = corrupt(correct, grammar, combination, rng, known)
                cases.append(dict(id=f"{base_id}-{index + 1:02}", base_id=base_id, family=family, combination=combination[0], input=text, expected=correct, expected_edits=annotations, kind="corrupted_paragraph"))
    assert len(cases) == 1000 and len(controls) == 100
    assert len({c["input"] for c in cases}) == 1000
    assert all(c["input"] != c["expected"] and c["expected_edits"] for c in cases)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in cases))
    args.output.with_name("english-100-clean.jsonl").write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in controls))
    metadata = dict(seed=args.seed, base_paragraphs=100, combinations_per_base=10, corrupted_paragraphs=1000, clean_controls=100, families=[f[0] for f in FAMILIES], combinations=[c[0] for c in COMBINATIONS], sha256=hashlib.sha256(args.output.read_bytes()).hexdigest(), scope="Authored synthetic standard-English challenge set. Exact references are not the only possible grammatical corrections; dialect/style variants require human review.")
    args.output.with_name("english-1000-manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Generated {len(cases)} unique corrupted paragraphs, {len(controls)} clean controls, and {sum(len(c['expected_edits']) for c in cases)} annotated error spans.")


if __name__ == "__main__":
    main()
