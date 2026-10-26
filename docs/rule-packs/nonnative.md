# Non-native transfer pack (`l1.`)

`engine/rules/packs/nonnative.json` holds the transfer errors of Hindi and other L1 writers of English in work chat and email that no other pack owns: 338 rules. 37 of them (the Indian-English forms the owner's own regression set expects unchanged in Fix) carry `"modes": ["professional"]` and run only in the Professional rewrite, see "Professional mode only"; `scripts/rule-pack-gen/nonnative/held-back.json` lists them.

The rules are generated and self-checked by `scripts/rule-pack-gen/nonnative/gen.py` (modules `register`, `phrasing`, `complements`, `timewords`, `tags`, `emphasis`, `uncountable`, `extras` to `extras5`): each rule's positive must become exactly the stated correction (the generator emulates the engine's edit, including its case matching and the linked `moved` pair) and its negative, a few correct sentences with the near misses, must not match at all. Run the generator, then `python3 scripts/check-rule-packs.py engine/rules/packs/nonnative.json` and `cargo test --release rules::`.

Policy used throughout (packs README): a pattern that is wrong in every variety of English is a correction (Grammar, Verb form, Tense, Word choice) at 0.85 to 0.93; a form that is standard in Indian English is a Register or Style suggestion at 0.75 or less, with the plain form beside it. Names are never edited (only the word "myself" before a name is). Digits are protected spans in the engine, so no target contains a number; where a number sits inside the phrase it stays outside the edit (`before 2 days` is a linked pair that deletes "before " and adds " ago" after the number; `from 2018` keeps the year and changes only the words before it).

How to read the map: *rules* are the ids without the `l1.` prefix; *base* names a rule that already existed in the base files, another pack or the Rust engine, so no rule here repeats it.

## Covered by this pack (loaded)

| Construction | Rules |
|---|---|
| "revert back to the previous version" (redundancy, the restore sense only) | `revert.back_state` |
| "please kindly", "kindly please", "request you to please" | `kindly.please_kindly`, `kindly.kindly_please`, `request.please` |
| "Myself Aman" and "Hello sir, myself Ravi", "your good self", "Respected Sir" | `myself.name_start`, `myself.name_comma`, `goodself`, `respected` |
| "mail id" / "mail ids" | `mailid`, `mailids` |
| "passed out from college / in 2015 / the passed out batch", "batchmate" | `passedout.institution`, `passedout.year`, `passedout.batch`, `batchmate` |
| "cousin brother / sister", "co-brother", "co-sister", "native place", "my native is …", "where do you stay?" | `cousin_brother`, `co_brother`, `co_sister`, `native_place`, `native_is`, `where_stay` |
| "marriage" for a wedding ("marriage hall", "attend a marriage") | `marriage.event_noun`, `marriage.attend` |
| "expired" for a person, "intimate" for inform | `expired.relative`, `expired.pronoun`, `intimate.base`, `intimate.past`, `intimate.ing` |
| soft copy, cent percent, pen drive, godown, time pass, current cut / "the current went off", updation, upgradation, "office timings" | `softcopy`, `softcopies`, `centpercent`, `pendrive`, `godown`, `timepass.for`, `timepass.is`, `current.cut`, `current.off`, `updation`, `upgradation`, `timings.hours`, `timings.times` |
| "two years back" for "two years ago" | `yearsback.past`, `yearsback.lead` |
| "open the light / close the fan", "give IELTS / give my exams", "avail leave", "came to know that", "we people", "as per me", "last but not the least", "in the meanwhile", "next to next week", "last to last week" | `open.on` to `closing.off`, `exam.*`, `avail.*`, `cametoknow.*`, `wepeople`, `asperme`, `lastbutnot`, `meanwhile`, `nexttonext`, `last_to_last` |
| "herewith attached", "two-three days" | `herewith.attached`, `two.three` |
| extra word after a verb: "discuss about everything / Q3 targets", "discuss on this issue", "inform to the team", "asked me that why", "order for a pizza", "stress on", "call to me", "attend to the meeting", "go for shopping", "apply on the vacancy / to a college", "knowledge on", "access of", "participate on the quiz", "disagree to", "keen in", "surprised on the news", "married with him", "key of success", "highlight about", "check about", "meet to him", "thank to you", "marry to her", "get rid from", "ashamed on", "impressed from", "in holiday", "on weekend" | `discuss.*`, `inform.to`, `ask.that_wh`, `order.for_item`, `stress.on`, `call.to`, `attend.to`, `go.for_activity`, `apply.for`, `apply.to`, `knowledge.on`, `access.of`, `participate.on`, `disagree.to`, `keen.in`, `surprised.on`, `married.with`, `key.of`, `about.verbs`, `check.about`, `meet.to`, `thank.to`, `marry.to`, `rid.from`, `ashamed.on`, `upset.with`, `holiday.on`, `weekend.on` |
| "didn't able to", "doesn't able to", "very less time / people", "very much tired", "much happy", "do you know to swim", "told that he", "takes two days time", "thinking to buy", "looking for to hire", "looking a flat", "also too", "like for example", "most of the times", "need not to", "in details", "lots of works", "datas", "musics", "I am born in", "got died", "make a question", "assist the meeting" | `able.*`, `very.*`, `much.adj`, `know.how_to`, `told.that`, `takes.time`, `thinking.*`, `looking.*`, `also.too`, `too.also`, `like.for_example`, `mostofthetimes`, `need.not_to*`, `in.details_*`, `works.lots`, `mass.data`, `mass.music`, `born.am`, `died.got`, `question.*`, `assist*.meeting` |
| "come till my desk", "drop you till the station" | `till.place`, `drop.till` |
| "do a mistake", "make a selfie / photo", "eat the medicine" | `mistake.*`, `photo.*`, `medicine.*` |
| "I am having a car / five years of experience / fever / back pain / not having time", "I am not understanding / liking / knowing / believing / wanting / needing" | `having.*`, `stative.*` |
| "take tension", "in tension", "giving me tension", "No tension." | `tension.*` |
| time words: "from last three years" with a progressive, "from morning", "from 2018", "married from five years", "has been absent from yesterday", "is down from / since morning", "before two days", "not seen him from two weeks" | `from.*`, `since.*`, `before.ago` |
| "I am totally agree", "She is also agree" | `agree.adv_plural`, `agree.adv_third` |
| the tag "isn't it?" and "is it?" after a sentence whose subject is you, we, they, he, she or I ("You are coming, isn't it?" becomes "aren't you?"), for are/were/will/can/have/would, is/was/has, am; the clause must have no negative word | `tag.isnt.*`, `tag.isit.*` (72 rules, Register 0.75) |
| emphasis: "today itself", "tomorrow morning itself", "here itself", "at the start itself", "the same day itself", "got it now only", "he is there only" | `itself.*`, `only.just_time`, `only.right_here` |
| mass nouns with an "s": feedbacks (after "your", "give", "share" and the like), luggages, baggages, knowledges, hardwares, jewelleries, machineries, stationeries, cutleries, sceneries, garbages, applauses, pollutions, poetries, lightnings, staffs, datas, musics | `mass.*` |
| "younger to me", "lesser than ten", "paining" for aches, "hanged" for a frozen device, "in meeting", "in bus / in cab", "by walk", "belong from" | `younger.to`, `lesser.than`, `paining.*`, `hanged.device`, `in.meeting`, `in.bus`, `in.cab`, `by.walk`, `belong.*` |

## Professional mode only

The forms below are standard Indian English and the owner's everyday regression set (`benchmarks/everyday/items.jsonl`, frozen) lists them as correct text that a Fix check must leave unchanged: b002-0135, 0160, 0314, 0408, 0533, 0549, 0563, 0673, 0712, 0826, 0904, 0915, 0953, 0954, 0978 and b003-0870 ("I have a doubt regarding the invoice.", "Kindly find the attached document.", "The call is preponed to Monday.", "Please revert at the earliest.", "Kindly do the needful.", "Please do the needful.", "I have completed the task, please check the same.", "I am out of station till Monday.", "Request you to share the status by EOD.", "My good name is Rahul.", "Can we prepone the meeting to 3pm?"). A Fix-path rule for any of them would turn a correct item wrong, and the engine applies every edit it returns, Register and Style included, so these rules carry `modes: ["professional"]`: a Professional rewrite (which runs the mode's wording rules after the model since the clarity pack landed) asks for business English and says "do what is needed". Each family is held back whole, so a Fix check treats "do the needful" and "did the needful" alike.

| Construction | Professional-mode rules |
|---|---|
| "do the needful" in all tenses, "needful action" | `needful.*` (5) |
| "prepone", "preponed", "preponing", "prepones", with and without a pronoun | `prepone.*` (8) |
| "revert" meaning reply ("revert by EOD", "revert with your comments", "I will revert on this"), "awaiting your revert" | `revert.reply`, `revert.reply_past`, `revert.reply_ing`, `revert.noun` |
| "Kindly" + imperative, "Request you to …" with no subject, "request you to kindly" | `kindly.imperative`, `request.start`, `request.kindly_start`, `request.kindly` |
| "the same" as a pronoun ("please find the same attached", "update on the same") | `same.pronoun`, `same.prep` |
| "out of station", "outstation" | `outofstation`, `outstation.state`, `outstation.trip` |
| "your good name", "my good name is …" | `goodname.ask`, `goodname.please`, `goodname.is` |
| "I have a doubt regarding …", "a quick doubt", "clear my doubt" | `doubt.*` (5) |
| "Please be informed that", "Thanking you" | `informed.please`, `thanking.you`: correct formal English, and the 30k corpus has correct sentences with them |
| "reply back" | `reply.back`: common in native writing |

To move a family into Fix, delete its id prefix from `HELD_BACK` in `gen.py` and relabel the items above.

## Already covered by a base or other rule (not repeated)

| Construction | Rule |
|---|---|
| "I am agree", "I am not agree", "we are agree" | `grammar.i_am_agree`, `tense.am_verb.delete`, `tense.am_verb.not`, `tense.am_verb.not_3sg` |
| "I am having a doubt / a car / two brothers" (determiner + common noun) | `usage.have_possession`, `usage.has_possession` |
| "discuss about the / it / how / what / several …", "cope up with", "despite of", "in spite of he was late", "inspite of" | `grammar.discuss_about`, `usage.discuss_about_pronoun`, `prep.discuss_about_more`, `prep.cope_up_with`, `grammar.despite_of`, `prep.despite_of_more`, `clause.prep_clause.in_spite_of_subject`, `spelling.common_misspelling` |
| "I will revert back to you / me / us" | `usage.revert_reply` |
| "since three years", "since last three days", "since a week", "since long", "I am working here since …", "It is raining since morning" | `usage.since_duration`, `tense.since_for.*`, `usage.progressive_since*`, `grammar.since_perfect` |
| "myself" as a subject after a name ("Ravi and myself will") and as an object | `usage.myself_subject`, `usage.myself_object`, `usage.myself_imperative` |
| mention / explain / describe about, emphasize on, reach to, approach to, contact to / with, enter into / to, resemble to, marry with, listen the, wait the bus / you, angry on, jealous on, senior than, prefer than, similar with, same like, afraid from, aware about, proud on, comprise of, reply for, appreciate for, pay attention on, consider about, agree to you / for, congratulations for, answer of, interested for, responsible of, insist for, depends of, obey to, disappointed of, good in maths, look forward for / to meet, according to me | `prep.*`, `usage.*`, `grammar.depends_on`, `grammar.interested_in` |
| reply me, explain me, said me, tell to me, borrow me | `usage.reply_to`, `usage.explain_to`, `usage.said_told`, `prep.tell_to_person`, `usage.lend_object` |
| can able, will able, must to, let's to, suggest to go, enjoy to read, avoid to, finish to, busy to, interested to join, I want that you send, for to learn | `grammar.can_able`, `tense.modal_able`, `tense.modal_to.*`, `grammar.extra_to`, `grammar.gerund_complement`, `vcomp.*`, `clause.frame.for_to_infinitive` |
| stative verbs in the progressive, affirmative ("He is knowing", "I am wanting a coffee", "I was knowing") | `grammar.state_progressive`, `tense.stative.*`, `grammar.stative_know` |
| "return back", "and etc.", "was died" | `usage.return_back`, `confuse.eg_and_etc2`, `tense.intransitive_passive.died` |
| "Although it rained, but …", "Because …, so …", "in case if", "the reason is because" | `grammar.double_conjunction`, `prep.in_case_if`, `usage.reason_is_because` |
| "a news", "an advice", "advices", "informations", "equipments", "furnitures", "homeworks", "softwares", "clothings" | `det.a_news`, `det.a_advice`, `grammar.uncountable_*`, `spelling.common_misspelling` |
| "the more taller", "too much hot / tired", "enough tall", "elder than / to", "very much happy / beautiful" | `usage.double_comparative`, `mod.too_much_hot`, `mod.too_much_tired`, `mod.enough_tall`, `usage.elder_than`, `mod.elder_to`, `mod.very_much_happy`, `mod.very_much_beautiful` |
| "in morning", "in evening", "in leave", "go to home", "reach to home" | `det.in_the_morning`, `prep.in_leave`, `prep.go_to_home`, `prep.reach_at_to_place` |
| "I am understanding", "I am liking" | `tense.stative.*` |
| "today morning / today evening" | word-order pack (`order.time_phrase.*`); skipped here as the brief says |
| "one of my friend" | agreement pack and `usage.one_of_plural`; skipped here |

## Left out on purpose

| Construction | Why |
|---|---|
| "no?" / "na?" after a sentence | Roman Hindi and the "no?" tag are left as typed (owner policy); "It is nice, isn't it?" is correct and never matched |
| a bare "Please revert." | in software "revert" is the git verb; the held-back reply rules need a reply cue ("by EOD", "with your comments", "on this") |
| "only" and "itself" as plain emphasis ("for members only", "the meeting itself", "Today itself is a holiday") | correct English; only the Indian patterns (a time or place word + "itself", a past verb + "now only") are matched |
| "doing good", "I am fine only", "do one thing", "what all", reduplication ("small small things"), "do a call", "do the payment", "do the changes" | meaning or register depends on context, and natives say several of them |
| "with regards to", "by foot", "reply back", "feedbacks" in science text, "Please be informed" | correct or widely used in native writing; a first draft of `regards.with`, `by.foot` and an unrestricted `mass.feedback` fired on correct corpus sentences and was dropped or narrowed |
| "was wanting / liking / believing", "I am not remembering / owning up" | progressive of these verbs is correct in some uses ("owning up", "I was wanting to ask") |
| "I am getting late", "we're getting late" | accepted informally in many varieties |
| "My age is 25 years" | the number is protected by the engine, so the rewrite to "I am 25 years old" cannot be one edit |
| "confident on", "different with", "consists in", "composed from", "suggest me" | correct in some uses, or the right fix depends on meaning |
| "provide me the details", "forward me the mail", "confirm me the date" | accepted informally; the verb-complement pack decides |
| "Thanks & Regards", "PFA", "pls", "yaar" | sign-offs, shorthand and Roman Hindi stay as typed |

## Interactions found while building

- The base `grammar.explicit_past_time` and `grammar.perfect_past_time` rewrite "is pending from last month" and "has been absent from yesterday" to the simple past, which is wrong. `from.state_is`, `from.state_are` and `from.perfect_point` start one word earlier than those edits, so they win the overlap; a state with a name in front ("Ravi has been absent from yesterday") is protected as a name and keeps the base result.
- At the same start the higher confidence wins, and the base rules are at 0.93 to 0.95: a rule here that repeats a base fix is dropped from the plan, and a rule that must beat a base edit starts earlier (`kindly.please_kindly` takes the whole "please kindly" span and `request.please` takes "to please", to get ahead of `punctuation.run_on`).
- A target that touches a name or a number is blocked by the engine, so `from.year.*` leaves the year outside the target, and "He is living in Pune from 2015" keeps its text (a place name inside the target is a name).
- `myself.name_start` and `myself.name_comma` need a word after the name ("from", "working", "a" …) and never fire on "Myself Rahul, I am new in the team.": the fix would give "I am Rahul, I am new in the team.", which the comma-splice pass turns into two sentences, and the everyday set (b003-0830) accepts the sentence as typed.
- Base bugs seen while probing, not touched here: `grammar.inverted_subject_agreement` rewrites "What are the office hours?" to "What is the office hours?" and "Where are the office files?" to "Where is the office files?"; `grammar.subject_third` rewrites "Keep it like this only." to "Keep it likes this only."; `grammar.fewer_count` rewrites "very less people" to "very fewer people" (`very.less_count` gets ahead of it); `vcomp.idiom.suggest_person` turns "suggest me a laptop" into "suggest to me a laptop", and `usage.explain_to` turns "explain me this" into "explain to me this".
