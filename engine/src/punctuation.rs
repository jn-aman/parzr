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
