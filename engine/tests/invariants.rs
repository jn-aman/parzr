#![cfg(not(feature = "local-model"))] // Legacy rule-checker research, never the production model score.
use parzr_engine::{Mode, Request, TextRange, apply_edits, process_json, rewrite};
fn request(text: &str, mode: Mode) -> Request {
    serde_json::from_value(serde_json::json!({"text":text,"mode":mode})).unwrap()
}
#[test]
fn plan_demonstrations() {
    for (input, expected) in [
        ("i hope your doing well.", "I hope you're doing well."),
        ("can you chek this once?", "Can you check this once?"),
        (
            "The logs is available here.",
            "The logs are available here.",
        ),
        ("I recieved your mesage.", "I received your message."),
    ] {
        let result = rewrite(&request(input, Mode::Fix)).unwrap();
        assert_eq!(result.text, expected);
    }
}
#[test]
fn protected_code_urls_paths_mentions_numbers_signatures() {
    let input = "I recieved this. Visit https://example.com/teh. Email teh@example.com. `teh` @teh #teh /tmp/teh 12.50\n```\nteh mesage\n```\n> teh mesage\n-- \nteh mesage";
    for mode in [
        Mode::Fix,
        Mode::Professional,
        Mode::Friendly,
        Mode::Concise,
        Mode::Direct,
    ] {
        let result = rewrite(&request(input, mode)).unwrap();
        assert!(result.text.contains("https://example.com/teh."));
        assert!(result.text.contains("teh@example.com"));
        assert!(result.text.contains("`teh` @teh #teh /tmp/teh 12.50"));
        assert!(result.text.ends_with("-- \nteh mesage"));
        assert!(result.text.contains("```\nteh mesage\n```"));
        assert!(result.text.contains("> teh mesage"));
    }
}
#[test]
fn unclosed_code_is_protected() {
    let input = "Check `teh mesage";
    assert_eq!(rewrite(&request(input, Mode::Fix)).unwrap().text, input);
}
#[test]
fn emoji_unicode_and_source_map() {
    let input = "👩🏽‍💻 i recieved your mesage. café 中文";
    let result = rewrite(&request(input, Mode::Fix)).unwrap();
    assert_eq!(apply_edits(input, &result.edits).unwrap().0, result.text);
    assert!(result.text.contains("👩🏽‍💻 I received your message."));
    assert!(result.text.ends_with("café 中文"));
    let mut prev = 0;
    for mapping in result.source_map {
        assert_eq!(mapping.output_start_utf16, prev);
        assert!(mapping.output_end_utf16 >= prev);
        prev = mapping.output_end_utf16;
    }
    assert_eq!(prev, result.text.encode_utf16().count());
}
#[test]
fn entity_and_negation_preservation() {
    let text = "I don't want to send 15 files on 2026-10-04. Could you not delete the link https://example.com?";
    for mode in [
        Mode::Fix,
        Mode::Professional,
        Mode::Friendly,
        Mode::Concise,
        Mode::Direct,
    ] {
        let result = rewrite(&request(text, mode)).unwrap();
        assert!(result.text.contains("15"));
        assert!(result.text.contains("2026-10-04"));
        assert!(result.text.contains("not delete"));
        assert!(result.text.contains("https://example.com?"));
        assert!(result.text.contains("don't") || result.text.contains("do not"));
    }
}
#[test]
fn dictionary_and_rich_spans() {
    let mut req = request("I recieved teh mesage.", Mode::Fix);
    req.dictionary = vec!["mesage".into()];
    req.protected_ranges = vec![TextRange {
        start_utf16: 11,
        end_utf16: 14,
    }];
    let result = rewrite(&req).unwrap();
    assert_eq!(result.text, "I received teh mesage.");
}
#[test]
fn invalid_ranges_and_size_fail_closed() {
    let mut req = request("😀", Mode::Fix);
    req.protected_ranges = vec![TextRange {
        start_utf16: 1,
        end_utf16: 2,
    }];
    assert!(rewrite(&req).is_err());
    assert!(rewrite(&request(&"x".repeat(65537), Mode::Fix)).is_err());
    assert!(process_json("{bad").contains("error"));
    assert!(process_json(r#"{"text":"x","mode":"invented"}"#).contains("error"));
}
#[test]
fn no_sentence_capitalization_mid_selection() {
    let mut req = request("check this once?", Mode::Fix);
    req.sentence_start = false;
    assert_eq!(rewrite(&req).unwrap().text, req.text);
}
#[test]
fn repeated_words_not_valid_had_had() {
    assert_eq!(
        rewrite(&request("The the report is ready.", Mode::Fix))
            .unwrap()
            .text,
        "The report is ready."
    );
    let good = "We had had enough.";
    assert_eq!(rewrite(&request(good, Mode::Fix)).unwrap().text, good);
}
#[test]
fn determinate_request_tones_preserve_timing() {
    let text =
        "I just wanted to ask if you could maybe send me the document when you get a chance.";
    for (mode, prefix) in [
        (Mode::Professional, "Could you "),
        (Mode::Friendly, "Could you please "),
        (Mode::Concise, "Please "),
        (Mode::Direct, "Send "),
    ] {
        let result = rewrite(&request(text, mode)).unwrap();
        assert!(
            result.text.starts_with(prefix),
            "{:?}: {}",
            mode,
            result.text
        );
        assert!(result.text.ends_with("when you get a chance."));
        assert_eq!(rewrite(&request(text, mode)).unwrap().text, result.text);
    }
}
#[test]
fn style_not_applied_by_fix() {
    let text = "We need to utilize this in order to reduce latency.";
    assert_eq!(rewrite(&request(text, Mode::Fix)).unwrap().text, text);
    assert_eq!(
        rewrite(&request(text, Mode::Concise)).unwrap().text,
        "We need to use this to reduce latency."
    );
}
#[test]
fn command_line_blocks_remain_exact() {
    let text = "Hi John,\n\nCan you chek below?\n\ncurl -X POST \\\n  https://api.example.com/v1/foo\n\nThanks,\nRiley";
    let result = rewrite(&request(text, Mode::Fix)).unwrap();
    assert!(result.text.contains("Can you check below?"));
    assert!(
        result
            .text
            .contains("curl -X POST \\\n  https://api.example.com/v1/foo")
    );
}
