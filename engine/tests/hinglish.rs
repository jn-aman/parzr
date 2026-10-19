#![cfg(not(feature = "local-model"))] // Rule path only: the model path needs the bundled model.
//! Hinglish (Roman Hindi mixed with English) is written, not misspelled: its words keep their
//! spelling and a code-mixed sentence is never "corrected" into English grammar.
use parzr_engine::{Request, apply_edits, rewrite};

fn fix(text: &str) -> String {
    let result = rewrite(&Request {
        text: text.into(),
        ..Request::default()
    })
    .unwrap();
    assert_eq!(apply_edits(text, &result.edits).unwrap().0, result.text);
    result.text
}

#[test]
fn everyday_hinglish_stays_as_typed() {
    for text in [
        "yaar kal meeting hai, theek hai?",
        "haan bhai, main aa raha hoon.",
        "kya scene hai yaar, bahut kaam hai.",
        "Thanks yaar, see you kal.",
        "nahi yaar, abhi nahi ho payega.",
        "arre bhai, mujhe pata nahi tha.",
        "ok accha thik hai, kal milte hain",
        "tum kaha ho, call karo",
        "wo log aa gaye kya?",
        "kuch nahi yaar, bas timepass",
        "PR review kar lena",
        "client ko call karna hai",
        "please ek baar check kar lo",
        "ye bug toh pehle bhi tha na",
        "mera laptop kaam nahi kar raha",
        "koi baat nahi, next time",
        "haan ji, done kar diya",
        "tension mat lo, ho jayega",
    ] {
        // Every sentence takes its capital, Hinglish included (owner rule, 2026-10-19); nothing
        // else in the sentence changes.
        let mut chars = text.chars();
        let opened: String = match text.strip_prefix("ok ") {
            Some(rest) => format!("OK {rest}"),
            None => chars
                .next()
                .map(|c| c.to_uppercase().chain(chars).collect())
                .unwrap_or_default(),
        };
        assert_eq!(fix(text), opened, "{text}");
    }
}

#[test]
fn english_slips_in_hinglish_are_still_fixed() {
    assert_eq!(
        fix("sab theek hai, dont worry"),
        "Sab theek hai, don't worry"
    );
    assert_eq!(fix("I recieved the file yaar"), "I received the file yaar");
}

#[test]
fn short_hindi_words_alone_in_english_stay_correctable() {
    // "tha", "ko", "wo" are Hindi beside other Hindi, and slips of English words otherwise.
    assert_eq!(fix("tha is teh best."), "That is the best.");
    // "chaat" is Hindi beside Hindi and a slip of "chat" in English.
    assert_eq!(
        fix("Do you have a minute to chaat?"),
        "Do you have a minute to chat?"
    );
    assert_eq!(fix("chaat khane chalein?"), "Chaat khane chalein?");
    // "thik" is Hindi beside Hindi ("thik hai") and a slip of "think" in English (English 1000).
    assert_eq!(
        fix("I thik you're going to enjoy the workshop."),
        "I think you're going to enjoy the workshop."
    );
    assert_eq!(fix("Send me the main file."), "Send me the main file.");
}
