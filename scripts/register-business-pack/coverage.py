"""Renders docs/rule-packs/register-business.md: the coverage map (construction -> rule ids, base rule, or why not)."""
import collections

FAMILIES = [
    ("purpose", "Purpose phrases", "in order to / so as to / in order for / in order that"),
    ("time", "Time phrases", "at this point in time, at the present time, at this time (only where it clearly means now), at a later date, until such time as, during the time that, at the time that"),
    ("basis", "\"On a ... basis\"", "on a daily/weekly/monthly/quarterly basis, on a regular/consistent/continuous/... basis, on an annual/temporary/voluntary/as-needed/case-by-case basis"),
    ("manner", "\"In a ... manner\"", "in a timely manner, in an efficient/effective/professional/... manner"),
    ("cause", "Cause and condition", "due to the fact that, in view of the fact that, despite the fact that, in the event that"),
    ("reference", "Reference and relation", "with regard to, with reference to, pertaining to, as to whether, in lieu of, in conjunction with, with the exception of, in excess of, in the vicinity of, in close proximity to"),
    ("quantity", "Quantity", "a sufficient number of, a large number of, the majority of, in the majority of cases"),
    ("preposition", "Wordy prepositions", "prior to, subsequent to, previous to, during/throughout the course of, for a period of"),
    ("verb", "Formal and jargon verb phrases", "utilize, commence, endeavor, ascertain, leverage, touch base, circle back, make use of, take into consideration, have a tendency to, has the ability to, in a position to, in receipt of, of the opinion that, it is my understanding that, it would be appreciated, in agreement, in need of, in possession of, make an attempt, come to the conclusion"),
    ("advisory", "Advisory wrappers", "please be advised that, this is to inform you that, bring to your attention that, it should be noted that, take this opportunity to"),
    ("per", "per / as per", "as per, per our conversation"),
    ("enclosure", "Enclosures", "attached herewith, enclosed please find, herewith"),
    ("archaic", "Archaic adverbs", "aforementioned, heretofore, henceforth, forthwith"),
    ("forward", "going / moving forward", "going forward, moving forward"),
    ("kindly", "kindly", "kindly + imperative, please kindly, kindly please"),
    ("thanks", "Thanks", "thanking you, thanks in advanced"),
    ("boilerplate", "Email boilerplate", "should you have, do not hesitate to, at your earliest convenience, under separate cover, you are requested to, writing this email to, as and when, as of yet, in this day and age, the month of, 9 AM in the morning"),
    ("signoff", "Greetings and sign-offs", "comma after Best regards / Thanks / Dear Name, Hi, Aman, regards misspellings"),
]

LEFT_OUT = [
    ("Left to the nonnative pack", "do the needful, revert (usage.revert_reply covers revert back to), the same, prepone, kindly revert", "The brief assigns them to the non-native pack."),
    ("Left alone on purpose", "awaiting your reply, Dear Sir/Madam, Please find attached, Please note that, I hope this email finds you well, reach out to, loop in, at the end of the day, per my last email, assist, purchase, obtain, require", "Courteous, idiomatic or merely a preference: the pack policy says a style rule never flags a preference."),
    ("Not regex-safe", "the undersigned", "It can be plural, a contract party label, or a signature block; \"I\" or \"we\" cannot be chosen from the words around it."),
    ("Not regex-safe", "with respect to, in relation to, in connection with, pursuant to, in accordance with, hereby", "Each has a technical or legal meaning (\"derivative with respect to x\", \"in connection with a crime\", \"I hereby resign\") that a plain word would break."),
    ("Not regex-safe", "bandwidth (\"I don't have the bandwidth\"), take this offline, circle back (literal movement, handled only with business objects), going forward (literal, handled only when set off by commas)", "A literal reading exists; the rule needs a business-only context or is left out."),
    ("Not regex-safe", "Yours sincerely after Dear Sir/Madam (UK pairing)", "The salutation and the closing sit paragraphs apart; the engine only looks one sentence either side of a match."),
    ("Not regex-safe", "Best regads / Sincerley / Yours faithfuly at the start of a closing line", "The engine's name guard protects a capitalized closing before a name and drops edits that touch it, so only Kind/Warm/Thanks-and variants can be fixed (the rule `signoff.regards_misspelled` covers them)."),
    ("Base rule", "in order to, prior to, subsequent to, utilize / utilized, at this point in time, at the present time, due to the fact that, in the event that, with regard to, a large number of, on a daily basis, has the ability to, at a later date", "tone.json already has them for the concise and direct modes. The pack repeats only the ones it widens (other forms, other spellings, a following noun it must keep): `wordy.now_phrases`, `wordy.because_phrases`, `wordy.regarding`, `wordy.basis_period`, `wordy.large_number_of` / `wordy.large_number_of_the`, `verb.ability.*`, `wordy.later_date`; `in order to`, `prior to`, `subsequent to` and `utilize`/`utilized` are not repeated."),
    ("Base rule", "in regards to", "confuse.x_in_regard_to corrects the plural; `wordy.regarding` then suggests \"regarding\" (concise and direct only)."),
    ("Base rule", "prior to + a base verb (\"prior to apply\")", "prep.prior_to_base_verb corrects the verb in Fix mode; the plain \"before\" for `prior to` itself is the base tone rule `concise.phrase.prior_to`."),
    ("Base rule", "looking forward to hear, regarding to, awaiting for", "prep.look_forward_to_*, prep.regarding_to and prep.await_for fix these already."),
]

def render(rules):
    by = collections.defaultdict(list)
    for r in rules:
        by[r["_family"]].append(r["id"].split("register.", 1)[1])
    cats = collections.Counter(r["category"] for r in rules)
    out = []
    out.append("# Register (business and email) pack: coverage map\n")
    out.append(f"`engine/rules/packs/register-business.json` holds {len(rules)} rules (id prefix `register.`), generated by `scripts/register-business-pack/build.py` (`python3 scripts/register-business-pack/build.py` rewrites the JSON and this file). `scripts/register-business-pack/e2e.py` runs every positive and negative through the built engine.\n")
    fix = [r for r in rules if "modes" not in r]
    tone = [r for r in rules if "modes" in r]
    out.append(f"**Where the rules run.** {len(fix)} rules run in Fix mode: misspelled closings (`regads`, `regardz`, `wishs`), \"thanks in advanced\", \"best regard\", \"previous to\", plain redundancies (\"please kindly\", \"attached herewith\", \"9 AM in the morning\") and the comma conventions of greetings and closings. The other {len(tone)} are plain-language suggestions for text that is correct as written (\"in order to\", \"as per\", \"kindly\", \"utilize\", \"going forward\"); they carry `modes: [\"concise\", \"direct\"]`, as the base wordiness rules in `tone.json` do, because the everyday gate (`benchmarks/everyday`) labels such sentences \"must stay unchanged\" in Fix mode: running them there changed 35 labelled items. They apply in the rules-only build (`--no-default-features`); the shipped local-model build hands a tone rewrite to the model and does not run tone rules (`pipeline.rs: tone()`), so today they are not user-visible there. Which rules run where is one set, `FIX` in `scripts/register-business-pack/core.py`.\n")
    out.append("Categories: Style (" + str(cats["Style"]) + "), Redundancy (" + str(cats["Redundancy"]) + "), Register (" + str(cats["Register"]) + "), Spelling (" + str(cats["Spelling"]) + "), Word choice (" + str(cats["Word choice"]) + "); confidence 0.60 to 0.78 for suggestions, 0.88 to 0.95 for the corrections. Every rule has a required literal, a positive and a negative written for it, and is context-anchored: a phrase is only touched where its plain replacement keeps the sentence grammatical (the verb families name the subject or object that must surround them; `circle back` and `touch base` need a business object or time word, so the literal \"the plane circled back\" stays).\n")
    out.append("## Constructions and rules\n")
    out.append("| Construction | Rules |\n|---|---|")
    for key, title, what in FAMILIES:
        ids = by.get(key, [])
        shown = ", ".join(f"`{i}`" for i in ids[:6]) + (f" and {len(ids) - 6} more" if len(ids) > 6 else "")
        out.append(f"| **{title}**: {what} | {len(ids)} rule(s): {shown} |")
    out.append("\n## Not covered, and why\n")
    out.append("| Kind | Constructions | Reason |\n|---|---|---|")
    for kind, what, why in LEFT_OUT:
        out.append(f"| {kind} | {what} | {why} |")
    out.append("")
    return "\n".join(out)
