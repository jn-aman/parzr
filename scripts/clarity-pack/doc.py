"""Writes docs/rule-packs/clarity-style.md from the coverage rows the generator collected."""
import core

LEFT_OUT = [
    ('very unique, most unique, more unique', 'covered by the modifiers pack (`mod.very_unique_abs`, `mod.most_unique`, `mod.more_unique`); not repeated here'),
    ('Pleonasms (return back, each and every, first and foremost, reason why)', 'the redundancy pack owns them'),
    ('Business clichés (at the end of the day, circle back, please be advised, kindly, per my last email, at your earliest convenience)', 'the register-business pack owns them'),
    ('in order for, in order that, in order not to', 'only the plain "in order to" + verb is shortened; the others change the structure'),
    ('"in such a way that" / "in such a manner that" -> "so that"', 'dropped: the base punctuation pass (`punctuation.coordinated_clauses`) puts a comma before the "so that" the rewrite produces, which is wrong for a purpose clause'),
    ('prior to / subsequent to / in lieu of / in advance of / pursuant to / in accordance with', 'correct formal register, not padding; concise mode (tone.json) already offers "before" and "after"'),
    ('utilize, commence, terminate, facilitate, ascertain, endeavor', 'a single-word register choice, not a wordy construction; concise mode (tone.json) covers utilize'),
    ('with respect to, in relation to, in connection with, in terms of, in the case of, as per', 'correct in maths, law and technical writing ("differentiate with respect to x"); no one fixed rewrite'),
    ('is considered to be -> is considered', 'dropped: the base rule `grammar.gerund_complement` rewrites the correct "is considered to be an expert" to "considered being", so the pack stays out of that frame (base defect, reported)'),
    ('in a position to; in the not too distant future; with the exception of; at that point in time; make a change to; in a timely manner ("promptly" is not "timely"); it is my understanding that', 'each of these rewrote an everyday-set sentence that is correct as written (benchmarks/everyday, typing path: "no newly wrong"), so the rule was dropped; the "very near future" variant, "have the capacity to" and "make a decision by Thursday" were narrowed out for the same reason'),
    ('is able to / be able to / is capable of', 'left on purpose (brief): correct, and "can" is not valid after a modal'),
    ('is required to -> must; is dependent on -> depends on; is made up of -> consists of; is located in -> is in', 'a preference; "is located in" is also the passive of "locate" ("the hikers were located in a cave"), so dropping "located" would change the meaning'),
    ('analyze / summarize / emphasize / prioritize / organize / apologize as the plain verb', 'the spelling differs by dialect (-ise/-ize) and the dialect is not visible to a pack rule, so "perform an analysis of", "give a summary of", "put emphasis on" (the last one is rewritten with "stress") are left alone'),
    ('make a payment / a request / an inquiry / a reservation / a prediction / a statement / a claim / a list', 'the plain verb takes a different complement ("make a payment to X", "make a request for X", "make a reservation for four"), so a fixed rewrite would break the sentence'),
    ('have a look at / take a look at / take a decision / take action / take part in / take care of / take advantage of', 'idiom or dialect; the plain verb is no shorter or not equal'),
    ('a number of, a lot of, a variety of, a wide range of, a majority of, a large amount of', 'no safe fixed plain word: "a number of" is not "many", "a majority of" is not "most", and "much" is wrong in an affirmative clause'),
    ('Sentence-initial Basically, / Actually, / Literally, and "is basically a"', 'a filler in chat but a real contrast or summary marker in prose; only "I would actually/basically like to" (a polite-request frame) is flagged'),
    ('Personally, I think; I myself; I, for one', 'the contrast with other people is often the point, so only "I personally think" and "in my personal opinion" are flagged'),
    ('very, really, quite, extremely, pretty before an adjective', 'policy (README): no "very" hunting; only a repeated intensifier is flagged'),
    ('kind of / sort of in chat ("that is kind of cool")', 'informal on purpose; only formal subjects (report, results, approach, analysis ...) with a copula and a plain adjective are flagged'),
    ('whether or not', 'only after know/ask/wonder/decide/check/see and "regardless of": in "we will go whether or not it rains" the "or not" carries the meaning'),
    ('the question of whether, the fact that, the fact is, in the process of + noun, in the field of, in the realm of, in terms of', 'the rewrite depends on the sentence ("in the field of view", "raises the question of whether")'),
    ('at this time, at present, at the moment', 'short and correct ("at this time of year" is another sense)'),
    ('the month of June, the city of Paris, the year of 1998 as a noun phrase', 'pleonasm: redundancy pack. Only "in the year 1998" is shortened to "in 1998" here'),
    ('a period of time, an amount of time', 'only after long/short/limited/considerable/certain ("for a long period of time" -> "for a long time"); "a period of time" alone has no safe rewrite'),
    ('on a case-by-case basis, on a first-come first-served basis, on a rolling basis', 'a term of art; no shorter form'),
]


def write():
    lines = ['# Clarity and style pack: coverage map', '',
             f'`engine/rules/packs/clarity-style.json` holds {len(core.RULES)} rules (id prefix `clarity.`), generated by `scripts/clarity-pack/build.py` '
             '(`python3 scripts/clarity-pack/build.py` rewrites the JSON, `scripts/clarity-pack/expected.json` and this file). '
             'Every rule is category Style at 0.6 to 0.8, has a required literal, and a positive and a negative example written for it; '
             '`scripts/clarity-pack/e2e.py` runs every example through the built engine and checks the corrected text. '
             'A rule fires only where the rewrite is a drop-in: the verb form follows the light verb ("made a decision" -> "decided", '
             '"is in need of" -> "needs"), the phrase is whole ("in the course of" only before a determiner), and a clause-ending phrase is '
             'judged only before punctuation or a small word list, so "make a decision tree" and "a decision-making plan" are never touched.', '',
             'Fix mode only: the tone-mode wording rules (concise.* in tone.json) stay as they are and do not run in Fix mode.', '']
    sections = {}
    for sec, cons, ids in core.COVER:
        sections.setdefault(sec, []).append((cons, ids))
    for sec, rows in sections.items():
        lines += [f'## {sec}', '', '| Construction | Rules |', '|---|---|']
        for cons, ids in rows:
            short = [i[len('clarity.'):] for i in ids]
            shown = ', '.join(f'`{s}`' for s in short[:6]) + (f' and {len(short) - 6} more' if len(short) > 6 else '')
            lines.append(f'| {cons.replace("|", "/")} | {len(ids)} rule(s): {shown} |')
        lines.append('')
    lines += ['## Deliberately left out', '', '| Construction | Why |', '|---|---|']
    for what, why in LEFT_OUT:
        lines.append(f'| {what.replace("|", "/")} | {why} |')
    lines.append('')
    (core.ROOT / 'docs/rule-packs/clarity-style.md').write_text('\n'.join(lines))
