//! Hinglish: Roman Hindi written beside English ("kal meeting hai", "PR review kar lena").
//! The word lists live in `spelling` (`spelling::hinglish`, `spelling::roman_hindi`); this module
//! decides which sentences are code-mixed and screens a finished check's edits, so English grammar
//! never "corrects" a Hindi sentence into nonsense ("check kar lo" to "checks kar lo").
use crate::{Edit, spelling, tokenizer::Token};
use std::collections::{HashMap, HashSet};

/// A sentence, as (paragraph, sentence) of its tokens.
type Sentence = (usize, usize);

/// Sentences that Roman Hindi carries: two Roman Hindi words, or one that is at least a third of
/// the sentence's words ("Thanks yaar", "kal pakka"). One Hindi word in an English sentence ("He
/// is a very accha person") leaves the sentence English.
pub fn code_mixed(tokens: &[Token<'_>]) -> HashSet<Sentence> {
    let mut counts: HashMap<Sentence, (usize, usize)> = HashMap::new();
    for (i, t) in tokens.iter().enumerate().filter(|(_, t)| t.is_word) {
        let (words, hindi) = counts.entry((t.paragraph, t.sentence)).or_default();
        *words += 1;
        if spelling::roman_hindi(tokens, i) {
            *hindi += 1;
        }
    }
    counts
        .into_iter()
        .filter(|(_, (words, hindi))| *hindi >= 2 || *hindi >= 1 && hindi * 3 >= *words)
        .map(|(sentence, _)| sentence)
        .collect()
}

/// The on-device models' edits: trained on English, they read Roman Hindi as broken English.
fn from_model(e: &Edit) -> bool {
    e.rule_id
        .split('+')
        .any(|r| r.starts_with("gector") || r.starts_with("context.") || r == "local-model")
}

/// Only the case of the text changes ("kal" to "Kal" at a sentence start).
fn case_only(e: &Edit) -> bool {
    !e.original.is_empty() && e.original.to_lowercase() == e.replacement.to_lowercase()
}

/// Drops the edits English grammar gets wrong in Hinglish, and their linked partners:
/// - any edit that changes a Roman Hindi word other than by case ("ko" to "to", "kaha" to "kana");
/// - in a code-mixed sentence, every edit but a rule's spelling, capitalization or punctuation fix
///   ("recieved", "dont", a sentence's capital); grammar, agreement and the models' edits go.
///
/// Returns whether anything was dropped.
pub fn screen(tokens: &[Token<'_>], edits: &mut Vec<Edit>) -> bool {
    let mixed = code_mixed(tokens);
    let hindi: Vec<&Token<'_>> = tokens
        .iter()
        .enumerate()
        .filter(|(i, t)| t.is_word && spelling::roman_hindi(tokens, *i))
        .map(|(_, t)| t)
        .collect();
    if hindi.is_empty() {
        return false;
    }
    // The sentence an edit sits in: its first overlapping token's, or for an insertion the
    // nearest word before it (else the first word after it).
    let sentence_of = |e: &Edit| -> Option<Sentence> {
        tokens
            .iter()
            .find(|t| t.start_utf16 < e.end_utf16 && t.end_utf16 > e.start_utf16)
            .or_else(|| {
                tokens
                    .iter()
                    .rev()
                    .find(|t| t.is_word && t.end_utf16 <= e.start_utf16)
            })
            .or_else(|| tokens.iter().find(|t| t.is_word))
            .map(|t| (t.paragraph, t.sentence))
    };
    let touches_hindi = |e: &Edit| {
        hindi.iter().any(|t| {
            if e.start_utf16 == e.end_utf16 {
                e.start_utf16 > t.start_utf16 && e.start_utf16 < t.end_utf16
            } else {
                e.start_utf16 < t.end_utf16 && e.end_utf16 > t.start_utf16
            }
        }) && !case_only(e)
    };
    let dropped = |e: &Edit| {
        touches_hindi(e)
            || sentence_of(e).is_some_and(|s| mixed.contains(&s))
                && (from_model(e)
                    || !["Spelling", "Capitalization", "Punctuation"]
                        .contains(&e.category.as_str()))
    };
    let groups: HashSet<String> = edits
        .iter()
        .filter(|e| dropped(e))
        .filter_map(|e| e.group_id.clone())
        .collect();
    let before = edits.len();
    edits.retain(|e| !dropped(e) && !e.group_id.as_ref().is_some_and(|g| groups.contains(g)));
    edits.len() != before
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::tokenizer::tokenize;

    fn edit(text: &str, word: &str, replacement: &str, category: &str, rule: &str) -> Edit {
        let at = text.find(word).expect("word in text");
        let start = text[..at].encode_utf16().count();
        Edit {
            start_utf16: start,
            end_utf16: start + word.encode_utf16().count(),
            replacement: replacement.into(),
            original: word.into(),
            category: category.into(),
            rule_id: rule.into(),
            explanation: String::new(),
            confidence: 1.0,
            group_id: None,
        }
    }

    #[test]
    fn code_mixed_sentences_need_hindi_to_carry_them() {
        for (text, mixed) in [
            ("kal meeting hai, theek hai?", true),
            ("PR review kar lena", true),
            ("Thanks yaar", true),
            ("please ek baar check kar lo", true),
            ("client ko call karna hai", true),
            ("He is very accha person", false),
            ("accha, I will send it tomorrow and call you.", false),
            ("The beta release is out today.", false),
            ("Send me the main file.", false),
            ("I recieved the file yesterday.", false),
        ] {
            let tokens = tokenize(text, &[]);
            assert_eq!(!code_mixed(&tokens).is_empty(), mixed, "{text}");
        }
    }

    #[test]
    fn screen_keeps_english_fixes_and_drops_grammar_in_mixed_sentences() {
        let text = "PR review kar lena, I recieved it";
        let tokens = tokenize(text, &[]);
        let mut edits = vec![
            edit(
                text,
                "review",
                "reviews",
                "Grammar",
                "grammar.subject_third",
            ),
            edit(
                text,
                "recieved",
                "received",
                "Spelling",
                "grammar.phrase.23",
            ),
        ];
        assert!(screen(&tokens, &mut edits));
        assert_eq!(edits.len(), 1);
        assert_eq!(edits[0].replacement, "received");
    }

    #[test]
    fn screen_never_respells_a_hindi_word_but_lets_its_case_change() {
        let text = "tum kaha ho, call karo";
        let tokens = tokenize(text, &[]);
        let mut edits = vec![
            edit(text, "kaha", "kana", "Spelling", "spelling.delete_index"),
            edit(
                text,
                "tum",
                "Tum",
                "Capitalization",
                "grammar.sentence_capitalization",
            ),
        ];
        screen(&tokens, &mut edits);
        assert_eq!(edits.len(), 1);
        assert_eq!(edits[0].replacement, "Tum");
    }

    #[test]
    fn screen_drops_model_edits_in_mixed_sentences_and_their_partners() {
        let text = "ye bug toh pehle bhi tha na";
        let tokens = tokenize(text, &[]);
        let mut a = edit(text, "bug", "bugs", "Grammar", "gector.replace");
        a.group_id = Some("g".into());
        let mut b = edit(text, "toh", "too", "Spelling", "spelling.delete_index");
        b.group_id = Some("g".into());
        let mut edits = vec![a, b];
        assert!(screen(&tokens, &mut edits));
        assert!(edits.is_empty());
    }

    #[test]
    fn english_text_is_untouched() {
        let text = "this si a test, and tha is teh best.";
        let tokens = tokenize(text, &[]);
        let mut edits = vec![
            edit(text, "si", "is", "Spelling", "spelling.delete_index"),
            edit(text, "tha", "that", "Spelling", "spelling.delete_index"),
            edit(text, "teh", "the", "Spelling", "grammar.phrase.21"),
        ];
        assert!(!screen(&tokens, &mut edits));
        assert_eq!(edits.len(), 3);
    }
}
