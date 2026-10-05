#![cfg(not(feature = "local-model"))] // Legacy rule-checker research, never the production model score.
use parzr_engine::{Mode, Request, TextRange, apply_edits, rewrite};
#[test]
fn short_contextual_typos_surface_before_sentence_punctuation() {
    for mode in [
        Mode::Fix,
        Mode::Professional,
        Mode::Friendly,
        Mode::Concise,
        Mode::Direct,
    ] {
        for (input, expected) in [
            ("this si too bod", "This is too bad"),
            ("that si very bod", "That is very bad"),
            ("it si not good", "It is not good"),
            ("This is too bod", "This is too bad"),
        ] {
            let result = rewrite(&Request {
                text: input.into(),
                mode,
                ..Request::default()
            })
            .unwrap();
            assert_eq!(result.text, expected, "{mode:?}: {input}");
            assert!(!result.edits.is_empty());
            assert_eq!(apply_edits(input, &result.edits).unwrap().0, expected);
            assert!(
                rewrite(&Request {
                    text: result.text,
                    ..Request::default()
                })
                .unwrap()
                .edits
                .is_empty()
            );
        }
    }
    for input in [
        "This si note is difficult.",
        "A friendly bod helped us.",
        "The nickname is Bod.",
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
    let dictionary = Request {
        text: "This is too bod".into(),
        dictionary: vec!["bod".into()],
        ..Request::default()
    };
    assert_eq!(rewrite(&dictionary).unwrap().text, dictionary.text);
    let mid_sentence = Request {
        text: "this si too bod".into(),
        sentence_start: false,
        ..Request::default()
    };
    assert_eq!(rewrite(&mid_sentence).unwrap().text, "this is too bad");
}
#[test]
fn workplace_corpus_corrects_errors_and_preserves_valid_english() {
    let corpus: serde_json::Value = serde_json::from_str(include_str!("corpus.json")).unwrap();
    let mut failures = vec![];
    for case in corpus["cases"].as_array().unwrap() {
        let input = case["input"].as_str().unwrap();
        let req = Request {
            text: input.into(),
            ..Request::default()
        };
        let result = rewrite(&req).unwrap();
        if result.text != case["expected"].as_str().unwrap() {
            failures.push(format!(
                "{}: {} → {} (expected {})",
                case["id"], input, result.text, case["expected"]
            ));
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
            "{} stable",
            case["id"]
        );
    }
    assert!(failures.is_empty(), "{}", failures.join("\n"));
}
#[test]
fn every_mode_finishes_with_grammar_spelling_and_punctuation() {
    for mode in [
        Mode::Fix,
        Mode::Professional,
        Mode::Friendly,
        Mode::Concise,
        Mode::Direct,
    ] {
        let req = Request {
            text: "i hope your doing well. We should sends teh report,please.".into(),
            mode,
            ..Request::default()
        };
        let result = rewrite(&req).unwrap();
        assert!(
            result.text.contains("We should send the report, please."),
            "{:?}: {}",
            mode,
            result.text
        );
        let final_fix = rewrite(&Request {
            text: result.text,
            ..Request::default()
        })
        .unwrap();
        assert!(final_fix.edits.is_empty(), "{:?} correctness", mode);
    }
}
#[test]
fn chained_fixes_keep_original_ranges_and_protected_spans() {
    let req = Request {
        text: "👩🏽‍💻\nThe informations are useful. Please note that teh mesage is ready.".into(),
        mode: Mode::Concise,
        protected_ranges: vec![TextRange {
            start_utf16: 7,
            end_utf16: 8,
        }],
        ..Request::default()
    };
    let result = rewrite(&req).unwrap();
    assert!(result.text.contains("The information is useful."));
    assert_eq!(
        apply_edits(&req.text, &result.edits).unwrap().0,
        result.text
    );
    assert!(
        rewrite(&Request {
            text: result.text,
            ..Request::default()
        })
        .unwrap()
        .edits
        .is_empty()
    );
}
#[test]
fn direct_action_keeps_a_separate_style_anchor() {
    let result = rewrite(&Request {
        text: "Could you review this?".into(),
        mode: Mode::Direct,
        ..Request::default()
    })
    .unwrap();
    assert_eq!(result.text, "Review this.");
    assert!(
        result
            .edits
            .iter()
            .any(|e| e.start_utf16 == 0 && e.end_utf16 == 10 && e.replacement.is_empty())
    );
    assert!(
        result
            .edits
            .iter()
            .any(|e| e.start_utf16 == 10 && e.end_utf16 == 11 && e.replacement == "R")
    );
}

#[test]
fn present_tense_rules_work_in_every_mode_without_breaking_other_clauses() {
    let corpus: serde_json::Value = serde_json::from_str(include_str!("corpus.json")).unwrap();
    for case in corpus["cases"].as_array().unwrap().iter().filter(|c| {
        c["id"].as_str().unwrap().starts_with("grammar.present_")
            || c["id"]
                .as_str()
                .unwrap()
                .starts_with("grammar.negative_base_")
    }) {
        let input = case["input"].as_str().unwrap();
        for mode in [
            Mode::Fix,
            Mode::Professional,
            Mode::Friendly,
            Mode::Concise,
            Mode::Direct,
        ] {
            let result = rewrite(&Request {
                text: input.into(),
                mode,
                ..Request::default()
            })
            .unwrap();
            if case["kind"] == "correction" {
                assert_ne!(result.text, input, "{} {:?}", case["id"], mode);
            }
            assert_eq!(apply_edits(input, &result.edits).unwrap().0, result.text);
            assert!(
                rewrite(&Request {
                    text: result.text,
                    ..Request::default()
                })
                .unwrap()
                .edits
                .is_empty()
            );
        }
    }
    for valid in [
        "I suggest that he go to school.",
        "It is important that she agree with you.",
        "He and she walk to work.",
        "What she does works well.",
        "Did he go to school?",
        "He can walk to work.",
        "She read the book yesterday.",
    ] {
        assert_eq!(
            rewrite(&Request {
                text: valid.into(),
                ..Request::default()
            })
            .unwrap()
            .text,
            valid
        );
    }
}
