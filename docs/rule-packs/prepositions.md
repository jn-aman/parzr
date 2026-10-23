# Prepositions pack: coverage map

`engine/rules/packs/prepositions.json` holds 371 rules (id prefix `prep.`). Every rule has a required literal, a positive and a negative example written for it (the negatives carry the near misses: the noun use, the idiom, the valid preposition, the dialect form), and a confidence between 0.72 and 0.97. A rule fires only when the context makes the reading certain; where a construction is correct in some dialect or sense, the rule is narrower or absent (see "Deliberately left out").

Many patterns were generated from shared word lists and a trie-based "any word except…" fragment (the engine regex has no lookahead), so they are long; the JSON is the shipped source, and every rule carries its own positive and negative example.

## Verb + a preposition it does not take (the preposition is deleted)

The verb takes its object directly; the extra word is removed.

| Construction | Rules (`prep.` prefix) or base rule |
|---|---|
| discuss about + the / this / that / a / an / our / your, and + a pronoun (it, them, …) | covered by base rules `grammar.discuss_about` and `usage.discuss_about_pronoun` |
| discuss about + how / what / why / each / all / its / issues / options…, discusses about + anything | `discuss_about_more`, `discusses_about` |
| emphasize on, stress on (verb), highlight on, put emphasis to | `emphasize_on`, `stress_on_verb`, `highlight_on`, `put_emphasis_to` |
| comprise(s) of, contain(s) of, lack(s) of (verb) | `comprise_of`, `contain_of`, `lack_of_verb`, `lacks_of` |
| mention about, consider about, explain about, describe about | `mention_about`, `consider_about`, `explain_about`, `describe_about` |
| regarding to / about, concerning about, as regards to | `regarding_to`, `regarding_about`, `concerning_about`, `as_regards_to` |
| enter into / in / to (a room, a school), reach at / to, attend to / at / in (an event), visit to / at, join to / in, oppose to, resemble to, obey to, avoid from, await for, seek for, demand for, request for, appreciate for, affect on, influence on | `enter_into_place`, `enter_in_to_place`, `enter_in_to_institution`, `reach_at_to_place`, `reach_at_to_abstract`, `attend_to_event`, `attend_at_in_event`, `visit_to_verb`, `visit_at_place`, `join_to`, `join_in_organisation`, `oppose_to`, `resemble_to`, `obey_to`, `avoid_from`, `await_for`, `seek_for`, `demand_for_verb`, `request_for_verb`, `requested_for_active`, `to_request_for`, `appreciate_for`, `affect_on_verb`, `influence_on_verb` |
| marry / divorce with, ask / tell / inform / notify / advise / consult / phone / email to (a person), answer / approach / access / contact (verb) to or with | `marry_with`, `divorce_with_active`, `ask_to_person`, `tell_to_person`, `inform_to_person`, `notify_to`, `advise_to_person`, `consult_to`, `phone_to_person`, `email_to_person`, `request_to_person`, `answer_to_noun`, `approach_to_verb`, `approaching_to`, `access_to_verb`, `contact_to`, `contact_with` |
| arrive to home / here / there, cope up with, fill up a form, go to home / abroad / there, go to shopping | `arrive_to_home`, `cope_up_with`, `fill_up_form`, `go_to_home`, `go_to_abroad`, `go_to_there`, `go_to_activity` |
| prepositions that never take "of": except of, without of, within of, among of, between of, beside of, behind of, near of, across of, during of, upon of, until of, despite of | `except_of`, `without_of`, `within_of`, `among_of`, `between_of`, `beside_of`, `behind_of`, `near_of`, `across_of`, `during_of`, `upon_of`, `until_of`, `despite_of_more` |

## Verb + the wrong preposition (the preposition is replaced)

| Construction | Rules (`prep.` prefix) or base rule |
|---|---|
| depend of / from / in / to / with, dependent of / from, rely in / with, trust on, suffer of, benefit by / of, react on, invest on, specialize on, graduate at, result to, believe-type slips | `depended_of`, `depend_wrong_prep`, `dependent_of`, `rely_wrong_prep`, `rely_in_noun`, `depend_in_noun`, `trust_on_person`, `trust_on_thing`, `suffer_of`, `benefit_by_of`, `react_on`, `invest_on`, `specialize_on`, `graduated_at`, `result_to` |
| consist on / from / by, composed by, based from, base on | `consist_on_from_by`, `composed_by_parts`, `based_from`, `base_on_missing_d` |
| agree to a person, agree for terms, disagree to, differ to, participate to, participation to, worry of / on, congratulations for, apologize you / of, insist for, accuse for, accused for, blame of / about, take part to, take advantage from, take care for / on, make fun on / at / with, doubt on, complain on, laugh on, shout on, smile to, fall in love to / of / on, join in | `agree_to_person`, `agree_for_terms`, `disagree_to_person`, `differ_to`, `participate_to`, `participation_to`, `congratulations_for`, `apologize_object`, `apologize_of`, `insist_for`, `accuse_for_object`, `accused_for_passive`, `blame_of_about`, `take_part_to`, `take_advantage_from`, `take_care_wrong_prep`, `make_fun_wrong`, `doubt_on`, `complain_on_person`, `laugh_on`, `shout_on`, `smile_to_person`, `fall_in_love_pronoun`, `fall_in_love_of`, `worry_of_on` |
| hear to (listen to), thank to, I thank for, thanks you for, thank you on, thankful of, apply to a job, reply for, die by (an illness), look forward for / about, translate in (a language), convert in (a format), focus about / into / to, concentrate in / at | `hear_to_present`, `heard_to_past`, `hearing_to_progressive`, `thank_to_noun`, `thank_for_missing_you`, `thanks_you_for`, `thank_you_on`, `thankful_of`, `apply_to_job`, `reply_for`, `died_by_disease`, `look_forward_wrong`, `translate_in_lang`, `convert_in_format`, `focus_about`, `focus_into_abstract`, `focus_to`, `concentrate_in_at` |
| interested for, prefer … than, superior / inferior / preferable / prior / senior / junior than, compared than, similar with / than / like, same like / than, as + adjective + than | `interested_for`, `prefer_than_plural`, `prefer_than_gerund`, `prefer_than_bare`, `superior_than`, `inferior_than`, `preferable_than`, `prior_than`, `senior_than`, `compared_than`, `similar_with_than`, `similar_like`, `same_like_than`, `as_adjective_than` |

## Missing preposition

A verb or word that needs a preposition has none; the rule inserts it.

| Construction | Rules (`prep.` prefix) or base rule |
|---|---|
| listen (to) music / me, wait (for) the bus / me, search (for) a job, look (at) the picture, take a look (at), respond (to), refer (to) the attached document, apply (for) a job, depend (on) the weather | `listen_object`, `listen_pronoun`, `wait_object`, `wait_person`, `search_object`, `search_about`, `look_object`, `take_a_look_the`, `take_a_look_on`, `respond_missing_to`, `refer_missing_to`, `apply_missing_for`, `depend_missing_on` |
| knock (on) the door, pay attention on → to, give attention on → to | `knock_the_door`, `pay_attention_on`, `give_attention_on` |
| in front (of) the, regardless (of) the, according (to) the, prior (to) the, due (to) the, due of, because (of) him, instead (of) him, in spite (of) the, on behalf (of), look forward (to) your reply | `in_front_missing_of`, `regardless_missing_of`, `according_missing_to`, `prior_missing_to`, `due_missing_to`, `due_of`, `because_object_pronoun`, `instead_object_pronoun`, `in_spite_missing_of`, `on_behalf_missing_of`, `look_forward_missing_to` |

## Adjective, participle or noun + the wrong preposition

| Construction | Rules (`prep.` prefix) or base rule |
|---|---|
| afraid / scared / terrified from, angry / upset on a person, worried of / for, anxious of / on, curious of / on, aware about, familiar about / of, accustomed with / for, addicted with / of / on, allergic with / of / from, proud on / from / with, fond on / with, keen in / at, jealous from / on, ashamed from / with, loyal with / for, grateful of, thankful of | `afraid_from`, `angry_on_person`, `worried_of`, `worried_for_thing`, `anxious_of_on`, `curious_of_on`, `aware_about`, `familiar_about_of`, `accustomed_with_for`, `addicted_with_of_on`, `allergic_wrong_prep`, `proud_on_from`, `proud_with`, `fond_on_with`, `keen_in_at`, `jealous_from_on`, `ashamed_from_with_on`, `loyal_wrong_prep`, `grateful_of_on` |
| disappointed / impressed / delighted / pleased / happy of, excited / thrilled of, surprised of, shocked / amazed from, busy in work, capable for / in, good / bad in (a subject or -ing) | `disappointed_of`, `impressed_of`, `delighted_of`, `pleased_of`, `happy_of`, `excited_of`, `thrilled_of`, `surprised_of`, `shocked_of_from`, `amazed_of_from`, `busy_in_work`, `capable_for_in`, `good_in_subject`, `good_in_language`, `good_in_gerund` |
| responsible of, famous of, different of, equivalent with, compatible to, related with, contrary of / with, full with, rich of, known like, guilty for, married with a person | `responsible_of`, `famous_of`, `different_of`, `equivalent_with`, `compatible_to`, `related_with`, `contrary_wrong_prep`, `full_with`, `rich_of`, `known_like`, `guilty_for_legal`, `married_with_person`, `divorced_with_passive` |
| reason of, answer of (a question), key of success, cure of (an illness), recipe of (success), interest for, invitation for (an event), arrival to (a place), arrive to a place / a city | `reason_of`, `answer_of`, `key_of_abstract`, `cure_of_disease`, `recipe_of_abstract`, `interest_for`, `invitation_for_event`, `arrival_to_place`, `arrive_to_place`, `arrive_to_city`, `arrive_to_the_city` |
| in accordance / compliance to, in response of, in need for, in addition of, in comparison of, as compare to, in relation of, in connection of, in contrast of, with reference / regard of, in reference / regard of | `in_accordance_wrong`, `in_compliance_wrong`, `in_response_wrong`, `in_need_for`, `in_addition_of_with`, `in_comparison_wrong`, `as_compare_to`, `in_relation_wrong`, `in_connection_of`, `in_contrast_wrong`, `with_reference_wrong`, `in_reference_wrong`, `with_regard_wrong`, `in_regard_of` |

## Time, date and place

| Construction | Rules (`prep.` prefix) or base rule |
|---|---|
| at night / in the morning / in the evening | `work_in_night`, `at_part_of_day`, `in_part_of_day_no_article` |
| on Monday, in March, in 1998, on 5 March, at 5 pm | `in_at_weekday`, `on_month_after_event`, `on_year_after_event`, `in_day_month_date`, `in_at_clock_time` |
| on the weekend, last / next week, yesterday, at the age of | `in_the_weekend`, `in_last_next_period`, `on_last_next_period`, `on_yesterday`, `in_the_age_of_number` |
| since / for / from with durations and years | `lived_for_year`, `perfect_from_duration`, `from_time_instead_of_since`, `since_last_n_years`, `since_long_time` |
| between 5 to 10 → and, between 5 or 6 → and, from 9 am and 5 pm → to, from April and June → to | `between_numbers_to`, `between_days_months_to`, `between_numbers_or`, `from_time_and_time`, `from_month_and_month` |
| in the end of → at the end of, at the middle of, in the other hand, in one hand, in the contrary, on the same time, in conclusion, in this regards, in general, in average, in matter of fact, in advance, on a regular basis | `in_the_end_of`, `at_the_middle_of`, `in_the_other_hand`, `in_the_other_hand_mid`, `in_one_hand`, `on_other_hand_missing_the`, `in_the_contrary`, `in_contrary`, `on_the_same_time`, `as_a_conclusion`, `in_this_regards`, `on_general`, `in_average_phrase`, `in_matter_of_fact`, `thanks_on_advance`, `in_regular_basis` |
| at home, on vacation / holiday / leave / a trip / a diet / a break, in a hurry, at the airport | `in_home`, `in_vacation`, `in_holiday`, `in_leave`, `in_a_trip`, `on_a_diet`, `on_a_break`, `on_hurry`, `on_the_airport` |
| on the internet / TV / the phone / the third floor / the left side / top of the page / the same page | `in_the_internet`, `saw_in_tv_radio`, `talk_in_phone`, `talk_in_phone_bare`, `in_the_floor`, `in_ordinal_floor`, `in_left_right_side_of_screen`, `in_top_bottom_of_list`, `in_the_same_page` |
| on purpose, by this way, travel with train, from time to time, at first sight, at front of | `in_purpose`, `by_this_way`, `travel_with_vehicle`, `time_to_time`, `in_first_sight`, `at_front_of` |
| in my opinion, from my point of view | `opinion_boundary`, `point_of_view_boundary` |
| in terms of, on the basis of, by means of, on behalf of, as a result of, in case | `in_term_of`, `in_the_basis_of`, `on_basis_of_missing_the`, `by_the_means_of`, `on_behalf_wrong_prep`, `on_the_behalf_of`, `in_result_of`, `in_case_if` |
| on average / on behalf; among two → between; according to me | `among_two`, `according_to_me`, `with_respect_of`, `in_spite_missing_of` |

## A base verb after a preposition (one rule maps many verbs to their -ing form)

Each rule lists its verbs in one alternation of named capture groups, and the replacement rebuilds the -ing form (plain verbs add -ing; verbs ending in e drop it; short verbs such as get, put, run, begin double the last consonant). Verbs with a noun reading right after the preposition (work, rest, change, use, start…) and verbs whose -ing spelling differs by variety (travel, cancel) are left out of the lists.

| Construction | Rules (`prep.` prefix) or base rule |
|---|---|
| look forward to see → seeing | `look_forward_to_base_verb`, `look_forward_to_meet` |
| get used to live → living, I am used to wake → waking | `get_used_to_base_verb`, `am_used_to_base_verb` |
| capable to handle → of handling, prevent / discourage X to go → from going, insist to pay → on paying, succeed to pass → in passing | `capable_to_base_verb`, `prevent_object_to_verb`, `discourage_object_to_verb`, `insist_to_verb`, `succeed_to_verb` |
| difficulty to understand → in understanding, trouble to sleep → sleeping, worth to visit → visiting | `difficulty_to_verb`, `trouble_to_verb`, `worth_to_verb` |
| thanks for send → sending, sorry for be → being, good at speak → speaking, interested in learn → learning, responsible for manage → managing, how about go → going, prior to sign → signing, addicted to play → playing | `thanks_for_base_verb`, `thanks_for_noun_verb`, `sorry_for_base_verb`, `good_at_base_verb`, `interested_in_base_verb`, `responsible_for_base_verb`, `how_about_base_verb`, `how_about_go_to`, `prior_to_base_verb`, `addicted_to_base_verb` |
| before / without / despite to go → before going; before / after / without go; instead of go | `before_to_verb`, `without_to_verb`, `despite_to_verb`, `before_base_verb`, `after_base_verb`, `without_base_verb`, `instead_of_base_verb` |
| in order to getting → get, so as to saving → save | `in_order_to_ing_plain`, `in_order_to_ing_e`, `in_order_to_ing_dbl`, `so_as_to_ing_plain`, `so_as_to_ing_e`, `so_as_to_ing_dbl` |

## Doubled prepositions

"to to", "of of", "with with", "from from", "into into" and "about about". Not "in in", "on on", "by by" or "up up" (a phrasal verb meets a preposition: "log in in the morning"), and not "for for" or "at at" (a stranded preposition meets a second one: "the thing I was waiting for for ages", "what I am looking at at the moment"); "had had" and "that that" are fine too.

| Construction | Rules (`prep.` prefix) or base rule |
|---|---|
| doubled word | `double_to`, `double_of`, `double_with`, `double_from`, `double_into`, `double_about` |

## Deliberately left out

| Construction | Why it is not a rule |
|---|---|
| congratulate for, help me on (a task), called as, get engaged with, measured in weekdays | Accepted or sense-dependent after review: "congratulated the team for finishing" is in the dictionaries, "helped me on the migration" means working on it, "called as a witness" is a role, "get engaged with" means interact, and "in weekdays" is a unit. |
| above / below of, on the way of, keep on touch | Rare as errors and valid in captions ("the photo below of the bridge"), titles ("the way of tea") and interface text ("stays on touch"), so they were dropped after review. |
| suffer with (an illness) | Standard in British English ("she suffers with asthma"). A dialect-dependent rule belongs in Rust, not in a pack. |
| tired from / tired of, bored of, fed up of | Both prepositions are correct and mean different things (tired from work, tired of waiting); "bored of" and "fed up of" are British. |
| died with (cancer) | Medical writing distinguishes dying "with" a condition from dying "of" it; only "died by (an illness)" is flagged. |
| near to, opposite to, next to | "Near to" and "opposite to" are accepted British forms. |
| centre / center around, comprised of, off of, inside of, outside of, as per | Widely accepted modern usage or register choices, not errors. Style rules never flag preference. |
| independent from, different to, different than, different with, differ with | Accepted in one or more varieties ("independent of / from", British "different to", American "different than", "I differ with you"). |
| on time / in time, at night / in the night, on Monday / in the Monday morning edition, on the weekend (AmE) / at the weekend (BrE) | Correct pairs with different meanings or varieties; only the clearly wrong member of each pair is a rule. |
| in the end / at the end (meaning "finally" vs "at the finish") | Needs the sense; only "in the end of the month" (wrong in every sense) is a rule. |
| apologize about, angry at, excited for, surprised with, worried for a person, interested to | Standard or accepted in a common variety. |
| agree with a plan, agree on a plan, depend upon, rely upon, emphasize upon, focus upon | Correct. |
| than me / than I, between you and I | Pronoun case: owned by the pronouns pack and the base rule `grammar.between_you_i`. |
| discuss about 20 items, mention about a week ago, consider about 30 options | "about" meaning "approximately": the rules require a determiner or wh-word and skip numbers and quantity nouns. |
| accustomed to + base verb, used to + base verb after "be" | Literary and passive uses ("was accustomed to rise at six", "the tool is used to cut wire") are correct; only the clear "get used to + base verb" and "I am used to + base verb" are rules, the latter at lower confidence. |
| consider as, regard as | Accepted and common. |
| fill the form (without out / in) | The software sense ("the script fills the form") is correct, so only "fill up the form" is a rule. |
| marriage with (her), in the same time, in the way to (the office), at conclusion | Each has a valid reading ("her marriage with him" in historical prose, "In the same time, he wrote five" as a comparison of durations, "stood in the way to the airport", "On conclusion, the account is closed"), so each was dropped after review. |
| consist in several / the following / two | "Happiness consists in several small habits" is correct (consist in = lie in), so the pack no longer touches "consists in". |
| in regards to, with regards to | Widely used and listed as a variant by large dictionaries; the pack briefly had both and they fired on sentences annotators had left unchanged, so they were dropped. "regarding to", "regard of" and "with regard on" (wrong in every variety) are rules. |
| associated to, related with, compatible to | "Associated to" is routine in mathematical and technical writing; "related with" and "compatible to" stay as lower-confidence corrections because dictionaries give only "related to" and "compatible with". |
| instead to go, after to go, for to go | "Instead", "after" and "before" can be adverbs followed by a purpose infinitive ("he chose instead to work", "his parents moved shortly after to live abroad") and "for to" is archaic or stranded ("the courses you are looking for to help you"). Only "before to eat" (with a guard for "the day before to…"), "without to say" and "despite to wait" are rules. |
| by foot | Used by many native writers ("only reached by foot"); dictionaries list "on foot" as the standard form, so this is a preference. |
| before three days, before 3 minutes | "Before 3 minutes" can be a deadline ("answer before 3 minutes") and "before 1100 hours" is a time; the reading needs the sentence. |
| in the beginning of the film / book / year | Very common native usage ("at the beginning of" is the textbook form); only "in the end of the month" is a rule. |
| by the help of, in the favour of | Archaic or legal but valid English ("by the help of God", "exercised in the favour of such person"). |
| look my keys, prepare the exam, pay for the bill, fail in the exam, believe on, refer for, reply on, search the evidence | The intended preposition depends on the writer's meaning (look at / look for, prepare as a teacher or a student), or the form is valid in a sense a regex cannot tell apart. |
| shift focus to, return focus to, "focus" as a noun | Valid; the focus rules only fire on the verb ("focus to the task"). |
| "fall in love on the Internet", "fell in love to the music" | Valid; the rules only fire before a pronoun or "of". |
| prepositions before a gerund where the gerund form depends on dialect (travel → travelling / traveling, cancel → cancelling / canceling) | The -ing spelling differs by variety; those verbs are left out of the -ing rules. |

## Overlap with the base rules

`grammar.interested_in` (interested about / at / of / on), `grammar.depends_on` (depends of), `grammar.discuss_about` and `usage.discuss_about_pronoun` (discuss about + determiner or pronoun), `grammar.despite_of` (despite of + the / this / that / our / your), `grammar.between_you_i`, `usage.reply_to`, `usage.explain_to` and `usage.said_told` stay as they are. This pack adds the other forms and followers; the patterns are written so that a sentence is matched by only one of the two. No base file was edited.
