#![cfg(not(feature = "local-model"))] // Rule-engine contract; the model build needs the bundled model.
use parzr_engine::{Request, apply_edits, process_json, rewrite};
fn run(json: serde_json::Value) -> serde_json::Value {
    serde_json::from_str(&process_json(&json.to_string())).unwrap()
}
#[test]
fn names_contract_is_accepted_and_unknown_fields_are_not() {
    let ok = run(
        serde_json::json!({"text":"ask aman jain about it","names":["Aman Jain"],"capitalize_names":true}),
    );
    assert_eq!(ok["text"], "ask Aman Jain about it");
    assert_eq!(ok["edits"][0]["rule_id"], "names.capitalize");
    assert_eq!(ok["edits"][0]["category"], "Style");
    assert!(run(serde_json::json!({"text":"x","name_index":[]}))["error"].is_string());
    assert!(run(serde_json::json!({"text":"x","names":vec!["a"; 2001]}))["error"].is_string());
}
#[test]
fn default_keeps_chat_behaviour_and_real_typos_are_fixed() {
    let off = run(serde_json::json!({"text":"ask aman jain about it","names":["Aman Jain"]}));
    assert_eq!(off["text"], "ask aman jain about it");
    for (input, expected) in [
        (
            "teh cat recieved the mesage",
            "the cat received the message",
        ),
        ("I will go and may said hi", "I will go and may said hi"),
    ] {
        let got =
            run(serde_json::json!({"text":input,"names":["Will","May"],"capitalize_names":true}));
        if input.starts_with("teh") {
            assert_eq!(got["text"], expected);
        } else {
            assert!(!got["text"].as_str().unwrap().contains("Will"));
        }
    }
}
#[test]
fn a_name_never_gets_punctuation_or_a_respelling() {
    let text = "I met Aman Jain, and Aman's friend said aman jain was kind.";
    let req: Request = serde_json::from_value(
        serde_json::json!({"text":text,"names":["Aman","Jain"],"capitalize_names":true}),
    )
    .unwrap();
    let result = rewrite(&req).unwrap();
    assert_eq!(
        result.text,
        "I met Aman Jain, and Aman's friend said Aman Jain was kind."
    );
    assert_eq!(apply_edits(text, &result.edits).unwrap().0, result.text);
    for e in &result.edits {
        assert_eq!(e.original.to_lowercase(), e.replacement.to_lowercase());
    }
}
