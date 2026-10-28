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

/// Who or what a negative opener asks about ("can't you", "isn't it", "don't they", "aren't we").
const ASKED_ABOUT: &[&str] = &[
    "you",
    "u",
    "we",
    "i",
    "he",
    "she",
    "they",
    "it",
    "this",
    "that",
    "there",
    "someone",
    "anyone",
    "somebody",
    "anybody",
    "everyone",
    "everybody",
    "these",
    "those",
    "the",
    "my",
    "your",
    "our",
    "his",
    "her",
    "their",
];

/// Chat laughter a Professional rewrite leaves out.
const LAUGHTER: &[&str] = &[
    "lol", "lmao", "lmfao", "rofl", "haha", "hahaha", "hehe", "omg",
];
/// What follows "ur" when it stands for "you are" ("ur right", "ur the best", "ur going to");
/// before anything else it is "your" ("ur email").
const UR_PREDICATES: &[&str] = &[
    "right",
    "wrong",
    "correct",
    "welcome",
    "going",
    "not",
    "the",
    "a",
    "an",
    "so",
    "very",
    "really",
    "too",
    "always",
    "never",
    "just",
    "still",
    "already",
    "ready",
    "able",
    "done",
    "sure",
    "being",
    "doing",
    "getting",
    "coming",
    "late",
    "early",
    "such",
    "all",
    "probably",
    "definitely",
    "totally",
    "absolutely",
    "also",
    "only",
    "now",
    "here",
    "there",
    "perfect",
    "fine",
    "ok",
    "okay",
    "good",
    "great",
    "awesome",
    "amazing",
    "kind",
    "nice",
    "sweet",
    "funny",
    "crazy",
    "invited",
    "free",
    "busy",
    "supposed",
    "allowed",
    "in",
    "on",
    "at",
    "from",
    "with",
    "gonna",
    "welcome",
];
/// Words before "gotta" that give it its subject: "I gotta run" is "I have to run".
const GOTTA_SUBJECTS: &[&str] = &[
    "i", "you", "we", "they", "and", "but", "so", "just", "really", "now", "also", "then", "if",
    "that", "because", "who", "which", "what", "when", "as", "or", "still", "all",
];
/// Words that follow a sentence-opening "ya" when it means "yes" ("ya, I can", "ya I can"), as
/// against "ya know" or "ya coming?", which are "you".
const YA_YES_BEFORE: &[&str] = &[
    "i",
    "we",
    "he",
    "she",
    "they",
    "it",
    "that",
    "sure",
    "definitely",
    "totally",
    "exactly",
    "thanks",
    "please",
    "no",
    "of",
];

/// Chat shorthand a Professional rewrite spells out, with what it stands for.
const SHORTHAND: &[(&str, &str)] = &[
    ("u", "you"),
    ("pls", "please"),
    ("plz", "please"),
    ("thx", "thanks"),
    // Said of a doubt, not a negation: "I am unsure" keeps the writer's "idk" free of a "not".
    ("idk", "I am unsure"),
    ("brb", "I am stepping away briefly"),
    ("omg", "wow"),
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
        let first = tokens[..i]
            .iter()
            .rev()
            .find(|p| p.is_word || [".", "!", "?"].contains(&p.surface))
            .is_none_or(|p| p.sentence != t.sentence);
        // The word's own neighbours, for the shorthand whose meaning depends on them.
        let before = i
            .checked_sub(1)
            .map(|k| tokens[k].surface.to_lowercase())
            .unwrap_or_default();
        let next = tokens
            .get(i + 1..)
            .and_then(|rest| rest.iter().find(|n| n.is_word))
            .filter(|n| n.sentence == t.sentence)
            .map(|n| n.surface.to_lowercase());
        let full: String = match lower.as_str() {
            // "ya, I can" is "yes"; "see ya" and "ya know" are "you".
            "ya" => {
                let yes = first
                    && (tokens.get(i + 1).is_some_and(|n| n.surface == ",")
                        || next.as_deref().is_some_and(|n| YA_YES_BEFORE.contains(&n)));
                if yes { "yes" } else { "you" }.to_owned()
            }
            // "gotta run" is "I have to run"; "we gotta run" is "we have to run"; "she's gotta" is "she's got to".
            "gotta" => if before.ends_with("'s")
                || before.ends_with("’s")
                || before.ends_with("'ve")
                || before.ends_with("’ve")
            {
                "got to"
            } else if matches!(before.as_str(), "he" | "she" | "it") {
                "has to"
            } else if first || !GOTTA_SUBJECTS.contains(&before.as_str()) && !tokens[i - 1].is_word
            {
                "I have to"
            } else {
                "have to"
            }
            .to_owned(),
            // "ur right" is "you are right"; "ur email" is "your email".
            "ur" => if next.as_deref().is_some_and(|n| UR_PREDICATES.contains(&n)) {
                "you are"
            } else {
                "your"
            }
            .to_owned(),
            _ => {
                let Some(&(_, full)) = SHORTHAND.iter().find(|(s, _)| *s == lower) else {
                    continue;
                };
                // "U" alone is a letter or a name ("Plan U"); only the lowercase chat form is "you".
                if lower == "u" && t.surface != "u" {
                    continue;
                }
                full.to_owned()
            }
        };
        let replacement = if first && t.surface.starts_with(char::is_uppercase) {
            upper_first(&full)
        } else {
            full
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

/// Sign-off phrases a letter or message closes with ("Thanks,", "Best regards,", "See you Monday,").
const SIGN_OFF: &str = r"(?:thanks(?:\s+(?:a\s+lot|again|so\s+much))?|thank\s+you(?:\s+(?:again|so\s+much))?|many\s+thanks|with\s+thanks|(?:(?:best|kind|warm|warmest|with\s+best|with\s+kind|with\s+warm)\s+)?regards|best(?:\s+wishes)?|cheers|(?:yours\s+)?(?:sincerely|faithfully|truly)|respectfully|cordially|warmly|enjoy|talk\s+soon|see\s+you(?:\s+\w+)?|take\s+care)";
/// The opening words of a greeting ("Hi", "Dear", "Good morning").
const GREETING: &str = r"(?:hi|hello|hey|dear|greetings|good\s+(?:morning|afternoon|evening))";

/// The greeting and the sign-off of a letter or message: byte ranges a tone rewrite leaves as
/// the writer wrote them, as it leaves the line breaks between them and the body. "Hi Dana,"
/// and "Cheers,\nLee" are not content to reword, and the model drops or merges them.
pub(crate) fn letter_frame(text: &str) -> Vec<(usize, usize)> {
    static GREETING_RE: std::sync::OnceLock<regex::Regex> = std::sync::OnceLock::new();
    static SIGN_OFF_RE: std::sync::OnceLock<regex::Regex> = std::sync::OnceLock::new();
    let greeting = GREETING_RE.get_or_init(|| {
        // "Hi Dana,", "Good morning Ms. Alvarez," or "Hello," on a line of their own, or "Hey Sam,"
        // opening a message.
        regex::Regex::new(&format!(r"(?i)^\s*{GREETING}\b[^,\n!]{{0,32}}[,!]"))
            .expect("constant greeting pattern")
    });
    let sign_off = SIGN_OFF_RE.get_or_init(|| {
        // "Thanks,\nOmar" and "…last night. Best, Maya": the phrase, a comma, and a name of up to
        // three words that ends the message.
        regex::Regex::new(&format!(
            r"(?i)(?:^|\n|[.!?][ \t]+){SIGN_OFF}[ \t]*,[ \t]*\n?[ \t]*[\p{{L}}][\p{{L}}.'’-]*(?:[ \t]+[\p{{L}}][\p{{L}}.'’-]*){{0,2}}[ \t]*$"
        ))
        .expect("constant sign-off pattern")
    });
    let mut spans = vec![];
    if let Some(m) = greeting.find(text) {
        // The greeting is the first line's words up to its comma; leading space and the line break
        // after it are not part of it.
        let found = m.as_str();
        let end = m.end();
        let start = m.start() + (found.len() - found.trim_start().len());
        if start < end && end - start <= 40 {
            spans.push((start, end));
        }
    }
    if let Some(m) = sign_off.find(text) {
        let found = m.as_str();
        let lead = found.len()
            - found
                .trim_start_matches(['\n', '.', '!', '?', ' ', '\t'])
                .len();
        let (start, end) = (m.start() + lead, m.end());
        if spans.last().is_none_or(|&(_, e)| start >= e) {
            spans.push((start, end));
        }
    }
    spans
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

/// A clause that only hedges or apologizes before a request or a claim, to be followed by
/// "but" or a comma: "I'm not sure, but", "I may be wrong, but", "I hope you don't mind me
/// asking, but", "Sorry to bother you again, but", "I hate to ask, but". Padding in Concise and
/// Direct, words, negations and modals included (`meaning::hedge_opener_regex` is the same list).
fn hedge_lead_regex() -> &'static regex::Regex {
    static RE: std::sync::OnceLock<regex::Regex> = std::sync::OnceLock::new();
    RE.get_or_init(|| {
        regex::Regex::new(
            r"(?i)^(?:sorry,?\s+)?(?:i\s+(?:may|might|could)\s+be\s+wrong|i\s+(?:do\s+not|don['’]t)\s+know|i(?:['’]m|\s+am)\s+not\s+(?:sure|certain)|i\s+hope\s+you\s+(?:do\s+not|don['’]t)\s+mind(?:\s+(?:me|my)\s+ask(?:ing)?)?|i\s+hate\s+to\s+ask|sorry\s+to\s+bother\s+you(?:\s+again)?)(?:\s*,\s*(?:but\s+)?|\s+but\s+)",
        )
        .expect("constant hedge lead regex")
    })
}
/// "I was hoping you might be able to help me with …": a request said as a hope.
fn hoping_regex() -> &'static regex::Regex {
    static RE: std::sync::OnceLock<regex::Regex> = std::sync::OnceLock::new();
    RE.get_or_init(|| {
        regex::Regex::new(
            r"(?i)^i(?:\s+was|\s+am|['’]m)\s+hoping\s+(?:that\s+)?you\s+(?:could|can|might\s+be\s+able\s+to|would\s+be\s+able\s+to|might|would)\s+(?:possibly\s+|maybe\s+|perhaps\s+)?(?P<verb>[a-z]+)\b",
        )
        .expect("constant hoping regex")
    })
}
/// "could you possibly …": the adverb goes with the hedge.
fn possibly_regex() -> &'static regex::Regex {
    static RE: std::sync::OnceLock<regex::Regex> = std::sync::OnceLock::new();
    RE.get_or_init(|| {
        regex::Regex::new(
            r"(?i)^(?P<modal>could|can|would|will)\s+you\s+(?:possibly|maybe|perhaps|kindly)\s+",
        )
        .expect("constant possibly regex")
    })
}
/// "Would you mind terribly if I borrowed …": a request for permission.
fn would_mind_regex() -> &'static regex::Regex {
    static RE: std::sync::OnceLock<regex::Regex> = std::sync::OnceLock::new();
    RE.get_or_init(|| {
        regex::Regex::new(
            r"(?i)^would\s+you\s+mind\s+(?:(?:terribly|very\s+much|too\s+much|at\s+all)\s+)?if\s+i\s+(?P<verb>[a-z]+)\b",
        )
        .expect("constant would mind regex")
    })
}
/// "Maybe it would be a good idea to …": a suggestion put as a question.
fn good_idea_regex() -> &'static regex::Regex {
    static RE: std::sync::OnceLock<regex::Regex> = std::sync::OnceLock::new();
    RE.get_or_init(|| {
        regex::Regex::new(r"(?i)^maybe\s+it\s+would\s+be\s+a\s+good\s+idea\s+to\s+")
            .expect("constant good idea regex")
    })
}

/// How one sentence changes: the bytes before `cut` become `head`, and a final "." may become
/// "?". The rest of the sentence stays as written.
struct HedgePlan {
    cut: usize,
    head: String,
    mark: Option<&'static str>,
}
fn hedge_plan(mode: crate::Mode, sentence: &str) -> Option<HedgePlan> {
    let words = |s: &str| s.split_whitespace().count();
    let concise = mode == crate::Mode::Concise;
    let lead = hedge_lead_regex().find(sentence).map_or(0, |m| m.end());
    let rest = &sentence[lead..];
    if lead > 0 {
        // A clause must follow the hedge ("I'm not sure, but." alone stays).
        if words(rest) < 3 || !rest.starts_with(char::is_alphanumeric) {
            return None;
        }
        // "I was hoping you might be able to help me with …" asks for the help.
        if let Some(c) = hoping_regex().captures(rest) {
            let verb = c.name("verb")?;
            if REQUEST_VERBS.contains(&verb.as_str().to_lowercase().as_str())
                && sentence.ends_with('.')
            {
                return Some(HedgePlan {
                    cut: lead + verb.start(),
                    head: if concise { "Could you " } else { "Please " }.into(),
                    mark: concise.then_some("?"),
                });
            }
        }
        // "could you possibly cover …" is "Could you cover …".
        if let Some(c) = possibly_regex().captures(rest) {
            let modal = c.name("modal")?.as_str();
            let cap = format!(
                "{}{} you ",
                modal[..1].to_uppercase(),
                &modal[1..].to_lowercase()
            );
            return Some(HedgePlan {
                cut: lead + c.get(0)?.end(),
                head: cap,
                mark: None,
            });
        }
        let first = rest.chars().next()?.len_utf8();
        return Some(HedgePlan {
            cut: lead + first,
            head: rest[..first].to_uppercase(),
            mark: None,
        });
    }
    // "Would you mind terribly if I borrowed my notes?" is "Could I borrow my notes?".
    if let Some(c) = would_mind_regex().captures(sentence) {
        let verb = c.name("verb")?;
        let past = verb.as_str().to_lowercase();
        let base = crate::morphology::verb(&past)
            .filter(|v| v.past == past && v.base != past)?
            .base;
        return Some(HedgePlan {
            cut: verb.end(),
            head: format!("Could I {base}"),
            mark: None,
        });
    }
    // Concise keeps a question a question: "Maybe it would be a good idea to back up the files
    // before we upgrade?" is "Should we back up the files before we upgrade?".
    if concise && sentence.ends_with('?') {
        let m = good_idea_regex().find(sentence)?;
        let body = &sentence[m.end()..];
        if words(body) >= 3
            && body
                .split(|c: char| !c.is_alphabetic())
                .any(|w| w.eq_ignore_ascii_case("we"))
        {
            return Some(HedgePlan {
                cut: m.end(),
                head: "Should we ".into(),
                mark: None,
            });
        }
    }
    None
}

/// Hedge openers said plainly (Concise, Direct): "I hope you do not mind me asking, but have you
/// had a chance to review the invoice?" is "Have you had a chance to review the invoice?", "I
/// hate to ask, but could you possibly cover my shift?" is "Could you cover my shift?", "Sorry
/// to bother you again, but I was hoping you might be able to help me with it." is "Could you
/// help me with it?" (Concise) or "Please help me with it." (Direct), "Would you mind terribly
/// if I borrowed your notes?" is "Could I borrow your notes?". Only at a sentence start, and
/// only when a clause follows.
pub(crate) fn hedge_forms(req: &Request, protected: &[TextRange]) -> Vec<Edit> {
    if !matches!(req.mode, crate::Mode::Concise | crate::Mode::Direct) {
        return vec![];
    }
    let text = req.text.as_str();
    // The tagger reads a capitalized "Sorry," as a name; here it is the apology that opens a hedge.
    let protected: Vec<TextRange> = protected
        .iter()
        .filter(|p| {
            crate::byte_at(text, p.start_utf16)
                .zip(crate::byte_at(text, p.end_utf16))
                .and_then(|(a, b)| text.get(a..b))
                .is_none_or(|word| !word.eq_ignore_ascii_case("sorry"))
        })
        .cloned()
        .collect();
    let protected = protected.as_slice();
    let tokens = tokenizer::tokenize(text, &req.tokens);
    let mut edits = vec![];
    let mut previous = usize::MAX;
    for (i, t) in tokens.iter().enumerate() {
        if t.sentence == previous || !t.is_word {
            previous = t.sentence;
            continue;
        }
        previous = t.sentence;
        let Some(last) = tokens
            .iter()
            .skip(i)
            .take_while(|n| n.sentence == t.sentence)
            .last()
        else {
            continue;
        };
        let sentence = &text[t.start_byte..last.end_byte];
        let Some(plan) = hedge_plan(req.mode, sentence) else {
            continue;
        };
        let utf16 = |b: usize| text[..b].encode_utf16().count();
        let (a, b) = (t.start_byte, t.start_byte + plan.cut);
        let mut spans = vec![(a, b, plan.head)];
        if let Some(mark) = plan.mark
            && last.surface == "."
        {
            spans.push((last.start_byte, last.end_byte, mark.to_owned()));
        }
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
                    "tone.plain_hedge",
                    "Say it without the hedge.",
                ));
            }
        }
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
    // A sign-off at the end ("Thanks, remy", "Cheers,\nLee") is a name, not a sentence.
    if letter_frame(text)
        .iter()
        .any(|&(from, to)| to == body.len() && from > 0)
    {
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
            // "can't you do it", "isn't it done": a negative opener asks only before its subject.
            // "Can't open the file" and "Don't forget the milk" are statements and commands.
            && (!words[lead].ends_with("n't")
                || words
                    .get(lead + 1)
                    .is_some_and(|w| ASKED_ABOUT.contains(&w.as_str())))
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
        // A negative contraction opens a question only before its subject.
        for text in [
            "can't make it tomorrow, got a dentist appointment at 9am",
            "can't open the file, it says it's corrupted",
            "don't forget to bring the charger",
        ] {
            assert!(floored(text).ends_with('.'), "{text}");
        }
        assert_eq!(floored("isn't it ready by now"), "Isn't it ready by now?");
        assert_eq!(
            floored("can't you send it today"),
            "Can't you send it today?"
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

    fn hedged(mode: crate::Mode, text: &str) -> String {
        let req = Request {
            text: text.into(),
            mode,
            ..Default::default()
        };
        apply(text, hedge_forms(&req, &[]))
    }

    #[test]
    fn hedge_openers_are_said_plainly_in_concise_and_direct() {
        use crate::Mode::{Concise, Direct};
        for (mode, text, expected) in [
            (
                Concise,
                "I hope you do not mind me asking, but have you had a chance to review the invoice?",
                "Have you had a chance to review the invoice?",
            ),
            (
                Direct,
                "I hope you don\u{2019}t mind me asking, but have you had a chance to review the invoice?",
                "Have you had a chance to review the invoice?",
            ),
            (
                Concise,
                "I hate to ask, but could you possibly cover my shift on Saturday?",
                "Could you cover my shift on Saturday?",
            ),
            (
                Direct,
                "I hate to ask, but could you possibly cover my shift on Saturday?",
                "Could you cover my shift on Saturday?",
            ),
            (
                Concise,
                "Sorry to bother you again, but I was hoping you might be able to help me with one more thing.",
                "Could you help me with one more thing?",
            ),
            (
                Direct,
                "Sorry to bother you again, but I was hoping you might be able to help me with one more thing.",
                "Please help me with one more thing.",
            ),
            (
                Concise,
                "Sorry, I may be wrong, but I believe the total might be off by a bit.",
                "I believe the total might be off by a bit.",
            ),
            (
                Direct,
                "I\u{2019}m not sure, but the client might prefer the blue version.",
                "The client might prefer the blue version.",
            ),
            (
                Direct,
                "I don't know, I guess we might want to think about hiring another designer.",
                "I guess we might want to think about hiring another designer.",
            ),
            (
                Concise,
                "Would you mind terribly if I borrowed your notes from the lecture?",
                "Could I borrow your notes from the lecture?",
            ),
            (
                Direct,
                "Would you mind if I took the last slot?",
                "Could I take the last slot?",
            ),
            (
                Concise,
                "Maybe it would be a good idea to back up the files before we upgrade?",
                "Should we back up the files before we upgrade?",
            ),
            // The second sentence of a message is handled too.
            (
                Direct,
                "Hello. I\u{2019}m not sure, but the report is late.",
                "Hello. The report is late.",
            ),
        ] {
            assert_eq!(hedged(mode, text), expected, "{mode:?}: {text}");
        }
        // Nothing changes without a clause behind the hedge, in the other tones, or when the
        // doubt is the point of the sentence.
        for (mode, text) in [
            (Concise, "I\u{2019}m not sure, but."),
            (Concise, "I am not sure the design works."),
            (Direct, "I don't know whether the invoice was paid."),
            (
                crate::Mode::Friendly,
                "I hate to ask, but could you possibly cover my shift?",
            ),
            (
                crate::Mode::Professional,
                "I hate to ask, but could you possibly cover my shift?",
            ),
            // A suggestion without a "we" in it, or a verb whose past is its base, stays.
            (Concise, "Maybe it would be a good idea to rest?"),
            (Direct, "Would you mind if I read your notes?"),
            (Direct, "Would you mind if I put the box here?"),
        ] {
            assert_eq!(hedged(mode, text), text, "{mode:?}: {text}");
        }
    }

    #[test]
    fn a_sorry_the_tagger_took_for_a_name_still_goes_with_its_hedge() {
        let text = "Sorry, I may be wrong, but I believe the total might be off by a bit.";
        let req = Request {
            text: text.into(),
            mode: crate::Mode::Direct,
            ..Default::default()
        };
        let sorry = [TextRange {
            start_utf16: 0,
            end_utf16: 5,
        }];
        assert_eq!(
            apply(text, hedge_forms(&req, &sorry)),
            "I believe the total might be off by a bit."
        );
    }

    #[test]
    fn a_hedge_around_a_protected_name_is_left_alone() {
        let text = "I hate to ask, but could you possibly cover Priya's shift?";
        let req = Request {
            text: text.into(),
            mode: crate::Mode::Concise,
            ..Default::default()
        };
        let head = [TextRange {
            start_utf16: 0,
            end_utf16: 3,
        }];
        assert!(hedge_forms(&req, &head).is_empty());
        assert_eq!(
            apply(text, hedge_forms(&req, &[])),
            "Could you cover Priya's shift?"
        );
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

    #[test]
    fn a_letter_frame_is_its_greeting_and_its_sign_off() {
        let frame = |text: &str| -> Vec<String> {
            letter_frame(text)
                .into_iter()
                .map(|(a, b)| text[a..b].to_owned())
                .collect()
        };
        assert_eq!(
            frame("Hi Dana,\n\nThe files are attached.\n\nThanks,\nOmar"),
            ["Hi Dana,", "Thanks,\nOmar"]
        );
        assert_eq!(
            frame("Good morning Ms. Alvarez,\n\nSee you at ten."),
            ["Good morning Ms. Alvarez,"]
        );
        assert_eq!(
            frame("Hello,\n\nI would like to cancel.\n\nRegards,\nM. Okonkwo"),
            ["Hello,", "Regards,\nM. Okonkwo"]
        );
        assert_eq!(
            frame("Hi team, the build is green again. Cheers, Jo"),
            ["Hi team,", "Cheers, Jo"]
        );
        assert_eq!(
            frame("hey jules, did the package come? thanks, remy"),
            ["hey jules,", "thanks, remy"]
        );
        assert_eq!(
            frame("Hey Rhea, the meeting is at 4. Talk soon, Dev"),
            ["Hey Rhea,", "Talk soon, Dev"]
        );
        assert_eq!(
            frame("Hello Ines,\n\nWe have received your payment.\n\nWith thanks,\nBilling"),
            ["Hello Ines,", "With thanks,\nBilling"]
        );
        assert_eq!(
            frame("Hi Noor,\n\nWelcome to the team.\n\nSee you Monday,\nAlex"),
            ["Hi Noor,", "See you Monday,\nAlex"]
        );
        // Not a frame: a body that merely starts like one or ends with thanks.
        assert!(frame("Hello world is a program.").is_empty());
        assert!(frame("I said hi to everyone.").is_empty());
        assert!(frame("Thanks, I will send the report tomorrow morning.").is_empty());
        assert!(frame("Send it today.").is_empty());
    }

    #[test]
    fn professional_spells_out_the_rest_of_the_chat_shorthand() {
        for (text, expected) in [
            // omg goes like laughter does (the floor then gives the next word its capital).
            (
                "omg the demo went great, everyone loved it",
                "the demo went great, everyone loved it",
            ),
            ("OMG the demo went great", "the demo went great"),
            ("that was omg so good", "that was so good"),
            ("omg", "wow"),
            // idk is a doubt, said without a negation.
            (
                "idk, maybe try restarting the router first",
                "I am unsure, maybe try restarting the router first",
            ),
            ("IDK if he is coming", "I am unsure if he is coming"),
            (
                "brb, grabbing my charger",
                "I am stepping away briefly, grabbing my charger",
            ),
            ("Brb", "I am stepping away briefly"),
            // ya is yes at the start of a reply, you elsewhere.
            ("ya i can cover thursday", "yes i can cover thursday"),
            ("Ya, I can cover Thursday", "Yes, I can cover Thursday"),
            ("see ya at the meeting", "see you at the meeting"),
            ("ya know what I mean", "you know what I mean"),
            // gotta takes its subject, or is given "I".
            (
                "gotta run, my train leaves at 6:15",
                "I have to run, my train leaves at 6:15",
            ),
            ("Gotta run", "I have to run"),
            ("we gotta run", "we have to run"),
            ("ok, gotta run", "ok, I have to run"),
            ("she's gotta run", "she's got to run"),
            ("she gotta run", "she has to run"),
            // ur is "you are" before a predicate and "your" before a noun.
            (
                "ur right, i should have asked",
                "you are right, i should have asked",
            ),
            ("Ur the best", "You are the best"),
            ("ur going to love it", "you are going to love it"),
            ("send ur email", "send your email"),
            ("Ur invoice is late", "Your invoice is late"),
        ] {
            assert_eq!(professional(text), expected, "{text:?}");
        }
        // Words that merely contain the shorthand, and ones beside a dash or dot, stay.
        for text in [
            "The yacht gotten there",
            "Omega gotta-go",
            "burr is not ur-text",
            "Visit ya.example.com",
            "The idk-test passed",
        ] {
            assert_eq!(professional(text), text, "{text:?}");
        }
    }
}
