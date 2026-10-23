# Agreement pack: coverage map

`engine/rules/packs/agreement.json` holds the subject–verb agreement rules (ids `agree.*`). It is generated from word lists
and construction templates in `scripts/rule-pack-gen/agreement/` (`python3 build.py`, then `python3 check-correct.py`), because most of
the category is lexical: one construction crossed with a list of verbs or nouns. Every rule has its own hand-written positive,
a negative that holds the near misses (imperative, subjunctive, compound subject, title, noun–noun compound, British group
noun), a required literal for the prefilter and a confidence. `correct-*.txt` next to the generator are 470 correct sentences
(written for this pack) that no rule may touch.

The engine already corrects a lot of agreement without any pack: the 84 `Agreement` rules in `grammar.json`, usage rules in
`usage.json`, and token passes in Rust (`grammar.subject_third`, `subject_base`, `subject_copula`, `subject_have`,
`inverted_subject_agreement`, `there_agreement`, `each_of_agreement`, `auxiliary_base`, `infinitive_base`, `modal_base`). The
pack adds only what those miss. The generator measured that: every rule's positive and its word-list variants were run through
the engine **without** the pack, and a rule the engine already fixed completely (95% or more of its variants, for the single-
construction families) was left out (70 of the 1,091 generated rules). What is left either fixes cases the engine leaves alone,
or covers the same construction in clause positions the Rust passes do not reach.

## Coverage

| Construction | Rule ids | Notes |
|---|---|---|
| Pronoun + `be`, present (`I is`, `you is`, `we am`, `he are`, `they is`) | `agree.i_*`, `you_*`, `we_*`, `they_*`, `he_she_it_am`, `he_she_it_are` | mid-clause, after `think`, `if`, `because`…; `Part I is`, `World War I was` are untouched |
| Pronoun + `be`, past (`you was`, `we was`, `they was`, `I were`, `he were`, `weren't`) | `agree.you_was_clause`, `we_were`, `they_were`, `*_wasnt`, `i_were_clause`, `he_she_it_were*`, `*_werent_clause` | `if I were`, `wish he were`, `as it were` untouched; `I/he/she/it were` only in a plain past clause (sentence start, after `because`/`when`/`since`) |
| Pronoun + `have` (`she have`, `I has`, `they has`, `he haven't`) | `agree.he_she_it_have_clause`, `i_you_has_clause`, `we_they_has`, `he_she_it_havent`, `i_you_we_they_hasnt` | `let her have`, `does he have`, `I suggest that he have` untouched |
| Pronoun + `do` (`he don't`, `she do`, `they doesn't`) | `agree.he_she_it_dont_clause`, `he_she_it_do_clause`, `i_you_we_they_doesnt`, `i_you_we_they_does` | `Mike and she don't` (compound) untouched |
| Third-person `-s` on lexical verbs, both directions (`he go`, `she make`, `it cause`; `they goes`, `we uses`) | `agree.sg_<verb>`, `agree.pl_<verb>`, 259 verbs each | irregular `go/do/have` included; `like`, `need`, `dare` (filler / modal), verbs whose bare form is also the past (`read`, `put`, `cut`…) and `come/run/become` are left out; for `it`, verbs that are also nouns after a mistyped `its` (`design`, `order`, `test`…) and adjectives (`clear`, `close`) are left out |
| Modal / `do` + `-s` (`can goes`, `does he goes`, `doesn't makes`) | `agree.modal_s_*`, `dosupport_s_*`, `negaux_s_*` | covered by base `modal_*`, `auxiliary_base`; the pack versions are kept only where the engine missed variants |
| `there is/are/was/were`, `there's` + plural or singular | `agree.there_*`, `agree.is_there_*`, `are_there_*`, `was_there_pl_*`, `were_there_sg_*` | quantifier (`several`, `a few`), number + listed plural noun (units such as `minutes` are never listed: `there's ten minutes left` stays), `a lot of`; `there are a pen and a book` stays (the singular rule only fires when nothing follows but a stop or a preposition) |
| `here is/are`, `where's/what's` + plural | `agree.here_*`, `agree.wh_*` | `Here's the files` is a lower-confidence (0.84) rule: widespread in speech |
| Indefinite pronouns (`everyone are`, `somebody have`, `nobody don't`) | `agree.indef_*` | `let everyone have`, `if everyone were` untouched |
| `each of / either of / neither of` + `them` or a plural noun | `agree.each_of_*`, `agree.eitherneither_of_*` | `either/neither` rules are 0.82: plural verbs are common in edited prose, but the singular is the textbook form |
| `one of the …s are`, `the number of …s are`, `a number of …s is` | `agree.one_of_*`, `the_number_of_*`, `a_number_of_*` | `one of the problems users have` (relative clause) untouched |
| Subject separated by a prepositional phrase | `agree.head_of_*` (`the list of items are`), `plural_head_of_*` (`the results of the test is`), `pl_noun_pp_*`, `sg_noun_pp_*` (`the people in the lobby is`) | only `of`, `in`, `on`; the head list is hand-picked (no `rest`, `majority`, `group`, `variety`, `range`, which take either number) |
| Partitives and percentages (`half of the files is`, `most of the work are`, `a lot of people was`, `percent of the …`) | `agree.partitive_pl_*`, `partitive_sg_*`, `partitive_of_it_*`, `partitive_of_them_*`, plus the quantifiers in `agree.pl_noun_*` | collective nouns are never in the lists |
| `both is`, `both of them is`, `all/most/many of them is` | `agree.both_*`, `agree.both_of_nouns_*`, `agree.partitive_of_them_*` | |
| Listed plural nouns + singular verb (`the students is`, `these scissors is`, `the criteria is`, `People has`) | `agree.pl_noun_<people|work|home|only|classical>*_<verb>`, `agree.bare_plural_*` | 329 plural nouns (and 277 singular, 65 mass nouns in the other families), all non-collective; lower-case only, so `Files`, `Messages`, `Settings` (app names) and titles are safe; words the engine itself mishandles (`phenomena`, `diagnoses`, `tights`…) and nouns that make its possessive pass loop with `has` (`cats has`) are excluded |
| Listed singular nouns + plural verb (`the file are`, `the student have`, `each report don't`) | `agree.sg_noun_<people|work|home>*_<verb>` | `have`/`do` only at a clause start (`does the student have`, `we insist that the student have` untouched); `were` only in a plain past clause |
| Mass nouns (`the information are`, `the news are`, `Mathematics are`, `the money were`) | `agree.sg_noun_mass_*`, `agree.bare_mass_*`, `agree.bare_mass_conj_*` | |
| Classical plurals (`the criteria is`, `the bacteria is`, `the alumni is`) and plural-only nouns (`the scissors is`, `the police is`, `the clothes is`) | in the `pl_noun_*` families | `the data is`, `the media is`, `the staff are`, `the team are` are all left alone (accepted in at least one major variety) |
| Compound subjects with `and` | `agree.pron_and_*` (`he and I is`, `Tom and I has`), `agree.me_and_*` (`Me and Tom was`) | compound subjects whose second noun could be a separate clause (`, Blackburn and he was`) and titles (`The Lion and the Mouse is`) are never touched; noun + noun compounds are left to the engine (it flips the plural back after `I think …`, so a rule here would loop) |
| `either … or`, `neither … nor`, `not only … but also`: nearer subject | `agree.nearer_pl_*`, `nearer_sg_*`, `nearer_pron_*` | the verb follows the nearer noun |
| `along with / as well as / together with` + noun | `agree.along_with_*` | the verb stays with the first noun (0.82) |
| Relative clauses (`those who is`, `anyone who are`, `a person who have`, `the students who is`) | `agree.those_who_*`, `anyone_who_*`, `sg_noun_who_*`, `pl_noun_who_*` | `who`/`which` for plural antecedents only: `that` is left out because the engine rewrites `students that are` to `that is` (bug, see below) |
| Wh-questions with the wrong noun (`What are the problem?`, `Where is the files?`) | `agree.wh_*` | the noun must be followed by a stop or a function word, so `Where is the files folder?` stays |
| Question helpers (`Do he know`, `Does they live`, `Is they`, `Are she`, `Am you`, `Was you`, `Has they`, `Have she`, `Does the files`) | `agree.q_*` | the following word must be a verb or a clear complement, so `Do he and Sam` and `Are he and she coming` stay |
| Gerund subjects (`Learning a language are hard`) | `agree.gerund_subject_*` | `Running shoes are`, `Reading and writing are`, `Learning a language and exploring a culture are` untouched |
| `this are`, `this have`, `these is`, `those was` | `agree.this_*`, `agree.these_*` | clause start only |
| Names (`I think Tom don't`) | `agree.name_*` | not at a sentence start (`Tom, don't forget` is an address) |

## Not rules, and why

- **Quantities and measures** (`five years is`, `ten dollars is enough`, `two plus two is four`): both numbers are standard; a regex cannot tell a measure from a count.
- **Collective nouns** (`the team is/are`, `the committee have`): American singular, British either. Parzr takes the writer's choice and never fights the British setting, so no rule touches them, and the noun lists exclude collectives.
- **`none of`, `any of`, `the majority/rest/remainder of`, `a variety/range/couple/pair of`**: either number is accepted.
- **`what/which` cleft subjects** (`What I need are more hours`): the plural complement is accepted.
- **Titles and names as subjects** (`Harry Potter and the Chamber of Secrets are`, `Les Misérables`): a regex cannot know a title; plural-looking singular proper names (`The Netherlands`, `Wales`, `The Beatles`) differ by variety.
- **Mandative subjunctive** (`I insist that he go`, `it is vital that she have`), `if I were`, `wish he were`, `as it were`, `were he to`: correct, so every rule keeps out of them.
- **`ain't`**: left alone in chat on purpose.
- **Determiner–noun number** (`this files`, `these file`, `many student`): a determiner rule, not an agreement rule.
- **Possessive repair** (`the students needs` for `the students' needs`): not an agreement fix.

## What the pack measured

Without the pack and with it (same build otherwise), Fix mode, American English:

| Check | Without | With |
|---|---|---|
| 30k clean sentences (`mining.jsonl`, `clean: true`): rule hits | 0 | 1, a true error ("the results of our work is written") |
| 123k corrected references of non-clean rows (own check): rule hits | 0 | 28 on 22 rules, all real errors; 4 bare verbs after he/she in past-tense narrative ("he lead his team") get a present-tense fix |
| English 1000 / 2000 sets | exact | exact (1000/1000 and 2000/2000, controls kept) |
| Everyday gate, typing path (2,870 items) | baseline | 1 newly correct, 0 newly wrong |
| Held-out DEV, rules / Smart grammar | 69.3% / 88.2% fixed, 0.0% false alarms | 69.8% / 88.5% fixed, 0.0% false alarms |
| Typo-fuzz DEV, rules / Smart grammar | 80.4% / 85.3% fixed, 0.6% false alarms | 80.4% / 85.3% fixed, 0.6% false alarms |
| Names benchmark | typo recall 96.08%, 2 damaged | identical |
| Own probe of 115 agreement errors | 81 fixed | 103 fixed, none lost |

Cost: the pack is 1.2 MB of JSON; the engine process starts about 0.2 s slower on its first check (300 to 510 ms), a check of one
sentence takes about 1.5 ms longer (2.3 to 3.9 ms), a 6.7k-character passage about 0.45 s longer (135 to 590 ms, more patterns
than the 48-pattern compile cache keeps) and the peak resident memory is about 27 MB higher. Every rule has a prefilter literal
that needs the construction itself (a noun and its verb, `half of the`), so a rule only compiles where its construction occurs.

## Defects found in the base engine (not changed here)

- `grammar.each_of_were` / `each_of_are` read `one of the students who were late` as `one of … were` and change it to `was`.
- `grammar.relative_plural` rewrites `is` to `be` (`one of the people who is` becomes `who be`).
- `grammar.subject_copula` changes correct `the students that are ready` to `that is` and `the phenomena were` to `was`; `spelling.real_word` changes `nor` to `not` in `neither he nor you are`; `grammar.subject_do_agreement` turns `the manager and the director don't` into `doesn't`.
- `The cats has arrived.`, `The neighbors has arrived.`, `Jeans has arrived.` make the engine answer "Corrections did not stabilize" (its possessive and agreement passes undo each other); the pack keeps those nouns out of its `has` rules so it adds no new case.
