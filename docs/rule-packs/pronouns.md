# Pronouns pack: coverage map

`engine/rules/packs/pronouns.json` holds the pronoun rules (ids `pron.*`, 431 rules). It is generated from the family files in `scripts/rule-pack-gen/pronouns/` (`python3 build.py --dump`; `python3 cycle.py` also drops what the engine already fixes, rebuilds the engine and verifies). Every rule has its own hand-written positive, a negative that holds the near misses, a required literal and a confidence. `correct-*.txt` next to the generator are 364 correct sentences that no rule may touch; `verify.py` also runs every negative and every correct sentence through the built engine and requires that no `pron.*` rule fires, and that each positive comes out as the expected text.

How it was measured: every positive was first run through the engine *without* the pack, and a rule the engine already fixed completely was left out (`skipped-ids.txt`, 15 rules). Then the whole mining corpus (622,203 rows) was scanned with every rule: hits on rows marked clean were each judged by hand, and hits on rows with known errors showed which fixes the annotators agreed with. That scan removed or narrowed eleven rules before release (see "Found by the corpus scan").

## Covered by this pack

| Construction | Rule ids (prefix `pron.` omitted) | Notes |
|---|---|---|
| `for my wife and I`, `with John and I`, `behind my parents and I` (preposition + noun phrase + `and I`) | `coord_obj_i_<prep>` (24 prepositions) | place-taking prepositions (`on`, `at`, `in`, `near`, `across from`...) accept only a person as the first conjunct (`my wife`, `the kids`, `you`), so `at London and I` is never touched; `than`, `as`, `like`, `before`, `after`, `since` are never in the list (conjunctions); the word after `I` must be a stop or a short function word, never a verb or an adverb (`I also`, `I sometimes`), so `I at the bank and I at school` style gapping stays |
| verb + noun phrase + `and I` (`contact`, `notify`, `inform`, `visit`, `welcome`, `hire`, `assist`, `accompany`, `greet`, `hug`, `kiss`, `surprise`, `beat`, `defeat`, `impress`, `annoy`, `disappoint`, `forgive`, `trust`, `hear`, `watch`, `serve`, `guide`, `lead`, `encourage`, `thank`, `bother`, `stop`, `catch`) | `coord_obj_i_v_<verb>` (30) | the verbs already in `usage.x_and_I_object` (invite, tell, ask, send, give, call, email, text, meet, help, join, ...) are not repeated |
| `between he and I`, `between you and he`, `between the leaders and we`, `between him and I` | `between_x_and_i`, `between_pron_and_i`, `between_x_and_he/she/they/we` | `between you and I` is `grammar.between_you_i` |
| `let/make my wife and I handle it` | `obj_let_x_and_i_name`, `obj_make_x_and_i_name` | `let him and I` is left out: the engine's `grammar.subject_third` turns the correct `let him and me handle` into `handles` |
| `John and me went`, `my wife and me are`, `she and me left` (object case as subject, mid-sentence and with `the N` / `his N`) | `x_and_me_subject_name/poss/the/pron` | sentence-start `Name and me` is `usage.x_and_me_subject`; these add the clause positions after `so`, `because`, `yesterday`... and the nouns the base misses |
| `me and him went`, `Yesterday me and my sister`, `me and Dana` (mid-sentence) | `me_and_him/her/them/you/poss/the/name_subject_mid` | the name is moved, never respelled (the engine's `moved` group) |
| `Dana and him went`, `the manager and her left`, `my cousin and them` | `x_and_him/her/them_subject_name/poss/the/pron` | `her` only before verbs that cannot also be a noun (`her will`, `her can`, `her saw` are left alone) |
| `Him is`, `Them are`, `Them is`, `Us are` at a clause start; `I think him is`, `I know her is`, `I hope them are`, `I guess us are` | `subject_him/them/us/them_is/them_was`, `mid_him_is`, `mid_them_are/is/was`, `mid_us_are/is/was` | `Us is/was` is protected by the engine as the country, `Her is` is left out (a typo of `He is` in the corpus); `everyone but him is`, `let us have`, `The US have` stay |
| subject pronoun after a preposition (`for she`, `with they`, `to we`, `at he and Sam`) | `prep_<prep>_he/she/we/they` (about 20 prepositions) | `he` only before `and`/`or` (`for he first time` is a typo of `the`), `for` only before a stop or `and`/`or` (literary `for they, like...`), no `I` at all (`divided into I, II`, `at I.S.O.` are Roman numerals and initialisms) |
| `for we students`, `to we teachers`, `between we two` | `prep_<prep>_we_noun` (15) | |
| subject pronoun after a verb that needs an object (`She told he to wait`, `Maya gave she`, `Maya let he go`, `Maya made they feel`, `Maya helped we move`, `Maya asked they`, `Maya brought we`, `Maya showed he`) | `vobj_<verb>_he/she/we/they/i` | the person before the verb must be a pronoun or a name (rules out `I was told he would call` and relative clauses); `told I`/`asked I` never get through the engine (its tagger reads the `I` as a name) |
| subject pronoun left at the end of a clause (`We all love she.`, `Nobody saw they.`, `Maya helped we.`, `Maya took they.`) | `end_love/see/help/bring_he/she/we/they` | dialogue tags (`asked she`, `said he`) are never in the verb lists |
| `neither do me/him/her/us/them` | `neither_do_<pronoun>` | |
| `Myself and Dana will present`, `my sister and myself went`, `Myself will handle it`, `Himself and his wife attended` | `myself_and_start`, `myself_and_start_poss`, `myself_alone_start`, `x_and_myself_subject_mid/the`, `himself_start`, `herself_start` | a reflexive is never a subject |
| `Please contact myself`, `feel free to ask myself`, `Please send myself a copy` | `myself_contact_*`, `myself_send` | only after `please`/`kindly`/`feel free to`/`don't hesitate to`; `I will just ask myself` stays |
| `She gave it to Nora and myself`, `He told Priya and myself` (reflexive for `me`) | `myself_obj_<prep>` (15), `myself_obj_v_<verb>` (16) | **only when the subject of the clause is plainly not `I`** (`He`, `She`, `They`, `Everyone`, a name, `the/my N` followed by lowercase words only): `I saved a seat for Nora and myself` is a correct reflexive |
| `If yourself or a colleague needs help` | `yourself_subject` | |
| `who/whom`: `the man to who I spoke`, `At who did you look?`, `In who do you trust?` | `whom_after_<prep>` (18, after a person noun), `whom_start_<prep>` (17, sentence-start questions) | `I like you for who you are`, `about who I met`, `Who did you see?` stay; the question rules take the auxiliary into the edit so the engine's `grammar.relative_singular` cannot turn `do` into `does` |
| `whom` as the subject: `Whom is calling?`, `Whom will be there?`, `I wonder whom is coming`, `Whom do you think will win?` | `whom_is_ing`, `whom_has_sub`, `whom_mid_is`, `whom_mid_modal`, `whom_do_you_think` | `Whom do you think we should hire?` stays |
| `whomever wants it`, `whomsoever` | `whomever_aux/s1/s2`, `whom_to_whomever_subject_pronoun` | `whomever you like` stays |
| `who's car`, `the man who's daughter`, `Whose coming?`, `I wonder whose going`, `anyone whose been` | `whos_after_person`, `whose_start_contraction`, `whose_mid_contraction`, `whose_after_someone` | `who's` + noun is also in base (`usage.whose`, `usage.whose_noun`, 15 rules left out as redundant); `Whose going rate is that?`, `Whose home is this?` stay |
| `the woman which called`, `anybody which wants` | `which_for_people_det`, `which_for_people_pron` | 0.9; person nouns only, never `people`, `person`, `teacher`, `those which`, never after a comma |
| `it's` for `its`: `about it's size`, `love it's design`, `It's head is round`, `it's own` | `its_after_prep_parts/attrs/abstract`, `its_after_verb_*`, `its_clause_noun_verb` | nouns that can follow `it's` as a predicate (`history`, `people`, `performance`, `time`) are never in the lists |
| `its` for `it's` before an adjective or adverb (`I think its sunny`, `its only a phase`) | `its_for_its_adj_weather/evaluation/kind/size`, `its_for_its_adv` | a comma after the adjective is never accepted (`its rainy, erosion-prone geography`); the adjectives the engine already fixes (`good`, `easy`, `hard`, `cold`...) were removed |
| `your an idiot`, `your a good cook`, `your the best`, `your not alone`, `your gonna`, `I think your hungry` | `your_an`, `your_a`, `your_the`, `your_not`, `your_gonna`, `your_adj_feel/quality/status` | `your a priori`, `your A grade`, `your not-for-profit`, `your tired eyes` stay; the nouns after `your an` and `your the` are whitelists (`your an original description` is a typo of `an`) |
| `they're` / `their` mirror: `I think their happy`, `I hope their not coming` | `their_adj_feel/quality/status`, `their_going_to_start_mid` | |
| `you're` for `your`: `Thank you for you're kindness`, `you're own`, `love you're hair`, `check you're inbox` | `youre_after_prep`, `youre_own`, `youre_noun_body/tech/life` | `like you're`, `than you're`, `given you're` are never in the preposition list |
| `there` / `they're` for `their`: `on there own`, `There kids are noisy`, `at there house`, `on they're own` | `there_own`, `there_possessive_start/prep`, `theyre_possessive`, `theyre_possessive_start` | `There are kids`, `over there`, `Is there own-brand milk?` stay |
| `he's car is`, `at she's house`, `his a good cook`, `his gonna`, `he's own boss` | `hes_possessive_start/prep`, `shes_possessive_start/prep`, `his_a/an/the/gonna`, `hes_own/shes_own` | `from now on he's going` and the name `He` stay (the preposition rule needs a possessed noun and a lowercase `he`) |
| `its'`, `yours'`, `hers'`, `ours'`, `theirs'` | `apostrophe_yours/hers/ours/theirs` (`its'` and `it's own` are base) | |
| `a friend of mines`, `yours or mines`, `that seat is mines`, `a friend of my.` , `yours house`, `mine mother` | `mines_of/pair/is`, `of_my/your/our/her/their_end`, `det_yours/hers/ours/theirs`, `mine_det_kin` | `Yours truly`, `The gold mines were a job` stay |
| `theirself`, `hisself`, `herselfs`, `myselfs`, `ourself`, `youself`, `itselfs` | `theirself` and the rest | the single-token typos are also in the engine's typo list; these catch `theirself`, `himselfs`, `hisselfs`... |
| `each others toys`, `one anothers views`, `someone elses car`, `someone's else`, `by its self` | `each_others`, `one_anothers`, `elses_possessive`, `else_s_order`, `by_its_self` | |
| `Theirs a problem` | `theirs_theres` | |
| `My brother he is a doctor` | `double_subject_m/f/n_he/n_she/p` | no comma; the relative reading (`the man he is today`) is never touched; 0.84 |
| `anyone of them`, `everyone of us` | `anyone_of`, `everyone_of` | 0.84, only before `them/us/you/these/those`; `told anyone of the events` stays |
| `like them boots` | `them_det_verb` | `How do you like them apples?` and `got them flowers` stay |
| `Theirs`, `there's` and the `he's`/`his` mix-ups | see above | |

## Already covered by a base rule (no pack rule added)

| Construction | Base rule |
|---|---|
| `between you and I` | `grammar.between_you_i` |
| `Me and him went`, `Me and my wife`, `Me and Ravi`, `Him and me`, `Them and I` at a sentence start | `usage.me_and_*_subject`, `usage.him_and_*`, `usage.her_and_*`, `usage.them_and_i_subject` |
| `John and me went` at a sentence start | `usage.x_and_me_subject` |
| `to/for/with/from/about/like + NP and I`, and the verbs invite, tell, ask, send, give, call, email, text, meet, help, join, thank, picked, drove, take... | `usage.x_and_I_object` |
| `everyone except I/he/she/we/they` | `usage.except_*` |
| `to who should I`, `for who do you` | `usage.to_whom` |
| `the man whom called`, `whom I think is` | `usage.who_subject_verb`, `usage.who_parenthetical` |
| `Omar and myself will`, `Please forward to myself`, `contact X or myself` | `usage.myself_subject`, `usage.myself_imperative`, `usage.myself_object` |
| `its a`, `its been`, `its not`, `its working`, `its good/great/easy/hard` | `usage.its_*`, `grammar.its_contraction`, `grammar.its_working` |
| `it's tail`, `it's own`, `of it's size` for most nouns | `grammar.object_its`, `grammar.its_possessive`, `usage.its_possessive`, `usage.its_after_preposition` |
| `your a star`, `your the best` (after a clause opener), `your going to`, `your tired/happy/fine`, `you're help` | `usage.youre_*`, `usage.your_possessive_noun`, `usage.your_after_object` |
| `Their going`, `There coming`, `their is` | `usage.theyre_*`, `usage.there_*` |
| `that is mines` | `usage.mines` |
| `her's`, `your's`, `their's`, `our's` | `usage.possessive_pronoun_apostrophe` |
| `Them boots are` | `usage.them_determiner` |
| `Us nurses need` | `usage.us_subject` |
| `bought we interns pizza` | `usage.we_object` |
| `said me to wait` | `usage.said_told` |
| `each others` (no apostrophe) | `grammar.possessive_each_other` |
| `hisself`, `theirselves`, `myselfs`, `ourselfs`, `my self`, `it self` | `spelling.*` |
| `Everyones`, `Someones`, `Nobodys` | `punctuation.apostrophe` |
| `The woman who called`, agreement of `who` with its noun | `grammar.relative_*`, the agreement pack |

## Not rules, and why

- **Pronoun after `than`, `as`, `like`** (`taller than me`, `as good as he`): both cases are accepted in speech and in print.
- **`It is I`, `This is she`**: correct and formal.
- **`you and me should go`, `me too`, `me neither`**: accepted in the spoken register; the base rules already treat `you and me` at a sentence start as a fix, the pack stays out of every other position.
- **`everyone ... their`, `somebody ... they`, singular `they`/`themself`**: accepted usage.
- **Possessive before a gerund** (`him going` against `his going`): contested; both forms stand.
- **`who` for `whom` after a verb or in a question** (`Who did you see?`, `the person who I met`): standard in speech and most edited prose; only the frames that are wrong in every register (`to who I spoke`, `At who did you look?`) are flagged.
- **`that` against `who`** for people: a style choice.
- **`This/these`, `that/those` with the wrong number**: owned by the articles-determiners pack.
- **`everybody are`, `someone have`, subject-verb agreement of any pronoun**: owned by the agreement pack.
- **`its` / `it's` in `its time`, `its worth`, `its best`, `its light`**, any adjective that can also be the possessed noun: the possessive reading is real.
- **`the man which`/`the people which`/`those which`**: `people which`, `person which`, `teacher which` are left alone (the annotators of the mining corpus kept them in several rows); `which` after a comma is the ordinary relative.
- **`I and my wife went`**: grammatical.
- **A reflexive after a coordination when the subject is `I`** (`I bought it for Nora and myself`): correct.
- **`Vague it/this/that`**: not a pattern a regex can see.
- **`Roman numeral I` and initialisms after a preposition** (`into I, II`, `at I.S.O.`, `Henry I`): the reason no rule has a bare `I` after a preposition.
- **Dialect `them` as a determiner after `gave/got/bought`** (`bought them flowers`): ditransitive, correct.

## Found by the corpus scan (rules removed or narrowed before release)

The scan of 622,203 rows (clean rows are the false-alarm check, changed rows show whether the annotators agree) removed `prep_*_i` (`divided into I, II` and `at I.S.O.` are Roman numerals and initialisms), `them_det_prep` (`with them people do` is a missing comma), `subject_her` and `mid_her_is` (`Her is` is a typo of `He is`), and narrowed `your_the`/`his_the`/`your_an`/`his_an` to whitelists (`your the app` is a stray word), `his_a`/`your_a` (`I appreciate his a lot` is `him a lot`), the adjective rules (a comma after the adjective is an adjective list), `hes_possessive_prep` (`on he's going`), `anyone_of`/`everyone_of` (`told anyone of the events`), `prep_for_he/they` (a typo of `the`; literary `for they, like...`), and the `which` rules (annotators kept `the person which has`).
