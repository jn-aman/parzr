# Held-out evaluation corpus: taxonomy

`errors.jsonl`: **2329** items with errors. `clean.jsonl`: **905** correct sentences for measuring false positives.

Every item was written by hand for this corpus. Nothing was taken from the existing `benchmarks/*.jsonl` sets, the checker's rules, its lexicons or its generator scripts, and none of those were consulted while writing. The corpus is meant to stay held out: do not tune rules against individual items.

## Error categories

| Category / subcategory | Items | Definition |
|---|---:|---|
| **real_word** | **216** | Typos and confusions that produce another real English word, so a dictionary lookup cannot catch them. |
| &nbsp;&nbsp;real_word/keyboard_slip | 50 | One-key substitution that lands on a real word (out/but, form/from, fro/for, wit/with, cam/can). |
| &nbsp;&nbsp;real_word/letter_drop_add | 48 | A dropped, added or swapped letter that forms a real word (thing/think, sill/still, of/off, an/and). |
| &nbsp;&nbsp;real_word/homophone | 65 | Same-sounding words (there/their/they're, your/you're, its/it's, to/too/two, whole/hole, week/weak). |
| &nbsp;&nbsp;real_word/near_homophone | 53 | Similar-sounding or similar-looking pairs (lose/loose, quite/quiet, then/than, affect/effect, accept/except). |
| **spelling** | **243** | Non-word misspellings and word-boundary errors. |
| &nbsp;&nbsp;spelling/transposition | 40 | Two adjacent letters swapped (teh, waht, recieve, freind). |
| &nbsp;&nbsp;spelling/doubled_dropped_letter | 41 | A doubled letter dropped or a single letter doubled (untill, finaly, occured, comming). |
| &nbsp;&nbsp;spelling/phonetic | 41 | Spelled by sound (shud, pritty, Wensday, seperate, docter). |
| &nbsp;&nbsp;spelling/common_misspelling | 40 | Classic high-frequency misspellings (definately, maintainance, questionaire, liason). |
| &nbsp;&nbsp;spelling/joined_words | 41 | Two words written as one (alot, infront, incase, awhile, phrasal verbs like login/setup/backup used as verbs). |
| &nbsp;&nbsp;spelling/split_words | 40 | One word written as two (some times, no where, every one, with out, data base). |
| **agreement** | **203** | Number/person agreement. |
| &nbsp;&nbsp;agreement/subject_verb | 43 | Adjacent subject-verb mismatch, including indefinite pronouns and questions (she don't, everyone are, where is my keys). |
| &nbsp;&nbsp;agreement/subject_verb_distance | 41 | Agreement across an intervening phrase or clause (the list of vendors are, a number of customers has). |
| &nbsp;&nbsp;agreement/there_is_are | 39 | Existential there/here with the wrong number (there's two meetings, is there any snacks). |
| &nbsp;&nbsp;agreement/pronoun_antecedent | 38 | Pronoun disagrees with its antecedent in number or gender (my jeans shrank so I can't wear it). |
| &nbsp;&nbsp;agreement/this_these | 42 | Demonstrative disagrees with its noun (this cookies, these information). |
| **verb_form** | **205** | Wrong verb forms. |
| &nbsp;&nbsp;verb_form/participle | 42 | Past participle vs simple past and irregular forms (have went, I seen, brang, buyed). |
| &nbsp;&nbsp;verb_form/modal | 38 | Modal constructions (should of, must went, can able to, suppose to, use to). |
| &nbsp;&nbsp;verb_form/do_support | 41 | Wrong form after do/does/did or missing do-support (did you went, does it works). |
| &nbsp;&nbsp;verb_form/tense_consistency | 41 | Tense conflicts with a time marker or surrounding clause (yesterday I go, I have seen her yesterday). |
| &nbsp;&nbsp;verb_form/gerund_infinitive | 43 | Gerund/infinitive choice and stative progressive misuse (look forward to see, I am agree, is having two kids). |
| **articles_determiners** | **165** | Articles and quantifiers. |
| &nbsp;&nbsp;articles_determiners/a_an | 41 | a/an chosen by spelling instead of sound (a hour, an university, an US-based). |
| &nbsp;&nbsp;articles_determiners/missing_article | 41 | Required article omitted (I'm going to store, she's teacher). |
| &nbsp;&nbsp;articles_determiners/extra_article | 44 | Article inserted where English uses none (the life is short, a good news, an advice). |
| &nbsp;&nbsp;articles_determiners/quantifier | 39 | much/many, less/fewer, few/little, every/all, amount/number, a lot vs a lot of. |
| **prepositions** | **111** | Preposition errors. |
| &nbsp;&nbsp;prepositions/wrong_preposition | 37 | Wrong preposition (married with, depend of, good in math, since three years). |
| &nbsp;&nbsp;prepositions/missing_preposition | 38 | Required preposition dropped (waiting you, listen me, worried about). |
| &nbsp;&nbsp;prepositions/extra_preposition | 36 | Preposition that the verb does not take (discuss about, contact to, return back). |
| **word_choice_usage** | **119** | Usage and word-choice errors that are grammatical slips rather than typos. |
| &nbsp;&nbsp;word_choice_usage/pronoun_case | 39 | Subject/object/reflexive case and who/whom/which (me and Sarah are, between you and I, contact myself). |
| &nbsp;&nbsp;word_choice_usage/confused_usage | 36 | Non-standard or confused usage (irregardless, could care less, lay/lie, lend/borrow, good/well). Some are style-level. |
| &nbsp;&nbsp;word_choice_usage/comparative_adjective | 30 | Double comparatives/superlatives and irregular comparatives (more better, gooder, most easiest). |
| &nbsp;&nbsp;word_choice_usage/participle_adjective | 14 | -ed/-ing participial adjective confusion (I'm boring for I'm bored, very disappointing with the delivery). |
| **missing_extra_word** | **120** | Dropped, doubled, or superfluous words. |
| &nbsp;&nbsp;missing_extra_word/missing_word | 40 | A required word is missing (I going, let me if, thanks the update). |
| &nbsp;&nbsp;missing_extra_word/doubled_word | 41 | The same word typed twice (the the, to to, can you can you). |
| &nbsp;&nbsp;missing_extra_word/extra_word | 39 | A superfluous word (although ... but, the guy he lives, made me to wait). |
| **word_order** | **79** | Word-order errors. |
| &nbsp;&nbsp;word_order/question_order | 41 | Missing inversion in direct questions or inversion in embedded questions (where you are?, do you know where is the bathroom). |
| &nbsp;&nbsp;word_order/adverb_placement | 38 | Misplaced adverbs, objects, 'enough', and adjective order (I go always, enough big, a leather new jacket). |
| **punctuation** | **397** | Punctuation errors. |
| &nbsp;&nbsp;punctuation/comma_splice | 41 | Two independent clauses joined by a comma (mostly email/doc register, with conjunctive adverbs like however). |
| &nbsp;&nbsp;punctuation/intro_comma | 40 | Missing comma after an introductory word, phrase or clause, or after yes/no. |
| &nbsp;&nbsp;punctuation/comma_misuse | 40 | Missing comma before a coordinating conjunction joining long clauses, commas in city/state and dates, and unnecessary commas (compound predicates, between subject and verb, after a verb or preposition). |
| &nbsp;&nbsp;punctuation/apostrophe | 39 | Plural with an apostrophe, missing or misplaced possessive apostrophe (kid's for kids, Sarahs laptop, Johnson's for Johnsons'). |
| &nbsp;&nbsp;punctuation/end_punctuation | 39 | Missing final period/question mark, a statement ending in '?', or a question ending in '.'. |
| &nbsp;&nbsp;punctuation/spacing | 40 | Space before punctuation or missing space after it. |
| &nbsp;&nbsp;punctuation/double_punctuation | 39 | Accidental doubled or mixed punctuation (,, .. ?. .!). |
| &nbsp;&nbsp;punctuation/hyphenation | 40 | Missing hyphen in compound modifiers or numbers, and wrong hyphens in predicate/adverb compounds and phrasal verbs. |
| &nbsp;&nbsp;punctuation/semicolon_colon | 38 | Semicolon where a colon or comma is needed, colon after a verb/preposition, missing colon. |
| &nbsp;&nbsp;punctuation/quotes | 41 | Unclosed quotation marks (curly and straight). |
| **capitalization** | **165** | Capitalization errors. |
| &nbsp;&nbsp;capitalization/sentence_start | 37 | Lowercase sentence start (including inside quotes). |
| &nbsp;&nbsp;capitalization/after_colon | 3 | Capital letter after a colon that introduces a list rather than a full sentence (three options: Keep, merge, or delete). |
| &nbsp;&nbsp;capitalization/pronoun_i | 40 | Lowercase 'i' and its contractions (i'm, i’ll). |
| &nbsp;&nbsp;capitalization/proper_noun | 42 | Lowercase names, places, brands, languages, nationalities, holidays (paris, google, github, spanish). |
| &nbsp;&nbsp;capitalization/days_months | 43 | Lowercase days and months, and capitalized seasons. |
| **run_on_fragment** | **78** | Sentence-boundary errors. |
| &nbsp;&nbsp;run_on_fragment/run_on | 39 | Fused sentences with no punctuation between independent clauses. |
| &nbsp;&nbsp;run_on_fragment/fragment | 39 | A subordinate clause or phrase punctuated as its own sentence (I left early. Because I was tired.). |
| **contractions** | **88** | Contraction apostrophe errors. |
| &nbsp;&nbsp;contractions/missing_apostrophe | 59 | Apostrophe omitted (dont, cant, im, ive, didnt, whats), including inside text that otherwise uses curly apostrophes (the reference keeps the curly style; the straight form is an alternative). |
| &nbsp;&nbsp;contractions/misplaced_apostrophe | 29 | Apostrophe in the wrong place or replaced by ';' or '"' (did'nt, I'am, don;t). |
| **mixed** | **140** | Realistic messages with exactly two errors from different families. |
| &nbsp;&nbsp;mixed/chat | 39 | Chat/text messages. |
| &nbsp;&nbsp;mixed/email | 31 | Work email. |
| &nbsp;&nbsp;mixed/doc | 29 | Documentation and reports. |
| &nbsp;&nbsp;mixed/social | 24 | Social posts. |
| &nbsp;&nbsp;mixed/technical | 17 | Engineering chat, PRs and tickets. |
| **total** | **2329** | |

## Clean (false-positive) categories

| Subcategory | Items | Definition |
|---|---:|---|
| tricky_real_word | 125 | Correct uses of words that are common real-word-error targets ('working out fine', 'sold out, which is fine by me', form, of, on, then/than, affect as a noun, effect as a verb). |
| its_their_your | 49 | Correct its/it's, their/there/they're, your/you're, whose/who's, and contractions that are also words (we'll/well, he'll/hell). |
| informal_fragments | 70 | Grammatical-in-context fragments and sign-offs typical of chat and email ('Sounds good.', 'Coffee later?', 'Best,'). |
| names_brands | 70 | Personal names, places and product names that look like typos (Siobhan, Niamh, Jakob, Thom, eBay, iPad, Figma, Venmo as a verb). |
| code_identifiers | 60 | Technical text with code spans, identifiers, paths, flags, versions, URLs, emails and units. |
| apostrophes_quotes | 40 | Correct curly and straight apostrophes and quotes, plural/possessive edge cases (’80s, rock ’n’ roll, A’s, James’s, the Smiths’). |
| punctuation_correct | 77 | Correct punctuation that a checker might wrongly 'fix' (optional Oxford comma, no comma before compound predicates, short intro phrases without a comma, predicate 'well known', noun 'setup' vs verb 'set up', e.g./i.e., dashes). |
| grammar_tricky | 133 | Correct but often mis-flagged grammar (subjunctive, data show/shows, none is/are, singular they, ending with a preposition, fewer/less used correctly, idioms). |
| email_doc_general | 101 | Ordinary correct email and documentation sentences (many are corrected versions of error items). |
| social_posts | 50 | Correct social posts with emoji, hashtags and stylistic fragments. |
| en_gb | 50 | British spelling and usage (colour, organise, cancelled, licence, practise, the team are, at the weekend). Marked dialect en-GB. |
| chat_general | 60 | Ordinary correct chat messages. |
| chat_no_period | 20 | Chat messages without terminal punctuation. Omitting the final period is normal in chat and should not be flagged. |
| **total** | **905** | |

## Registers

| Register | Error items | Clean items |
|---|---:|---:|
| chat | 1642 | 528 |
| email | 290 | 101 |
| doc | 268 | 146 |
| social | 43 | 52 |
| technical | 86 | 78 |

## Item format

Error items: `id`, `category`, `subcategory`, `input`, `reference` (the minimal correction), `alternatives` (other acceptable full-sentence corrections), `spans` (`start`/`end` are UTF-16 code-unit offsets into `input`; `original` is the text at that range; `fix` is its replacement; an empty `original` is an insertion and an empty `fix` is a deletion), `register`, `source` (always `authored`), and optionally `severity: "style"` for usage points that some style guides accept (could care less, try and, anyways, less than ten people). Applying the spans to `input` in order yields `reference` exactly.

Clean items: `id`, `category` (`clean`), `subcategory`, `input`, `register`, `source`, and `dialect: "en-GB"` on British-English items.

Stats: 145 error items have two spans (all `mixed` items plus a few with two errors of the same kind); 143 items list alternatives; 13 are style-level; 50 clean items are en-GB.

## How items were authored

- Each sentence was written by hand to sound like something a person would actually type into Slack, a text thread, an email, a work doc, a social post or an engineering channel. They include contractions, curly and straight apostrophes and quotes, names, numbers, prices, times, URLs, code identifiers and the occasional emoji.
- The error was written into the sentence the way a writer would make it: keyboard slips, phonetic spellings, autocorrect-style real-word swaps, and common native and non-native grammar mistakes. Template expansion over word lists was not used. Many inputs are 1 sentence; some are 2 or 3.
- Each item has one error. Items in `mixed` have exactly two errors from different families. The rest of the sentence is meant to be correct for its register. Chat items may use casual fragments and comma-separated interjections, but they don't contain other spelling, capitalization or agreement errors. Comma splices in non-punctuation items were removed.
- The reference is the smallest edit that makes the sentence correct. When there is more than one reasonable fix (period vs semicolon for a splice, `should have` vs `should've`, US vs UK spelling, `I'm` vs `I am`), the other options are listed in `alternatives`.
- Items whose 'error' is accepted by mainstream usage guides were dropped or marked `severity: style`, for example singular 'they' for a person, 'excited for', 'on the same team', Oxford comma either way, and a comma after a short introductory phrase.
- The clean set contains hard negatives: correct sentences close to the error patterns (often the corrected form of an error item), names and product names, code, British spellings, and chat without terminal punctuation.
- Items were authored in inline markup (`src/errors/*.txt`, `src/clean/*.txt`, e.g. `I don’t think this is working, [[out=>but]] fine.`) and compiled with `src/build.py`, which computes UTF-16 spans and expands alternatives. `src/taxonomy.py` regenerates this file. A validator checked every line: it is valid JSON, its span offsets match `original`, applying the spans gives `reference`, ids are unique, there are no duplicate inputs across both files, and no markup or doubled spaces are left over.
- The author removed debatable items while writing. Second readers reviewed error items 1-1600 and their clear fixes were applied: debatable inputs dropped, leftover comma splices and wrong references fixed. The last ~750 error items and the clean set have not yet had a second-reader pass.

## Known limitations

- The corpus has one author, so the error distribution reflects that author's idea of realistic errors, not frequencies measured from real logs.
- References follow US spelling by default. British spellings in error items are accepted through `alternatives` where relevant.
- Chat end-punctuation: missing final periods in chat count as correct (`clean/chat_no_period`). A missing `?` on a chat question is annotated as an error (`punctuation/end_punctuation`). Scorers may choose to treat chat end-punctuation as optional.
- The single reference does not list every possible correction. A checker suggestion that differs from both `reference` and `alternatives` may still be valid and should be reviewed by a person.
