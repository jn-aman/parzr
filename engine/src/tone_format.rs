//! The formatting floor of a tone rewrite: whatever the model wrote (or withheld), the result
//! starts its sentences with a capital and ends with sentence punctuation, as Fix would, and a
//! Professional rewrite spells chat shorthand out. Chat text included: the typing check leaves
//! "hey can u send it" as typed, but a rewrite the writer asked for is finished writing.
use crate::{Edit, Request, TextRange, byte_at, overlaps, tokenizer};

/// Words that open a question when they start a sentence ("can you", "is it", "what time").
const QUESTION_OPENERS: &[&str] = &[
    "can",
    "could",
    "would",
    "will",
    "do",
    "does",
    "did",
    "is",
    "are",
    "am",
    "was",
    "were",
    "have",
    "has",
    "should",
    "shall",
    "may",
    "what",
    "why",
    "how",
    "when",
    "where",
    "who",
    "which",
    "whose",
    "isn't",
    "aren't",
    "don't",
    "doesn't",
    "didn't",
    "won't",
    "can't",
    "couldn't",
    "wouldn't",
    "shouldn't",
    "haven't",
    "hasn't",
    "wasn't",
    "weren't",
];
/// Words that may stand before a question's opener ("hey, can you", "so when is it").
const LEAD_INS: &[&str] = &[
    "hey", "hi", "hello", "so", "also", "and", "but", "ok", "okay", "btw",
];
/// Subjects that start a second clause in a run-on ("can you send it I need it now"): a sentence
/// with one is not read as a single question.
const SUBJECTS: &[&str] = &[
    "i", "we", "they", "he", "she", "i'm", "we're", "i'll", "we'll",
];

/// Chat laughter a Professional rewrite leaves out.
const LAUGHTER: &[&str] = &["lol", "lmao", "lmfao", "rofl", "haha", "hahaha", "hehe"];
/// Chat shorthand a Professional rewrite spells out, with what it stands for.
const SHORTHAND: &[(&str, &str)] = &[
    ("u", "you"),
    ("pls", "please"),
    ("plz", "please"),
    ("thx", "thanks"),
    ("tmrw", "tomorrow"),
    ("tmr", "tomorrow"),
    ("tmw", "tomorrow"),
    ("gonna", "going to"),
    ("wanna", "want to"),
    ("btw", "by the way"),
    ("imo", "in my opinion"),
    ("bc", "because"),
    ("cuz", "because"),
    ("coz", "because"),
    ("rn", "right now"),
    ("asap", "ASAP"),
    ("msg", "message"),
    ("mins", "minutes"),
    ("hrs", "hours"),
];

fn edit(
    start: usize,
    end: usize,
    original: &str,
    replacement: String,
    rule: &str,
    why: &str,
) -> Edit {
    Edit {
        start_utf16: start,
        end_utf16: end,
        original: original.to_owned(),
        replacement,
        category: "Style".into(),
        rule_id: rule.into(),
        explanation: why.into(),
        confidence: 0.9,
        group_id: None,
    }
}

fn protected_at(protected: &[TextRange], start: usize, end: usize) -> bool {
    protected.iter().any(|p| overlaps(start, end, p))
}

/// Chat shorthand spelled out for a Professional rewrite ("u" to "you", "pls" to "please").
/// Edits are in `req.text` coordinates; protected text (code, links, names) is never touched.
pub(crate) fn professional_forms(req: &Request, protected: &[TextRange]) -> Vec<Edit> {
    let tokens = tokenizer::tokenize(&req.text, &req.tokens);
    let mut edits = vec![];
    // "lol" alone is the whole message, not laughter beside one.
    let worded = tokens
        .iter()
        .any(|t| t.is_word && !LAUGHTER.contains(&t.surface.to_lowercase().as_str()));
    for (i, t) in tokens.iter().enumerate() {
        if !t.is_word || protected_at(protected, t.start_utf16, t.end_utf16) {
            continue;
        }
        // "u-turn", "U.S.", "rn.": only a word standing alone.
        let after = &req.text[t.end_byte..];
        let before = &req.text[..t.start_byte];
        if after.starts_with(['-', '.', '\'', '’', '/', '_', '@'])
            && !after.starts_with(". ")
            && !after.trim_end().eq(".")
            || before.ends_with(['-', '/', '_', '@', '#'])
        {
            continue;
        }
        let lower = t.surface.to_lowercase();
        // Chat laughter has no place in professional writing: it goes, with its comma and space
        // ("lol that meeting was long" is "that meeting was long").
        if LAUGHTER.contains(&lower.as_str()) && worded {
            let rest = &req.text[t.end_byte..];
            let gap = rest.len() - rest.trim_start_matches([',', '!', '.']).len();
            let rest = &rest[gap..];
            let space = rest.len() - rest.trim_start_matches([' ', '\t']).len();
            let (end_byte, start_byte) = if rest[space..].is_empty() {
                // At the end, the space before it goes instead ("see you at 7 lol").
                let head = &req.text[..t.start_byte];
                (t.end_byte + gap, head.trim_end_matches([' ', '\t']).len())
            } else {
                (t.end_byte + gap + space, t.start_byte)
            };
            let utf16 = |b: usize| req.text[..b].encode_utf16().count();
            if !protected_at(protected, utf16(start_byte), utf16(end_byte)) {
                edits.push(edit(
                    utf16(start_byte),
                    utf16(end_byte),
                    &req.text[start_byte..end_byte],
                    String::new(),
                    "tone.professional_shorthand",
                    "Leave chat laughter out of professional writing.",
                ));
            }
            continue;
        }
        let Some(&(_, full)) = SHORTHAND.iter().find(|(s, _)| *s == lower) else {
            continue;
        };
        // "U" alone is a letter or a name ("Plan U"); only the lowercase chat form is "you".
        if lower == "u" && t.surface != "u" {
            continue;
        }
        let first = tokens[..i]
            .iter()
            .rev()
            .find(|p| p.is_word || [".", "!", "?"].contains(&p.surface))
            .is_none_or(|p| p.sentence != t.sentence);
        let replacement = if first && t.surface.starts_with(char::is_uppercase) {
            upper_first(full)
        } else {
            full.to_owned()
        };
        if replacement != t.surface {
            edits.push(edit(
                t.start_utf16,
                t.end_utf16,
                t.surface,
                replacement,
                "tone.professional_shorthand",
                "Spell out chat shorthand in professional writing.",
            ));
        }
    }
    edits
}

fn upper_first(word: &str) -> String {
    let mut chars = word.chars();
    chars
        .next()
        .map_or_else(String::new, |c| c.to_uppercase().chain(chars).collect())
}

/// Actions a request asks the reader to do: "can you send me the file?" asks for a sending,
/// while "can you make it Friday?" or "can you see the error?" asks a question.
const REQUEST_VERBS: &[&str] = &[
    "send", "review", "check", "look", "take", "share", "update", "fix", "call", "email", "help",
    "grab", "add", "merge", "approve", "confirm", "sign", "schedule", "move", "test", "ping",
    "forward", "upload", "submit", "finish", "complete", "prepare", "write", "draft", "give",
    "resend", "cover", "handle", "deploy", "push", "run", "book", "reply", "respond", "rerun",
    "retest", "clean", "remove", "delete", "rename", "close", "open", "file", "print", "order",
    "pick", "drop", "bring", "post", "ask", "tell", "remind", "loop", "cc", "invite", "join",
];
/// Padding at the end of a request that Direct leaves out ("…, when you get a chance").
const SOFT_TAILS: &[&str] = &[
    "when you get a chance",
    "when you have a chance",
    "when you have a moment",
    "when you get a moment",
    "if you get a chance",
    "if you have a chance",
    "if you have a moment",
    "if possible",
    "if you can",
    "when you can",
];

/// A Direct rewrite asks for an action plainly: "Hey, can you send me the file ASAP?" is
/// "Send me the file ASAP.", "Could you please review it when you get a chance?" is "Please
/// review it." Only a request for one of `REQUEST_VERBS` from "you" changes; questions,
/// requests to someone else ("can someone look") and protected text stay as they are.
pub(crate) fn direct_forms(req: &Request, protected: &[TextRange]) -> Vec<Edit> {
    let text = req.text.as_str();
    let tokens = tokenizer::tokenize(text, &req.tokens);
    let mut edits = vec![];
    let sentences: Vec<usize> = {
        let mut s: Vec<usize> = tokens.iter().map(|t| t.sentence).collect();
        s.dedup();
        s
    };
    for sentence in sentences {
        let part: Vec<&tokenizer::Token<'_>> =
            tokens.iter().filter(|t| t.sentence == sentence).collect();
        let Some(last) = part.last() else { continue };
        if last.surface != "?" {
            continue;
        }
        let lower = |i: usize| part.get(i).map(|t| t.surface.to_lowercase());
        let mut i = 0;
        if lower(0)
            .is_some_and(|w| ["hey", "hi", "hello", "so", "ok", "okay"].contains(&w.as_str()))
        {
            i = 1;
            if lower(1).as_deref() == Some(",") {
                i = 2;
            }
        }
        if !lower(i).is_some_and(|w| ["can", "could", "would", "will"].contains(&w.as_str()))
            || lower(i + 1).as_deref() != Some("you")
        {
            continue;
        }
        let please = lower(i + 2).as_deref() == Some("please");
        let v = i + 2 + usize::from(please);
        let Some(verb) = part.get(v) else { continue };
        if !REQUEST_VERBS.contains(&verb.surface.to_lowercase().as_str())
            || part.iter().any(|t| {
                // "can you send it or should I?" is a question with a choice in it.
                t.surface.eq_ignore_ascii_case("or") || t.surface.eq_ignore_ascii_case("whether")
            })
        {
            continue;
        }
        let utf16 = |b: usize| text[..b].encode_utf16().count();
        // The body runs from the verb to the mark; a soft tail at its end goes with the mark.
        let body = text[verb.start_byte..last.start_byte].trim_end();
        let mut body_end = verb.start_byte + body.len();
        let lower_body = body.to_lowercase();
        if lower_body.len() == body.len()
            && let Some(cut) = SOFT_TAILS.iter().find_map(|t| lower_body.strip_suffix(t))
            && body.is_char_boundary(cut.len())
        {
            let kept = body[..cut.len()]
                .trim_end()
                .trim_end_matches(',')
                .trim_end();
            body_end = verb.start_byte + kept.len();
        }
        // "Hey, can you s" becomes "S" (or "Please s"); the tail and "?" become ".".
        let first = verb.surface.chars().next().map_or(0, char::len_utf8);
        let head_end = verb.start_byte + first;
        let letter = &text[verb.start_byte..head_end];
        let head = if please {
            format!("Please {}", letter.to_lowercase())
        } else {
            letter.to_uppercase()
        };
        let spans = [
            (part[0].start_byte, head_end, head),
            (body_end, last.end_byte, ".".to_owned()),
        ];
        if spans
            .iter()
            .any(|(a, b, _)| protected_at(protected, utf16(*a), utf16(*b)))
        {
            continue;
        }
        for (a, b, replacement) in spans {
            if text[a..b] != replacement {
                edits.push(edit(
                    utf16(a),
                    utf16(b),
                    &text[a..b],
                    replacement,
                    "tone.direct_request",
                    "Ask for it directly.",
                ));
            }
        }
    }
    edits
}

fn opener_regex() -> &'static regex::Regex {
    static RE: std::sync::OnceLock<regex::Regex> = std::sync::OnceLock::new();
    RE.get_or_init(|| {
        regex::Regex::new(
            r"(?i)^(?:i\s+(?:just\s+|simply\s+)?wanted\s+to\s+(?:take\s+a\s+(?:moment|minute|second)\s+to\s+)?(?:let\s+you\s+know|inform\s+you|tell\s+you|mention)|i\s+(?:am|'m|’m)\s+(?:just\s+)?writing\s+to\s+(?:let\s+you\s+know|inform\s+you)|this\s+is\s+(?:just\s+)?to\s+(?:let\s+you\s+know|inform\s+you)|just\s+(?:wanted\s+to\s+)?(?:let\s+you\s+know))(?:\s+that)?[\s,:]+",
        )
        .expect("constant opener regex")
    })
}

/// The padded opener of a message said plainly. Friendly: "I wanted to take a moment to let
/// you know that the budget is still $450" is "Just a quick note: the budget is still $450";
/// Concise and Direct leave the opener out ("The budget is still $450"). Only at a sentence
/// start, and only when a sentence follows it.
pub(crate) fn opener_forms(req: &Request, protected: &[TextRange]) -> Vec<Edit> {
    if !matches!(
        req.mode,
        crate::Mode::Friendly | crate::Mode::Concise | crate::Mode::Direct
    ) {
        return vec![];
    }
    let text = req.text.as_str();
    let tokens = tokenizer::tokenize(text, &req.tokens);
    let mut edits = vec![];
    let mut previous = usize::MAX;
    for t in &tokens {
        if t.sentence == previous || !t.is_word {
            previous = t.sentence;
            continue;
        }
        previous = t.sentence;
        let Some(m) = opener_regex().find(&text[t.start_byte..]) else {
            continue;
        };
        let (a, b) = (t.start_byte, t.start_byte + m.end());
        let rest = &text[b..];
        // A clause must follow ("I wanted to let you know." alone stays).
        if rest.split_whitespace().take(3).count() < 3 || !rest.starts_with(char::is_alphanumeric) {
            continue;
        }
        let utf16 = |x: usize| text[..x].encode_utf16().count();
        // The first word of the rest takes the sentence capital when the opener goes.
        let first = rest.chars().next().map_or(0, char::len_utf8);
        let (end, replacement) = if req.mode == crate::Mode::Friendly {
            (b, "Just a quick note: ".to_owned())
        } else {
            (b + first, rest[..first].to_uppercase())
        };
        if protected_at(protected, utf16(a), utf16(end)) {
            continue;
        }
        edits.push(edit(
            utf16(a),
            utf16(end),
            &text[a..end],
            replacement,
            "tone.plain_opener",
            "Say it without the padded opener.",
        ));
    }
    edits
}

/// Sentence capitals and final punctuation, as Fix gives them, for a finished rewrite.
/// Edits are in `req.text` coordinates; protected text is never touched.
pub(crate) fn floor(req: &Request, protected: &[TextRange]) -> Vec<Edit> {
    let text = req.text.as_str();
    let tokens = tokenizer::tokenize(text, &req.tokens);
    let mut edits = vec![];
    // Whether the next word opens a sentence.
    let mut open = req.sentence_start;
    let mut previous: Option<&tokenizer::Token<'_>> = None;
    for t in &tokens {
        if let Some(p) = previous
            && (p.sentence != t.sentence
                || p.paragraph != t.paragraph
                || text[p.end_byte..t.start_byte].contains('\n'))
        {
            open = true;
        }
        previous = Some(t);
        if !t.is_word {
            // A quote, bracket or list marker before the first word: the word still opens.
            if !["(", "\"", "“", "'", "‘", "-", "*", "•"].contains(&t.surface) {
                open = false;
            }
            continue;
        }
        if !std::mem::take(&mut open) {
            continue;
        }
        let lower = t.surface.to_lowercase();
        let starts_lower = t.surface.chars().next().is_some_and(char::is_lowercase);
        // "iPhone", "eBay", "macOS": a capital inside the word is the writer's spelling.
        let inner_capital = t.surface.chars().skip(1).any(char::is_uppercase);
        let glued = text[t.end_byte..].starts_with(['.', '/', '_', '@', ':'])
            && text[t.end_byte..]
                .chars()
                .nth(1)
                .is_some_and(char::is_alphanumeric)
            || text[..t.start_byte].ends_with(['@', '#', '/', '_', '.']);
        if !starts_lower
            || inner_capital
            || glued
            || protected_at(protected, t.start_utf16, t.end_utf16)
        {
            continue;
        }
        // "lol" takes a capital like any word ("Lol"); "fyi" and "ok" are written in capitals.
        let replacement = if lower == "ok" {
            "OK".to_owned()
        } else if crate::capitalization::interjection(&lower) {
            upper_first(t.surface)
        } else if crate::names::is_chat_acronym(&lower) {
            lower.to_uppercase()
        } else if let Some(canonical) = crate::spelling::canonical_case(&lower) {
            canonical.to_string()
        } else if crate::spelling::known(&lower) {
            upper_first(t.surface)
        } else {
            continue;
        };
        if replacement != t.surface {
            edits.push(edit(
                t.start_utf16,
                t.end_utf16,
                t.surface,
                replacement,
                "grammar.sentence_capitalization",
                "Start the sentence with a capital letter.",
            ));
        }
    }
    if let Some(e) = final_mark(req, protected, &tokens) {
        edits.push(e);
    }
    edits
}

/// The full stop or question mark a finished rewrite ends with, when it has none. Left alone:
/// a selection that continues, text ending in an emoji, code, a link or a sign-off line ("Thanks,
/// \nDana"), and very short replies ("ok", "on it").
fn final_mark(
    req: &Request,
    protected: &[TextRange],
    tokens: &[tokenizer::Token<'_>],
) -> Option<Edit> {
    if !req.sentence_end {
        return None;
    }
    let text = req.text.as_str();
    let body = text.trim_end();
    let last = body.chars().last()?;
    if !last.is_alphanumeric() && !matches!(last, ')' | '"' | '”' | '\'' | '’') {
        return None;
    }
    // "(I should charge a fee.)" and "she said “done.”" are already finished.
    if !last.is_alphanumeric()
        && body
            .trim_end_matches([')', '"', '”', '\'', '’'])
            .ends_with(['.', '!', '?', '…'])
    {
        return None;
    }
    let end = body.encode_utf16().count();
    // Code, a link or a path at the end stays exactly as typed; a name ("… from Mei or Jonas")
    // takes the full stop like any word.
    if protected.iter().any(|p| {
        p.end_utf16 >= end
            && p.start_utf16 < end
            && crate::byte_at(text, p.start_utf16)
                .zip(crate::byte_at(text, p.end_utf16))
                .and_then(|(a, b)| text.get(a..b))
                .is_none_or(|s| {
                    !s.split_whitespace().all(|w| {
                        w.starts_with(char::is_uppercase)
                            && w.chars().all(|c| c.is_alphabetic() || "'’-.".contains(c))
                    })
                })
    }) {
        return None;
    }
    let line = body.rsplit('\n').next().unwrap_or(body);
    let line_words = line.split_whitespace().count();
    // A closing line of a letter or a list item, not a sentence: "Thanks,\nDana", "- tests".
    if body.contains('\n') && (line_words <= 3 || line.trim_start().starts_with(['-', '*', '•']))
    {
        return None;
    }
    if line_words < 3 {
        return None;
    }
    let sentence = tokens.last().map(|t| t.sentence)?;
    let last: Vec<&tokenizer::Token<'_>> =
        tokens.iter().filter(|t| t.sentence == sentence).collect();
    let words_of = |part: &[&tokenizer::Token<'_>]| -> Vec<String> {
        part.iter()
            .filter(|t| t.is_word)
            .map(|t| t.surface.to_lowercase())
            .collect()
    };
    let asks = |words: &[String]| {
        let lead = words
            .iter()
            .take_while(|w| LEAD_INS.contains(&w.as_str()))
            .count();
        words
            .get(lead)
            .is_some_and(|w| QUESTION_OPENERS.contains(&w.as_str()))
            && !words
                .iter()
                .skip(lead + 2)
                .any(|w| SUBJECTS.contains(&w.as_str()))
    };
    // The sentence, or its last clause after a comma ("the build is broken again, can someone
    // look"), opens like a question.
    let clause = last
        .iter()
        .rposition(|t| t.surface == ",")
        .map_or(&last[..0], |i| &last[i + 1..]);
    // A clause question names who it asks about ("can someone look", "is it done"), unlike
    // "thanks, will send it tomorrow"; a wh-word needs none ("ok, what time works").
    let clause_asks = |words: &[String]| {
        const WH: &[&str] = &["what", "why", "how", "when", "where", "who", "which"];
        const WHO: &[&str] = &[
            "you", "we", "i", "someone", "anyone", "somebody", "anybody", "it", "he", "she",
            "they", "this", "that", "there", "the", "my", "your", "our", "everyone",
        ];
        asks(words)
            && (words.first().is_some_and(|w| WH.contains(&w.as_str()))
                || words.get(1).is_some_and(|w| WHO.contains(&w.as_str())))
    };
    let mark = if asks(&words_of(&last)) || clause.len() > 2 && clause_asks(&words_of(clause)) {
        "?"
    } else {
        "."
    };
    byte_at(text, end)?;
    Some(edit(
        end,
        end,
        "",
        mark.into(),
        "grammar.final_punctuation",
        "End the sentence with punctuation.",
    ))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn apply(text: &str, edits: Vec<Edit>) -> String {
        crate::apply_edits(text, &edits).unwrap().0
    }
    fn floored(text: &str) -> String {
        let req = Request {
            text: text.into(),
            ..Default::default()
        };
        apply(text, floor(&req, &[]))
    }
    fn professional(text: &str) -> String {
        let req = Request {
            text: text.into(),
            ..Default::default()
        };
        apply(text, professional_forms(&req, &[]))
    }

    #[test]
    fn chat_gets_sentence_capitals_and_a_final_mark() {
        assert_eq!(
            floored("hey can you send me the file ASAP I need it now"),
            "Hey can you send me the file ASAP I need it now."
        );
        assert_eq!(
            floored("are you free for lunch on Friday"),
            "Are you free for lunch on Friday?"
        );
        assert_eq!(
            floored("thanks for the help. really appreciate it"),
            "Thanks for the help. Really appreciate it."
        );
        assert_eq!(floored("fyi the build is green"), "FYI the build is green.");
        assert_eq!(
            floored("the build is broken again, can someone look"),
            "The build is broken again, can someone look?"
        );
        assert_eq!(
            floored("i tried that, it did not work"),
            "I tried that, it did not work."
        );
        assert_eq!(
            floored("thanks, will send it tomorrow"),
            "Thanks, will send it tomorrow."
        );
    }

    #[test]
    fn short_replies_and_sign_offs_get_capitals_but_no_final_mark() {
        for (text, expected) in [
            ("Hey, can you send it?", "Hey, can you send it?"),
            ("ok", "OK"),
            ("on it", "On it"),
            ("sounds good 👍", "Sounds good 👍"),
            (
                "Hi Sam,\nthe numbers are attached.\nThanks,\nDana",
                "Hi Sam,\nThe numbers are attached.\nThanks,\nDana",
            ),
            ("iPhone sales are up", "iPhone sales are up."),
            ("see config.yaml", "See config.yaml"),
            (
                "(I should charge you a 10% listing fee.)",
                "(I should charge you a 10% listing fee.)",
            ),
        ] {
            assert_eq!(floored(text), expected, "{text:?}");
        }
    }

    fn direct(text: &str) -> String {
        let req = Request {
            text: text.into(),
            ..Default::default()
        };
        apply(text, direct_forms(&req, &[]))
    }

    #[test]
    fn direct_turns_a_request_for_an_action_into_an_instruction() {
        for (text, expected) in [
            (
                "Hey, can you send me the file ASAP? I need it now.",
                "Send me the file ASAP. I need it now.",
            ),
            (
                "Could you please review my PR when you get a chance?",
                "Please review my PR.",
            ),
            ("Can you check the logs, if possible?", "Check the logs."),
            // Questions, choices and requests to someone else stay.
            ("Can you make it on Friday?", "Can you make it on Friday?"),
            ("Can you see the error?", "Can you see the error?"),
            (
                "Can someone look at the build?",
                "Can someone look at the build?",
            ),
            (
                "Can you send it, or should I?",
                "Can you send it, or should I?",
            ),
            ("Can you send it.", "Can you send it."),
        ] {
            assert_eq!(direct(text), expected, "{text:?}");
        }
    }

    #[test]
    fn padded_openers_are_said_plainly() {
        let text = "I wanted to take a moment to let you know that the budget is still $450.";
        for (mode, expected) in [
            (
                crate::Mode::Friendly,
                "Just a quick note: the budget is still $450.",
            ),
            (crate::Mode::Concise, "The budget is still $450."),
            (crate::Mode::Direct, "The budget is still $450."),
            (crate::Mode::Professional, text),
        ] {
            let req = Request {
                text: text.into(),
                mode,
                ..Default::default()
            };
            assert_eq!(apply(text, opener_forms(&req, &[])), expected, "{mode:?}");
        }
        let alone = Request {
            text: "I just wanted to let you know.".into(),
            mode: crate::Mode::Friendly,
            ..Default::default()
        };
        assert!(opener_forms(&alone, &[]).is_empty());
    }

    #[test]
    fn a_continuing_selection_gets_no_capital_or_final_mark() {
        let req = Request {
            text: "can you send it".into(),
            sentence_start: false,
            sentence_end: false,
            ..Default::default()
        };
        assert!(floor(&req, &[]).is_empty());
    }

    #[test]
    fn protected_text_is_never_recased_or_punctuated() {
        let text = "npm run build";
        let req = Request {
            text: text.into(),
            ..Default::default()
        };
        let protected = [TextRange {
            start_utf16: 0,
            end_utf16: 13,
        }];
        assert!(floor(&req, &protected).is_empty());
        // A protected name at the end still takes the full stop.
        let text = "never deploy without approval from Jonas";
        let req = Request {
            text: text.into(),
            ..Default::default()
        };
        let name = [TextRange {
            start_utf16: 35,
            end_utf16: 40,
        }];
        assert_eq!(
            apply(text, floor(&req, &name)),
            "Never deploy without approval from Jonas."
        );
    }

    #[test]
    fn professional_spells_out_chat_shorthand() {
        assert_eq!(
            professional("can u send it tmrw pls"),
            "can you send it tomorrow please"
        );
        assert_eq!(professional("Thx, will do asap"), "Thanks, will do ASAP");
        assert_eq!(professional("Plan U is the U-turn"), "Plan U is the U-turn");
        assert_eq!(professional("u-boat"), "u-boat");
        assert_eq!(
            professional("lol that meeting was long"),
            "that meeting was long"
        );
        assert_eq!(professional("haha, see u at 7 lol"), "see you at 7");
        assert_eq!(professional("lol"), "lol");
    }
}
