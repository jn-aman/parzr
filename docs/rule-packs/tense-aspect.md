# Tense and aspect: coverage map

Pack: `engine/rules/packs/tense-aspect.json`, **2437 rules**, ids `tense.*`. The pack is produced by a generator
(`scripts/tense-pack/build.py`) from reviewed verb tables; every rule has its own positive and negative sentence, written
for the rule, and the Rust tests check all of them. This page maps each construction to the rules that cover it, the
checks that already existed, and what was left out and why.

How the rules relate to what was there before. The engine already repairs many of these slips in Rust
(`grammar.perfect_participle`, `grammar.passive_participle`, `grammar.auxiliary_base`, `grammar.explicit_past_time`,
`grammar.perfect_past_time`, `grammar.since_perfect`, `grammar.used_to`, `grammar.state_progressive`,
`grammar.regularized_past`, `grammar.conditional_past_perfect` ...), driven by a table of about 110 irregular verbs, and
the base `grammar.json` has 89 tense and 33 verb-form rules. Before writing a rule the generator ran the construction
through the engine without this pack; a rule is written only for a verb or context that the engine does not already fix
(the count of verbs the engine already fixed is given per family below). Overlapping edits never double-apply: the
engine keeps the higher-confidence edit on the same word.

## 1. Irregular verb forms (136 irregular verbs in the tables, 131 regular verbs for the perfect rules)

| Construction | Rules | Notes |
|---|---|---|
| `has went`, `would have saw`, `Have you ever ate?`, `Had I knew`, `Having went`, `Has the team came?` (past form where the participle belongs) | `tense.perfect_past.<verb>` (59) | Declarative, inverted question, modal perfect, contractions (`I've`, `hasn't`), adverbs between, noun-phrase or name subject in a question. `saw`, `bit`, `rose` need a verb-like follower (`have saw blades` is a noun). Left out because the "wrong" form is an accepted participle: forget (`forgot`), weave (`wove`), bite (`bit`), wake (`woke`), tread (`trod`), strive (`strove`), hide (`hid`), show (`showed`), sew; `was`/`were` after `had` ("all they had was") is a relative clause, not a slip. |
| `was wrote by`, `is being tore`, `has been undid` (passive with the past form) | `tense.passive_past.<verb>` (22) | Transitive verbs the engine's own passive check misses; the next word must be a preposition, particle or the end ("was took the money" may be a spurious "was"). `woke`, `broke`, `shook`, `froze`, `hid` are adjectives too ("I was woke", "he is broke"). |
| `I seen`, `we gone`, `she written` (participle as the simple past) | `tense.participle_as_past.<verb>` (52) | Needs a clause start, a subject pronoun and an object or particle after the verb; `done`/`seen` stay with the base rules. Not written because the form is an accepted past: sunk, shrunk, sung, rung, drunk, swum, sprung. |
| `didn't went`, `Did you saw?`, `Why did he came?`, `Did the team went?` | `tense.did_past.<verb>` (60) | 71 verbs were already fixed by the engine (`grammar.auxiliary_base`). Left out where the past form is also a base verb: find/found, lay, bind/bound, wind/wound, grind/ground, bear/bore; `saw` and `fell` need a follower ("didn't saw the board" may be carpentry). |
| `to went`, `Let's went`, `let him came` | `tense.to_past.<verb>` (65) | 55 verbs were already fixed. Left out where the past form is a noun: thought, won (Korean currency), led ("converted to LED"), bent, left, saw, found, fell, rose, shot. |
| `I have already go`, `She has never take`, `We hadn't yet see` (bare verb after a perfect cue) | `tense.have_base.<verb>` (121), `tense.have_base_reg.<verb>` (131) | A perfect cue (already, just, never, ever, yet, recently, finally, lately, previously, once, twice, not) must sit between `have` and the verb. Without it "I have go to the market" is ambiguous with "I have to go", so it is left alone; `'d` is excluded ("I'd never go"). Nouny bases need an object or particle after them (`have also sink` is a kitchen sink). Adjective-like verbs (open, close, clean, complete) need an object. |
| `should have go`, `could've take`, `to have see` | `tense.modal_have_base.<verb>` (121), `tense.modal_have_base_reg.<verb>` (131) | A modal plus `have` is unambiguous; the same nouny-base guard as above. |
| `I will went`, `She can't took`, `You should not gave` | `tense.modal_past.<verb>` (56) | 72 verbs were already fixed. Pronoun subject only ("the can sank" has a noun `can`). |
| `buyed`, `swinged`, `forbided`, `undoed`, `shooted` (irregular verb with a regular ending) | `tense.regularized.past|part|base.<verb>` (113) | Only forms that are not words; the correction depends on the context (after a subject: past; after `have`/`be`: participle; after `did`, `to`, a modal: base). Left out because the regular form is a word or a spelling variant: lied, ringed, seed, singed, strived, waked, weaved, slayed, treaded, creeped, hanged, kneeled, shined, payed, winded, bended, grinded, leaded, retaked/binded (the engine's own participle check then rewrites the correct form). |
| `wouldn't of known` | `tense.modal_of.*` (5) | The base `could of` phrases cover the positive modals; these are the contracted negatives. The word after `of` must be a participle ("couldn't of course"). |

Verbs deliberately dropped from individual families because the engine's existing checks rewrite the correct form
afterwards: retake (participle `retakened`), sting and swing (`st`, `saw`), bind, grind, ring/slay/sit/wind in the
marker rules (`rang` to `ranged`). They are engine bugs, not tense errors; they are listed in the commit message.

## 2. Time, aspect and mood constructions

| Construction | Rules | Notes |
|---|---|---|
| `I have seen him yesterday`, `two days ago`, `last June`, `the other day` (perfect with a finished past time) | `tense.perfect_marker.<verb>` (56), `tense.perfect_marker_gap.<verb>` (68) | The engine fixes `yesterday`, `ago`, `last week` and `in 2019` for its table verbs; the first group is for the other verbs, the second adds the markers the engine lacks (`last June`, `the other day`) to all verbs. The window between verb and marker is tiny (a pronoun object, a determiner and a noun, a name, a short prepositional phrase) so "I have read the email you sent yesterday" is never touched. A year is not used as a marker (it can be the current year). |
| `Last night I go to the market` (fronted past time, present verb) | `tense.past_marker_front.<verb>` (238) | The time word keeps its capital, so "since last year we use it" is not matched. `grammar.explicit_past_time` already fixes many of these for "yesterday", "last night" and "last week" but not for "last year", "last summer" or "last winter", so every verb has a rule; where both fire the edits are identical or this pack's (0.95) wins. Pronoun subjects only; `In 1999 he is called ...` (historical present in encyclopedic prose) is never matched. |
| `I know him since 2010`, `She works here since January` | `tense.since_present.<verb>.plural|3sg` (93) | The engine handles `since` plus a month or `last ...`; digits (years, times) were a gap. The words between verb and `since` are an object or a short phrase, never a clause ("I know that since 2010 ..."). |
| `I am here since morning`, `She's sick since yesterday` | `tense.since_present.be.*` | State plus `since` takes `has/have been`. |
| `I have lived here for 2010` | `tense.for_year.for` | Only a state verb, an optional place and a year at the end ("planned for 2007" is a target year). |
| `since a long time`, `since ages`, `since long`, `since an hour`, `since last three years` | `tense.since_for.*` (4) | The base rule covers `since two years`; these are the vague and article forms. |
| `How long are you living here?`, `How long do you know him?` | `tense.how_long.*` (20) | Only verbs that cannot mean a plan or a habit ("How long are you staying?" is fine). |
| `after I will finish`, `until he will arrive`, `as soon as they will come`, `When I will reach home,`, `If I will go,` | `tense.time_clause.*` (14), `tense.time_clause_be.*` (26), `tense.time_clause_3sg.<verb>` (145), `tense.time_clause.if_initial_state` | Connectors: after, before, as soon as, until, till, once, by the time, whenever, every time, the next time, in case; `when`/`if` only as a sentence opener with a comma ("I don't know when I will go" is an indirect question; "if you will follow me" is an idiom). `the moment` and `the minute` were dropped ("at the moment I will finish" is a run-on, not a time clause). `will be` becomes am/are/is. |
| `If I would have the money`, `If I would be you`, `If you will have any questions,` | `tense.conditional.*` (2), `tense.time_clause.if_initial_state` | `If I would have known` is the engine's `grammar.conditional_past_perfect`. "If you would have a seat" is a polite request and is left alone. |
| `I wish I can`, `I wish I will`, `I wish I am`, `I wish I have`, `I wish I would have gone` | `tense.wish.*` (6) | Anchored on "I wish"/"we wish" ("if you wish we can" is a conditional). |
| `use to`, `didn't used to`, `I am use to`, `get use to`, `I got used to wake up` | `tense.used_to.*` (29) | `grammar.used_to` covers `We use to go`; added: adverb between, `be/get use to`, and `get/be used to` plus a bare verb for `I` or `get` ("they are used to deal with riots" is a passive). `didn't used to` is the engine's. |
| `suppose to` | `tense.supposed_to.*` (2) | After any form of be, including `I'm`, and in questions. |
| `I would rather to stay`, `You had better to go`, `You have better go` | `tense.would_rather.to`, `tense.had_better.*` (3) | |
| `Lets go`, `Okay lets get started`, `she let's me` | `tense.lets.*` (3) | `lets` before a bare verb after a sentence start, comma or marker word; `she lets the dog out` and `He lets go of the rope` are untouched. |
| `He is go to school`, `I am work in a bank`, `They were play football` | `tense.be_base.<verb>` (38) | Pronoun subject plus am/is/are/was/were and a bare verb with a typical object. Not `it` (`it's work to do`), not `'s`. |
| `I have being working`, `I am been`, `I'm been`, `I was been`, `have be working` | `tense.been.*` (16) | |
| `I have working here since 2015` (missing `been`) | `tense.been.have_ing.<verb>` | Verb-specific followers; "I have reading to do" and "working knowledge" are not touched. |
| `I am having a question`, `We are having two brothers` | `tense.stative.having_*` (4) | Possession objects only ("I am having a meeting" is fine). `I am understanding` and `I am liking` are Register suggestions (0.7); `grammar.state_progressive` covers know, believe, need, want, own, belong, prefer ... |
| `The accident was happened`, `has been died`, `It was came` | `tense.intransitive_passive.<verb>` (13) | "A decision was arrived at" is a real prepositional passive and is untouched; `disappeared` (transitive in "he was disappeared") and `stayed` (legal "stayed") are not included. |
| `Have you finish your homework?`, `Has he go?`, `Why have they come late` (inverted perfect question, no cue) | `tense.have_question.<verb>` (121), `tense.have_question_reg.<verb>` (131) | `Have you` / `Has he` at a sentence start or after a question word; `Have it ship by Friday` (an instruction) is untouched. |
| `It was happen last week` | `tense.was_base.<verb>` (6) | Intransitive verbs only. |
| `I lived here since 2015`, `They played since 2009` (past form with `since`) | `tense.since_past.<verb>.plural|3sg` (82) | State verbs; `since 2010 until 2015` is not matched. |
| `My bike got stole`, `The window gets tore` | `tense.get_passive.<verb>` (18) | Only the forms that are never an adjective or a noun after `got` (not `got broke`, `got shook`, `got took`: slang). |
| `I'll called you`, `She'll just went` | `tense.ll_past.<verb>` (241) | The engine's modal check cannot see through the `'ll` contraction. |
| `We will able to ship`, `They won't able to join` | `tense.modal_able` | Any modal but `can`/`could` (the engine has `can able`). |
| `We know each other for ten years` | `tense.for_duration.<verb>.plural|3sg` (16) | State verbs only (`I work here for three years` can be a contract). |
| `He is works at Amazon`, `Who is wants pizza?` | `tense.be_before_verb.<verb>` (29) | Only `he/she/who` plus a third-person form. `They are live in Brooklyn` is not matched ("the concerts are live"). |
| `I had went there last year` (past perfect form with a finished past time) | `tense.had_marker.<verb>` (52) | The correction is the simple past, which the writer already typed: "I went there last year". |
| `I will to go`, `She must to leave`, `I can't to find` | `tense.modal_to.*` (8) | Not for `can`/`could`: "everything I could to help" is correct. |
| `I will can help`, `I didn't can find`, `I don't can open` | `tense.modal_can.*`, `tense.negative_can.*` (11) | Followed by a verb ("She didn't can the peaches" is untouched). |
| `I am want to go`, `I'm agree`, `I am not agree`, `She is not agree` | `tense.am_verb.*` (4) | `like` is excluded ("he is not like his family"); `think` is left to the progressive rule. |

## 3. Deliberately left out

* `gonna`, `wanna`, `gotta`: chat forms, left as typed (owner policy).
* Reported-speech backshift ("He said he will come"): fine when the situation still holds; a rule would flag good sentences.
* `yet`, `already`, `just` with the simple past ("Did you eat yet?", "I already ate"): standard in American English.
* `have go`/`has take` with no perfect cue: ambiguous between "have gone" and "have to go".
* `If I was`/`as if he was`: accepted in everyday English; no preference rules.
* Noun subjects with `is go`, `will to`, or fronted `Yesterday my brother go`: the neighbouring noun phrase cannot be told apart from a modifier without parsing.
* `think`, `see`-type verbs after `to` whose past form is a noun (see section 1), `sit/stand/hang` fronted-marker rules (the present form is often a noun).
* "I am used to + base" ("I am used to deal with"): can be a passive of a tool; only `I am/I'm` and get/become are matched.
* `went to the store and buy milk` (a past verb and a bare verb joined by `and`): often right in English ("I bought a phone and use it every day"), so it cannot be a rule.
* `The office will closed on December 25`: "will close" and "will be closed" are both right; the engine's own choice (the base form) stands.
* Noun subjects with a present verb and a past time word ("The power goes out around 3am last night", "Last year the company hires fifty people"): the clause boundary needs a parser.
* Mixed and counterfactual tenses that depend on meaning ("I wish he comes") and tense consistency across sentences.
* Past progressive and perfect progressive choices that are matters of aspect, not form.
* Regular verbs after `did`/`to`/modals: already handled by the engine's morphology.

## 4. Bugs found in the engine's existing checks (not changed here)

Found while writing and testing the rules; each is a correct sentence the engine already rewrites, or a wrong rewrite.

* `grammar.perfect_past_time` turns correct "I have read the email you sent yesterday.", "I have received the package sent
  yesterday." and "I have wondered how long ago he left." into the simple past (the marker belongs to a relative clause).
* `grammar.noun_number`: "The meeting starts at nine yesterday" becomes "yesterdays".
* `grammar.explicit_past_time` writes "willed" for "will" ("I will go tomorrow yesterday"), "waked" for "wake", "planed"
  for "plan", "ranged" for "rang", "slewed" for "slew".
* `grammar.perfect_participle` / `grammar.modal_base`: correct "has bound", "has ground", "has retaken" become "bounded",
  "grounded", "retakened"; "I will sting" becomes "I will st" and "I will swing" becomes "I will saw". Verbs that trigger this
  were dropped from the matching families (see section 1) rather than turned into worse output.

## 5. How the prefilter was kept cheap

The engine compiles a rule's regex only when a required literal of the rule occurs in the text, and compiling costs about
a millisecond. Each rule is written so that its literal is a short phrase specific to the rule (` went`, `could have go `,
`yesterday i go`), with single literal spaces instead of `\s+` and optional parts written with their own leading space.
The generator's literal analysis predicts about 0.3 candidate rules per ordinary sentence for the whole pack
(0.28 measured on 20,000 sentences).
