//! Contractions typed without their apostrophe ("dont", "Im", "theyre"), with it in the wrong place
//! ("did'nt", "Your'e", "Lets'") or with another key in its place ("I;m", "don\"t").
//!
//! The apostrophe-less form of most contractions is no English word, so it is always restored.
//! The few that are words ("lets", "cant", "wont", "ill", "id", "were") are restored only in the
//! frames where the word reading is impossible ("Lets go", "I cant find it", "Ill be there").
use crate::tokenizer::Token;
use crate::{Edit, Request, make_edit, morphology, spelling, starts_sentence, utf16_at};
use regex::Regex;
use std::{collections::HashMap, sync::OnceLock};

/// Every standard English contraction, lowercase with a straight apostrophe.
const CONTRACTIONS: [&str; 80] = [
    "i'm",
    "i've",
    "i'll",
    "i'd",
    "you're",
    "you've",
    "you'll",
    "you'd",
    "he's",
    "he'll",
    "he'd",
    "she's",
    "she'll",
    "she'd",
    "it's",
    "it'll",
    "it'd",
    "we're",
    "we've",
    "we'll",
    "we'd",
    "they're",
    "they've",
    "they'll",
    "they'd",
    "that's",
    "that'll",
    "that'd",
    "who's",
    "who'll",
    "who'd",
    "who've",
    "what's",
    "what're",
    "what'll",
    "what'd",
    "what've",
    "where's",
    "where'd",
    "where'll",
    "when's",
    "when'd",
    "why's",
    "why'd",
    "how's",
    "how'd",
    "how'll",
    "there's",
    "there'll",
    "there'd",
    "there're",
    "here's",
    "let's",
    "isn't",
    "aren't",
    "wasn't",
    "weren't",
    "don't",
    "doesn't",
    "didn't",
    "haven't",
    "hasn't",
    "hadn't",
    "won't",
    "wouldn't",
    "can't",
    "couldn't",
    "shouldn't",
    "mustn't",
    "needn't",
    "mightn't",
    "shan't",
    "ain't",
    "should've",
    "could've",
    "would've",
    "must've",
    "might've",
    "y'all",
    "this'll",
];
/// Apostrophe-less forms that are also words. They are restored only in a frame (see `framed`),
/// or never ("well", "hell", "shell", "wed", "shed", "whys", "whens" and "its", which is a
/// possessive and belongs to the real-word checks).
const WORD_FORMS: [&str; 14] = [
    "lets", "cant", "wont", "ill", "id", "were", "its", "well", "hell", "shell", "wed", "shed",
    "whys", "whens",
];
/// Words that are listed in the lexicon but are only ever contractions missing their apostrophe.
const NOT_WORDS: [&str; 3] = ["whats", "wheres", "hows"];

/// The contraction whose letters are `joined` ("dont" to "don't").
fn contraction(joined: &str) -> Option<&'static str> {
    static JOINED: OnceLock<HashMap<String, &'static str>> = OnceLock::new();
    JOINED
        .get_or_init(|| {
            CONTRACTIONS
                .iter()
                .map(|c| (c.replace('\'', ""), *c))
                .collect()
        })
        .get(joined)
        .copied()
}
/// Base-form verbs and adverbs that follow "I'll" and "I'd" ("Ill be there", "Id love to").
const AFTER_I_WILL: [&str; 52] = [
    "be",
    "see",
    "go",
    "have",
    "get",
    "call",
    "send",
    "do",
    "let",
    "take",
    "make",
    "try",
    "check",
    "look",
    "ask",
    "bring",
    "come",
    "talk",
    "text",
    "email",
    "ping",
    "follow",
    "pick",
    "grab",
    "meet",
    "keep",
    "give",
    "tell",
    "write",
    "read",
    "fix",
    "find",
    "wait",
    "just",
    "probably",
    "definitely",
    "never",
    "also",
    "still",
    "always",
    "update",
    "share",
    "review",
    "handle",
    "think",
    "need",
    "leave",
    "put",
    "start",
    "help",
    "pay",
    "stop",
];
const AFTER_I_WOULD: [&str; 36] = [
    "love",
    "like",
    "rather",
    "better",
    "be",
    "have",
    "go",
    "say",
    "need",
    "want",
    "appreciate",
    "prefer",
    "suggest",
    "recommend",
    "never",
    "probably",
    "really",
    "definitely",
    "also",
    "just",
    "still",
    "think",
    "imagine",
    "hate",
    "guess",
    "bet",
    "gladly",
    "happily",
    "ask",
    "take",
    "try",
    "get",
    "do",
    "been",
    "already",
    "actually",
];
/// Words between "we're" and its predicate ("Were just leaving").
const ADVERBS: [&str; 17] = [
    "just",
    "still",
    "already",
    "almost",
    "all",
    "so",
    "really",
    "not",
    "finally",
    "currently",
    "also",
    "never",
    "always",
    "both",
    "actually",
    "definitely",
    "probably",
];
/// Predicates after "we're" that "were" cannot take at a sentence start.
const WE_ARE: [&str; 20] = [
    "ready", "done", "sorry", "glad", "happy", "excited", "late", "close", "back", "home", "good",
    "fine", "gonna", "thrilled", "proud", "pleased", "almost", "here", "there", "open",
];
const SUBJECTS: [&str; 17] = [
    "i", "you", "we", "they", "he", "she", "it", "that", "this", "there", "who", "which",
    "someone", "everyone", "nobody", "people", "one",
];
const DETERMINERS: [&str; 12] = [
    "the", "a", "an", "my", "your", "his", "her", "our", "their", "its", "this", "that",
];
const CONJUNCTIONS: [&str; 12] = [
    "and", "but", "so", "because", "if", "when", "then", "or", "though", "although", "cause",
    "since",
];
fn base_verb(word: &str) -> bool {
    morphology::verb(word).is_some_and(|v| v.base == word)
        && ![
            "will", "would", "can", "could", "may", "might", "must", "shall", "should",
        ]
        .contains(&word)
}
fn gerund(word: &str) -> bool {
    word.ends_with("ing") && morphology::verb(word).is_some_and(|v| v.gerund == word)
}
struct Frame<'t, 'a> {
    tokens: &'t [Token<'a>],
    index: usize,
}
impl<'a> Frame<'_, 'a> {
    fn word(&self, at: Option<usize>) -> &str {
        at.and_then(|i| self.tokens.get(i))
            .filter(|t| t.is_word && t.paragraph == self.tokens[self.index].paragraph)
            .map_or("", |t| t.normalized.as_str())
    }
    fn prev(&self) -> &str {
        self.word(self.index.checked_sub(1))
    }
    fn next(&self) -> &str {
        self.word(Some(self.index + 1))
    }
    fn after_next(&self) -> &str {
        self.word(Some(self.index + 2))
    }
    /// The token opens a sentence, line or clause ("..., but ill be there").
    fn clause_start(&self, sentence: bool) -> bool {
        let token = &self.tokens[self.index];
        let Some(p) = self.index.checked_sub(1).map(|i| &self.tokens[i]) else {
            return true;
        };
        p.paragraph != token.paragraph
            || [".", "!", "?", ";", ":"].contains(&p.surface)
            || !sentence && (p.surface == "," || CONJUNCTIONS.contains(&p.normalized.as_str()))
            || sentence && p.surface == "(" && self.index == 1
    }
}
/// A word-form contraction in a frame that rules out the ordinary word.
fn framed(form: &str, f: &Frame<'_, '_>, text: &str, token: &Token<'_>) -> bool {
    let (prev, next) = (f.prev(), f.next());
    match form {
        // "Lets go" opens a sentence; "it lets you" has a subject.
        "lets" => {
            f.clause_start(true)
                && (base_verb(next) || ["not", "just", "all", "both"].contains(&next))
                && !["me", "you", "him", "her", "it", "us", "them"].contains(&next)
        }
        // "I cant find it", "Cant wait": a subject before or a bare verb after.
        "cant" | "wont" => {
            let verb_after =
                base_verb(next) || ["even", "ever", "really", "just", "always"].contains(&next);
            SUBJECTS.contains(&prev) && (verb_after || next.is_empty())
                || f.clause_start(false) && base_verb(next)
        }
        "ill" => f.clause_start(false) && AFTER_I_WILL.contains(&next),
        "id" => f.clause_start(false) && AFTER_I_WOULD.contains(&next),
        // "Were just parking now": no question opens this way.
        "were" => {
            let rest = &text[token.end_byte..];
            let sentence_end = rest.find(['.', '!', '?', '\n']).map_or(rest.len(), |i| i);
            f.clause_start(true)
                && !rest[sentence_end..].starts_with('?')
                && (gerund(next)
                    || WE_ARE.contains(&next)
                    || ADVERBS.contains(&next)
                        && (gerund(f.after_next()) || WE_ARE.contains(&f.after_next())))
        }
        _ => false,
    }
}
/// The case of `surface` on `contraction` ("Dont" to "Don't", "DONT" to "DON'T"); None for mixed
/// case, which is a name or an identifier.
fn cased(contraction: &str, surface: &str, apostrophe: char) -> Option<String> {
    let letters: Vec<char> = surface.chars().filter(|c| c.is_alphabetic()).collect();
    let upper = letters.iter().filter(|c| c.is_uppercase()).count();
    let out = if contraction.starts_with("i'") {
        // The pronoun is always a capital; "IM" and "ID" are abbreviations.
        if upper > 1 {
            return None;
        }
        format!("I{}", &contraction[1..])
    } else if upper == 0 {
        contraction.to_string()
    } else if upper == 1 && letters[0].is_uppercase() {
        let mut chars = contraction.chars();
        chars
            .next()
            .map(|c| c.to_uppercase().collect::<String>() + chars.as_str())?
    } else if upper == letters.len() && letters.len() > 1 {
        contraction.to_uppercase()
    } else {
        return None;
    };
    Some(out.replace('\'', &apostrophe.to_string()))
}
fn push(
    req: &Request,
    edits: &mut Vec<Edit>,
    start: usize,
    end: usize,
    replacement: String,
    reason: &str,
) {
    if let Some(e) = make_edit(
        &req.text,
        utf16_at(&req.text, start),
        utf16_at(&req.text, end),
        replacement,
        "Spelling",
        "spelling.contraction",
        reason,
        0.95,
    ) {
        edits.push(e);
    }
}
/// Whether an opening single quote earlier in the sentence makes a trailing one a closing quote.
fn quoted(text: &str, at: usize) -> bool {
    let start = text[..at].rfind(['.', '!', '?', '\n']).map_or(0, |i| i + 1);
    let before = &text[start..at];
    before.char_indices().any(|(i, c)| {
        (c == '\'' || c == '‘')
            && before[..i]
                .chars()
                .next_back()
                .is_none_or(|p| p.is_whitespace() || "([{\"“".contains(p))
    })
}
pub fn check(req: &Request, tokens: &[Token<'_>], edits: &mut Vec<Edit>) {
    let text = req.text.as_str();
    let apostrophe = if text.contains('’') && !text.contains('\'') {
        '’'
    } else {
        '\''
    };
    for (index, token) in tokens.iter().enumerate() {
        if !token.is_word || !token.surface.is_ascii() && !token.surface.contains('’') {
            continue;
        }
        // Glued to an identifier, path or address ("x.dont", "isnt_valid"): not prose.
        let before = text[..token.start_byte].chars().next_back();
        let after = text[token.end_byte..].chars().next();
        if before.is_some_and(|c| "._/@#\\-".contains(c) || c.is_alphanumeric())
            || after.is_some_and(|c| "_/@\\".contains(c) || c.is_ascii_digit())
            || after == Some('.')
                && text[token.end_byte + 1..].starts_with(|c: char| c.is_alphanumeric())
        {
            continue;
        }
        let normalized = token.normalized.as_str();
        let joined = normalized.replace('\'', "");
        let Some(full) = contraction(&joined) else {
            continue;
        };
        let frame = Frame { tokens, index };
        if normalized.contains('\'') {
            // "did'nt", "Your'e": the apostrophe is typed, in the wrong place.
            if normalized != full
                && let Some(replacement) = cased(full, token.surface, apostrophe)
            {
                push(
                    req,
                    edits,
                    token.start_byte,
                    token.end_byte,
                    replacement,
                    "Put the apostrophe where the letters were left out.",
                );
            }
            continue;
        }
        // "Lets'", "dont’": the apostrophe typed after the word.
        let trailing = after
            .filter(|c| *c == '\'' || *c == '’')
            .filter(|c| {
                text[token.end_byte + c.len_utf8()..]
                    .chars()
                    .next()
                    .is_none_or(|c| !c.is_alphanumeric())
                    && !quoted(text, token.start_byte)
            })
            .map(char::len_utf8);
        let word_form = WORD_FORMS.contains(&joined.as_str());
        let allowed = if trailing.is_some() {
            !word_form || ["lets", "its", "cant", "wont"].contains(&joined.as_str())
        } else if word_form {
            framed(&joined, &frame, text, token)
        } else if NOT_WORDS.contains(&joined.as_str()) {
            !DETERMINERS.contains(&frame.prev())
        } else {
            !spelling::ordinary(&joined)
        };
        // A capitalized form inside a sentence or before another capitalized word may be a name
        // ("Jony Ive", "Im Jae-won").
        let capitalized = token.surface.starts_with(char::is_uppercase);
        let capital_inside = capitalized
            && (!starts_sentence(text, token.start_byte, req) && !frame.clause_start(true)
                || tokens.get(index + 1).is_some_and(|n| {
                    n.is_word && n.surface.starts_with(char::is_uppercase) && n.normalized != "i"
                }));
        if !allowed || capital_inside && full.starts_with("i'") {
            continue;
        }
        if let Some(replacement) = cased(full, token.surface, apostrophe) {
            push(
                req,
                edits,
                token.start_byte,
                token.end_byte + trailing.unwrap_or(0),
                replacement,
                "Add the apostrophe to this contraction.",
            );
        }
    }
    // "I;m", "don\"t", "That;s": another key where the apostrophe belongs.
    static WRONG_MARK: OnceLock<Regex> = OnceLock::new();
    let wrong_mark = WRONG_MARK.get_or_init(|| {
        Regex::new(r#"\b([A-Za-z]+)[;"“”`´]([A-Za-z]{1,2})\b"#).expect("constant contraction regex")
    });
    for c in wrong_mark.captures_iter(text) {
        let (whole, left, right) = (&c[0], &c[1], &c[2]);
        let candidate = format!("{}'{}", left.to_lowercase(), right.to_lowercase());
        if !CONTRACTIONS.contains(&candidate.as_str()) || !right.chars().all(|c| c.is_lowercase()) {
            continue;
        }
        let m = c.get(0).expect("whole match");
        if let Some(replacement) = cased(
            &candidate,
            &whole.replace(|c: char| !c.is_alphabetic(), ""),
            apostrophe,
        ) {
            push(
                req,
                edits,
                m.start(),
                m.end(),
                replacement,
                "Use an apostrophe in this contraction.",
            );
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn fixed(text: &str) -> String {
        let req = Request {
            text: text.into(),
            ..Request::default()
        };
        let tokens = crate::tokenizer::tokenize(text, &[]);
        let mut edits = vec![];
        check(&req, &tokens, &mut edits);
        crate::apply_edits(text, &edits).unwrap().0
    }
    #[test]
    fn apostrophe_less_contractions_are_restored() {
        for (input, output) in [
            ("Ive got the tickets.", "I've got the tickets."),
            ("im heading out now", "I'm heading out now"),
            ("Shes in a meeting.", "She's in a meeting."),
            ("Theyll call us back.", "They'll call us back."),
            ("Whos bringing snacks?", "Who's bringing snacks?"),
            ("Heres the link.", "Here's the link."),
            ("It wasnt me.", "It wasn't me."),
            ("We shouldnt wait.", "We shouldn't wait."),
            ("You mightve missed it.", "You might've missed it."),
            ("DONT PANIC", "DON'T PANIC"),
            ("Hows the new job?", "How's the new job?"),
        ] {
            assert_eq!(fixed(input), output, "{input}");
        }
    }
    #[test]
    fn word_forms_change_only_in_their_frames() {
        for (input, output) in [
            ("Lets meet at noon.", "Let's meet at noon."),
            ("I cant open the file.", "I can't open the file."),
            ("It wont start.", "It won't start."),
            ("Ill send it tonight.", "I'll send it tonight."),
            ("Sure, ill check.", "Sure, I'll check."),
            ("Id like a refund.", "I'd like a refund."),
            ("Were almost ready.", "We're almost ready."),
            ("Were heading out.", "We're heading out."),
        ] {
            assert_eq!(fixed(input), output, "{input}");
        }
        for text in [
            "She lets the dog out.",
            "He felt ill after lunch.",
            "Enter your id and password.",
            "Were you there?",
            "They were leaving early.",
            "As is his wont, he left early.",
            "Political cant annoys me.",
            "The well is dry.",
            "Its handle broke.",
            "Ill health kept him home.",
            "Ill will lingers.",
            "Lets you pick a colour.",
            "Im Jae-won joined today.",
            "Jony Ive spoke first.",
        ] {
            assert_eq!(fixed(text), text, "{text}");
        }
    }
    #[test]
    fn misplaced_and_mistyped_apostrophes() {
        for (input, output) in [
            ("We could'nt find it.", "We couldn't find it."),
            ("He has'nt replied.", "He hasn't replied."),
            ("Your'e late.", "You're late."),
            ("Lets' start.", "Let's start."),
            ("Its' raining.", "It's raining."),
            ("I don;t mind.", "I don't mind."),
            ("I;ll be there.", "I'll be there."),
            ("It\"s fine.", "It's fine."),
            ("I dont’ mind.", "I don’t mind."),
        ] {
            assert_eq!(fixed(input), output, "{input}");
        }
        for text in [
            "Say 'well' twice.",
            "The 'lets' keyword is new.",
            "It's done; they're happy.",
            "Use a;b in the loop.",
            "Set x.isnt to true.",
            "Run is_not_dont now.",
            "That's the students' room.",
        ] {
            assert_eq!(fixed(text), text, "{text}");
        }
    }
}
