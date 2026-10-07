//! Mark-level punctuation: doubled marks, spacing around sentence marks and brackets, quotation
//! marks left open, compound-modifier hyphens, apostrophes in plurals and possessives, and colons
//! or semicolons in the wrong place. Each rule needs an unambiguous local shape; anything a writer
//! may have meant (an ellipsis, "?!", a colon before a clause) stays as typed.
use crate::{
    Edit, Request, make_edit, morphology, spelling,
    tokenizer::{self, Token},
    utf16_at,
};
use regex::Regex;
use std::sync::OnceLock;

pub fn check(req: &Request, edits: &mut Vec<Edit>) {
    let tokens = tokenizer::tokenize(&req.text, &req.tokens);
    doubled_marks(req, edits);
    sentence_spacing(req, edits);
    bracket_spacing(req, edits);
    open_quotes(req, edits);
    hyphens(req, &tokens, edits);
    apostrophes(req, &tokens, edits);
    colons(req, &tokens, edits);
}

#[expect(
    clippy::too_many_arguments,
    reason = "Mirrors make_edit with byte offsets; every call site names its rule."
)]
fn put(
    req: &Request,
    edits: &mut Vec<Edit>,
    a: usize,
    b: usize,
    replacement: &str,
    id: &str,
    reason: &str,
    confidence: f32,
) {
    if let Some(edit) = make_edit(
        &req.text,
        utf16_at(&req.text, a),
        utf16_at(&req.text, b),
        replacement.into(),
        "Punctuation",
        id,
        reason,
        confidence,
    ) {
        edits.push(edit);
    }
}

/// Abbreviations whose period may be followed by another mark ("etc.,", "Inc.:").
const ABBREVIATIONS: [&str; 22] = [
    "etc", "inc", "ltd", "co", "corp", "jr", "sr", "st", "vs", "approx", "dept", "est", "no", "mr",
    "mrs", "ms", "dr", "prof", "jan", "feb", "aug", "sept",
];
/// Closing words of a letter, which keep their comma ("Kind regards.," is "Kind regards,").
const SIGN_OFFS: [&str; 9] = [
    "regards",
    "best",
    "thanks",
    "cheers",
    "sincerely",
    "wishes",
    "soon",
    "yours",
    "faithfully",
];

/// ",," ".." "?." "!," ".;" and the like: one mark too many. An ellipsis ("...") and emphatic runs
/// of only "!" and "?" ("?!", "!!") are the writer's choice.
fn doubled_marks(req: &Request, edits: &mut Vec<Edit>) {
    static RUN: OnceLock<Regex> = OnceLock::new();
    let run = RUN.get_or_init(|| Regex::new(r"[.,;:!?]{2,}").expect("constant mark run"));
    let text = &req.text;
    for m in run.find_iter(text) {
        let marks = m.as_str();
        if marks.contains("..") && marks.matches('.').count() >= 3
            || marks.chars().all(|c| c == '!' || c == '?')
        {
            continue;
        }
        let before = text[..m.start()].chars().next_back();
        let after = text[m.end()..].chars().next();
        if !before.is_some_and(|c| c.is_alphanumeric() || ")”\"’'%".contains(c))
            || after.is_some_and(|c| !c.is_whitespace() && !"”\"’)".contains(c))
        {
            continue;
        }
        // The word before the run, with its own dots ("p.m", "i.e").
        let word: String = text[..m.start()]
            .chars()
            .rev()
            .take_while(|c| c.is_alphanumeric() || *c == '.')
            .collect::<Vec<_>>()
            .into_iter()
            .rev()
            .collect();
        let first = marks.chars().next().unwrap_or(' ');
        let replacement: String = if marks.chars().all(|c| c == first) {
            if first == '.' && marks.len() != 2 {
                continue;
            }
            first.to_string()
        } else if marks.contains(['!', '?']) {
            marks.chars().filter(|c| *c == '!' || *c == '?').collect()
        } else if marks.contains('.') {
            if first == '.'
                && (word.contains('.') || ABBREVIATIONS.contains(&word.to_lowercase().as_str()))
            {
                continue;
            }
            // A sign-off line keeps its comma.
            let line = text[..m.start()].rsplit('\n').next().unwrap_or("");
            let last = line
                .split_whitespace()
                .next_back()
                .unwrap_or("")
                .to_lowercase();
            let line_end = after.is_none_or(|c| c == '\n');
            if marks == ".," && line_end && SIGN_OFFS.contains(&last.as_str()) {
                ",".into()
            } else {
                ".".into()
            }
        } else {
            continue;
        };
        put(
            req,
            edits,
            m.start(),
            m.end(),
            &replacement,
            "punctuation.doubled_mark",
            "Use one punctuation mark here.",
            0.93,
        );
    }
}

/// Words that start a sentence often enough that "file.Let" or "3pm.Please" is a missing space,
/// not a code identifier ("user.Name") or a domain.
const OPENERS: &[&str] = &[
    "the",
    "a",
    "an",
    "i",
    "we",
    "you",
    "he",
    "she",
    "they",
    "it",
    "this",
    "that",
    "these",
    "those",
    "there",
    "here",
    "my",
    "our",
    "your",
    "his",
    "her",
    "their",
    "please",
    "let",
    "let's",
    "thanks",
    "thank",
    "all",
    "see",
    "what",
    "where",
    "when",
    "why",
    "how",
    "who",
    "can",
    "could",
    "would",
    "will",
    "do",
    "did",
    "is",
    "are",
    "also",
    "so",
    "and",
    "but",
    "if",
    "just",
    "sorry",
    "ok",
    "okay",
    "no",
    "yes",
    "hope",
    "any",
    "some",
    "every",
    "then",
    "now",
    "both",
    "after",
    "before",
    "i'm",
    "i'll",
    "i've",
    "i'd",
    "we're",
    "we'll",
    "we've",
    "it's",
    "that's",
    "there's",
    "you're",
    "they're",
    "he's",
    "she's",
    "don't",
    "didn't",
    "can't",
    "call",
    "check",
    "feel",
    "talk",
    "note",
    "looking",
    "have",
    "send",
    "however",
    "otherwise",
    "meanwhile",
];
/// "end.Next", "Thanks!See", "time?I": a sentence mark glued to the next sentence.
fn sentence_spacing(req: &Request, edits: &mut Vec<Edit>) {
    static GLUED: OnceLock<Regex> = OnceLock::new();
    static BEFORE_STOP: OnceLock<Regex> = OnceLock::new();
    let glued = GLUED.get_or_init(|| {
        Regex::new(r"(?P<left>[\p{L}\d%)]+)(?P<mark>[.!?]+)(?P<right>\p{Lu}[\p{L}'’]*)")
            .expect("constant glued sentence")
    });
    let text = &req.text;
    for cap in glued.captures_iter(text) {
        let (left, mark, right) = (&cap["left"], &cap["mark"], &cap["right"]);
        let whole = cap.get(0).expect("match");
        // Part of a longer identifier, path or address.
        if text[..whole.start()]
            .chars()
            .next_back()
            .is_some_and(|c| !c.is_whitespace() && !"(\"“$€£".contains(c))
            || text[whole.end()..]
                .chars()
                .next()
                .is_some_and(|c| c.is_alphanumeric() || "._/@-".contains(c))
        {
            continue;
        }
        let sentence_mark = mark.contains(['!', '?']);
        if mark.contains('.') && mark.len() > 1 && !sentence_mark {
            continue;
        }
        let lower = right.to_lowercase().replace('’', "'");
        if !sentence_mark
            && (!OPENERS.contains(&lower.as_str())
                || !left
                    .chars()
                    .next_back()
                    .is_some_and(|c| c.is_lowercase() || c.is_ascii_digit())
                || left.chars().any(char::is_uppercase) && left.chars().count() > 1)
        {
            continue;
        }
        let at = cap.name("mark").expect("mark").end();
        put(
            req,
            edits,
            at,
            at,
            " ",
            "punctuation.after_sentence_mark",
            "Add a space after the end of the sentence.",
            0.95,
        );
    }
    // "I'm on my way ." and "Got it . Thanks": a space before the period.
    let before_stop = BEFORE_STOP.get_or_init(|| {
        Regex::new(r"[\p{L}\d)][ \t]+(?P<stop>\.)(?:[ \t\n]|$)").expect("constant spaced stop")
    });
    for cap in before_stop.captures_iter(text) {
        let whole = cap.get(0).expect("match");
        let stop = cap.name("stop").expect("stop");
        let start = whole.start()
            + text[whole.start()..]
                .chars()
                .next()
                .map_or(1, char::len_utf8);
        put(
            req,
            edits,
            start,
            stop.start(),
            "",
            "punctuation.before_mark",
            "Remove whitespace before punctuation.",
            0.95,
        );
    }
}

/// Words that open a parenthetical remark ("me(if you can)"), unlike a code call ("print(x y)").
const PARENTHETICAL: [&str; 24] = [
    "if",
    "maybe",
    "and",
    "or",
    "but",
    "not",
    "which",
    "who",
    "probably",
    "possibly",
    "see",
    "at",
    "in",
    "on",
    "for",
    "with",
    "about",
    "around",
    "just",
    "only",
    "especially",
    "including",
    "unless",
    "so",
];
/// "( second floor)", "(maybe 6:30 )" and "me(if you can)".
fn bracket_spacing(req: &Request, edits: &mut Vec<Edit>) {
    static INNER: OnceLock<Regex> = OnceLock::new();
    static GLUED: OnceLock<Regex> = OnceLock::new();
    let text = &req.text;
    let inner = INNER.get_or_init(|| {
        Regex::new(
            r"\((?P<open>[ \t]+)[^()\n]*?\S(?P<close>[ \t]*)\)|\([^()\n]*?\S(?P<close2>[ \t]+)\)",
        )
        .expect("constant bracket spacing")
    });
    for cap in inner.captures_iter(text) {
        for name in ["open", "close", "close2"] {
            if let Some(space) = cap.name(name).filter(|m| !m.is_empty()) {
                put(
                    req,
                    edits,
                    space.start(),
                    space.end(),
                    "",
                    "punctuation.bracket_spacing",
                    "Remove the space inside the parentheses.",
                    0.94,
                );
            }
        }
    }
    let glued = GLUED.get_or_init(|| {
        Regex::new(r"(?:^|[ \t])(?P<word>\p{Ll}{2,})\((?P<first>\p{Ll}{2,}) [^()=;{}\n]*\)")
            .expect("constant glued bracket")
    });
    for cap in glued.captures_iter(text) {
        let (word, first) = (&cap["word"], &cap["first"]);
        if !spelling::ordinary(word) || !PARENTHETICAL.contains(&first) {
            continue;
        }
        let at = cap.name("word").expect("word").end();
        put(
            req,
            edits,
            at,
            at,
            " ",
            "punctuation.bracket_spacing",
            "Add a space before the parentheses.",
            0.9,
        );
    }
}

/// Verbs that introduce what someone said or wrote.
const SPEECH: [&str; 26] = [
    "said",
    "says",
    "say",
    "asked",
    "asks",
    "ask",
    "wrote",
    "writes",
    "replied",
    "replies",
    "goes",
    "texted",
    "texts",
    "told",
    "tells",
    "yelled",
    "shouted",
    "added",
    "reads",
    "read",
    "typed",
    "answered",
    "whispered",
    "messaged",
    "posted",
    "tweeted",
];
/// Words that continue the outer sentence after a short quoted label ("“Export to download").
const CLOSERS: [&str; 22] = [
    "and", "like", "to", "from", "in", "on", "at", "if", "then", "but", "so", "or", "as",
    "because", "when", "cannot", "can't", "can", "must", "should", "will", "won't",
];
/// The byte of the unmatched opening quotation mark of `paragraph` (absolute offsets), if any.
fn unmatched_open(text: &str, from: usize, to: usize) -> Option<(usize, char)> {
    let paragraph = &text[from..to];
    let mut open: Option<usize> = None;
    for (i, c) in paragraph.char_indices() {
        match c {
            '“' => open = Some(from + i),
            '”' => open = None,
            _ => {}
        }
    }
    if let Some(at) = open {
        return Some((at, '“'));
    }
    if paragraph.contains(['`', '=', '{', '}']) || paragraph.matches('"').count().is_multiple_of(2)
    {
        return None;
    }
    // A straight quote that opens a quotation: after a space or bracket, before a non-space, and
    // the last one in the paragraph ("5'10\"" and "27\" monitor" follow a digit).
    let (i, _) = paragraph.char_indices().rfind(|(_, c)| *c == '"')?;
    let before = paragraph[..i].chars().next_back();
    let after = paragraph[i + 1..].chars().next();
    (before.is_none_or(|c| c.is_whitespace() || c == '(')
        && after.is_some_and(|c| !c.is_whitespace()))
    .then_some((from + i, '"'))
}
/// True when the sentence mark at `mark` sits inside a quotation that opened earlier in its
/// paragraph and was never closed ("“Where are you? she asked."): the outer sentence goes on.
pub(crate) fn inside_open_quote(text: &str, mark: usize) -> bool {
    let from = text[..mark].rfind('\n').map_or(0, |n| n + 1);
    let to = text[mark..].find('\n').map_or(text.len(), |n| mark + n);
    unmatched_open(text, from, to).is_some_and(|(at, _)| at < mark)
}
/// A quotation opened and never closed. A full quoted sentence after "said," closes at its end;
/// a short label ("Click “Export to download") closes before the word that resumes the sentence;
/// a quoted question or exclamation closes at its mark when the sentence goes on in lowercase.
fn open_quotes(req: &Request, edits: &mut Vec<Edit>) {
    static WORD: OnceLock<Regex> = OnceLock::new();
    let word_regex =
        WORD.get_or_init(|| Regex::new(r"[\p{L}\d][\p{L}\d'’-]*").expect("constant word"));
    let text = &req.text;
    let mut from = 0;
    for paragraph in text.split('\n') {
        let to = from + paragraph.len();
        let start = from;
        from = to + 1;
        let Some((open, quote)) = unmatched_open(text, start, to) else {
            continue;
        };
        let close_mark = if quote == '“' { "”" } else { "\"" };
        let inner_start = open + quote.len_utf8();
        let before: Vec<&str> = text[start..open]
            .split(|c: char| !c.is_alphanumeric() && c != '\'' && c != '’')
            .filter(|w| !w.is_empty())
            .collect();
        let speaker = before
            .last()
            .is_some_and(|w| SPEECH.contains(&w.to_lowercase().as_str()));
        let comma = text[start..open].trim_end().ends_with(',');
        let inner = &text[inner_start..to];
        if inner.trim().is_empty() || inner.contains(['“', '”']) {
            continue;
        }
        // Words of the quotation with their byte ranges.
        let words: Vec<(usize, usize)> = word_regex
            .find_iter(inner)
            .map(|m| (inner_start + m.start(), inner_start + m.end()))
            .collect();
        // A sentence mark inside the quotation followed by more of the paragraph.
        let mut mark_close: Option<(usize, bool)> = None;
        for (i, c) in inner.char_indices() {
            if !".!?".contains(c) {
                continue;
            }
            let at = inner_start + i;
            let rest = &text[at + 1..to];
            let next = rest.trim_start().chars().next();
            if rest.starts_with([' ', '\t']) && next.is_some_and(char::is_lowercase) && c != '.' {
                mark_close = Some((at + 1, true));
                break;
            }
            if rest.trim().is_empty()
                || next.is_some_and(char::is_uppercase) && rest.starts_with(' ')
            {
                mark_close = Some((at + 1, false));
                break;
            }
        }
        let label_close = if speaker && comma {
            None
        } else {
            words.iter().enumerate().skip(1).find_map(|(i, (a, b))| {
                let w = text[*a..*b].to_lowercase().replace('’', "'");
                (CLOSERS.contains(&w.as_str())
                    && mark_close.is_none_or(|(m, _)| *a < m)
                    && text[words[i - 1].1..*a].chars().all(|c| c == ' '))
                .then_some(words[i - 1].1)
            })
        };
        let (at, continues) = match (label_close, mark_close) {
            (Some(at), _) => (at, true),
            (None, Some(close)) => close,
            (None, None) => {
                let end = text[..to].trim_end().len();
                (end, false)
            }
        };
        // A label of several words with nothing to show where it ends.
        if !continues && !speaker && words.len() > 1 && text[at..to].trim().is_empty() {
            continue;
        }
        // "She asked “are you okay? and": a quoted question after a speech verb takes a comma
        // and a capital.
        let quoted_sentence = speaker && (comma || continues && label_close.is_none());
        if at <= inner_start {
            continue;
        }
        // "Her first word was “dog!": a mark that belongs to the whole sentence stays outside.
        let ending = &text[..at];
        let outside = !continues
            && ending.ends_with(['!', '?'])
            && !speaker
            && text[at..to].trim().is_empty()
            && words.len() <= 2;
        let at = if outside { at - 1 } else { at };
        put(
            req,
            edits,
            at,
            at,
            close_mark,
            "punctuation.open_quote",
            "Close the quotation.",
            0.88,
        );
        if quoted_sentence && !comma {
            let verb_end = start + text[start..open].trim_end().len();
            put(
                req,
                edits,
                verb_end,
                verb_end,
                ",",
                "punctuation.open_quote",
                "Put a comma before the quotation.",
                0.88,
            );
        }
        // A quoted sentence after "said," starts with a capital.
        if quoted_sentence {
            let first = text[inner_start..].chars().next().unwrap_or(' ');
            if first.is_lowercase() {
                put(
                    req,
                    edits,
                    inner_start,
                    inner_start + first.len_utf8(),
                    &first.to_uppercase().to_string(),
                    "punctuation.open_quote",
                    "A quoted sentence starts with a capital letter.",
                    0.88,
                );
            }
        }
    }
}

/// Determiners and possessives that put a compound right before its noun.
const DETERMINERS: [&str; 18] = [
    "a", "an", "the", "my", "our", "your", "his", "her", "their", "its", "this", "that", "these",
    "those", "some", "any", "every", "each",
];
const NUMBERS: [&str; 28] = [
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
    "twenty",
    "thirty",
    "forty",
    "fifty",
    "sixty",
    "seventy",
    "eighty",
    "ninety",
    "hundred",
];
const TENS: [&str; 8] = [
    "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety",
];
const UNITS: [&str; 23] = [
    "time",
    "second",
    "minute",
    "hour",
    "day",
    "night",
    "week",
    "month",
    "year",
    "mile",
    "kilometer",
    "meter",
    "metre",
    "foot",
    "inch",
    "page",
    "step",
    "person",
    "bedroom",
    "star",
    "point",
    "piece",
    "word",
];
/// Compounds that are hyphenated as modifiers before a noun ("a long-term plan") and open
/// elsewhere ("in the long term"). The flag marks those that also work as verbs or nouns on their
/// own ("follow up"), which need a determiner in front to be read as a modifier.
const COMPOUNDS: &[(&str, bool)] = &[
    ("long term", false),
    ("short term", false),
    ("full time", false),
    ("part time", false),
    ("last minute", false),
    ("real time", false),
    ("open source", false),
    ("third party", false),
    ("high quality", false),
    ("low cost", false),
    ("high level", false),
    ("low level", false),
    ("high end", false),
    ("first class", false),
    ("world class", false),
    ("long distance", false),
    ("high speed", false),
    ("up to date", false),
    ("out of date", false),
    ("state of the art", false),
    ("once in a lifetime", false),
    ("face to face", false),
    ("day to day", false),
    ("end to end", false),
    ("one on one", false),
    ("well thought out", false),
    ("so called", false),
    ("old fashioned", false),
    ("long lasting", false),
    ("large scale", false),
    ("small scale", false),
    ("full scale", false),
    ("top notch", false),
    ("step by step", false),
    ("user friendly", false),
    ("cutting edge", false),
    ("follow up", true),
    ("decision making", true),
    ("in person", true),
    ("on call", true),
    ("same day", true),
    ("next day", true),
    ("year end", true),
];
/// Words after a compound that show it is not modifying a noun.
const NOT_NOUNS: &[&str] = &[
    "of",
    "to",
    "in",
    "on",
    "at",
    "for",
    "with",
    "from",
    "by",
    "and",
    "or",
    "but",
    "is",
    "are",
    "was",
    "were",
    "be",
    "today",
    "tomorrow",
    "tonight",
    "yesterday",
    "later",
    "soon",
    "now",
    "here",
    "there",
    "again",
    "ago",
    "basis",
    "the",
    "a",
    "an",
    "it",
    "this",
    "that",
    "you",
    "me",
    "him",
    "them",
    "us",
    "if",
    "when",
    "as",
    "than",
    "so",
    "please",
    "too",
    "instead",
    "though",
];
fn noun_like(t: &Token<'_>) -> bool {
    t.is_word
        && !NOT_NOUNS.contains(&t.normalized.as_str())
        && (t.pos == "Noun"
            || t.pos == "Adjective"
            || spelling::flags(&t.normalized) & (2 | 8) != 0
                && t.pos != "Verb"
                && t.pos != "Adverb")
}
fn is_number(t: &Token<'_>) -> bool {
    NUMBERS.contains(&t.normalized.as_str()) || t.surface.chars().all(|c| c.is_ascii_digit())
}
fn spaced(text: &str, a: &Token<'_>, b: &Token<'_>) -> bool {
    a.end_byte < b.start_byte && text[a.end_byte..b.start_byte].chars().all(|c| c == ' ')
}
fn hyphens(req: &Request, tokens: &[Token<'_>], edits: &mut Vec<Edit>) {
    let text = &req.text;
    let join = |edits: &mut Vec<Edit>, a: &Token<'_>, b: &Token<'_>, id: &str, reason: &str| {
        put(req, edits, a.end_byte, b.start_byte, "-", id, reason, 0.9);
    };
    let compound_reason = "Hyphenate a compound that comes before the noun it describes.";
    for i in 0..tokens.len() {
        let t = &tokens[i];
        let next = tokens.get(i + 1);
        let after = tokens.get(i + 2);
        // "a 30 day trial", "My 5 year old", "a two hour drive".
        if is_number(t)
            && let Some(unit) = next.filter(|u| UNITS.contains(&u.normalized.as_str()))
            && spaced(text, t, unit)
            && let Some(w) = after
        {
            let one = ["one", "1"].contains(&t.normalized.as_str());
            let determined = i > 0 && DETERMINERS.contains(&tokens[i - 1].normalized.as_str());
            if w.normalized == "old" && spaced(text, unit, w) && (!one || determined) {
                join(
                    edits,
                    t,
                    unit,
                    "punctuation.compound_hyphen",
                    compound_reason,
                );
                join(
                    edits,
                    unit,
                    w,
                    "punctuation.compound_hyphen",
                    compound_reason,
                );
            } else if noun_like(w) && spaced(text, unit, w) && (!one || determined) {
                join(
                    edits,
                    t,
                    unit,
                    "punctuation.compound_hyphen",
                    compound_reason,
                );
            }
        }
        // "twenty one" is "twenty-one".
        if TENS.contains(&t.normalized.as_str())
            && let Some(n) = next.filter(|n| NUMBERS[..9].contains(&n.normalized.as_str()))
            && spaced(text, t, n)
            && !text[n.end_byte..].starts_with('-')
        {
            join(
                edits,
                t,
                n,
                "punctuation.number_hyphen",
                "Hyphenate a compound number from twenty-one to ninety-nine.",
            );
        }
        // "a well known author": well plus a participle before a noun.
        if t.normalized == "well"
            && i > 0
            && DETERMINERS.contains(&tokens[i - 1].normalized.as_str())
            && let Some(p) = next.filter(|p| {
                (morphology::verb(&p.normalized).is_some_and(|v| v.participle == p.normalized)
                    || p.normalized.ends_with("ed") && spelling::known(&p.normalized))
                    && p.normalized.len() > 3
            })
            && let Some(n) = after.filter(|n| noun_like(n))
            && spaced(text, t, p)
            && spaced(text, p, n)
        {
            join(edits, t, p, "punctuation.compound_hyphen", compound_reason);
        }
        // "a cloud based system": noun plus "based" before a noun.
        if t.normalized == "based"
            && i > 0
            && tokens[i - 1].is_word
            && spelling::flags(&tokens[i - 1].normalized) & 2 != 0
            && !crate::punctuation::finite(&tokens[i - 1])
            && next.is_some_and(noun_like)
            && spaced(text, &tokens[i - 1], t)
        {
            join(
                edits,
                &tokens[i - 1],
                t,
                "punctuation.compound_hyphen",
                compound_reason,
            );
        }
        // "my ex boyfriend".
        if t.normalized == "ex"
            && let Some(n) = next.filter(|n| {
                [
                    "boyfriend",
                    "girlfriend",
                    "husband",
                    "wife",
                    "partner",
                    "boss",
                    "colleague",
                    "coworker",
                    "employee",
                    "fiance",
                    "spouse",
                    "roommate",
                    "president",
                    "member",
                    "boyfriend's",
                    "girlfriend's",
                    "husband's",
                    "wife's",
                    "partner's",
                    "boss's",
                ]
                .contains(&n.normalized.as_str())
            })
            && spaced(text, t, n)
        {
            join(
                edits,
                t,
                n,
                "punctuation.compound_hyphen",
                "Hyphenate the prefix “ex-”.",
            );
        }
        for (compound, needs_determiner) in COMPOUNDS {
            let parts: Vec<&str> = compound.split(' ').collect();
            let end = i + parts.len();
            if end >= tokens.len()
                || !parts
                    .iter()
                    .enumerate()
                    .all(|(k, p)| tokens[i + k].normalized == *p)
                || !(i..end - 1).all(|k| spaced(text, &tokens[k], &tokens[k + 1]))
                || !noun_like(&tokens[end])
                || !spaced(text, &tokens[end - 1], &tokens[end])
            {
                continue;
            }
            let determined = i > 0 && DETERMINERS.contains(&tokens[i - 1].normalized.as_str());
            if *needs_determiner && !determined {
                continue;
            }
            // "state of the art": the noun after it must not be the end of a longer phrase.
            for k in i..end - 1 {
                join(
                    edits,
                    &tokens[k],
                    &tokens[k + 1],
                    "punctuation.compound_hyphen",
                    compound_reason,
                );
            }
        }
    }
    hyphens_to_remove(req, tokens, edits);
}
/// Adverbs ending in -ly that are adjectives or nouns themselves, so a hyphen after them may be
/// right ("an elderly-looking man", "family-owned").
const LY_ADJECTIVES: &[&str] = &[
    "elderly",
    "deadly",
    "likely",
    "unlikely",
    "lonely",
    "lively",
    "lowly",
    "homely",
    "kindly",
    "curly",
    "surly",
    "burly",
    "early",
    "only",
    "ugly",
    "holy",
    "jolly",
    "smelly",
    "friendly",
    "costly",
    "daily",
    "ghostly",
    "bodily",
    "earthly",
    "leisurely",
    "orderly",
    "manly",
    "motherly",
    "fatherly",
    "brotherly",
    "sisterly",
    "scholarly",
    "cowardly",
    "heavenly",
    "worldly",
    "sickly",
    "stately",
    "saintly",
    "silly",
    "chilly",
    "hilly",
    "family",
    "weekly",
    "monthly",
    "yearly",
    "hourly",
    "nightly",
    "quarterly",
    "lovely",
    "timely",
    "goodly",
    "beastly",
    "oily",
    "wily",
];
const PHRASAL: [&str; 20] = [
    "check", "log", "set", "work", "catch", "sign", "back", "follow", "pick", "drop", "warm",
    "clean", "shut", "start", "kick", "wrap", "cool", "break", "show", "print",
];
const PARTICLES: [&str; 7] = ["in", "up", "out", "off", "on", "down", "back"];
/// Words after which a phrasal verb is a verb ("to log in", "please set up", "let's catch up").
const VERB_SLOT: [&str; 22] = [
    "to", "can", "could", "will", "would", "should", "must", "might", "may", "please", "let's",
    "lets", "you", "we", "i", "they", "don't", "didn't", "can't", "won't", "i'll", "we'll",
];
fn hyphens_to_remove(req: &Request, tokens: &[Token<'_>], edits: &mut Vec<Edit>) {
    static LY: OnceLock<Regex> = OnceLock::new();
    static AGED: OnceLock<Regex> = OnceLock::new();
    let text = &req.text;
    // "highly-efficient": no hyphen after an -ly adverb.
    for cap in LY
        .get_or_init(|| {
            Regex::new(r"\b(?P<adverb>\p{Ll}{3,}ly)(?P<hyphen>-)\p{Ll}{2,}\b").expect("ly")
        })
        .captures_iter(text)
    {
        let adverb = &cap["adverb"];
        let stem = adverb.strip_suffix("ly").unwrap_or(adverb);
        let candidates = [
            stem.to_string(),
            stem.strip_suffix('i')
                .map(|s| format!("{s}y"))
                .unwrap_or_default(),
            format!("{stem}le"),
            stem.strip_suffix("al")
                .map(|s| format!("{s}al"))
                .unwrap_or_default(),
            format!("{stem}l"),
        ];
        if LY_ADJECTIVES.contains(&adverb)
            || !candidates
                .iter()
                .any(|c| !c.is_empty() && spelling::flags(c) & 8 != 0)
        {
            continue;
        }
        let hyphen = cap.name("hyphen").expect("hyphen");
        put(
            req,
            edits,
            hyphen.start(),
            hyphen.end(),
            " ",
            "punctuation.ly_hyphen",
            "An adverb ending in -ly needs no hyphen.",
            0.9,
        );
    }
    // "ten years-old": the open form after a plural.
    for cap in AGED
        .get_or_init(|| {
            Regex::new(r"\b(?:years|months|weeks|days)(?P<hyphen>-)old\b").expect("aged")
        })
        .captures_iter(text)
    {
        let hyphen = cap.name("hyphen").expect("hyphen");
        if text[..hyphen.start()]
            .trim_end_matches(char::is_alphabetic)
            .ends_with('-')
        {
            continue;
        }
        put(
            req,
            edits,
            hyphen.start(),
            hyphen.end(),
            " ",
            "punctuation.compound_hyphen",
            "After the noun, “years old” is written open.",
            0.9,
        );
    }
    // "Please log-in", "to set-up": the verb is two words; the hyphenated form is the noun.
    for i in 1..tokens.len().saturating_sub(2) {
        let (verb, hyphen, particle) = (&tokens[i], &tokens[i + 1], &tokens[i + 2]);
        if hyphen.surface == "-"
            && verb.end_byte == hyphen.start_byte
            && hyphen.end_byte == particle.start_byte
            && PHRASAL.contains(&verb.normalized.as_str())
            && PARTICLES.contains(&particle.normalized.as_str())
            && VERB_SLOT.contains(&tokens[i - 1].normalized.as_str())
        {
            put(
                req,
                edits,
                hyphen.start_byte,
                hyphen.end_byte,
                " ",
                "punctuation.phrasal_verb_hyphen",
                "As a verb, this is two words without a hyphen.",
                0.9,
            );
        }
    }
}

/// Nouns for people (and pets) whose plural is easily typed for the possessive ("my sisters
/// wedding").
const PEOPLE: &[&str] = &[
    "sister",
    "brother",
    "friend",
    "mom",
    "dad",
    "mum",
    "mother",
    "father",
    "grandma",
    "grandpa",
    "grandmother",
    "grandfather",
    "aunt",
    "uncle",
    "cousin",
    "wife",
    "husband",
    "son",
    "daughter",
    "boss",
    "manager",
    "neighbor",
    "neighbour",
    "teacher",
    "colleague",
    "boyfriend",
    "girlfriend",
    "partner",
    "roommate",
    "client",
    "dog",
    "cat",
    "ceo",
    "kid",
    "baby",
    "niece",
    "nephew",
    "parent",
    "grandparent",
    "coworker",
];
/// Words typed without the apostrophe of their possessive.
const POSSESSIVE_WORDS: [(&str, &str); 13] = [
    ("everyones", "everyone's"),
    ("everybodys", "everybody's"),
    ("nobodys", "nobody's"),
    ("somebodys", "somebody's"),
    ("someones", "someone's"),
    ("anyones", "anyone's"),
    ("anybodys", "anybody's"),
    ("childrens", "children's"),
    ("womens", "women's"),
    ("peoples", "people's"),
    ("your's", "yours"),
    ("their's", "theirs"),
    ("our's", "ours"),
];
const TIME_UNITS: [&str; 7] = ["day", "week", "month", "year", "hour", "night", "minute"];
const QUANTIFIERS: [&str; 30] = [
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "twelve",
    "twenty",
    "many",
    "few",
    "several",
    "more",
    "all",
    "some",
    "both",
    "these",
    "those",
    "multiple",
    "various",
    "numerous",
    "fewer",
    "most",
    "other",
    "different",
    "hundreds",
    "thousands",
    "lots",
];
fn apostrophes(req: &Request, tokens: &[Token<'_>], edits: &mut Vec<Edit>) {
    let text = &req.text;
    for (i, t) in tokens.iter().enumerate() {
        if !t.is_word {
            continue;
        }
        let next = tokens.get(i + 1);
        let prev = i.checked_sub(1).map(|p| &tokens[p]);
        if let Some((_, fixed)) = POSSESSIVE_WORDS
            .iter()
            .find(|(w, _)| *w == t.normalized && (*w != "peoples" || next.is_some_and(noun_like)))
        {
            let apostrophe = if t.surface.contains('’') {
                "’"
            } else {
                "'"
            };
            let fixed = crate::match_case(&fixed.replace('\'', apostrophe), t.surface);
            put(
                req,
                edits,
                t.start_byte,
                t.end_byte,
                &fixed,
                "punctuation.apostrophe",
                "Use the apostrophe of the possessive here.",
                0.92,
            );
            continue;
        }
        let possessive = t.normalized.ends_with("'s") && t.normalized.len() > 3;
        let base = t.normalized.trim_end_matches("'s");
        let acronym = t
            .surface
            .strip_suffix("'s")
            .or_else(|| t.surface.strip_suffix("’s"))
            .is_some_and(|s| s.chars().count() >= 2 && s.chars().all(|c| c.is_ascii_uppercase()));
        if possessive && t.normalized.matches('\'').count() == 1 {
            let apostrophe = t.start_byte + t.surface.rfind(['\'', '’']).unwrap_or(0);
            let width = t.surface[apostrophe - t.start_byte..]
                .chars()
                .next()
                .map_or(1, char::len_utf8);
            let noun = acronym
                || spelling::flags(base) & 2 != 0
                    && !crate::punctuation::finite(t)
                    && ![
                        "it",
                        "that",
                        "there",
                        "here",
                        "what",
                        "who",
                        "he",
                        "she",
                        "let",
                        "everyone",
                        "everybody",
                        "nobody",
                        "someone",
                        "somebody",
                        "anyone",
                        "anybody",
                        "everything",
                        "nothing",
                        "something",
                        "anything",
                        "where",
                        "how",
                        "when",
                        "why",
                        "this",
                        "one",
                    ]
                    .contains(&base);
            // "The dog's are barking": a plural verb after it makes it a plural.
            let plural_verb = next.is_some_and(|n| {
                [
                    "are", "were", "have", "aren't", "weren't", "haven't", "don't", "do",
                ]
                .contains(&n.normalized.as_str())
            });
            // "two PR's", "so many photo's", "All employee's must".
            let counted = prev.is_some_and(|p| {
                QUANTIFIERS.contains(&p.normalized.as_str())
                    || p.surface.chars().all(|c| c.is_ascii_digit()) && p.surface != "1"
            });
            if noun && (plural_verb || counted) {
                let possessive_next = next.is_some_and(|n| {
                    n.is_word
                        && spelling::flags(&n.normalized) & 2 != 0
                        && spelling::flags(&n.normalized) & (4 | 8) == 0
                        && !NOT_NOUNS.contains(&n.normalized.as_str())
                        && n.pos != "Verb"
                        && n.pos != "Adverb"
                });
                let unit_possessive = TIME_UNITS.contains(&base)
                    && next.is_some_and(|n| {
                        spelling::flags(&n.normalized) & 2 != 0
                            && !NOT_NOUNS.contains(&n.normalized.as_str())
                            && !["back", "last", "next", "ago", "later", "early", "late"]
                                .contains(&n.normalized.as_str())
                            && n.pos != "Verb"
                            && n.pos != "Adverb"
                            && n.pos != "Preposition"
                    });
                if counted && (possessive_next || unit_possessive) {
                    // "two week's vacation" is "two weeks' vacation".
                    if TIME_UNITS.contains(&base) {
                        let mark = &text[apostrophe..apostrophe + width];
                        put(
                            req,
                            edits,
                            apostrophe,
                            t.end_byte,
                            &format!("s{mark}"),
                            "punctuation.apostrophe",
                            "A plural possessive takes the apostrophe after the s.",
                            0.9,
                        );
                    }
                    continue;
                }
                put(
                    req,
                    edits,
                    apostrophe,
                    apostrophe + width,
                    "",
                    "punctuation.apostrophe",
                    "A plural takes no apostrophe.",
                    0.9,
                );
                continue;
            }
        }
        // "my sisters wedding", "My parents house", "The CEOs letter".
        if let Some(p) = prev
            && ["my", "your", "his", "her", "our", "their", "the"].contains(&p.normalized.as_str())
            && let Some(n) = next.filter(|n| {
                n.is_word
                    && n.surface.starts_with(char::is_lowercase)
                    && spelling::flags(&n.normalized) & 2 != 0
                    && !NOT_NOUNS.contains(&n.normalized.as_str())
                    && n.pos != "Verb"
                    && n.pos != "Adverb"
                    && n.pos != "Preposition"
            })
            && spaced(text, t, n)
            && tokens.get(i + 2).is_some_and(|v| {
                crate::clauses::finite_at(tokens, i + 2)
                    && (v.pos == "Verb"
                        || !crate::clauses::noun_or_verb(v)
                        || tokens.get(i + 3).is_none_or(|x| {
                            !x.is_word || !crate::clauses::finite_at(tokens, i + 3)
                        }))
            })
        {
            let stem = t.normalized.strip_suffix('s').unwrap_or("");
            let person = PEOPLE.contains(&stem)
                || t.surface.ends_with('s')
                    && t.surface.len() > 2
                    && t.surface[..t.surface.len() - 1]
                        .chars()
                        .all(|c| c.is_ascii_uppercase())
                    && p.normalized == "the";
            if person && !t.normalized.contains('\'') {
                let plural_only = ["parent", "grandparent", "kid"].contains(&stem);
                let replacement = if plural_only {
                    format!("{}'", t.surface)
                } else {
                    format!("{}'s", &t.surface[..t.surface.len() - 1])
                };
                put(
                    req,
                    edits,
                    t.start_byte,
                    t.end_byte,
                    &replacement,
                    "punctuation.apostrophe",
                    "Add the apostrophe of the possessive.",
                    0.88,
                );
                continue;
            }
        }
        // "a days rest" is "a day's rest".
        if prev.is_some_and(|p| ["a", "an"].contains(&p.normalized.as_str()))
            && let Some(stem) = t.normalized.strip_suffix('s')
            && TIME_UNITS.contains(&stem)
            && next.is_some_and(|n| noun_like(n) && spaced(text, t, n))
        {
            put(
                req,
                edits,
                t.end_byte - 1,
                t.end_byte - 1,
                "'",
                "punctuation.apostrophe",
                "Add the apostrophe of the possessive.",
                0.88,
            );
            continue;
        }
        // "Sarahs laptop", "Mikes place": a known first name plus s, before a noun.
        if t.surface.starts_with(char::is_uppercase)
            && t.surface.ends_with('s')
            && !t.normalized.contains('\'')
            && prev.is_none_or(|p| {
                p.is_word
                    && p.normalized != "the"
                    && (p.surface.starts_with(char::is_lowercase)
                        || crate::starts_sentence(text, p.start_byte, req) && !p.proper_name)
                    || p.paragraph != t.paragraph
                    || ".!?".contains(p.surface)
            })
            && let Some(stem) = t.normalized.strip_suffix('s')
            && stem.len() >= 3
            && (crate::names::is_bundled_name(stem) || spelling::name_only(stem))
            && !crate::names::is_bundled_name(&t.normalized)
            && !spelling::name_only(&t.normalized)
            && next.is_some_and(|n| {
                n.surface.starts_with(char::is_lowercase)
                    && spelling::flags(&n.normalized) & 2 != 0
                    && !NOT_NOUNS.contains(&n.normalized.as_str())
                    && n.pos != "Verb"
                    && spaced(text, t, n)
            })
        {
            put(
                req,
                edits,
                t.end_byte - 1,
                t.end_byte - 1,
                "'",
                "punctuation.apostrophe",
                "Add the apostrophe of the possessive.",
                0.86,
            );
        }
    }
    // "the 1990's", "the 90's": decades take no apostrophe.
    static DECADE: OnceLock<Regex> = OnceLock::new();
    for cap in DECADE
        .get_or_init(|| Regex::new(r"\b(?:1\d|20)?\d0(?P<mark>['’])s\b").expect("decade"))
        .captures_iter(text)
    {
        let mark = cap.name("mark").expect("mark");
        put(
            req,
            edits,
            mark.start(),
            mark.end(),
            "",
            "punctuation.apostrophe",
            "A decade takes no apostrophe before the s.",
            0.9,
        );
    }
}

/// Verbs and prepositions that run straight into their object, so a colon after them splits a
/// sentence in the middle ("The reasons are: budget", "calls for: flour").
const NO_COLON_AFTER: [&str; 24] = [
    "is",
    "are",
    "was",
    "were",
    "include",
    "includes",
    "included",
    "including",
    "need",
    "needs",
    "bring",
    "brings",
    "contain",
    "contains",
    "require",
    "requires",
    "for",
    "of",
    "to",
    "with",
    "want",
    "wants",
    "from",
    "as",
];
/// Words that open a clause after a colon ("The question is: who pays?"), which may stay.
const CLAUSE_OPENERS: [&str; 18] = [
    "who", "what", "when", "where", "why", "how", "whether", "if", "we", "i", "you", "they", "he",
    "she", "it", "there", "this", "that",
];
const CONJUNCTIONS: [&str; 5] = ["and", "but", "so", "or", "yet"];
fn colons(req: &Request, tokens: &[Token<'_>], edits: &mut Vec<Edit>) {
    let text = &req.text;
    for (i, t) in tokens.iter().enumerate() {
        if t.surface != ":" && t.surface != ";" {
            continue;
        }
        let Some(prev) = i.checked_sub(1).map(|p| &tokens[p]) else {
            continue;
        };
        let next = tokens.get(i + 1);
        let same_line = next
            .is_some_and(|n| n.paragraph == t.paragraph && text[t.end_byte..n.start_byte] == *" ");
        let sentence_start = tokens[..i]
            .iter()
            .rposition(|x| x.sentence != t.sentence || x.paragraph != t.paragraph)
            .map_or(0, |n| n + 1);
        let sentence_end = (i..tokens.len())
            .find(|&n| tokens[n].sentence != t.sentence || tokens[n].paragraph != t.paragraph)
            .unwrap_or(tokens.len());
        let glued = prev.end_byte == t.start_byte;
        if !glued {
            continue;
        }
        if t.surface == ":" {
            // "The reasons are: budget, timing" — a colon needs a complete clause before it.
            if same_line
                && NO_COLON_AFTER.contains(&prev.normalized.as_str())
                && next.is_some_and(|n| {
                    n.surface
                        .starts_with(|c: char| c.is_lowercase() || c.is_ascii_digit())
                        && !CLAUSE_OPENERS.contains(&n.normalized.as_str())
                })
                && i >= 2
                && !prev.surface.starts_with(char::is_uppercase)
            {
                put(
                    req,
                    edits,
                    t.start_byte,
                    t.end_byte,
                    "",
                    "punctuation.colon_after_verb",
                    "No colon between a verb or preposition and what follows it.",
                    0.88,
                );
            }
            continue;
        }
        // Semicolons.
        let Some(n) = next.filter(|_| same_line) else {
            // "Dear Mr. Patel;" ends a salutation.
            if tokens[sentence_start..i]
                .first()
                .is_some_and(|f| ["dear", "hi", "hello", "hey"].contains(&f.normalized.as_str()))
                && next.is_none_or(|n| n.paragraph != t.paragraph)
            {
                put(
                    req,
                    edits,
                    t.start_byte,
                    t.end_byte,
                    ",",
                    "punctuation.semicolon",
                    "A salutation ends with a comma.",
                    0.9,
                );
            }
            continue;
        };
        let first = tokens[sentence_start..i]
            .iter()
            .find(|x| x.is_word)
            .map_or("", |x| x.normalized.as_str());
        let left = &tokens[sentence_start..i];
        let left_words = left.iter().filter(|x| x.is_word).count();
        let finite_left = (sentence_start..i)
            .filter(|&k| {
                crate::clauses::finite_at(tokens, k) && !crate::clauses::noun_or_verb(&tokens[k])
            })
            .count();
        let right_clause = crate::clauses::clause_at(tokens, i + 1, sentence_end).is_some();
        let (replacement, reason) =
            if ["because", "since", "although", "though"].contains(&n.normalized.as_str()) {
                (
                    "",
                    "A subordinate clause joins its sentence without a semicolon.",
                )
            } else if CONJUNCTIONS.contains(&n.normalized.as_str()) {
                // "Paris, France; Berlin, Germany; and Madrid": semicolons between list items.
                if tokens[sentence_start..sentence_end]
                    .iter()
                    .filter(|x| [";", ","].contains(&x.surface))
                    .count()
                    > 1
                {
                    continue;
                }
                if crate::clauses::clause_at(tokens, i + 2, sentence_end).is_some()
                    || n.normalized == "so"
                {
                    (
                        ",",
                        "Use a comma before a conjunction that joins two clauses.",
                    )
                } else {
                    (
                        "",
                        "A conjunction that shares the subject needs no semicolon.",
                    )
                }
            } else if crate::clauses::SUBORDINATORS.contains(&first)
                && finite_left <= 1
                && (right_clause || crate::clauses::inverted_question(tokens, i + 1, sentence_end))
                || crate::clauses::PREPOSITIONS.contains(&first) && finite_left == 0 && right_clause
            {
                (",", "Use a comma after an introductory clause or phrase.")
            } else if left_words <= 2
                && finite_left == 0
                && sentence_start + left_words == i
                && left
                    .iter()
                    .all(|x| spelling::flags(&x.normalized) & 2 != 0 && x.pos != "Interjection")
            {
                (":", "Use a colon after a label.")
            } else if left_words >= 3
                && i >= 2
                && spelling::flags(&prev.normalized) & 16 != 0
                && (is_number(&tokens[i - 2])
                    || ["several", "few", "following"].contains(&tokens[i - 2].normalized.as_str()))
                && (tokens[i + 1..sentence_end]
                    .iter()
                    .filter(|x| x.surface == ",")
                    .count()
                    >= 1
                    || text[..tokens[sentence_end - 1].end_byte].ends_with('?'))
            {
                (":", "Use a colon to introduce a list.")
            } else {
                continue;
            };
        put(
            req,
            edits,
            t.start_byte,
            t.end_byte,
            replacement,
            "punctuation.semicolon",
            reason,
            0.88,
        );
    }
    // "as follows" at the end of a line introduces what comes next.
    static FOLLOWS: OnceLock<Regex> = OnceLock::new();
    for m in FOLLOWS
        .get_or_init(|| Regex::new(r"(?m)\b(?:as follows|the following)[ \t]*$").expect("follows"))
        .find_iter(text)
    {
        let end = m.start() + m.as_str().trim_end().len();
        put(
            req,
            edits,
            end,
            end,
            ":",
            "punctuation.colon_before_list",
            "Use a colon to introduce what follows.",
            0.9,
        );
    }
}

#[cfg(test)]
mod tests {
    use crate::Request;
    fn fix(text: &str) -> String {
        crate::pipeline::rewrite(&Request {
            text: text.into(),
            ..Request::default()
        })
        .unwrap()
        .text
    }
    #[test]
    fn doubled_marks_and_spacing() {
        for (input, expected) in [
            ("See you tomorrow..", "See you tomorrow."),
            ("Are you coming?.", "Are you coming?"),
            (
                "Dear Maria,, thank you for the note.",
                "Dear Maria, thank you for the note.",
            ),
            ("Sincerely.,", "Sincerely,"),
            (
                "The meeting ended early.We went home.",
                "The meeting ended early. We went home.",
            ),
            ("Is it ready?Let me know.", "Is it ready? Let me know."),
            (
                "Please call me ( after 5pm).",
                "Please call me (after 5pm).",
            ),
            ("That's all for today .", "That's all for today."),
        ] {
            assert_eq!(fix(input), expected, "{input}");
        }
        for text in [
            "Hmm... let me think.",
            "Wait... what?",
            "Wow!!",
            "What?!",
            "I'll bring snacks, drinks, etc., to the party.",
            "Use the default, i.e., the first option.",
            "Use os.path.join to build paths.",
            "Set user.Name to the new value.",
            "The range is 1..10 in Rust.",
            "print(hello world)",
        ] {
            assert_eq!(fix(text), text);
        }
    }
    #[test]
    fn hyphens_in_compound_modifiers() {
        for (input, expected) in [
            (
                "We hired a full time accountant.",
                "We hired a full-time accountant.",
            ),
            (
                "He has a 3 year old daughter.",
                "He has a 3-year-old daughter.",
            ),
            (
                "They signed a two year lease.",
                "They signed a two-year lease.",
            ),
            ("We need an up to date map.", "We need an up-to-date map."),
            ("It was a really-fun trip.", "It was a really fun trip."),
            (
                "Please sign-up before Friday.",
                "Please sign up before Friday.",
            ),
            (
                "My daughter is six years-old.",
                "My daughter is six years old.",
            ),
        ] {
            assert_eq!(fix(input), expected, "{input}");
        }
        for text in [
            "She is well known for her work.",
            "He works full time.",
            "In the long term, this pays off.",
            "The drive takes two hours.",
            "One time I saw a bear.",
            "The family-owned shop closed.",
            "Our login page is down.",
        ] {
            assert_eq!(fix(text), text);
        }
    }
    #[test]
    fn apostrophes_in_plurals_and_possessives() {
        for (input, expected) in [
            (
                "The cat's are fighting again.",
                "The cats are fighting again.",
            ),
            (
                "There were two typo's in the email.",
                "There were two typos in the email.",
            ),
            (
                "That was everybodys favorite part.",
                "That was everybody's favorite part.",
            ),
            (
                "I need a weeks rest after this.",
                "I need a week's rest after this.",
            ),
            ("The 1980's had great music.", "The 1980s had great music."),
            ("Is this book your's?", "Is this book yours?"),
        ] {
            assert_eq!(fix(input), expected, "{input}");
        }
        for text in [
            "The dog's barking again.",
            "Mind your p's and q's.",
            "She got straight A's.",
            "My parents' house is huge.",
            "I loved the '80s.",
        ] {
            assert_eq!(fix(text), text);
        }
    }
    #[test]
    fn colons_semicolons_and_quotes() {
        for (input, expected) in [
            (
                "We need three things; milk, eggs, and bread.",
                "We need three things: milk, eggs, and bread.",
            ),
            (
                "Because the train was late; I missed the meeting.",
                "Because the train was late, I missed the meeting.",
            ),
            (
                "I left early; because I felt sick.",
                "I left early because I felt sick.",
            ),
            (
                "The ingredients are: flour, butter, and sugar.",
                "The ingredients are flour, butter, and sugar.",
            ),
            ("Dear Professor Lee;", "Dear Professor Lee,"),
            (
                "Press “Start to begin the test.",
                "Press “Start” to begin the test.",
            ),
            (
                "She said, “I'll be there soon.",
                "She said, “I'll be there soon.”",
            ),
            (
                "“Is anyone home? she called.",
                "“Is anyone home?” she called.",
            ),
        ] {
            assert_eq!(fix(input), expected, "{input}");
        }
        for text in [
            "Note: the office is closed.",
            "The question is: who pays?",
            "The results were clear; the new design performed better.",
            "We have offices in Paris, France; Berlin, Germany; and Madrid, Spain.",
            "She called it “the big one.”",
            "I'm 5'10\" tall and have a 27\" monitor.",
        ] {
            assert_eq!(fix(text), text);
        }
    }
}
