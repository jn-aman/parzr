#![cfg(not(feature = "local-model"))] // Rule path only: the model path needs the bundled model.
//! Names that look like modals or verbs must neither oscillate nor be inflected or punctuated.
use parzr_engine::{Mode, Request, rewrite};

fn fix(text: &str) -> String {
    rewrite(&Request {
        text: text.into(),
        mode: Mode::Fix,
        ..Request::default()
    })
    .unwrap_or_else(|e| panic!("{text}: {e}"))
    .text
}

#[test]
fn modal_like_names_converge_and_keep_their_verbs() {
    for (input, expected) in [
        ("Will said hi.", "Will said hi."),
        (
            "Will said the meeting moved to Friday.",
            "Will said the meeting moved to Friday.",
        ),
        (
            "will said the meeting moved to Friday.",
            "Will said the meeting moved to Friday.",
        ),
        (
            "I think Will said the meeting moved.",
            "I think Will said the meeting moved.",
        ),
        ("May said yes.", "May said yes."),
        ("may said it is fine.", "May said it is fine."),
        (
            "I talked to Will he said yes.",
            "I talked to Will he said yes.",
        ),
        ("Hey Hope!", "Hey Hope!"),
        ("invite Rose to the party", "invite Rose to the party"),
    ] {
        assert_eq!(fix(input), expected, "{input}");
    }
}

#[test]
fn modal_verb_errors_are_still_corrected() {
    assert_eq!(fix("We should said this."), "We should say this.");
    assert_eq!(fix("He will goes home."), "He will go home.");
    assert_eq!(fix("Did she went home?"), "Did she go home?");
}

#[test]
fn lists_of_unknown_names_before_a_modal_do_not_oscillate() {
    for input in [
        "komal, nikhil and vivaan will join the call.",
        "srinivas, lavanya and harsha will join the call.",
        "an will join the call.",
    ] {
        assert!(
            rewrite(&Request {
                text: input.into(),
                mode: Mode::Fix,
                ..Request::default()
            })
            .is_ok(),
            "{input}"
        );
    }
}

#[test]
fn no_sentence_break_before_a_name_that_is_an_object_or_part_of_a_full_name() {
    for input in [
        "I talked to Aman and he said it is fine.",
        "I talked to Mark and he said it is fine.",
        "I talked to Zo\u{eb} and she said it is fine.",
        "I met Aman Jain, and Aman's friend said Aman Jain was kind.",
    ] {
        assert_eq!(fix(input), input);
    }
}
