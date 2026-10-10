//! Name knowledge. A token that is a name candidate may only receive case changes, so every
//! respelling, word split and grammar edit is dropped when it touches one.
//!
//! Evidence, strongest first:
//! * STRONG: the request's `names` or `dictionary` (including each part of a multi-word or
//!   hyphenated name), the same word capitalized elsewhere in the text, an email local part, or a
//!   capitalized bundled name in mid-sentence ("Hey Hope!").
//! * MEDIUM: the bundled list (`rules/names.txt`) when the word is not also an ordinary lowercase
//!   word and not a known misspelling (`rules/name-typos.txt`).
//! * WEAK: written like a name in context (greeting, sign-off, title, list...); see
//!   `spelling::lowercase_name`. Weak candidates are only shielded from respelling.
use crate::{
    Request, spelling,
    tokenizer::{self, Token},
};
use regex::Regex;
use std::{
    collections::{HashMap, HashSet},
    sync::OnceLock,
};

pub const WEAK: u8 = 1;
pub const MEDIUM: u8 = 2;
pub const STRONG: u8 = 3;
/// Names per request; entries beyond this are rejected, like the dictionary limit.
pub const MAX_NAMES: usize = 2000;
pub const MAX_NAME_BYTES: usize = 128;

/// Sorted, de-duplicated lowercase lines. Lines already sorted and lowercase borrow the embedded
/// text (no copy); anything else (comments, capitals) is normalized once.
fn load(text: &'static str) -> Vec<&'static str> {
    let mut lines: Vec<&'static str> = text
        .lines()
        .map(str::trim)
        .filter(|l| !l.is_empty() && !l.starts_with('#'))
        .map(|l| {
            if l.chars().any(char::is_uppercase) {
                &*Box::leak(fold(l).into_boxed_str())
            } else {
                l
            }
        })
        .collect();
    if !lines.is_sorted() {
        lines.sort_unstable();
    }
    lines.dedup();
    lines
}
fn bundled() -> &'static [&'static str] {
    static NAMES: OnceLock<Vec<&'static str>> = OnceLock::new();
    NAMES.get_or_init(|| load(include_str!("../rules/names.txt")))
}
fn typos() -> &'static [&'static str] {
    static TYPOS: OnceLock<Vec<&'static str>> = OnceLock::new();
    TYPOS.get_or_init(|| load(include_str!("../rules/name-typos.txt")))
}
/// Lowercase token in the bundled names list.
pub fn is_bundled_name(lower: &str) -> bool {
    bundled().binary_search(&lower).is_ok()
}
/// A misspelling that must still be corrected even when it looks like a name.
pub fn is_name_typo(lower: &str) -> bool {
    typos().binary_search(&lower).is_ok()
}
/// A reviewed misspelling: a listed typo or the source of a one-word phrase rule (teh, recieved,
/// alot). Never taken as a name; the user's `dictionary` keeps one on purpose. Lexicon
/// suggestions are not used: they also fire on real names (greta, great).
pub fn is_known_misspelling(word: &str) -> bool {
    static SOURCES: OnceLock<HashSet<&'static str>> = OnceLock::new();
    let lower = fold(word);
    let lower = base(&lower);
    let sources = SOURCES.get_or_init(|| {
        crate::rules::phrases()
            .rules
            .iter()
            .map(|r| r.source.as_str())
            .filter(|s| !s.contains(' '))
            .collect()
    });
    is_name_typo(lower) || sources.contains(lower)
}
/// Unicode case folding used for every name comparison (matches `Token::normalized`).
pub fn fold(s: &str) -> String {
    s.to_lowercase().replace('’', "'")
}
/// "aman's" and "aman’s" are the name "aman".
pub fn base(normalized: &str) -> &str {
    normalized.strip_suffix("'s").unwrap_or(normalized)
}
const SHORTHAND: [&str; 24] = [
    "u", "ur", "r", "k", "pls", "plz", "thx", "ty", "btw", "lol", "omg", "idk", "ok", "okk", "ya",
    "yep", "nope", "tbh", "imo", "fyi", "asap", "np", "yw", "brb",
];
const CALENDAR: [&str; 19] = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
];
/// Chat shorthand ("pls", "thx") is a word of its own: never a name, never respelled.
pub fn is_shorthand(lower: &str) -> bool {
    SHORTHAND.contains(&lower)
}
/// Days, months, chat shorthand and one or two lowercase letters are never name guesses, whatever
/// a language tagger or a list says; only the user's own names and dictionary can claim them.
pub fn never_a_name(token: &str) -> bool {
    let lower = fold(token);
    let lower = base(&lower);
    let short = lower.chars().count() <= 2 && token.chars().next().is_some_and(char::is_lowercase);
    // A known misspelling stays correctable in any case: the system lexicon may accept its
    // capitalized form (aquire/Aquire) and the tagger may call a capitalized typo a person ("for
    // Teh meeting"). Names the user taught Parzr are matched separately and still win.
    let typo = is_name_typo(lower) || is_known_misspelling(lower);
    short || typo || SHORTHAND.contains(&lower) || CALENDAR.contains(&lower)
}
/// MEDIUM predicate: a bundled name that is not an ordinary word and not a known typo.
pub fn name_word(lower: &str) -> bool {
    let lower = base(lower);
    is_bundled_name(lower)
        && !spelling::ordinary(lower)
        && !is_name_typo(lower)
        && !never_a_name(lower)
}

/// Single tokens plus token sequences ("jean - luc", "new york") keyed by their first token.
#[derive(Debug, Default)]
struct Entries {
    words: HashSet<String>,
    phrases: HashMap<String, Vec<Vec<String>>>,
}
impl Entries {
    fn add(&mut self, entry: &str, parts: bool) {
        let tokens = tokenizer::tokenize(entry, &[]);
        let sequence: Vec<String> = tokens.iter().map(|t| t.normalized.clone()).collect();
        if !tokens.iter().any(|t| t.is_word) {
            // Digits or symbols alone ("42", "C++") still match as a single exact token.
            if let [only] = &sequence[..] {
                self.words.insert(only.clone());
            }
            return;
        }
        if let [only] = &sequence[..] {
            self.words.insert(only.clone());
            return;
        }
        if parts {
            // "Aman Jain" and "Jean-Luc": each part is also the name, unless it is an ordinary word.
            for t in tokens.iter().filter(|t| t.is_word) {
                if !spelling::ordinary(&t.normalized) {
                    self.words.insert(t.normalized.clone());
                }
            }
        }
        self.phrases
            .entry(sequence[0].clone())
            .or_default()
            .push(sequence);
    }
    fn word(&self, normalized: &str) -> bool {
        self.words.contains(normalized) || self.words.contains(base(normalized))
    }
    /// Token count of the longest phrase starting at `i` (0 when none).
    fn phrase(&self, tokens: &[Token<'_>], i: usize) -> usize {
        self.phrases
            .get(&tokens[i].normalized)
            .into_iter()
            .flatten()
            .filter(|seq| {
                i + seq.len() <= tokens.len()
                    && seq.iter().enumerate().all(|(k, s)| {
                        let t = &tokens[i + k].normalized;
                        t == s || k + 1 == seq.len() && base(t) == s
                    })
            })
            .map(Vec::len)
            .max()
            .unwrap_or(0)
    }
    fn is_empty(&self) -> bool {
        self.words.is_empty() && self.phrases.is_empty()
    }
}

/// Request names and dictionary, folded once per request and shared by every pass.
#[derive(Debug, Default)]
pub struct NameIndex {
    dictionary: Entries,
    names: Entries,
}
impl NameIndex {
    pub fn new(req: &Request) -> Self {
        let mut index = Self::default();
        for word in &req.dictionary {
            index.dictionary.add(word, false);
        }
        for name in req.names.iter().filter(|n| !is_known_misspelling(n)) {
            index.names.add(name, true);
        }
        index
    }
    /// Tokens covered by a dictionary entry: protected verbatim, never respelled or recased.
    pub fn dictionary_hits(&self, tokens: &[Token<'_>]) -> Vec<bool> {
        let mut hit = vec![false; tokens.len()];
        if self.dictionary.is_empty() {
            return hit;
        }
        for i in 0..tokens.len() {
            if self.dictionary.word(&tokens[i].normalized) {
                hit[i] = true;
            }
            for flag in &mut hit[i..i + self.dictionary.phrase(tokens, i)] {
                *flag = true;
            }
        }
        hit
    }
    /// Tokens inside a multi-word request name ("jean - luc"): all of its parts are the name.
    pub fn phrase_cover(&self, tokens: &[Token<'_>]) -> Vec<bool> {
        let mut cover = vec![false; tokens.len()];
        if !self.names.phrases.is_empty() {
            for i in 0..tokens.len() {
                for c in &mut cover[i..i + self.names.phrase(tokens, i)] {
                    *c = true;
                }
            }
        }
        cover
    }
    /// Name level of every token (0 = not a name candidate).
    pub fn mark(&self, text: &str, tokens: &[Token<'_>]) -> Vec<u8> {
        let n = tokens.len();
        let mut level = vec![0u8; n];
        let hits = self.dictionary_hits(tokens);
        let sentence_start = |i: usize| {
            i == 0
                || tokens[i - 1].paragraph != tokens[i].paragraph
                || [".", "!", "?"].contains(&tokens[i - 1].surface)
        };
        // Capitalized or mixed, not SHOUTED ("NEH" is no evidence).
        let capitalized = |t: &Token<'_>| {
            let letters: Vec<char> = t.surface.chars().filter(|c| c.is_alphabetic()).collect();
            letters.first().is_some_and(|c| c.is_uppercase())
                && !(letters.len() > 1 && letters.iter().all(|c| c.is_uppercase()))
        };
        // Words capitalized somewhere in the text (not "I", not typos, not ordinary words).
        let mut capitalized_elsewhere: HashSet<&str> = HashSet::new();
        for (i, t) in tokens
            .iter()
            .enumerate()
            .filter(|(_, t)| t.is_word && capitalized(t))
        {
            let b = base(&t.normalized);
            // "Thi is fine": a sentence's capital on a short slip of a frequent word is no name.
            // A lone letter opening a sentence ("W e usually eat") is a broken word, not an initial.
            if sentence_start(i)
                && (!t.proper_name || spelling::opening_name_slip(tokens, i))
                && (spelling::opening_slip(b)
                    || spelling::glued_pair(b)
                    || b.len() == 1 && b != "i" && b != "a")
            {
                continue;
            }
            if !never_a_name(t.surface)
                && b != "i"
                && !b.starts_with("i'")
                && !spelling::ordinary(b)
                && !is_name_typo(b)
                && !spelling::typo_shaped(b)
            {
                capitalized_elsewhere.insert(b);
            }
        }
        // Email local parts ("aman.jain@example.com" names aman and jain).
        static EMAIL: OnceLock<Regex> = OnceLock::new();
        let email = EMAIL.get_or_init(|| {
            Regex::new(r"([\w.+-]+)@[\w-]+(?:\.[\w-]+)*\.[A-Za-z]{2,}")
                .expect("constant email regex")
        });
        let mut local: HashSet<String> = HashSet::new();
        for c in email.captures_iter(text) {
            for part in c[1].split(|ch: char| !ch.is_alphabetic()) {
                let part = fold(part);
                if part.chars().count() >= 3 && !spelling::ordinary(&part) && !is_name_typo(&part) {
                    local.insert(part);
                }
            }
        }
        for (i, t) in tokens.iter().enumerate().filter(|(_, t)| t.is_word) {
            let b = base(&t.normalized);
            // A request name that is also an ordinary word ("Will", "May") counts only when written
            // capitalized mid-sentence or addressed ("Dear will", "thanks, will").
            let by_request = self.names.word(&t.normalized)
                && (!spelling::ordinary(b)
                    || capitalized(t) && !sentence_start(i)
                    || spelling::addressed(tokens, i) && spelling::closes_name(tokens, i));
            // "Hey Hope!", "thanks, Rose", "Dr Mark": a capital right after a greeting or title, or any
            // word there that closes its phrase ("bye, hope.").
            // A known misspelling ("thanks alot") is never the person addressed.
            let addressed_capital = !sentence_start(i)
                && !is_known_misspelling(b)
                // "Thank yyou so much": a slip of "you", not a person thanked.
                && !spelling::slip_fits(b, i.checked_sub(1).map(|j| &tokens[j]), tokens.get(i + 1), t)
                && (capitalized(t) && spelling::addressed(tokens, i)
                    || spelling::greeted(tokens, i)
                        && spelling::closes_name(tokens, i)
                        // "thanks for", "thank you", "best quality", "dear me": an ordinary word is
                        // a name only behind a comma ("bye, hope.") or a salutation ("hey hope!").
                        && (!spelling::ordinary(b)
                            || i > 0 && tokens[i - 1].surface == ","
                            || i > 0
                                && ["hi", "hello", "hey", "hiya", "dear"]
                                    .contains(&tokens[i - 1].normalized.as_str())
                                && !["me", "you", "us", "all"].contains(&b)));
            // The tagger calls most capitalized sentence openers it does not know names; a clear
            // slip of a frequent word there ("Wwe watched") is not one.
            let tagger_name = t.proper_name
                && !(sentence_start(i)
                    && !is_bundled_name(b)
                    && spelling::opening_name_slip(tokens, i));
            level[i] = if hits[i]
                || tagger_name
                || addressed_capital
                || by_request
                || capitalized_elsewhere.contains(b)
                || local.contains(b)
                || capitalized(t)
                    && !sentence_start(i)
                    && is_bundled_name(b)
                    && !is_name_typo(b)
                    && !never_a_name(t.surface)
            {
                STRONG
            } else if name_word(b) {
                MEDIUM
            } else {
                0
            };
        }
        for i in 0..n {
            let k = self.names.phrase(tokens, i);
            // Typing a whole full name ("jean-luc", "will smith") is evidence in itself.
            level[i..i + k].fill(STRONG);
            if hits[i] {
                level[i] = STRONG;
            }
        }
        // "marie-claire": a hyphen joins two name parts, or a name and a word that is no ordinary word.
        for i in 0..n.saturating_sub(2) {
            let (a, dash, c) = (&tokens[i], &tokens[i + 1], &tokens[i + 2]);
            if dash.surface == "-"
                && a.is_word
                && c.is_word
                && a.end_byte == dash.start_byte
                && dash.end_byte == c.start_byte
            {
                let joined = level[i].max(level[i + 2]);
                let partner_ok = |word: &str, lvl: u8| {
                    lvl >= MEDIUM || !spelling::ordinary(word) || is_bundled_name(word)
                };
                if joined >= MEDIUM
                    && partner_ok(base(&a.normalized), level[i])
                    && partner_ok(base(&c.normalized), level[i + 2])
                {
                    level[i..i + 3].fill(joined);
                }
            }
        }
        for i in 0..n {
            if level[i] == 0 && tokens[i].is_word && spelling::lowercase_name(tokens, i) {
                level[i] = WEAK;
            }
        }
        level
    }
}

/// A case-only suggestion over `tokens[start..=end]`.
pub struct Capitalization {
    pub start_utf16: usize,
    pub end_utf16: usize,
    pub replacement: String,
}
pub(crate) fn title_case(token: &Token<'_>) -> String {
    // Keep the typed possessive suffix ("aman's" -> "Aman's"); the apostrophe may be curly.
    let at = token
        .surface
        .char_indices()
        .rev()
        .nth(1)
        .map_or(token.surface.len(), |(i, _)| i);
    let (stem, suffix) = if token.normalized.ends_with("'s") {
        token.surface.split_at(at)
    } else {
        (token.surface, "")
    };
    let lower = fold(stem);
    let cased = spelling::canonical_case(&lower)
        .map(String::from)
        .unwrap_or_else(|| match lower.find('\'') {
            // "o'neil" -> "O'Neil", "d'souza" -> "D'Souza": a one or two letter prefix owns the apostrophe.
            Some(at) if lower[..at].chars().count() <= 2 => {
                crate::upper_first(&lower[..at]) + "'" + &crate::upper_first(&lower[at + 1..])
            }
            _ => crate::upper_first(&lower),
        });
    cased + suffix
}
/// Lowercase names (strong, medium, or weak but dictionary proper nouns), merged into runs ("aman jain", "jean-luc").
pub fn capitalizations(
    text: &str,
    tokens: &[Token<'_>],
    level: &[u8],
    cover: &[bool],
    utf16_at: impl Fn(usize) -> usize,
) -> Vec<Capitalization> {
    // Sentences with Hinglish in them: Roman Hindi is full of words the dictionary knows only
    // capitalized ("karo", "dena"), so only stronger evidence capitalizes there.
    let hinglish: HashSet<(usize, usize)> = tokens
        .iter()
        .filter(|t| t.is_word && spelling::hinglish(base(&t.normalized)))
        .map(|t| (t.paragraph, t.sentence))
        .collect();
    // A strong name that is also an ordinary word ("hope", "rose") needs an addressing context.
    let eligible = |i: usize| {
        let t = &tokens[i];
        let b = base(&t.normalized);
        // A context guess counts when the dictionary only knows the word with a capital ("mumbai").
        t.is_word
            && (level[i] >= MEDIUM
                || level[i] == WEAK
                    && spelling::name_only(b)
                    && !hinglish.contains(&(t.paragraph, t.sentence)))
            && !spelling::PARTICLES.contains(&b)
            && !spelling::hinglish(b)
            && t.surface.chars().next().is_some_and(char::is_lowercase)
            && t.surface
                .chars()
                .filter(|c| c.is_alphabetic())
                .all(char::is_lowercase)
            && (!spelling::ordinary(b)
                || cover[i]
                || spelling::addressed(tokens, i) && spelling::closes_name(tokens, i))
    };
    let mut out = Vec::new();
    let mut i = 0;
    while i < tokens.len() {
        if !eligible(i) {
            i += 1;
            continue;
        }
        let mut end = i;
        let mut words = 1;
        loop {
            let next = end + 1;
            let joined = tokens.get(next + 1).is_some_and(|c| {
                tokens[next].surface == "-"
                    && tokens[end].end_byte == tokens[next].start_byte
                    && tokens[next].end_byte == c.start_byte
                    && eligible(next + 1)
            });
            let spaced = tokens.get(next).is_some_and(|c| {
                &text[tokens[end].end_byte..c.start_byte] == " " && eligible(next)
            });
            if words < 4 && joined {
                end = next + 1;
            } else if words < 4 && spaced {
                end = next;
            } else {
                break;
            }
            words += 1;
        }
        let mut replacement = String::new();
        for k in i..=end {
            if k > i {
                replacement.push_str(&text[tokens[k - 1].end_byte..tokens[k].start_byte]);
            }
            replacement.push_str(&if tokens[k].is_word && eligible(k) {
                title_case(&tokens[k])
            } else {
                tokens[k].surface.to_string()
            });
        }
        out.push(Capitalization {
            start_utf16: utf16_at(tokens[i].start_byte),
            end_utf16: utf16_at(tokens[end].end_byte),
            replacement,
        });
        i = end + 1;
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    fn level_of(text: &str, names: &[&str], dictionary: &[&str]) -> Vec<(String, u8)> {
        let req = Request {
            text: text.into(),
            names: names.iter().map(|s| s.to_string()).collect(),
            dictionary: dictionary.iter().map(|s| s.to_string()).collect(),
            ..Request::default()
        };
        let tokens = tokenizer::tokenize(text, &[]);
        let levels = NameIndex::new(&req).mark(text, &tokens);
        tokens
            .iter()
            .zip(levels)
            .map(|(t, l)| (t.surface.to_string(), l))
            .collect()
    }
    fn level(text: &str, names: &[&str], word: &str) -> u8 {
        level_of(text, names, &[])
            .into_iter()
            .find(|(w, _)| w == word)
            .unwrap()
            .1
    }
    #[test]
    fn bundled_lists_load_sorted_and_split_typos_from_names() {
        assert!(bundled().is_sorted() && typos().is_sorted());
        assert!(is_bundled_name("aman") && is_bundled_name("jain"));
        assert!(is_name_typo("teh") && !is_bundled_name("teh"));
        assert!(load("# note\nZoë\nana\nana\n").contains(&"zoë"));
    }
    #[test]
    fn known_misspellings_are_not_names_but_real_names_are() {
        for typo in [
            "teh", "Recieved", "alot", "sentense", "sentance", "recieve", "Teh's",
        ] {
            assert!(is_known_misspelling(typo), "{typo}");
        }
        for name in bundled()
            .iter()
            .chain(["aarav", "priyanka", "zoë", "jain", "aman", "hope"].iter())
        {
            assert!(!is_known_misspelling(name), "{name}");
        }
        assert_eq!(level("a teh b", &["teh"], "teh"), 0);
        assert_eq!(level("a teh b", &[], "teh"), 0);
        // An explicit dictionary word is the user's deliberate choice, so it stays.
        assert_eq!(level_of("a teh b", &[], &["teh"])[1].1, STRONG);
    }
    #[test]
    fn request_names_are_strong_with_unicode_possessive_and_parts() {
        assert_eq!(level("ask ZOË now", &["Zoë"], "ZOË"), STRONG);
        assert_eq!(level("zoë’s desk", &["Zoë"], "zoë’s"), STRONG);
        assert_eq!(level("send aman's file", &["Aman Jain"], "aman's"), STRONG);
        assert_eq!(level("see jain", &["Aman Jain"], "jain"), STRONG);
        assert_eq!(level("a jean-luc b", &["Jean-Luc"], "luc"), STRONG);
        assert_eq!(level("a well-knwon b", &[], "well"), 0);
    }
    #[test]
    fn bundled_names_are_medium_but_ordinary_words_and_typos_are_not() {
        assert_eq!(level("tell rahul now", &[], "rahul"), MEDIUM);
        assert_eq!(level("send teh file", &[], "teh"), 0);
        assert_eq!(level("I hope it works", &[], "hope"), 0);
    }
    #[test]
    fn capitalized_elsewhere_and_email_locals_are_strong() {
        assert_eq!(level("Zorbax came. ask zorbax", &[], "zorbax"), STRONG);
        assert_eq!(
            level("mail qwlop@example.com about qwlop", &[], "qwlop"),
            STRONG
        );
        assert_eq!(level("The Teh and teh", &[], "teh"), 0);
    }
    #[test]
    fn multiword_dictionary_entries_match_across_tokens() {
        let got = level_of("visit new york today", &[], &["New York"]);
        assert_eq!(got[1].1, STRONG);
        assert_eq!(got[2].1, STRONG);
        assert_eq!(got[0].1, 0);
    }
}
