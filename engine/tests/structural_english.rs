#![cfg(not(feature = "local-model"))] // Legacy rule-checker research, never the production model score.
use parzr_engine::{Mode, Request, TextRange, apply_edits, rewrite};

const EXAMPLES: &[(&str, &str)] = &[
    ("Omar has broke the handle.", "Omar has broken the handle."),
    (
        "They have finish the repair.",
        "They have finished the repair.",
    ),
    (
        "The invitation was deliver this morning.",
        "The invitation was delivered this morning.",
    ),
    (
        "The draft is suppose to be done today.",
        "The draft is supposed to be done today.",
    ),
    ("I did not knew the route.", "I did not know the route."),
    ("Where did Anika went?", "Where did Anika go?"),
    ("Why does he asks twice?", "Why does he ask twice?"),
    ("We was excited.", "We were excited."),
    ("My cousins visits often.", "My cousins visit often."),
    (
        "Her neighbors wants a refund.",
        "Her neighbors want a refund.",
    ),
    (
        "The technicians checks the wiring.",
        "The technicians check the wiring.",
    ),
    (
        "One of these boxes are damaged.",
        "One of these boxes is damaged.",
    ),
    (
        "The children who plays outside need water.",
        "The children who play outside need water.",
    ),
    ("I enjoy to swim.", "I enjoy swimming."),
    (
        "They suggested to drive home.",
        "They suggested driving home.",
    ),
    (
        "I look forward to visit the island.",
        "I look forward to visiting the island.",
    ),
    (
        "Never she has forgotten the date.",
        "Never has she forgotten the date.",
    ),
    (
        "Not only Amir did stay, but he also helped.",
        "Not only did Amir stay, but he also helped.",
    ),
    (
        "The plan is clear We should share it.",
        "The plan is clear. We should share it.",
    ),
    (
        "Why is the door locked When will it open?",
        "Why is the door locked? When will it open?",
    ),
    (
        "We went to the office The guard was absent.",
        "We went to the office. The guard was absent.",
    ),
    ("I took teh umbrelal.", "I took the umbrella."),
    (
        "We have already complteed it.",
        "We have already completed it.",
    ),
    ("The boxesare heavy.", "The boxes are heavy."),
    (
        "Please checkthe attachment.",
        "Please check the attachment.",
    ),
    ("The issue is resolvde.", "The issue is resolved."),
    (
        "Anika can finish the remaiming work today.",
        "Anika can finish the remaining work today.",
    ),
    (
        "This is not how it is suppose to be donme.",
        "This is not how it is supposed to be done.",
    ),
    (
        "Yesterday, Aarav sends a parcel.",
        "Yesterday, Aarav sent a parcel.",
    ),
    (
        "Last night, we visit the theater.",
        "Last night, we visited the theater.",
    ),
];

const VALID: &[&str] = &[
    "Maya can finish the remaining work today.",
    "The result depends on careful planning and a clear report.",
    "She saw the blade.",
    "They will saw the timber.",
    "She has a saw.",
    "We have saw blades.",
    "I wish he were here.",
    "If she were here, we would be ready.",
    "I suggest that he leave now.",
    "The nurse and the doctor work together.",
    "The nurse and the doctor were ready.",
    "He left and the manager works here now.",
    "I appreciate your going to the trouble.",
    "I read The Great Gatsby.",
    "She told us that he doesn't work here anymore.",
    "The work was complete.",
    "The door is open.",
    "They walked to and fro all morning.",
    "Ew! That smells awful.",
    "Rarely has Kiran seen such a display.",
    "Not only did Kiran help, but she also stayed.",
    "The letter I is capitalized.",
    "We had had enough.",
    "He has work to do.",
    "She can leave tomorrow.",
    "These are saw blades.",
    "I told my friend I would call tomorrow.",
    "My brother thinks I should stay.",
    "The people who work on the station repair need an updated schedule.",
    "We focus on the station repair and finish today.",
];

#[test]
fn structural_fixes_work_in_all_modes_and_are_stable() {
    for mode in [
        Mode::Fix,
        Mode::Professional,
        Mode::Friendly,
        Mode::Concise,
        Mode::Direct,
    ] {
        for (input, expected) in EXAMPLES {
            let req = Request {
                text: (*input).into(),
                mode,
                ..Request::default()
            };
            let result = rewrite(&req).unwrap_or_else(|e| panic!("{input}: {e}"));
            // Tone modes may transform requests; correctness still must stabilize.
            if mode == Mode::Fix {
                assert_eq!(result.text, *expected, "{input}");
            }
            assert_eq!(apply_edits(input, &result.edits).unwrap().0, result.text);
            assert!(
                rewrite(&Request {
                    text: result.text.clone(),
                    ..Request::default()
                })
                .unwrap()
                .edits
                .is_empty(),
                "{input}: {}",
                result.text
            );
        }
    }
}

#[test]
fn valid_constructions_remain_unchanged() {
    for input in VALID {
        assert_eq!(
            rewrite(&Request {
                text: (*input).into(),
                ..Request::default()
            })
            .unwrap()
            .text,
            *input,
            "{input}"
        );
    }
}

#[test]
fn new_checks_preserve_unicode_code_dictionary_and_edit_ranges() {
    let text = "👩🏽‍💻 The invitation was deliver. `deliver donme` https://example.com/donme";
    let result = rewrite(&Request {
        text: text.into(),
        ..Request::default()
    })
    .unwrap();
    assert_eq!(
        result.text,
        "👩🏽‍💻 The invitation was delivered. `deliver donme` https://example.com/donme"
    );
    assert_eq!(apply_edits(text, &result.edits).unwrap().0, result.text);
    let text = "The draft is suppose to be donme.";
    let result = rewrite(&Request {
        text: text.into(),
        dictionary: vec!["donme".into()],
        protected_ranges: vec![TextRange {
            start_utf16: 13,
            end_utf16: 20,
        }],
        ..Request::default()
    })
    .unwrap();
    assert_eq!(result.text, text);
}

#[test]
fn narrative_repro_returns_minimal_corrections() {
    let text = "Yesterday I goes to the market and buyer some vegetables but the shopkeeper was not there so I was waiting for him many times. Then my friend come and tell me that he don’t works there anymore. We was confused because nobody was knowing where he went, so we just goes back home without buying nothing.";
    let result = rewrite(&Request {
        text: text.into(),
        ..Request::default()
    })
    .unwrap();
    assert_eq!(
        result.text,
        "Yesterday, I went to the market and bought some vegetables, but the shopkeeper was not there, so I waited for him for a long time. Then my friend came and told me that he did not work there anymore. We were confused because nobody knew where he had gone, so we just went back home without buying anything."
    );
    assert_eq!(apply_edits(text, &result.edits).unwrap().0, result.text);
    assert!(result.edits.len() >= 9);
}

#[test]
fn inversion_preserves_protected_name_and_requires_both_parts() {
    let text = "Not only Mira did help, but she also stayed.";
    let result = rewrite(&Request {
        text: text.into(),
        protected_ranges: vec![TextRange {
            start_utf16: 9,
            end_utf16: 13,
        }],
        ..Request::default()
    })
    .unwrap();
    assert_eq!(result.text, "Not only did Mira help, but she also stayed.");
    assert_eq!(result.edits.len(), 2);
    assert_eq!(result.edits[0].group_id, result.edits[1].group_id);
    assert!(
        result
            .edits
            .iter()
            .all(|e| e.end_utf16 <= 9 || e.start_utf16 >= 13)
    );
    assert!(apply_edits(text, &result.edits[..1]).is_err());
    let blocked = rewrite(&Request {
        text: text.into(),
        protected_ranges: vec![TextRange {
            start_utf16: 0,
            end_utf16: 13,
        }],
        ..Request::default()
    })
    .unwrap();
    assert_eq!(blocked.text, text);
}

#[test]
fn possessive_dictionary_tokens_remain_fully_protected() {
    let text = "Mira'sreport is ready.";
    let result = rewrite(&Request {
        text: text.into(),
        dictionary: vec!["Mira'sreport".into()],
        tokens: vec![parzr_engine::TokenHint {
            start_utf16: 0,
            end_utf16: 12,
            pos: "Noun".into(),
            lemma: "Mira'sreport".into(),
            name: true,
        }],
        ..Request::default()
    })
    .unwrap();
    assert_eq!(result.text, text);
    assert!(result.edits.is_empty());
}

#[test]
fn frequency_ranking_respects_grammatical_context() {
    for (input, expected) in [
        ("I waied by the entrance.", "I waited by the entrance."),
        ("I wazted by the window.", "I waited by the window."),
        (
            "The garden prozect is ready.",
            "The garden project is ready.",
        ),
        ("The easiet one is here.", "The easiest one is here."),
        (
            "I cannot find any szare folders.",
            "I cannot find any spare folders.",
        ),
        ("We saw the stationry shop.", "We saw the stationery shop."),
        ("She has waied for an hour.", "She has waited for an hour."),
    ] {
        let result = rewrite(&Request {
            text: input.into(),
            ..Request::default()
        })
        .unwrap();
        assert_eq!(result.text, expected, "{input}");
        assert_eq!(apply_edits(input, &result.edits).unwrap().0, expected);
    }
    for input in [
        "I wanted to wait by the entrance.",
        "The paper was wasted by the printer.",
        "The rights were waived by the owner.",
        "Protect the garden project.",
        "Share the spare folders.",
        "The stationary train is beside the stationery shop.",
        "This is the easier option.",
        "We revised the report and will revise it again.",
    ] {
        assert_eq!(
            rewrite(&Request {
                text: input.into(),
                ..Request::default()
            })
            .unwrap()
            .text,
            input
        );
    }
}

#[test]
fn nearby_typos_do_not_turn_object_nouns_into_verbs_or_drop_articles() {
    for (input, expected) in [
        (
            "We explaimn the bridge repair clearly.",
            "We explain the bridge repair clearly.",
        ),
        (
            "I visited the hardware store yesterday.",
            "I visited the hardware store yesterday.",
        ),
        (
            "During the road repair, workers take a break.",
            "During the road repair, workers take a break.",
        ),
        ("It needs aclear statement.", "It needs a clear statement."),
        ("They had calledus earlier.", "They had called us earlier."),
        (
            "It is the easiestone to use.",
            "It is the easiest one to use.",
        ),
        (
            "The peoplewho live here are friendly.",
            "The people who live here are friendly.",
        ),
        (
            "The manager thanked everone.",
            "The manager thanked everyone.",
        ),
        ("Each of the fils is here.", "Each of the files is here."),
        (
            "We left yesterday Jules has arrived.",
            "We left yesterday. Jules has arrived.",
        ),
        (
            "The group watched the coed team.",
            "The group watched the coed team.",
        ),
        (
            "Mira has never seen anyone revisea letter so quickly.",
            "Mira has never seen anyone revise a letter so quickly.",
        ),
        ("Please reveala secret.", "Please reveal a secret."),
        (
            "This is supposed to be Done.",
            "This is supposed to be done.",
        ),
        (
            "This is supposed to be DONE.",
            "This is supposed to be DONE.",
        ),
    ] {
        let result = rewrite(&Request {
            text: input.into(),
            ..Request::default()
        })
        .unwrap();
        assert_eq!(result.text, expected, "{input}");
    }
}
