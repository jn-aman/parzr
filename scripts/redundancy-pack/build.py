#!/usr/bin/env python3
"""Builds engine/rules/packs/redundancy.json and docs/rule-packs/redundancy.md from the family modules here.
Every positive/negative is checked as the rule is added (core.py); e2e.py then runs them through the built engine."""
import json, pathlib, sys
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import core
import fam_pairs, fam_verbs, fam_dims, fam_acro, fam_misc, fam_comp, fam_prep, fam_neg, fam_extra

FAMILIES = [fam_pairs, fam_verbs, fam_dims, fam_acro, fam_misc, fam_extra, fam_comp, fam_prep, fam_neg]

# (section, construction, id prefixes or exact ids)
MAP = [
    ('Modifier plus a noun that repeats it',
     'end result, final outcome, final conclusion / culmination, past history / precedent / memories / track record, previous history, '
     'future plans, advance warning / preview, close proximity, basic fundamentals / essentials, core fundamentals, essential necessities, '
     'free gift / giveaway / complimentary, unexpected surprise, new innovation / invention, true fact, general consensus, consensus of '
     'opinion, whole entire, various different, sufficient / adequate enough, dead corpse, empty void / vacuum, frozen ice, sworn affidavit / '
     'oath, armed gunman, unmarried bachelor, widow woman, female actress / waitress / heroine / princess / widow, former ex-, illegal '
     'smuggling / poaching, temporary reprieve / stopgap / interim, joint collaboration, universal panacea, usual custom, my own personal '
     'opinion, and others (a/an follows the word that is left: an `_art` rule fixes "an end result" to "a result")', ('redund.pair.',)),
    ('Verb plus a particle it already contains',
     'return / revert / reply / respond / restore / regain / rewind / retreat / reclaim / retrieve / recover / refund / repay / reimburse back; repeat / '
     'reiterate / recur / reoccur again; ascend up, descend down, proceed / progress / advance forward; collaborate / cooperate / '
     'combine / join (base form only) / merge / unite / unify / consolidate / assemble / converge / congregate / fuse / coalesce / '
     'amalgamate / team up together; exit out (of); enter inside (of); protrude out (of); plunge / plummet / dwindle down; skyrocket up; reduce down; '
     'separate apart; over-exaggerate; visualize / imagine in your mind; oscillate / vacillate / alternate back and forth; '
     'foresee / predict / forecast / anticipate in advance; from whence', ('redund.verb.',)),
    ('Adjective plus the dimension it names',
     '"blue in color", "small in size", "oval in shape", "light in weight", "tall in height", "long in length", "narrow in width", '
     '"shallow in depth", "old in age", "few in number", "cold in temperature", "cheap in price", "fast in speed", "loud in volume", '
     '"salty in taste", "smooth in texture", "brief in duration", "strong in strength"', ('redund.dim.',)),
    ('Acronym followed by the word it ends in',
     'ATM machine, PIN number, HIV virus, AIDS syndrome, LCD display, LED diode, ISBN number, VIN number, GPS system, RAM / ROM memory, '
     'LAN / WAN / VPN network, DNS system, UPC code, ISP provider, FAQ questions, GUI / CLI / API interface, CPU processor, OCR recognition, '
     'SMS message, RIP in peace. Acronyms are matched in capitals only, so "pin number 3" and "ram memory" in a lowercase sense stay',
     ('redund.acro.',)),
    ('Fixed phrases',
     'each and every, in spite of the fact that, "7 am in the morning" / "6 p.m. in the evening", consecutive ... in a row, both of the two, "about 50 or so", minimum of at least, knots per hour (after a number), both ... as well as (mid-sentence), postponed until a '
     'later date, kindly please / please kindly, also too / also as well / too as well / as well too, enclosed / attached herewith, '
     'cacophony of sounds, round circle, same identical, pre-order in advance, retry / recheck / revisit / reconsider again, please RSVP',
     ('redund.misc.', 'redund.time.')),
    ('Intensified absolutes',
     'will completely eliminate / eradicate / annihilate / obliterate (only after an auxiliary with no "not" between), completely / '
     'totally unique / unanimous / identical, exactly identical, most optimum, more superior, more inferior',
     ('redund.abs.',)),
    ('Doubled comparatives and superlatives',
     'the -er and -est forms the base rules and the modifiers pack do not list: more cleaner, more costlier, more crazier, more fresher, '
     'more bolder ...; most coolest, most boldest ... (341 adjectives, each as comparative and superlative, in 18 grouped rules; forms that are also nouns, such as '
     '"cleaner", "cooler", "thinner", "dimmer", "tamer", are judged only at the end of a clause or before a function word)',
     ('redund.comp.',)),
    ('Doubled prepositions',
     'off of, alongside of, atop of, where is the bathroom at (place nouns only), where are you going to',
     ('redund.prep.',)),
    ('Doubled negatives with hardly / barely / scarcely',
     'isn\'t / aren\'t / wasn\'t / weren\'t / hasn\'t / haven\'t / hadn\'t / shouldn\'t hardly; didn\'t / doesn\'t hardly + verb '
     '(regular and about 30 irregular verbs); hardly nowhere',
     ('redund.neg.',)),
]

LEFT_OUT = [
    '**the reason is because, the reason why, reason for why**: clauses pack (`clause.relative.reason_for_why`) and the reason-because rules there.',
    '**so therefore, but however, but nevertheless-style stacks, addition_also, such as for example, as well as also**: clauses pack (`clause.connector.*`, `clause.frame.*`).',
    '**both ... as well as at the start of a sentence**: `clause.correlative.both_as_well_as` in the clauses pack; `redund.misc.both_as_well_as_mid` takes the mid-sentence form so the two never overlap.',
    '**like as if**: `clause.conditional.like_as_if` in the clauses pack.',
    '**and etc, etc etc**: `confuse.eg_and_etc2` in the confusions pack.',
    '**very unique, more unique, most unique, very perfect, very absolute, very identical, very universal, very impossible, very infinite**: modifiers pack (`mod.very_*_abs`, `mod.more_unique`, `mod.most_unique`).',
    '**more better, more easier, more faster, more clearer, most easiest, most fastest, most best, more worse, more bigger, more taller, more higher**: `grammar.phrase.*`, `grammar.more_comparative`, `grammar.most_superlative`, `usage.double_comparative` and about 180 `mod.more_*` / `mod.most_*` rules. The pack adds only the adjectives those leave out.',
    '**can\'t hardly, couldn\'t barely, won\'t scarcely, don\'t hardly (I/we/you/they), hardly never, hardly nobody / nothing / none / any**: modifiers pack (`mod.cant_hardly`, `mod.couldt_hardly`, `mod.willt_hardly`, `mod.wouldt_hardly`, `mod.dont_hardly`, `mod.hardly_*`).',
    '**in the month of May, in the year 1998, estimated at about 500, on the date of**: wordy but often chosen on purpose ("in the year 1845" is formal register; an estimate can still be rounded), so a suggestion would be a false alarm on correct text.',
    '**in order to, at this point in time, due to the fact that, prior to, for the purpose of, at the present time, in the event that, a large number of, on a daily basis, at a later date**: wordiness, owned by the tone-mode `concise.*` rules and the clarity-style pack. Only "in spite of the fact that" (named in the brief) has a Fix-mode rule here.',
    '**doubled words (in in, to to, a a)**: `grammar.repeated_word` and `prep.double_*`.',
    '**connect together, link together, gather together, mix together, meet together, stick together, pool together, close together, cluster together**: idiomatic or meaning-bearing ("gathered together in the hall"); no rule.',
    '**rise up, fall down, sit down, stand up, lift up, climb up, kneel down, bend down, hurry up, finish up, continue on, start off, enter into, refer back, bounce back, give back, come back again**: standard phrasal verbs; the particle carries direction or aspect.',
    '**joint partnership, sum total, old adage, first debut, exact duplicate ("exact" contrasts with "near" duplicates), advance planning, advance reservations (terms of art in planning and booking), added bonus, annual anniversary, brief moment, brief summary, specific example, emergency situation, crisis situation, safe haven, unsolved mystery, terrible tragedy, major breakthrough, mass exodus, true story, past experience, free of charge, advance notice, honest truth, personal opinion, personal friend, mutual cooperation, mutual agreement**: idiomatic or carries a contrast ("my personal opinion, not my employer\'s"); a suggestion would be a false alarm on correct text.',
    '**exact same, same exact, exact opposite, exact replica, all-time record, one and only, any and all, null and void, first and foremost, safe and sound, pick and choose, cease and desist, various and sundry, full and complete**: emphatic idioms and legal doublets that writers use on purpose.',
    '**absolutely essential / necessary / vital, totally unnecessary, very essential**: intensifier habit, not a fixed pleonasm; the modifiers pack decides the intensifier policy.',
    '**continue to remain / persist, still remains, start to begin**: the fix needs the verb re-inflected ("continues to remain" to "remains"); a regex cannot do it safely.',
    '**knots per hour**: included, but only after a preposition and a number, because "ties 40 knots per hour" is a real rate of knotting.',
    '**where are you at, where it\'s at, where I\'m at**: "where ... at" is a status question as often as a place question; only a place noun ("Where is the bathroom at?") is a rule.',
    '**inside of, outside of, up until, over with, round about, near to, off from**: accepted in one variety or carrying a distinct meaning ("outside of" = except).',
    '**PIN code, SIM card, ZIP code, PAN card, IFSC code, IMEI number, SAT test, PDF format, URL link, NEFT transfer**: the last word names a different thing or the whole phrase is the standard term.',
    '**re- verbs plus again (restart again, reopen again, rewrite again, redo again, reread again, rerun again)**: "again" can mark a second repetition; only the ten verbs where it cannot (retry, recheck, revisit, rethink, reconsider, resubmit, reapply, re-evaluate, re-examine, reassess) have a rule.',
]


def write_doc(root):
    lines = ['# Redundancy pack: coverage map', '',
             f'`engine/rules/packs/redundancy.json` holds {len(core.RULES)} rules (id prefix `redund.`), generated by '
             '`scripts/redundancy-pack/build.py` (`python3 scripts/redundancy-pack/build.py` rewrites the JSON and this file). Every rule has a '
             'required literal, a positive and a negative example written for it, and word guards that refuse a hyphen or apostrophe on either side '
             '("back-end", "free gift\'s", "non-free gift"). Pleonasms are Style suggestions (0.72 to 0.8), "off of" and "alongside of" included (colloquial American English, not an error); doubled '
             'comparatives, doubled negatives, "atop of" and a place noun followed by "at" are Grammar. `scripts/redundancy-pack/e2e.py` runs every '
             'example through the built engine.', '',
             'Rules that delete the first word of a pair keep the article right: "an end result" to "a result", "a new innovation" to "an '
             'innovation" are separate `_art` rules, and the plain rule never fires after "a" or "an".', '']
    for sec, cons, prefixes in MAP:
        ids = [r['id'] for r in core.RULES if r['id'].startswith(prefixes)]
        shown = ', '.join(f'`{i[len("redund."):]}`' for i in ids[:8]) + (f' and {len(ids) - 8} more' if len(ids) > 8 else '')
        lines += [f'## {sec}', '', '| Construction | Rules |', '|---|---|', f'| {cons.replace("|", "/")} | {len(ids)} rule(s): {shown} |', '']
    lines += ['## Covered by base rules and other packs, deliberately not repeated', '']
    lines += [f'- {t}' for t in LEFT_OUT]
    lines += ['']
    (root / 'docs/rule-packs/redundancy.md').write_text('\n'.join(lines))


def main():
    for f in FAMILIES:
        f.build()
    if core.ERRORS:
        print('\n'.join(core.ERRORS))
        sys.exit(f'{len(core.ERRORS)} rule(s) failed their own examples')
    root = HERE.parent.parent
    out = root / 'engine/rules/packs/redundancy.json'
    out.write_text(json.dumps(core.RULES, ensure_ascii=False, indent=2) + '\n')
    (HERE / 'expected.json').write_text(json.dumps(core.EXPECTED, ensure_ascii=False, indent=1))
    write_doc(root)
    print(len(core.RULES), 'rules ->', out)


if __name__ == '__main__':
    main()
