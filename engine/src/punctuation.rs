//! Objective spacing fixes. Never collapse paragraph layout or invent sentence meaning.
use crate::{
    Edit, Request, make_edit, morphology,
    tokenizer::{self, Token},
    utf16_at,
};
use regex::Regex;
use std::sync::OnceLock;
pub fn check(req: &Request, edits: &mut Vec<Edit>) {
    static PATTERNS: OnceLock<Vec<(Regex, &str, &str, &str)>> = OnceLock::new();
    let patterns = PATTERNS.get_or_init(|| {
        vec![
            (
                Regex::new(r"[A-Za-z][ \t]+(?P<target>[,;:!?])").unwrap(),
                "punctuation.before_mark",
                "Remove whitespace before punctuation.",
                "before",
            ),
            (
                Regex::new(r"[A-Za-z](?P<target>[,;:])(?P<next>[A-Za-z])").unwrap(),
                "punctuation.after_mark",
                "Separate words with a space after punctuation.",
                "after",
            ),
        ]
    });
    for (regex, id, reason, kind) in patterns {
        for cap in regex.captures_iter(&req.text) {
            let whole = cap.get(0).unwrap();
            let mark = cap.name("target").unwrap();
            let (a, b, replacement) = if *kind == "before" {
                (whole.start() + 1, mark.start(), String::new())
            } else {
                (mark.end(), mark.end(), " ".into())
            };
            if let Some(edit) = make_edit(
                &req.text,
                utf16_at(&req.text, a),
                utf16_at(&req.text, b),
                replacement,
                "Punctuation",
                id,
                reason,
                0.98,
            ) {
                edits.push(edit);
            }
        }
    }
    sentence_boundaries(req, edits);
    clause_commas(req, edits);
}

fn clause_commas(req: &Request, edits: &mut Vec<Edit>) {
    let tokens = tokenizer::tokenize(&req.text, &req.tokens);
    for (i, token) in tokens.iter().enumerate() {
        if ["yesterday", "tomorrow"].contains(&token.normalized.as_str())
            && crate::starts_sentence(&req.text, token.start_byte, req)
            && tokens.get(i + 1).is_some_and(|t| {
                ["i", "we", "he", "she", "they", "the"].contains(&t.normalized.as_str())
                    || t.proper_name
            })
            && let Some(edit) = make_edit(
                &req.text,
                token.end_utf16,
                token.end_utf16,
                ",".into(),
                "Punctuation",
                "punctuation.introductory_time",
                "Separate this introductory time expression from its clause.",
                0.9,
            )
        {
            edits.push(edit);
        }
        if i == 0 || !["but", "so"].contains(&token.normalized.as_str()) || !tokens[i - 1].is_word {
            continue;
        }
        if token.normalized == "so"
            && !tokens.get(i + 1).is_some_and(|t| {
                [
                    "i", "we", "you", "he", "she", "they", "it", "the", "our", "my", "this", "that",
                ]
                .contains(&t.normalized.as_str())
                    || t.proper_name
            })
        {
            continue;
        }
        let start = tokens[..i]
            .iter()
            .rposition(|t| {
                t.sentence != token.sentence || ["but", "so"].contains(&t.normalized.as_str())
            })
            .map(|n| n + 1)
            .unwrap_or(0);
        let end = (i + 1..tokens.len())
            .find(|&n| {
                tokens[n].sentence != token.sentence
                    || ["but", "so"].contains(&tokens[n].normalized.as_str())
            })
            .unwrap_or(tokens.len());
        if clause(&tokens[start..i])
            && clause(&tokens[i + 1..end])
            && let Some(edit) = make_edit(
                &req.text,
                tokens[i - 1].end_utf16,
                tokens[i - 1].end_utf16,
                ",".into(),
                "Punctuation",
                "punctuation.coordinated_clauses",
                "Separate these independent clauses before the coordinating conjunction.",
                0.9,
            )
        {
            edits.push(edit);
        }
    }
}

fn finite(t: &Token<'_>) -> bool {
    [
        "am", "is", "are", "was", "were", "has", "have", "had", "can", "could", "may", "might",
        "must", "shall", "should", "will", "would", "do", "does", "did", "cannot", "don't",
        "doesn't", "didn't", "you're", "we're", "they're", "he's", "she's", "it's", "i'm", "i've",
        "we've", "they've",
    ]
    .contains(&t.normalized.as_str())
        || morphology::verb(&t.normalized)
            .is_some_and(|v| t.normalized == v.third || t.normalized == v.past)
}
fn clause(tokens: &[Token<'_>]) -> bool {
    let words: Vec<_> = tokens.iter().filter(|t| t.is_word).collect();
    words.len() >= 3
        && words.iter().enumerate().skip(1).take(10).any(|(i, t)| {
            finite(t)
                || (morphology::verb(&t.normalized)
                    .is_some_and(|v| v.base == t.normalized && morphology::predicate(&v.base))
                    && ["we", "you", "they", "people", "colleagues", "friends"]
                        .contains(&words[i - 1].normalized.as_str()))
        })
}
fn sentence_boundaries(req: &Request, edits: &mut Vec<Edit>) {
    let tokens = tokenizer::tokenize(&req.text, &req.tokens);
    let mut start = 0;
    for i in 0..tokens.len() {
        let t = &tokens[i];
        if [".", "!", "?", ";"].contains(&t.surface) {
            start = i + 1;
            continue;
        }
        if i == 0 || tokens[i - 1].paragraph != t.paragraph {
            start = i;
            continue;
        }
        if i <= start || !t.is_word || !t.surface.chars().next().is_some_and(char::is_uppercase) {
            continue;
        }
        let named_start = t.proper_name
            || crate::spelling::name_only(&t.normalized) && tokens.get(i + 1).is_some_and(finite)
            || t.surface.ends_with("'s")
            || t.surface.ends_with("’s")
            || (!crate::spelling::known(&t.normalized) && tokens.get(i + 1).is_some_and(finite));
        if !named_start
            && ![
                "The",
                "This",
                "That",
                "These",
                "Those",
                "A",
                "An",
                "I",
                "We",
                "He",
                "She",
                "They",
                "It",
                "Its",
                "My",
                "Our",
                "Her",
                "Their",
                "Each",
                "Why",
                "Where",
                "When",
                "How",
                "What",
                "If",
                "Never",
                "Rarely",
                "Not",
                "Tomorrow",
                "Yesterday",
                "Then",
                "Last",
                "By",
            ]
            .contains(&t.surface)
        {
            continue;
        }
        let previous = &tokens[i - 1];
        // A name right after a preposition, determiner or transitive verb is its object
        // ("I talked to Aman and he said it is fine"), not the start of a new sentence.
        if [
            "to", "with", "for", "from", "of", "at", "in", "on", "by", "about", "into", "onto",
            "like", "than", "as", "per", "via", "near", "after", "before", "between", "among",
            "through", "over", "under", "upon", "around", "toward", "towards", "against",
            "without", "within", "the", "a", "an", "my", "your", "his", "our", "their", "its",
            "dear", "hey", "hi", "hello", "thanks", "thank", "cc", "ask", "tell", "invite", "call",
            "ping", "email", "meet", "see", "told", "asked", "met", "called", "emailed", "invited",
            "thanked", "pinged", "texted", "text", "message", "messaged", "contact",
        ]
        .contains(&previous.normalized.as_str())
            || (t.proper_name
                && morphology::verb(&previous.normalized).is_some_and(|v| {
                    morphology::predicate(&v.base)
                        && crate::spelling::flags(&previous.normalized) & 2 == 0
                }))
        {
            continue;
        }
        // A name after another capitalized word ("Aman Jain") is one name, not a new sentence.
        if named_start
            && previous.is_word
            && previous.surface.chars().count() > 1
            && previous
                .surface
                .chars()
                .next()
                .is_some_and(char::is_uppercase)
        {
            continue;
        }
        if t.surface == "I"
            && tokens[start..i].iter().rev().take(7).any(|x| {
                morphology::verb(&x.normalized).is_some_and(|v| {
                    ["tell", "think", "know", "believe", "say", "ask", "hear"]
                        .contains(&v.base.as_str())
                })
            })
        {
            continue;
        }
        if !previous.is_word
            || [
                "and", "or", "but", "so", "that", "because", "if", "when", "while", "although",
                "since", "called", "named", "titled", "said", "says", "asked", "asks", "me", "us",
                "him", "her", "them", "you", "think", "thought", "know", "knew", "believe",
                "believed", "am", "is", "are", "was", "were", "be", "been", "being", "has", "have",
                "had", "do", "does", "did", "can", "could", "will", "would", "shall", "should",
                "may", "might", "must",
            ]
            .contains(&previous.normalized.as_str())
        {
            continue;
        }
        let gap = &req.text[previous.end_byte..t.start_byte];
        if gap.is_empty() || !gap.chars().all(|c| c == ' ' || c == '\t') {
            continue;
        }
        let right_end = (i + 1..tokens.len())
            .find(|&j| {
                tokens[j].paragraph != t.paragraph
                    || [".", "!", "?", ";"].contains(&tokens[j].surface)
            })
            .unwrap_or(tokens.len());
        if !clause(&tokens[start..i]) || !clause(&tokens[i..right_end]) {
            continue;
        }
        let first = tokens
            .get(start)
            .map(|t| t.normalized.as_str())
            .unwrap_or("");
        let mark = if [
            "why", "where", "when", "how", "what", "who", "whose", "which",
        ]
        .contains(&first)
        {
            "?"
        } else {
            "."
        };
        if let Some(edit) = make_edit(
            &req.text,
            previous.end_utf16,
            previous.end_utf16,
            mark.into(),
            "Punctuation",
            "punctuation.missing_sentence_boundary",
            "Separate these complete clauses with sentence punctuation.",
            0.88,
        ) {
            edits.push(edit);
        }
        start = i;
    }
}

#[cfg(test)]
mod name_tests {
    use super::*;
    /// Boundary marks proposed for `text`, with `names` tagged the way the language tagger does.
    fn boundaries(text: &str, names: &[&str]) -> Vec<String> {
        let mut hints = vec![];
        for name in names {
            for (byte, _) in text.match_indices(name) {
                let start = text[..byte].encode_utf16().count();
                hints.push(crate::TokenHint {
                    start_utf16: start,
                    end_utf16: start + name.encode_utf16().count(),
                    pos: "Noun".into(),
                    lemma: String::new(),
                    name: true,
                });
            }
        }
        let req = Request {
            text: text.into(),
            tokens: hints,
            ..Request::default()
        };
        let mut edits = vec![];
        check(&req, &mut edits);
        edits
            .into_iter()
            .filter(|e| e.rule_id == "punctuation.missing_sentence_boundary")
            .map(|e| e.replacement)
            .collect()
    }
    #[test]
    fn a_name_is_never_a_sentence_start_after_an_object_marker_or_another_name() {
        for (text, names) in [
            ("I talked to Aman and he said it is fine.", &["Aman"][..]),
            ("I talked to Mark and he said it is fine.", &["Mark"]),
            (
                "I talked to Zo\u{eb} and she said it is fine.",
                &["Zo\u{eb}"],
            ),
            (
                "I met Aman Jain, and Aman's friend said aman jain was kind.",
                &["Aman", "Jain"],
            ),
            ("I met Aman Jain and he said it is fine.", &["Aman", "Jain"]),
        ] {
            assert!(boundaries(text, names).is_empty(), "{text}");
        }
    }
    #[test]
    fn a_real_run_on_still_gets_its_period() {
        assert_eq!(
            boundaries("The report is done Aman will send it tomorrow", &["Aman"]),
            ["."]
        );
    }
}
