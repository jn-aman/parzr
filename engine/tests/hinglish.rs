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
fn everyday_hinglish_keeps_its_words() {
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
        // Hindi words keep their spelling; the sentence start takes its capital like any other.
        let mut expected = text[..1].to_uppercase();
        expected.push_str(&text[1..]);
        assert_eq!(fix(text), expected, "{text}");
    }
}

#[test]
fn english_slips_in_hinglish_are_still_fixed() {
    assert_eq!(
        fix("sab theek hai, dont worry"),
        "Sab theek hai, don't worry"
    );
    assert_eq!(fix("I recieved the file yaar"), "I received the file yaar");
    // "thik" alone in English is "think"; beside Roman Hindi it stays.
    assert_eq!(
        fix("I thik you're going to enjoy it."),
        "I think you're going to enjoy it."
    );
    assert_eq!(fix("ok thik hai"), "Ok thik hai");
}

#[test]
fn short_hindi_words_alone_in_english_stay_correctable() {
    // "tha", "ko", "wo" are Hindi beside other Hindi, and slips of English words otherwise.
    assert_eq!(fix("tha is teh best."), "That is the best.");
    assert_eq!(fix("Send me the main file."), "Send me the main file.");
}
