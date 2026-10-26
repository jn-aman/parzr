# Confusable words, homophones and eggcorns (pack `confusions`)

Rule file: `engine/rules/packs/confusions.json`, id prefix `confuse.`, 568 rules. Every rule is a context-anchored pattern: the words around the target make the choice certain, so there is no bare word swap. Each carries a positive and a negative written for it, with the near misses (imperative, intransitive use, proper noun, idiom, the other word in its own frame) in the negative.

How to read the map: *construction* is the confusion; *rules* are the ids (without the `confuse.` prefix) that cover it; *base* names a rule that already existed in `usage.json`, `grammar.json`, `phrases.json` or the Rust engine, so no pack rule repeats it.

## Covered by this pack

| Construction | Rules |
|---|---|
| affect / effect / affective / effective | `affect_the_affect_of`, `affect_adj_on`, `affect_has_no_on`, `affect_a_adj_affect_end`, `affect_take_effect`, `affect_into_effect`, `affect_in_effect`, `affect_to_that_effect`, `affect_to_effect_adj`, `affect_for_effect`, `affect_just_for_effect`, `affect_personal_affects`, `affect_the_affects_of`, `affect_adj_affects`, `affect_effect_pronoun_obj`, `affect_effected_adverb`, `affect_i_was_effected`, `affect_effecting_pronoun`, `affect_how_it_effects`, `affect_modal_effect_group`, `affect_cost_affective`, `affect_more_affective_means`, `affect_affective_effective_fix`, `affect_affect_change` |
| then / than | `than_if_then`, `than_sequence_verb`, `than_sentence_start`, `than_since_then`, `than_back_just_then`, `than_no_sooner`, `than_more_often_then_not`, `than_more_adj_then`, `than_comparative_then` |
| lose / loose / loss / lost | `lose_loosing`, `lose_loose_weight`, `lose_loose_pounds`, `lose_lose_fit`, `lose_lose_after_feel`, `lose_the_loss_of`, `lose_i_loss`, `lose_great_lost_of` |
| accept / except / expect | `accept_except_that`, `accept_object_nouns`, `accept_expect_to`, `accept_was_excepted`, `accept_to_accept_for_all` |
| advice / advise (verb and noun frames) | `advice_verb_modal`, `advise_noun_give`, `advise_noun_possessive`, `advise_a_piece_of` |
| practice / practise (only frames wrong in both spellings), prophecy / prophesy | `practise_noun_det`, `practise_makes_perfect`, `practise_adjunct`, `practise_plural_noun`, `practise_prophecy_verb`, `practise_prophesy_noun` |
| principal / principle | `principal_named_principles`, `principal_principle_of_x`, `principal_matter_of`, `principal_school_principle`, `principal_principles_office` |
| complement / compliment / complementary / complimentary | `complement_complimentary_colors`, `complement_complementary_free`, `complement_compliment_to_the_x`, `complement_compliments_each_other`, `complement_compliments_the_x`, `complement_full_compliment`, `complement_pay_complement` |
| stationary / stationery | `stationary_stationery_office`, `stationary_stationery_shop`, `stationary_stationery_bike`, `stationary_stationery_remained` |
| discreet / discrete (and discretely / discreetly) | `discreet_be_discrete`, `discreet_discretely_verb`, `discreet_handled_discretely`, `discrete_discreet_units`, `discrete_discreet_math` |
| elicit / illicit | `elicit_illicit_verb`, `elicit_elicit_drugs`, `elicit_illicited`, `elicit_illiciting`, `elicit_illicits` |
| allude / elude / allusion / illusion / elusive | `allude_allude_me`, `allude_elude_to_inf`, `allude_eluded_to`, `allude_eludes_to`, `allude_eluding_to`, `allude_allusive_goal`, `allude_an_illusion_to`, `allude_optical_allusion2` |
| ensure / insure / assure (only the frames nobody accepts) | `ensure_insurance_against`, `ensure_insurance_for_amount`, `ensure_assure_you_that`, `ensure_insure_assure_you` |
| lay / lie / laid / lain / laying / lying | `lay_lie_modal_adverb`, `lay_lie_past_laid`, `lay_lie_past_participle`, `lay_lain_for_laid`, `lay_laying_lying`, `lay_lying_the_table`, `lay_layed`, `lay_lie_the_table`, `lay_lie_it_down` |
| eggcorns, mangled idioms and single-word slips (see list) | `idiom_nip_in_the_butt`, `idiom_case_and_point`, `idiom_toe_the_line`, `idiom_pique_peak_interest`, `idiom_pique_peaked`, `idiom_pique_peaking`, `idiom_sneak_peak2`, `idiom_reign_in`, `idiom_reigned_in2`, `idiom_free_rein_to`, `idiom_home_in_on`, `idiom_honed_in_on2`, `idiom_honing_in_on`, `idiom_pass_muster`, `idiom_deep_seeded`, `idiom_one_in_the_same2`, `idiom_doggy_dog`, `idiom_dog_eat_dog_hyphen`, `idiom_make_due2`, `idiom_piece_of_mind`, `idiom_all_of_a_sudden`, `idiom_by_and_large`, `idiom_scapegoat`, `idiom_hunger_pains`, `idiom_supposed_to`, `idiom_wreck_havoc`, `idiom_wrecks_havoc`, `idiom_wrecked_havoc`, `idiom_wrecking_havoc`, `idiom_tongue_in_cheek3`, `idiom_for_granite`, `idiom_tenterhooks`, `idiom_flesh_out`, `idiom_flesh_out_ed`, `idiom_sleight_of_hand`, `idiom_shoo_in`, `idiom_expatriate3`, `idiom_tide_you_over2`, `idiom_chest_of_drawers`, `idiom_prima_donna`, `idiom_harebrained`, `idiom_medieval`, `idiom_intact`, `idiom_albeit`, `idiom_apart_of`, `idiom_fall_a_part`, `idiom_border_a`, `idiom_border_c`, `idiom_border_d`, `idiom_boarder_take_in`, `idiom_capitol_hill`, `idiom_capital_gains`, `idiom_cereal_killer`, `idiom_serial_bowl` |
| coarse / course / of course | `course_of_coarse2`, `course_coarse_of_action`, `course_course_of_the`, `course_golf_coarse`, `course_course_sand` |
| corps / corpse | `corps_dead_corps`, `corps_peace_corpse` |
| defuse / diffuse | `defuse_diffuse_tension`, `defuse_diffusing`, `defuse_diffused`, `defuse_defuse_light` |
| flaunt / flout | `flout_flaunt`, `flout_flaunts`, `flout_flaunted`, `flout_flaunting`, `flout_flout_wealth` |
| imply / infer | `infer_imply_data`, `infer_imply_from2` |
| prostate / prostrate | `prostate_prostrate`, `prostate_prostrate_verb` |
| choose / chose / chosen | `choose_to_chose`, `choose_yesterday_choose` |
| cloth / clothes | `cloth_clothes` |
| learn / teach | `learn_me`, `learned_me`, `teach_from_mistakes` |
| remind / remember | `remind_remember_me` |
| say / tell | `say_tell_me`, `tell_to_me3` |
| rise / raise | `rise_prices_raise`, `rise_rise_the_price`, `rise_risen_the` |
| sit / set | `sit_set_down`, `sit_sit_the_table` |
| fall / fell | `fall_fell_modal` |
| beside / besides | `beside_besides_sit`, `beside_beside_start` |
| etc. | `eg_and_etc2`, `eg_etc_ect` |
| to / too / two / four | `too_to_adj`, `too_too_verb`, `too_two_verb`, `too_to_end`, `too_the_two`, `four_for_numbers2` |
| were / where | `where_were_place`, `where_know_were3` |
| which / witch | `witch_wicked_which`, `witch_which_one` |
| pole / poll | `pole_poll_opinion2`, `pole_poll_opinion3`, `pole_poll_flag`, `pole_poll_vault` |
| pore / pour | `pore_pour_over`, `pore_pouring_over`, `pore_poured_over2`, `pore_pore_water` |
| precede / proceed | `precede_proceed_with`, `precede_proceeded_the`, `precede_proceeds_the` |
| presence / presents | `presents_presence_of_mind`, `presents_in_the_presence`, `presents_wrap_presence` |
| patience / patients | `patience_thanks`, `patience_virtue` |
| role / roll | `roll_role_model2`, `roll_play_a_roll2`, `roll_role_call`, `roll_role_the_dice`, `roll_cinnamon_role2` |
| sight / site / cite | `sight_site_web2`, `sight_lose_site_of`, `sight_out_of_site2`, `sight_cite_sight`, `sight_cite_site` |
| sole / soul | `sole_soul_mate`, `sole_soul_purpose`, `sole_body_and_soul2` |
| stake / steak | `stake_steak_beef2`, `stake_steak_hold`, `stake_high_steaks`, `stake_steak_out2` |
| steal / steel | `steel_steal_stainless`, `steel_steal_verb` |
| suit / suite / lawsuit | `suite_hotel_suit`, `suite_wear_suite`, `suite_bathing_suite`, `suite_follow_suite`, `suite_law_suite2`, `suite_will_suite` |
| taught / taut | `taut_pull_taught`, `taut_taut_me` |
| vain / vein | `vain_in_vein`, `vain_blood_vain`, `vain_so_vein` |
| waist / waste | `waste_waist_of`, `waste_waist_food`, `waste_waist_verb` |
| waive / wave | `waive_wave_fee2`, `waive_waved_fee`, `waive_waving_fee`, `waive_waive_goodbye` |
| weak / week | `week_weak_ago`, `week_weaks_plural`, `week_last_weak2`, `week_per_weak2`, `week_looks_week` |
| yoke / yolk | `yolk_egg_yoke2`, `yolk_throw_off`, `yolk_ox_yolk` |
| dual / duel | `duel_dual_at_dawn2`, `duel_duel_core` |
| envelop / envelope | `envelope_envelop_noun`, `envelope_envelope_verb` |
| heroin / heroine | `heroine_heroin_lead`, `heroin_heroine_addiction` |
| knew / new | `knew_a_knew`, `knew_i_new_that` |
| lead / led | `led_has_lead`, `led_to_led`, `led_pencil_led`, `led_led_poisoning` |
| lightning / lightening | `lightning_lightening_bolt`, `lightning_thunder_and` |
| loath / loathe | `loathe_loath_verb`, `loathe_loathe_to` |
| moral / morale | `morale_moral_low`, `morale_morale_compass` |
| passed / past | `past_pronoun_past`, `past_the_passed_few` |
| plain / plane | `plane_fighter_plain`, `plane_board_the_plain`, `plain_plane_sight` |
| right / write / rite | `rite_right_of_passage`, `rite_rights_of_passage2`, `write_right_code`, `write_that_is_write`, `write_turn_write` |
| rain / reign / rein | `rain_reign_supreme`, `rain_rains_supreme`, `rain_reign_check`, `rain_reigndrops`, `rain_reigns_cats`, `rein_rein_supreme`, `rein_keep_a_tight_reign` |
| device / devise | `device_to_device2`, `device_devise_driver` |
| hear / here | `hear_is_hear`, `hear_can_here_the` |
| a lot / alot / allot | `lot_allot_of`, `lot_a_lot_time2` |
| everyday / every day | `everyday_every_day_life`, `everyday_each_and_everyday` |
| altogether / all together | `altogether_all_together`, `altogether_put_it2`, `altogether_not_all_together`, `altogether_all_together_different3` |
| anytime / any time | `anytime_at_anytime`, `anytime_anytime_of` |
| into / in to | `into_came_into_see`, `into_translate_in_to3` |
| onto / on to | `onto_load_on_to` |
| awhile / a while | `awhile_for_awhile`, `awhile_been_awhile` |
| maybe / may be | `maybe_it_maybe`, `maybe_sentence_may_be` |
| bear / bare | `bare_bear_minimum`, `bear_bare_fruit` |
| brake / break | `brake_hit_the_breaks`, `brake_hit_the_break`, `break_take_a_brake`, `break_lunch_brake`, `break_to_brake_up2` |
| breath / breathe | `breath_to_breath_in`, `breath_your_breathe` |
| conscience / conscious | `conscience_guilty_conscious` |
| council / counsel | `council_town_counsel`, `council_city_counsel_voted`, `counsel_to_council`, `counsel_marriage_council2` |
| desert / dessert | `desert_dessert_choc`, `desert_dessert_menu`, `desert_for_desert`, `desert_dessert_sahara`, `desert_dessert_island`, `desert_to_dessert_verb3` |
| peace / piece | `peace_piece_talks` |
| wait / weight | `weight_wait_loss`, `weight_gain_wait`, `wait_weight_for` |
| meet / meat | `meet_nice_to_meat`, `meat_red_meet` |
| son / sun | `son_sunscreen`, `son_my_only_sun2`, `son_father_and_sun` |
| Compound noun used as a verb, with the verb frames that decide it (modal, "to" after want/need/try/..., "please", "let's"): 51 compounds | `blackout_as_verb`, `blowout_as_verb`, `breakdown_as_verb`, `breakout_as_verb`, `buildup_as_verb`, `buyout_as_verb`, `checkin_as_verb`, `checkup_as_verb`, `comeback_as_verb`, `cooldown_as_verb`, `countdown_as_verb`, `crackdown_as_verb`, `cutoff_as_verb`, `dropout_as_verb`, `getaway_as_verb`, `handoff_as_verb`, `holdup_as_verb`, `hookup_as_verb`, `knockout_as_verb`, `letdown_as_verb`, `lineup_as_verb`, `lockdown_as_verb`, `lockout_as_verb`, `makeup_as_verb`, `markdown_as_verb`, `meltdown_as_verb`, `mixup_as_verb`, `optin_as_verb`, `payback_as_verb`, `payoff_as_verb`, `payout_as_verb`, `playback_as_verb`, `printout_as_verb`, `pushback_as_verb`, `roundup_as_verb`, `rundown_as_verb`, `shakeup_as_verb`, `signin_as_verb`, `signout_as_verb`, `slowdown_as_verb`, `spinoff_as_verb`, `startup_as_verb`, `stopover_as_verb`, `takeout_as_verb`, `teardown_as_verb`, `tuneup_as_verb`, `turnaround_as_verb`, `turnout_as_verb`, `walkout_as_verb`, `walkthrough_as_verb`, `workaround_as_verb` |
| Phrasal verb used as a noun, with the noun frames that decide it (determiner or adjective before, a noun-like word after): 73 compounds | `backup_as_noun`, `blackout_as_noun`, `blowout_as_noun`, `breakdown_as_noun`, `breakout_as_noun`, `breakup_as_noun`, `buildup_as_noun`, `buyout_as_noun`, `checkin_as_noun`, `checkout_as_noun`, `checkup_as_noun`, `cleanup_as_noun`, `comeback_as_noun`, `cooldown_as_noun`, `countdown_as_noun`, `crackdown_as_noun`, `cutoff_as_noun`, `dropoff_as_noun`, `dropout_as_noun`, `followup_as_noun`, `getaway_as_noun`, `handoff_as_noun`, `holdup_as_noun`, `hookup_as_noun`, `kickoff_as_noun`, `knockout_as_noun`, `layoff_as_noun`, `layout_as_noun`, `letdown_as_noun`, `lineup_as_noun`, `lockdown_as_noun`, `lockout_as_noun`, `login_as_noun`, `logout_as_noun`, `lookup_as_noun`, `makeup_as_noun`, `markdown_as_noun`, `meltdown_as_noun`, `mixup_as_noun`, `optin_as_noun`, `payback_as_noun`, `payoff_as_noun`, `payout_as_noun`, `pickup_as_noun`, `playback_as_noun`, `printout_as_noun`, `pushback_as_noun`, `rollback_as_noun`, `rollout_as_noun`, `roundup_as_noun`, `rundown_as_noun`, `sendoff_as_noun`, `setup_as_noun`, `shakeup_as_noun`, `shutdown_as_noun`, `signin_as_noun`, `signout_as_noun`, `signup_as_noun`, `slowdown_as_noun`, `spinoff_as_noun`, `startup_as_noun`, `stopover_as_noun`, `takeout_as_noun`, `takeover_as_noun`, `tuneup_as_noun`, `turnaround_as_noun`, `turnout_as_noun`, `wakeup_as_noun`, `walkout_as_noun`, `walkthrough_as_noun`, `warmup_as_noun`, `workaround_as_noun`, `workout_as_noun` |
| Further homophone frames (bread/bred, lesson/lessen, deer/dear, flour/flower, heel/heal, idol/idle, aisle/isle, knight/night, navel/naval, pale/pail, pear/pair, pedal/peddle, pray/prey, profit/prophet, wrap/rap, wreak/reek, sale/sail, scene/seen, stare/stair, strait/straight, wine/whine, excess/access, adopt/adapt, bury/berry, blue/blew, bridal/bridle, ceiling/sealing, sell/cell, sent/cent/scent, chord/cord, cymbal/symbol, dough/doe, flee/flea, guerrilla/gorilla, horde/hoard, horse/hoarse, loan/lone, medal/meddle/metal/mettle, muscle/mussel, peel/peal, seem/seam, sheer/shear, soar/sore, tail/tale, throne/thrown, cue/queue, buy/by/bye, angle/angel, altar/alter, martial law, scot-free, eke out, beck and call, vice versa, woe is me, supposedly, in regard to) | `x_bred_bread`, `x_bread_bred`, `x_lesson`, `x_dear_sir`, `x_deer_dear`, `x_flour2`, `x_flower`, `x_head_over_heels`, `x_achilles_heal`, `x_idol`, `x_idle`, `x_aisle`, `x_night_armor`, `x_knight_medieval`, `x_belly_navel`, `x_pale`, `x_pear`, `x_pear_fruit`, `x_pedal2`, `x_peddle2`, `x_prey`, `x_pray`, `x_profit`, `x_rap_up2`, `x_rap_music`, `x_rap_sheet2`, `x_reek_havoc2`, `x_garage_sail`, `x_set_sale`, `x_crime_scene`, `x_seen_scene`, `x_stare_at2`, `x_stairs_at`, `x_strait_of`, `x_dire_straits`, `x_straitjacket`, `x_wine`, `x_whine2`, `x_excess_access`, `x_excess_baggage`, `x_adopt_a_dog3`, `x_adapt_to`, `x_bury`, `x_blue`, `x_blew2`, `x_bridal`, `x_ceiling`, `x_sell3`, `x_cell_tower2`, `x_sent2`, `x_scent`, `x_chord`, `x_cymbal`, `x_symbol_of`, `x_dough`, `x_flee2`, `x_flea`, `x_guerrilla`, `x_horde`, `x_hoard`, `x_horse2`, `x_hoarse`, `x_loan`, `x_medal`, `x_meddle2`, `x_heavy_metal`, `x_mettle`, `x_muscle2`, `x_peel`, `x_peel2`, `x_seem2`, `x_seems`, `x_sheer`, `x_soar`, `x_sore`, `x_wag_tale`, `x_tail_light`, `x_throne2`, `x_thrown`, `x_on_cue`, `x_buy`, `x_say_bye`, `x_angle`, `x_altar`, `x_martial_law`, `x_sooner_rather`, `x_eke_out2`, `x_beck_and_call`, `x_vice_versa`, `x_woe_is_me`, `x_supposedly`, `x_in_regard_to` |

## Already covered by a base rule (no pack rule added)

| Construction | Base rule |
|---|---|
| would/could/should/must/might of | `grammar.could_have_of`, `phrases.json` (could of, would of, should of, must of, might of) |
| then/than after a comparative, "different then", "rather ... then", ", than we" | `grammar.comparison_then`, `grammar.different_than_then`, `usage.rather_than`, `usage.then_sequence` |
| lose/loose after "to/you/we/they/don't/not/never/gonna/could/will"; loose after is/was/got/too/so | `usage.lose_verb`, `usage.loose_adjective`, `grammar.realword_lose` |
| accept/except: "everyone accept Maria", ", accept for the", "please except our" | `usage.except`, `usage.except_for`, `grammar.realword_accept` |
| advice/advise after please/can you/I/we/they | `usage.advise`, `grammar.possessive_advice_past`, `grammar.uncountable_advices` |
| affect/effect: "side affect", "the affect on", "effect me" after a modal | `usage.effect_noun`, `usage.effect_noun_article`, `usage.affect_verb`, `grammar.realword_effect_noun` |
| principal/principle: "principle cause", "core principal", "in principal" | `usage.principal`, `usage.principle`, `usage.in_principle` |
| complement/compliment: "kind complement", "thanks for the complement", "complemented me on" | `usage.compliment`, `usage.compliment_thanks`, `usage.compliment_verb` |
| who's/whose, your/you're, its/it's, their/there/they're, to/too after "be", hear/here, know/no, weak/week | `usage.whose`, `usage.whose_noun`, `grammar.your_doing`, `usage.its_contraction`, `usage.there_place`, `usage.too_degree`, `usage.hear`, `usage.know_*`, `usage.weak_week` |
| piece/peace "a peace of", whole/hole, wear/where, whether/weather, bare/bear "can't bare", fare/fair, plane/plain, threw/through, quiet/quite, breath/breathe, later/latter, personal/personnel, counsel/council (legal), moot/mute, hire/higher, allowed/aloud, board/bored, forth/fourth ("back and fourth"), eight/ate | the matching `usage.*` rules |
| "for all intensive purposes", "bare in mind", "baited breath", "wet your appetite", "in one foul swoop", "trail and error", "old wives tale", "per say", "in lieu" | `usage.intents_and_purposes`, `phrases.json` |
| irregardless, could care less, anyways, equally as, lay/lie "to lay down", lend/borrow | `usage.irregardless`, `usage.could_care_less`, `usage.anyways`, `usage.equally_as`, `usage.lie_down`, `usage.lying_down`, `usage.lend_object`, `usage.borrow_possession` |
| everyday used as an adverb ("log in everyday"), setup/backup/login/checkout/signup/workout/pickup/shutdown/takeover/rollout/cleanup/kickoff/lookup/followup/dropoff/warmup/wakeup/breakup/logout/sendoff/writeup/handover used as a verb | Rust `compounds.rs` (`PHRASAL`, the `everyday` arm) |
| alot, eachother, aswell, infront, inbetween, infact, noone, ontop, afterall | `phrases.json`, `spelling` tables |
| there/their/they're, then/than, to/too in common frames, lie/lay "perfect participle" | `grammar.perfect_participle`, `grammar.used_to`, `grammar.perfect_chose`, `grammar.auxiliary_base`, `grammar.explicit_past_time` |

## Deliberately left out

| Construction | Why |
|---|---|
| farther / further; who / that; among / between; can / may; bring / take; try and; cannot / can not; historic / historical; literally; nauseous; reticent; disinterested | Accepted variants or a real distinction of register. A rule would flag correct English. |
| fewer / less and amount / number | Owned by the articles-determiners pack and base `grammar.fewer_count`, `grammar.fewer_mass`, `grammar.amount_number`. |
| alright | Established informal spelling in every major dictionary; not an error. |
| practice / practise as a verb, licence / license, defence / defense, programme | Dialect spellings. Only the noun frames that are wrong in both varieties (a "practise", "practise makes perfect") are flagged. |
| emigrate / immigrate | "emigrated to Canada" and "immigrated from India" are both normal; no frame decides it without the writer's viewpoint. |
| tortuous / torturous | Writers use "torturous" for both senses and dictionaries accept the overlap; no certain frame. |
| imply / infer ("what are you inferring?") | Needs to know who is speaking; only the source-as-subject ("the data infers") and "imply from" frames are flagged. |
| ensure / insure / assure when meaning "make certain" | Merriam-Webster and Collins accept all three; the first run of the false-alarm gate showed these frames in correct prose, so only the insurance and "assure you" frames remain. |
| e.g. / i.e. | Which one is meant depends on the writer's intent; the cue words ("for example", "that is") that would decide it are rarely written next to the abbreviation. |
| main/mane, weigh/way, tear/tier, new/knew in many other frames | Only the frames that were certain are included; the rest are for the language-model swap check (`confusion.rs`). |
| take the reigns (reins) | The rule fired correctly but the corrected text was changed back by another layer in the same check, so the engine reported "Corrections did not stabilize". Dropped until that layer is fixed. |
| seasonal effective disorder | Same problem: `spelling.delete_index` rewrites "affective" to "effective", so the corrected text is changed back. |
| hone in / honed in on | Listed in the dictionaries as a standard variant of "home in"; kept as a Style suggestion at 0.75, never a correction. |

## Interactions found while building (base behaviour, not edited)

- `grammar.auxiliary_base` rewrites "lay off" to "lie off" after a modal ("They might lay off some workers" becomes "They might lie off some workers"). It is a base false alarm; the pack drops its own `layoff` verb rule so it does not feed it.
- `grammar.subject_third` changes the imperative "Come sit down" to "Come sits down".
- `grammar.adverb_position` moves "never" in "I would never give" to "I never would give".
- Rules that a base rule or the Rust compound check already fires on are not duplicated: `engine_check` showed each remaining pack rule fires on its positive.
