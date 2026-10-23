# Articles and determiners: coverage map

Pack file: `engine/rules/packs/articles-determiners.json` (id prefix `det.`). Rules: 1151.

## How the rules are built

Every rule is a regular expression whose edited span is a small `target` group; the engine restores the case of a sentence start. Four ideas keep the false-alarm rate near zero:

1. **Closed lexical lists.** A rule names the nouns (and, for missing articles, the verbs) it applies to. "I have question" is a rule for `question`, `problem`, `idea` and so on; there is no rule for "have" + any noun, because "have time", "take note" and "need room" are right.
2. **Tails.** A noun that can also modify another noun ("a software engineer", "a news article", "UK law", "United States dollars", "station wagon") is only corrected when punctuation, the end of the text or a function word follows it.
3. **Anchors.** Rules that put "a" or "the" before a noun need a finite verb, a sentence start or a subject before the verb, so a participle used as an adjective ("a scheduled appointment") is never taken for the verb.
4. **Edits that avoid names.** When the missing word belongs before a proper noun ("in Netherlands"), the edit is the preposition alone ("in" to "in the"), so the engine's name guard never blocks it and the name is never touched.

The rules were checked against their own positive and negative examples (also across all rules), the 30,000-sentence false-alarm corpus, 300,000 corrected sentences from the mining pairs (hits inspected, never copied), the held-out dev split, the English 1,000 and 2,000 sets and the everyday set.

| Construction | Status | Rules / note |
|---|---|---|
| a/an before digits (8, 11, 18, 80-89; consonant-sound numerals) | rules | det.an_before_8, det.an_before_11, det.an_before_18, det.a_before_consonant_numeral |
| a/an before number words (eight, eleven; two..ninety, hundred, half) | rules | det.an_before_eight_words, det.a_before_consonant_number_words |
| a/an before letter+digit labels (A4, N95, M1 vs B2B, G7, V8) | rules | det.an_before_vowel_letter_label, det.a_before_consonant_letter_label |
| a/an before single letter + hyphen (e-mail, X-ray, F-16 vs T-shirt, U-turn) | rules | det.an_before_vowel_letter_hyphen, det.a_before_consonant_letter_hyphen |
| a/an before hyphenated compounds (an in-depth, a long-term) | rules | det.an_before_vowel_compound, det.a_before_consonant_compound |
| an before y- words (an year, an young, an yellow ...) | rules | det.a_before_year .. det.a_before_yummy |
| an before x- words said with z (xylophone), a before Xbox | rules | det.a_before_xylophone, det.an_before_xbox |
| a/an before plain words by sound (an hour, an honest, a university, a European, a one-time, a unique) | covered by base rule | grammar.a_vowel, grammar.an_consonant, grammar.article_sound (Rust, determiners.rs) |
| a/an before uppercase acronyms (an MBA, an FBI, an HTML, a URL, a UFO, an SUV, an X) | covered by base rule | grammar.article_sound: letters AEFHILMNORSX take an. Known gap: word-like acronyms (a NASA, a FIFA) are changed to "an" by it; a rule cannot undo another rule's edit, so it is reported, not patched |
| SQL, FAQ, MAC, SCSI (said both ways) | not a regex-safe rule | both articles are right by pronunciation |
| a / an before a mass noun (a furniture, an advice, an information, a luggage, a homework, an equipment, a research, a feedback, a news, a progress, a software, a hardware, a traffic, a weather, a money, a stuff ...) | rules | 40 rules det.a_<noun>; the noun must be followed by punctuation or a function word, so "a software engineer", "a news article", "a traffic jam" stay untouched |
| a good knowledge of / a working knowledge of | not a rule | correct English: "a knowledge of" is skipped |
| a pair of scissors / a scissors, a glasses, a pants | not a regex-safe rule | informal but attested |
| a / an + irregular plural (a men, a women, a children, a feet, a criteria, a phenomena, a analyses ...) | rules | 42 rules det.a_<plural>; regular plurals (a cars) are base grammar.article_number; data/media/bacteria/alumni/people are left out (usage varies) |
| every / each + plural noun (every days, each students, every people, every children ...) | rules | 49 rules det.every_<noun>; base grammar.noun_number already fixes some regular plurals when a verb follows |
| another + plural noun (another cars, another things) | rules | det.other_not_another_plural -> "other"; "another two", "another few", "another 10" stay as they are correct |
| "a other" / "an other" for "another" | rules | det.another_not_a_other (an another is base Rust grammar.another_article) |
| each others | rules | det.each_other_s (each other's is base grammar.possessive_each_other) |
| much/many with an uncountable noun (too many information, so many traffic, how many water) | rules | 95 rules det.much_not_many_<noun>; "many research papers" style compounds are left alone |
| fewer/less with an uncountable noun (fewer energy, fewer time) | rules | 88 rules det.less_not_fewer_<noun> + base grammar.fewer_mass for eight nouns |
| a few / few with an uncountable noun (a few money, few hope) | rules | 190 rules det.a_little_not_a_few_<noun>, det.little_not_few_<noun> |
| number of / amount of with an uncountable noun (a large number of money) | rules | 95 rules det.amount_not_number_<noun> |
| much + irregular plural (much people, much children, much men, much women) | rules | det.many_not_much_people, _children, _men, _women, _persons; regular plurals (much cars) are base grammar.quantifier_number |
| less + irregular plural (less children, less men, less women, less teeth) | rules | det.fewer_not_less_*; less people and regular plurals are covered by base grammar.fewer_count and quantifier_number |
| amount of + countable plural (the amount of people, a large amount of errors) | rules | det.number_not_amount_people, det.number_not_amount_things; "amount of times/calories" left alone (common idiom) |
| a little + plural (a little friends, a little more days) | rules | det.a_few_not_a_little_more, det.a_few_not_a_little, det.so_few_not_so_little; "little" as an adjective ("little things") is untouched |
| few / little with a count noun after a plain "little" (little options) | not a regex-safe rule | "little" is also an adjective ("little changes add up"); only "a little" and "so/too little" are used |
| few days without "a" (for few days, in few minutes) | rules | det.a_few_days |
| a lot / lots / plenty + noun without "of" | rules | det.a_lot_of_missing, det.lots_of_missing, det.plenty_of_missing |
| lot of / couple of without "a"; "a lots of" | rules | det.lot_of_missing_a, det.couple_of_missing_a, det.a_lots_of |
| such / what / quite + adjective + singular noun without "a" (such nice day, what nice idea!) | rules | det.such_missing_a_*, det.what_missing_a_*, det.quite_missing_a_* (a / an by the adjective) |
| "a such a", "a such nice day" | rules | det.a_such_a, det.a_such_swap |
| what a + plural noun (what a lovely flowers!) | rules | det.what_a_plural |
| the all people; the all of; both two; spent the most of the day | rules | det.the_all, det.the_all_of, det.the_all_the, det.both_two, det.most_of_time_spent; "the all time record" and "the all new model" (unhyphenated compounds) are left alone |
| a half of the, the half of the | not a rule | both are attested in careful writing (a half of lager) |
| The most people (for Most people) | rules | det.the_most_people |
| every my friends; every of the | rules | det.all_not_every_possessive, det.each_of_not_every_of |
| other one (for another one) | rules | det.another_one; "the other" and "other ones" are correct |
| this + irregular plural (this children, this men, this criteria) | rules | det.these_not_this_<noun>; "this people" (a nation) and "that people" (conjunction) are left alone |
| other + singular noun (I need other option -> another option) | rules | det.another_not_other_singular ("the other", "any other", "no other" are right) |
| a own / the own (for my own, his own ...) | rules | det.own_not_article_i/we/you/he/she/they (subject pronoun within four verbs) |
| some in a negative (I don't have some money -> any) | rules | det.some_in_negative_money, det.some_in_negative_plural (0.84: "some" can be stressed on purpose) |
| these kind of / those sort of; all kind of / many type of / two sort of | rules | det.these_{kind,sort,type}_of, det.many_{kind,sort,type}_of |
| "the" before plural-form names (the Netherlands, the Philippines, the Bahamas, the Maldives, the Alps, the Andes ...) | rules | 17 rules det.the_<name>; target = preposition + name (in/to/from/across/near/of ...) |
| "the" before singular names that take it (the Hague, the Czech Republic, the United States, the Middle East, the Nile, the Atlantic, the Eiffel Tower, the Taj Mahal ...) | rules | 41 rules; names that double as modifiers ("United States dollars", "Atlantic City", "Nile Hotel") are only fixed before punctuation or a function word |
| "the" before UK, USA, US, EU, UN, UAE, USSR and organisations (the FBI, the CIA, the NHS, the BBC, the NBA ...) | rules | 21 rules det.the_<acronym>; fires only before punctuation or a function word so "UK law", "FBI files" stay |
| "the" before NATO, OPEC, NASA, UNESCO, UNICEF, Congress, Parliament | not a rule | these take no article |
| extra "the" before a country, city or continent (in the India, to the Mumbai, in the Europe, the Ukraine) | rules | det.no_the_asia/europe/africa/americas/indian_cities/world_cities; "the India of my youth" and "the Netherlands" are left alone |
| missing "the" before a unique thing (on the internet, in the sky, in the sun, on the moon, in the world, around the world) | rules | det.the_internet, det.the_sky, det.the_sun, det.the_moon, det.the_universe, det.the_world |
| in whole world / across entire country | rules | det.the_whole_world |
| missing "the" before a fixed place (in the kitchen, on the floor, in the garden, on the roof ...) | rules | 33 rules det.the_<place>; the noun must end the phrase, so "kitchen table" and "floor 3" stay; "to ground" (go to ground) and "from floor to ceiling" are left alone |
| at home, at work, at school, in bed, by car, on foot, at night, in town, on campus, in hospital (BrE), in prison, to church | not a rule | correct without an article |
| the WhatsApp, on the Facebook, open the Gmail | rules | det.no_the_app (not before a noun: "the Facebook page" is right) |
| as a result / on the other hand / on the contrary / in the meantime / at the same time / all of a sudden / once in a while / as a matter of fact / a matter of time (the article dropped) | rules | det.as_a_result ... det.a_matter_of_time |
| in the near future / in the coming days / in the next few days / for the first time / at the last minute / by the end of / in the middle of / for the rest of / to a certain extent | rules | det.in_the_near_future ... det.to_a_large_extent |
| in a row / as a whole / at the moment / on the whole / in the long run / for a while / in the beginning (tail-guarded) | rules | det.in_a_row, det.as_a_whole, det.at_the_moment, det.on_the_whole, det.in_the_long_run, det.for_a_while, det.in_the_beginning, det.in_the_end, det.at_first_glance |
| in morning / in afternoon / in evening (no "the") | rules | det.in_the_morning |
| on daily basis / on regular basis / on annual basis (missing a/an) | rules | det.on_a_basis_consonant, det.on_a_basis_vowel |
| in good mood / in difficult situation / in similar way / in easy way (article missing) | rules | det.in_a_mood_c, det.in_an_adj |
| in good shape / in good time / in good faith / in bad shape | not a rule | correct without an article |
| I am bit tired / I am little worried (missing a) | rules | det.a_bit_adjective, det.a_little_adjective |
| same without "the" (from same city, it is same, it's same problem) | rules | det.the_same_noun, det.the_same_copula, det.the_same_it_is |
| on second floor / on next page (ordinal + noun without the) | rules | det.the_ordinal_noun |
| is best way / is most important thing / is only one who / is main reason | rules | det.the_best_way, det.the_most_adj_noun, det.only_one_who |
| in first place | not a rule | "finished in first place" is correct; "in the first place" cannot be told apart by pattern |
| what's name of / what's problem / what's matter | rules | det.what_is_the_noun_of, det.what_is_the_problem |
| missing a/an after have / get / make / take / send / ask (I have question, take break, send email, give me ride ...) | rules | 116 rules det.missing_a_<noun> / det.missing_an_<noun>; each noun has its own verb list so "take note", "make profit", "need room" stay |
| take note of / make note of / need room / have class / make profit / have lunch | not a rule | correct without an article (mass or idiomatic) |
| bought new car / need big table (verb + adjective + singular noun, no article) | rules | det.missing_a_adjective_noun_consonant, det.missing_an_adjective_noun_vowel |
| it is good idea / that is great opportunity / this is important point (article missing after be + adjective) | rules | det.missing_a_after_copula_consonant, det.missing_an_after_copula_vowel |
| she is teacher / he is engineer / my brother is doctor / works as nurse (job without a/an) | rules | det.missing_a_profession_plain_c/mod_c, det.missing_an_profession_plain_v/mod_v and the _as_ versions; unique posts (president, director of) and "answer is doctor" are left alone |
| I am fan of / she became member of (role noun + of, no a/an) | rules | det.missing_a_member_of_consonant, det.missing_an_member_of_vowel |
| go to the work / go to the bed / go to the home / go to the school every day | rules | det.no_the_to_work, _bed, _home, _school, _college, _university, _church, det.no_the_kindergarten (school-type nouns only before a frequency word) |
| go to the school (a particular school), go to the bank, go to the hospital | not a rule | correct for a specific place |
| at the home / working from the home / at the night | rules | det.no_the_at_home, det.no_the_from_home, det.no_the_at_night |
| by the bus / by the train / by the car (way of travel) | rules | det.no_the_by_transport (needs a motion verb; "by the bus stop", "stood by the car" stay) |
| play the football / play the chess (sports and games with "the") | rules | det.no_the_sport; instruments (play the guitar) are right with "the" |
| speak the English / learn the Spanish (language name with "the") | rules | det.no_the_language (not before "language", "of ...", "class") |
| The life is too short / The nature has always (general statement with "the") | rules | det.no_the_life, det.no_the_nature, det.no_the_love_nature |
| the love / the happiness / the freedom / the money / the music is ... (can be specific) | not a rule | "the" is right for a specific one; no safe pattern |
| in the 1994 (year with "the") | rules | det.no_the_year ("the 1990s" and "the 1994 election" are right) |
| talk to the Mike (the before a first name) | rules | det.no_the_name (only before punctuation or a few function words; "the Mike from accounting" is right) |
| have the breakfast / had the dinner (meal with "the") | rules | det.no_the_meal |
| in the love with / by the mistake / by the heart / for the example / in the order to / on the vacation / the every day / the one of the best | rules | det.in_love_with, det.in_a_hurry_the, det.by_heart, det.by_mistake, det.for_example, det.in_order_to, det.on_vacation, det.the_every_day, det.the_each, det.the_one_of_the |
| I have the headache / I have the fever (an illness with "the") | rules | det.a_not_the_illness, det.an_not_the_illness; "have the flu" and "have the measles" are right |
| Few days ago, ... (sentence opens without "A") | rules | det.few_days_ago_start |
| need a help; more the chairs; another information | rules | det.need_help_no_a, det.more_the_plural, det.more_not_another_mass |
| close door / turn off lights / turn on AC / pass salt / click button (a known thing, no "the") | rules | 34 rules det.the_object_<thing>; needs a finite verb or a sentence start before it, so "closed door policy" and "the open door" stay |
| on train / in car / on bus / on plane (no "the") | rules | det.the_transport_car/train/bus/plane/flight/metro/subway/tram/ferry/boat/ship; "by train" and "by car" are right |
| at station / at airport / at hotel / at office / in office tomorrow (no "the") | rules | det.the_public_<place>, det.the_public_office, det.the_in_office, det.a_stay_hotel; "at home", "in hospital" (BrE) and "in office" for public office are right |
| go to store / went to bank / going to airport / go to gym / go to doctor (no "the") | rules | det.the_to_<place> (after a verb of going; "going to store the boxes" and "to bank" as a verb stay; "to school", "to church", "to bed", "to work" are right) |
| watched sunset / saw moon | rules | det.watch_the_sunset |
| Please find attached copy of ... | rules | det.attached_a_copy, det.attached_an_copy |
| Main goal of this project is ... (sentence opens without "The") | rules | det.the_main_noun, _primary_, _biggest_, _greatest_, _chief_, _principal_ |
| The most people I know work remotely | rules | det.most_people_i_know |
| don't have many time; little options | rules | det.much_time_not_many, det.little_to_few |
| an hour / an honest / an honor / an heir; a university / a European / a unique / a one-time / a useful | covered by base rule | grammar.a_vowel, grammar.an_consonant, grammar.article_sound (engine/src/determiners.rs `an_fits`) |
| an MBA, an FBI, an HTML, an SUV, an X, an F; a URL, a UFO, a USB, a US | covered by base rule | grammar.article_sound (uppercase initialisms by their first letter) |
| a NASA, a FIFA, a NATO, a SWAT (acronyms said as words) | known gap in base code | grammar.article_sound turns "a NASA mission" into "an NASA mission"; a pack rule cannot undo another rule's edit (see report) |
| an historic / an hotel / an herb | covered by base rule | article_sound prefers "a historic"; "an herb" is kept (American) |
| an SQL / a SQL, an FAQ / a FAQ, a MAC address, a SCSI | not a regex-safe rule | both articles are right, by how the writer says the letters |
| a 1990s, a 2000, an 1812 overture, an 1,800 acre | not a regex-safe rule | four-digit numbers are said both ways (nineteen ninety / one thousand nine ninety) |
| a data / a media / a bacteria / an alumni / an agenda / a staff / a people / a police / a scissors / a pants / a glasses | not a regex-safe rule | accepted by many writers (a data point, a staff member, a media company) or the singular is a different word |
| a work / a time / a space / a room / a paper / an experience / a water / a coffee / a hair / a chicken / a light / a glass / an iron / a business | not a regex-safe rule | these nouns have a countable meaning, so "a" is often right |
| a knowledge of / a good knowledge of / a wealth of / a lot of / a piece of / a bit of | not a rule | correct English |
| a bread / a rice / a cheese / a wine / a pasta / a milk (a kind of, or an order) | not a regex-safe rule | countable in the sense of a type or a portion |
| a permission / a help / a support / a training / a pressure / a freedom / a peace / a silence | not a regex-safe rule | "a help" is a rule only after need/want/get (det.need_help_no_a); the others are right with a modifier ("a great help", "a long silence") |
| this / these, that / those with a regular plural or singular noun (this cars, these car) | covered by base rule | grammar.demonstrative_number (determiners.rs) and grammar.this_that_be / these_those_be |
| that people / that children (that + irregular plural) | not a regex-safe rule | "that" is also the conjunction ("I know that people care") |
| much / many + regular plural (much cars), less + regular plural (less complaints) | covered by base rule | grammar.quantifier_number (determiners.rs), grammar.fewer_count, grammar.fewer_mass |
| both of the / all of the / each of the / half of the / most of the / none of the | not a rule | correct English |
| a half of the / the half of the | not a regex-safe rule | attested in careful writing ("a half of lager", "the half of the team that stayed") |
| all of / both the + singular noun | not a rule | "all of the information", "both the boys" are right |
| the some / the any / the many / the several (doubled determiners) | not a regex-safe rule | rare; "the many people who helped" is right |
| a the / an the / the a / this the / that the / a this | not a regex-safe rule | which of the two words to drop is a guess, and "that the" is the conjunction; the engine's repeated-word rule handles "the the" |
| the my / the your / the our / the their / a my / my the; the this / the these | rules | det.the_possessive, det.a_possessive, det.possessive_the (my only: "your the" is a slip for "you're the"), det.the_these; "the this" is left (the `this` keyword) |
| some / any in questions and conditions (if you have some questions / any idea) | not a rule | both are right |
| I have not any money / I do not have not any | not a rule | formal but correct; "no any" and "don't have no" are rules |
| few and little with other nouns (very few time; little friends) | rules | det.little_not_few_<noun>, det.little_to_few; the rest depends on meaning |
| every + number ("every two days") | not a rule | correct English |
| several / various / numerous + singular noun | not a regex-safe rule | needs a noun list that is never a mass noun; left to the model layer |
| a number of + singular verb / the number of + plural verb | not a rule in this pack | agreement (base grammar.amount_number, grammar.a_number_plural) |
| one of the + singular noun (one of the best player) | covered by base rule | usage.one_of_plural (selected nouns), usage.head_of_plural_is |
| at home / at work / at school / by car / on foot / at night / in town / on campus / in hospital / in bed | not a rule | correct without an article |
| the with Monday / in the Monday / on the weekend / at the weekend / in the weekend | not a regex-safe rule | prepositions pack; "on the Monday" is right for a particular day |
| the Gambia / the Sudan / the Congo / the Lebanon / the Yemen / the Ukraine (old usage) | rules (Ukraine only) | det.no_the_europe removes "the Ukraine"; the others vary by variety and decade |
| the Amazon / the Slack / the Word / the Teams (app, river or ordinary word) | not a regex-safe rule | det.no_the_app leaves out names that are also ordinary words or a river; "the Amazon" is right for the river |
| in the first place | not a regex-safe rule | "finished in first place" is also right |
| by end of day / by end of week / by end of month / until end of year | not a rule | accepted business shorthand (the everyday benchmark keeps "by end of day") |
| in future (BrE) / in hospital (BrE) / go to university (BrE) | not a rule | dialect forms that need the dialect setting |
| missing "a" after any other verb + a noun the pack does not list (get meeting, buy phone) | not a regex-safe rule | a closed list of nouns and verbs is the only safe form; open-ended versions would flag "have time", "take note", "need room" |
| go to park / went to bank as a verb ("I am going to park near the entrance") | not a regex-safe rule | "park", "store" and "bank" are also verbs; the to-place rules leave "park" out and guard "store" and "bank" with a tail |
