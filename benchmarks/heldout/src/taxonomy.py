#!/usr/bin/env python3
"""Regenerate ../TAXONOMY.md from the built jsonl files. Run after build.py."""
import collections
import json
import os

OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFS = {
    "real_word": ("Typos and confusions that produce another real English word, so a dictionary lookup cannot catch them.", {
        "keyboard_slip": "One-key substitution that lands on a real word (out/but, form/from, fro/for, wit/with, cam/can).",
        "letter_drop_add": "A dropped, added or swapped letter that forms a real word (thing/think, sill/still, of/off, an/and).",
        "homophone": "Same-sounding words (there/their/they're, your/you're, its/it's, to/too/two, whole/hole, week/weak).",
        "near_homophone": "Similar-sounding or similar-looking pairs (lose/loose, quite/quiet, then/than, affect/effect, accept/except).",
    }),
    "spelling": ("Non-word misspellings and word-boundary errors.", {
        "transposition": "Two adjacent letters swapped (teh, waht, recieve, freind).",
        "doubled_dropped_letter": "A doubled letter dropped or a single letter doubled (untill, finaly, occured, comming).",
        "phonetic": "Spelled by sound (shud, pritty, Wensday, seperate, docter).",
        "common_misspelling": "Classic high-frequency misspellings (definately, maintainance, questionaire, liason).",
        "joined_words": "Two words written as one (alot, infront, incase, awhile, phrasal verbs like login/setup/backup used as verbs).",
        "split_words": "One word written as two (some times, no where, every one, with out, data base).",
    }),
    "agreement": ("Number/person agreement.", {
        "subject_verb": "Adjacent subject-verb mismatch, including indefinite pronouns and questions (she don't, everyone are, where is my keys).",
        "subject_verb_distance": "Agreement across an intervening phrase or clause (the list of vendors are, a number of customers has).",
        "there_is_are": "Existential there/here with the wrong number (there's two meetings, is there any snacks).",
        "pronoun_antecedent": "Pronoun disagrees with its antecedent in number or gender (my jeans shrank so I can't wear it).",
        "this_these": "Demonstrative disagrees with its noun (this cookies, these information).",
    }),
    "verb_form": ("Wrong verb forms.", {
        "participle": "Past participle vs simple past and irregular forms (have went, I seen, brang, buyed).",
        "modal": "Modal constructions (should of, must went, can able to, suppose to, use to).",
        "do_support": "Wrong form after do/does/did or missing do-support (did you went, does it works).",
        "tense_consistency": "Tense conflicts with a time marker or surrounding clause (yesterday I go, I have seen her yesterday).",
        "gerund_infinitive": "Gerund/infinitive choice and stative progressive misuse (look forward to see, I am agree, is having two kids).",
    }),
    "articles_determiners": ("Articles and quantifiers.", {
        "a_an": "a/an chosen by spelling instead of sound (a hour, an university, an US-based).",
        "missing_article": "Required article omitted (I'm going to store, she's teacher).",
        "extra_article": "Article inserted where English uses none (the life is short, a good news, an advice).",
        "quantifier": "much/many, less/fewer, few/little, every/all, amount/number, a lot vs a lot of.",
    }),
    "prepositions": ("Preposition errors.", {
        "wrong_preposition": "Wrong preposition (married with, depend of, good in math, since three years).",
        "missing_preposition": "Required preposition dropped (waiting you, listen me, worried about).",
        "extra_preposition": "Preposition that the verb does not take (discuss about, contact to, return back).",
    }),
    "word_choice_usage": ("Usage and word-choice errors that are grammatical slips rather than typos.", {
        "pronoun_case": "Subject/object/reflexive case and who/whom/which (me and Sarah are, between you and I, contact myself).",
        "confused_usage": "Non-standard or confused usage (irregardless, could care less, lay/lie, lend/borrow, good/well). Some are style-level.",
        "comparative_adjective": "Double comparatives/superlatives and irregular comparatives (more better, gooder, most easiest).",
        "participle_adjective": "-ed/-ing participial adjective confusion (I'm boring for I'm bored, very disappointing with the delivery).",
    }),
    "missing_extra_word": ("Dropped, doubled, or superfluous words.", {
        "missing_word": "A required word is missing (I going, let me if, thanks the update).",
        "doubled_word": "The same word typed twice (the the, to to, can you can you).",
        "extra_word": "A superfluous word (although ... but, the guy he lives, made me to wait).",
    }),
    "word_order": ("Word-order errors.", {
        "question_order": "Missing inversion in direct questions or inversion in embedded questions (where you are?, do you know where is the bathroom).",
        "adverb_placement": "Misplaced adverbs, objects, 'enough', and adjective order (I go always, enough big, a leather new jacket).",
    }),
    "punctuation": ("Punctuation errors.", {
        "comma_splice": "Two independent clauses joined by a comma (mostly email/doc register, with conjunctive adverbs like however).",
        "intro_comma": "Missing comma after an introductory word, phrase or clause, or after yes/no.",
        "comma_misuse": "Missing comma before a coordinating conjunction joining long clauses, commas in city/state and dates, and unnecessary commas (compound predicates, between subject and verb, after a verb or preposition).",
        "apostrophe": "Plural with an apostrophe, missing or misplaced possessive apostrophe (kid's for kids, Sarahs laptop, Johnson's for Johnsons').",
        "end_punctuation": "Missing final period/question mark, a statement ending in '?', or a question ending in '.'.",
        "spacing": "Space before punctuation or missing space after it.",
        "double_punctuation": "Accidental doubled or mixed punctuation (,, .. ?. .!).",
        "hyphenation": "Missing hyphen in compound modifiers or numbers, and wrong hyphens in predicate/adverb compounds and phrasal verbs.",
        "semicolon_colon": "Semicolon where a colon or comma is needed, colon after a verb/preposition, missing colon.",
        "quotes": "Unclosed quotation marks (curly and straight).",
    }),
    "capitalization": ("Capitalization errors.", {
        "sentence_start": "Lowercase sentence start (including inside quotes).",
        "after_colon": "Capital letter after a colon that introduces a list rather than a full sentence (three options: Keep, merge, or delete).",
        "pronoun_i": "Lowercase 'i' and its contractions (i'm, i’ll).",
        "proper_noun": "Lowercase names, places, brands, languages, nationalities, holidays (paris, google, github, spanish).",
        "days_months": "Lowercase days and months, and capitalized seasons.",
    }),
    "run_on_fragment": ("Sentence-boundary errors.", {
        "run_on": "Fused sentences with no punctuation between independent clauses.",
        "fragment": "A subordinate clause or phrase punctuated as its own sentence (I left early. Because I was tired.).",
    }),
    "contractions": ("Contraction apostrophe errors.", {
        "missing_apostrophe": "Apostrophe omitted (dont, cant, im, ive, didnt, whats), including inside text that otherwise uses curly apostrophes (the reference keeps the curly style; the straight form is an alternative).",
        "misplaced_apostrophe": "Apostrophe in the wrong place or replaced by ';' or '\"' (did'nt, I'am, don;t).",
    }),
    "mixed": ("Realistic messages with exactly two errors from different families.", {
        "chat": "Chat/text messages.",
        "email": "Work email.",
        "doc": "Documentation and reports.",
        "social": "Social posts.",
        "technical": "Engineering chat, PRs and tickets.",
    }),
}

CLEAN_DEFS = {
    "tricky_real_word": "Correct uses of words that are common real-word-error targets ('working out fine', 'sold out, which is fine by me', form, of, on, then/than, affect as a noun, effect as a verb).",
    "its_their_your": "Correct its/it's, their/there/they're, your/you're, whose/who's, and contractions that are also words (we'll/well, he'll/hell).",
    "informal_fragments": "Grammatical-in-context fragments and sign-offs typical of chat and email ('Sounds good.', 'Coffee later?', 'Best,').",
    "names_brands": "Personal names, places and product names that look like typos (Siobhan, Niamh, Jakob, Thom, eBay, iPad, Figma, Venmo as a verb).",
    "code_identifiers": "Technical text with code spans, identifiers, paths, flags, versions, URLs, emails and units.",
    "apostrophes_quotes": "Correct curly and straight apostrophes and quotes, plural/possessive edge cases (’80s, rock ’n’ roll, A’s, James’s, the Smiths’).",
    "punctuation_correct": "Correct punctuation that a checker might wrongly 'fix' (optional Oxford comma, no comma before compound predicates, short intro phrases without a comma, predicate 'well known', noun 'setup' vs verb 'set up', e.g./i.e., dashes).",
    "grammar_tricky": "Correct but often mis-flagged grammar (subjunctive, data show/shows, none is/are, singular they, ending with a preposition, fewer/less used correctly, idioms).",
    "email_doc_general": "Ordinary correct email and documentation sentences (many are corrected versions of error items).",
    "social_posts": "Correct social posts with emoji, hashtags and stylistic fragments.",
    "en_gb": "British spelling and usage (colour, organise, cancelled, licence, practise, the team are, at the weekend). Marked dialect en-GB.",
    "chat_general": "Ordinary correct chat messages.",
    "chat_no_period": "Chat messages without terminal punctuation. Omitting the final period is normal in chat and should not be flagged.",
}


def main():
    errors = [json.loads(l) for l in open(os.path.join(OUT, "errors.jsonl"), encoding="utf-8")]
    clean = [json.loads(l) for l in open(os.path.join(OUT, "clean.jsonl"), encoding="utf-8")]
    cat = collections.Counter(r["category"] for r in errors)
    sub = collections.Counter((r["category"], r["subcategory"]) for r in errors)
    csub = collections.Counter(r["subcategory"] for r in clean)
    reg_e = collections.Counter(r["register"] for r in errors)
    reg_c = collections.Counter(r["register"] for r in clean)
    two = sum(len(r["spans"]) == 2 for r in errors)
    alts = sum(bool(r["alternatives"]) for r in errors)
    style = sum(r.get("severity") == "style" for r in errors)
    gb = sum(r.get("dialect") == "en-GB" for r in clean)

    L = []
    L.append("# Held-out evaluation corpus: taxonomy\n")
    L.append(f"`errors.jsonl`: **{len(errors)}** items with errors. `clean.jsonl`: **{len(clean)}** correct sentences for measuring false positives.\n")
    L.append("Every item was written by hand for this corpus. Nothing was taken from the existing `benchmarks/*.jsonl` sets, the checker's rules, its lexicons or its generator scripts, and none of those were consulted while writing. The corpus is meant to stay held out: do not tune rules against individual items.\n")
    L.append("## Error categories\n")
    L.append("| Category / subcategory | Items | Definition |")
    L.append("|---|---:|---|")
    for c, (cdef, subs) in DEFS.items():
        L.append(f"| **{c}** | **{cat.get(c, 0)}** | {cdef} |")
        for s, sdef in subs.items():
            L.append(f"| &nbsp;&nbsp;{c}/{s} | {sub.get((c, s), 0)} | {sdef} |")
    known = {(c, s) for c, (_, subs) in DEFS.items() for s in subs}
    extra = [k for k in sub if k not in known]
    assert not extra, f"undocumented subcategories: {extra}"
    L.append(f"| **total** | **{len(errors)}** | |\n")
    L.append("## Clean (false-positive) categories\n")
    L.append("| Subcategory | Items | Definition |")
    L.append("|---|---:|---|")
    for s, d in CLEAN_DEFS.items():
        L.append(f"| {s} | {csub.get(s, 0)} | {d} |")
    assert not set(csub) - set(CLEAN_DEFS), "undocumented clean subcategories"
    L.append(f"| **total** | **{len(clean)}** | |\n")
    L.append("## Registers\n")
    L.append("| Register | Error items | Clean items |")
    L.append("|---|---:|---:|")
    for r in ("chat", "email", "doc", "social", "technical"):
        L.append(f"| {r} | {reg_e.get(r, 0)} | {reg_c.get(r, 0)} |")
    L.append("")
    L.append("## Item format\n")
    L.append("Error items: `id`, `category`, `subcategory`, `input`, `reference` (the minimal correction), `alternatives` (other acceptable full-sentence corrections), `spans` (`start`/`end` are UTF-16 code-unit offsets into `input`; `original` is the text at that range; `fix` is its replacement; an empty `original` is an insertion and an empty `fix` is a deletion), `register`, `source` (always `authored`), and optionally `severity: \"style\"` for usage points that some style guides accept (could care less, try and, anyways, less than ten people). Applying the spans to `input` in order yields `reference` exactly.\n")
    L.append("Clean items: `id`, `category` (`clean`), `subcategory`, `input`, `register`, `source`, and `dialect: \"en-GB\"` on British-English items.\n")
    L.append(f"Stats: {two} error items have two spans (all `mixed` items plus a few with two errors of the same kind); {alts} items list alternatives; {style} are style-level; {gb} clean items are en-GB.\n")
    L.append("## How items were authored\n")
    L.append("- Each sentence was written by hand to sound like something a person would actually type into Slack, a text thread, an email, a work doc, a social post or an engineering channel. They include contractions, curly and straight apostrophes and quotes, names, numbers, prices, times, URLs, code identifiers and the occasional emoji.")
    L.append("- The error was written into the sentence the way a writer would make it: keyboard slips, phonetic spellings, autocorrect-style real-word swaps, and common native and non-native grammar mistakes. Template expansion over word lists was not used. Many inputs are 1 sentence; some are 2 or 3.")
    L.append("- Each item has one error. Items in `mixed` have exactly two errors from different families. The rest of the sentence is meant to be correct for its register. Chat items may use casual fragments and comma-separated interjections, but they don't contain other spelling, capitalization or agreement errors. Comma splices in non-punctuation items were removed.")
    L.append("- The reference is the smallest edit that makes the sentence correct. When there is more than one reasonable fix (period vs semicolon for a splice, `should have` vs `should've`, US vs UK spelling, `I'm` vs `I am`), the other options are listed in `alternatives`.")
    L.append("- Items whose 'error' is accepted by mainstream usage guides were dropped or marked `severity: style`, for example singular 'they' for a person, 'excited for', 'on the same team', Oxford comma either way, and a comma after a short introductory phrase.")
    L.append("- The clean set contains hard negatives: correct sentences close to the error patterns (often the corrected form of an error item), names and product names, code, British spellings, and chat without terminal punctuation.")
    L.append("- Items were authored in inline markup (`src/errors/*.txt`, `src/clean/*.txt`, e.g. `I don’t think this is working, [[out=>but]] fine.`) and compiled with `src/build.py`, which computes UTF-16 spans and expands alternatives. `src/taxonomy.py` regenerates this file. A validator checked every line: it is valid JSON, its span offsets match `original`, applying the spans gives `reference`, ids are unique, there are no duplicate inputs across both files, and no markup or doubled spaces are left over.")
    L.append("- The author removed debatable items while writing. Second readers reviewed error items 1-1600 and their clear fixes were applied: debatable inputs dropped, leftover comma splices and wrong references fixed. The last ~750 error items and the clean set have not yet had a second-reader pass.\n")
    L.append("## Known limitations\n")
    L.append("- The corpus has one author, so the error distribution reflects that author's idea of realistic errors, not frequencies measured from real logs.")
    L.append("- References follow US spelling by default. British spellings in error items are accepted through `alternatives` where relevant.")
    L.append("- Chat end-punctuation: missing final periods in chat count as correct (`clean/chat_no_period`). A missing `?` on a chat question is annotated as an error (`punctuation/end_punctuation`). Scorers may choose to treat chat end-punctuation as optional.")
    L.append("- The single reference does not list every possible correction. A checker suggestion that differs from both `reference` and `alternatives` may still be valid and should be reviewed by a person.")
    open(os.path.join(OUT, "TAXONOMY.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("wrote TAXONOMY.md")


if __name__ == "__main__":
    main()
