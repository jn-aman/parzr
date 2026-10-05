//! Inflection-aware deletion index with deterministic context ranking.
use crate::tokenizer::Token;
use crate::{context, morphology, names};
use std::{
    collections::{HashMap, HashSet},
    sync::OnceLock,
};
struct Lexicon {
    words: HashMap<String, u8>,
    lowercase: HashSet<String>,
    /// Original casing of entries that are neither plain capitalized nor acronyms ("McDonald", "iPhone").
    canonical: HashMap<String, String>,
    deletes: HashMap<String, Vec<String>>,
}
fn frequency(word: &str) -> u16 {
    static FREQUENCIES: OnceLock<HashMap<String, u16>> = OnceLock::new();
    FREQUENCIES
        .get_or_init(|| {
            #[derive(serde::Deserialize)]
            struct Prior {
                metadata: serde_json::Value,
                entries: Vec<(String, u16)>,
            }
            let prior: Prior = serde_json::from_str(include_str!("../rules/frequency.json"))
                .expect("valid attributed frequency prior");
            assert_eq!(prior.metadata["license"], "CC-BY-SA-4.0");
            prior.entries.into_iter().collect()
        })
        .get(word)
        .copied()
        .unwrap_or(0)
}
fn lexicon() -> &'static Lexicon {
    static LEXICON: OnceLock<Lexicon> = OnceLock::new();
    LEXICON.get_or_init(|| {
        let entries: Vec<(String, u8)> =
            serde_json::from_str(include_str!("../rules/lexicon.json")).unwrap_or_default();
        let mut words = HashMap::with_capacity(entries.len());
        let mut lowercase = HashSet::new();
        let mut canonical: HashMap<String, String> = HashMap::new();
        for (word, flags) in entries {
            let lower = word.to_lowercase();
            if word == lower {
                lowercase.insert(word.clone());
            } else if word.chars().skip(1).any(char::is_uppercase)
                && word.chars().any(char::is_lowercase)
            {
                // Mixed case beyond a first capital ("McDonald", "iPhone"), not "Rahul" or "NASA".
                // The spelling with the most capitals wins ("McDonald" over "Mcdonald").
                let capitals = |w: &str| w.chars().filter(|c| c.is_uppercase()).count();
                let better = canonical
                    .get(&lower)
                    .is_none_or(|old| capitals(&word) > capitals(old));
                if better {
                    canonical.insert(lower.clone(), word.clone());
                }
            }
            *words.entry(lower).or_insert(0) |= flags;
        }
        let mut deletes: HashMap<String, Vec<String>> = HashMap::new();
        // Index common words only for suggestions; all words remain valid dictionary entries.
        for (word, flags) in &words {
            let common_form = flags & 1 != 0
                || frequency(word) >= 250
                || ["s", "es", "ed", "ing"].iter().any(|suffix| {
                    word.strip_suffix(suffix).is_some_and(|stem| {
                        words.get(stem).is_some_and(|f| f & 1 != 0)
                            || words.get(&format!("{stem}e")).is_some_and(|f| f & 1 != 0)
                    })
                });
            if !common_form || word.len() > 24 || !word.bytes().all(|b| b.is_ascii_lowercase()) {
                continue;
            }
            for deleted in deletions(word) {
                deletes.entry(deleted).or_default().push(word.clone());
            }
        }
        for values in deletes.values_mut() {
            values.sort();
            values.dedup();
        }
        canonical.retain(|lower, _| !lowercase.contains(lower));
        Lexicon {
            words,
            lowercase,
            canonical,
            deletes,
        }
    })
}
fn deletions(word: &str) -> HashSet<String> {
    (0..word.len())
        .map(|i| format!("{}{}", &word[..i], &word[i + 1..]))
        .collect()
}
pub fn known(word: &str) -> bool {
    lexicon().words.contains_key(&word.to_lowercase())
}
pub fn flags(word: &str) -> u8 {
    lexicon()
        .words
        .get(&word.to_lowercase())
        .copied()
        .unwrap_or(0)
}
pub fn name_only(word: &str) -> bool {
    known(word) && !lexicon().lowercase.contains(word)
}
/// An ordinary lowercase dictionary word ("hope", "rose"), as opposed to a name or acronym.
pub fn ordinary(word: &str) -> bool {
    lexicon().lowercase.contains(word)
}
/// "mcdonald" -> "McDonald", "iphone" -> "iPhone": the dictionary spelling of a word that is not
/// an ordinary lowercase word.
pub fn canonical_case(lower: &str) -> Option<&'static str> {
    lexicon().canonical.get(lower).map(String::as_str)
}
/// A name from the lexicon or the bundled list, whether or not the user capitalized it.
fn namey(word: &str) -> bool {
    let word = names::base(word);
    name_only(word) && !names::is_name_typo(word) || names::name_word(word)
}
pub fn possessive_boundary(token: &Token<'_>) -> Option<usize> {
    if !token.surface.chars().next().is_some_and(char::is_uppercase) {
        return None;
    }
    let apostrophe = token.surface.find(['\'', '’'])?;
    let mark = token.surface[apostrophe..].chars().next()?;
    let boundary = apostrophe + mark.len_utf8() + 1;
    if !token.surface[apostrophe + mark.len_utf8()..].starts_with('s')
        || boundary >= token.surface.len()
    {
        return None;
    }
    let tail = &token.surface[boundary..];
    if tail.len() >= 4
        && tail.chars().all(char::is_lowercase)
        && flags(tail) & 2 != 0
        && known(tail)
    {
        Some(token.surface[..boundary].encode_utf16().count())
    } else {
        None
    }
}
fn distance_one(a: &str, b: &str) -> bool {
    if !a.bytes().all(|c| c.is_ascii_alphabetic()) || !b.bytes().all(|c| c.is_ascii_alphabetic()) {
        return false;
    }
    let a = a.as_bytes();
    let b = b.as_bytes();
    if a.len().abs_diff(b.len()) > 1 {
        return false;
    }
    if a.len() == b.len() {
        let differences: Vec<usize> = a
            .iter()
            .zip(b)
            .enumerate()
            .filter_map(|(i, (x, y))| (x != y).then_some(i))
            .collect();
        return differences.len() == 1
            || differences.len() == 2
                && differences[1] == differences[0] + 1
                && a[differences[0]] == b[differences[1]]
                && a[differences[1]] == b[differences[0]];
    }
    let (short, long) = if a.len() < b.len() { (a, b) } else { (b, a) };
    let mut i = 0;
    let mut j = 0;
    let mut skipped = false;
    while i < short.len() && j < long.len() {
        if short[i] == long[j] {
            i += 1;
            j += 1;
        } else if !skipped {
            skipped = true;
            j += 1;
        } else {
            return false;
        }
    }
    true
}
fn transposed(a: &str, b: &str) -> bool {
    a.len() == b.len()
        && a.bytes().zip(b.bytes()).filter(|(a, b)| a != b).count() == 2
        && distance_one(a, b)
}
fn function(word: &str) -> bool {
    if ["be", "been", "being"].contains(&word) {
        return true;
    }
    [
        "a", "an", "the", "and", "or", "but", "so", "to", "of", "in", "on", "at", "by", "for",
        "from", "with", "before", "after", "during", "every", "some", "any", "all", "no", "not",
        "is", "are", "was", "were", "has", "have", "had", "will", "would", "can", "could",
        "should", "must", "do", "does", "did", "it", "its", "we", "they", "their", "our", "her",
        "my", "your", "you", "if", "then", "so", "anything", "this", "that", "i", "you're",
        "we're", "they're", "it's", "don't", "doesn't", "didn't", "i'm", "me", "us", "him", "them",
        "who", "whom", "whose", "which", "one",
    ]
    .contains(&word)
}
fn joined(
    word: &str,
    prev: &str,
    following: &str,
    new_sentence: bool,
    following_flags: u8,
) -> Option<(i32, String)> {
    if !word.is_ascii() || word.len() < 4 || word.len() > 40 {
        return None;
    }
    fn valid(w: &str) -> bool {
        (w.len() >= 3 || function(w)) && (function(w) || known(w) && frequency(w) >= 250)
    }
    let mut splits: Vec<(i32, String)> = Vec::new();
    for i in 1..word.len() {
        let (a, b) = word.split_at(i);
        if !valid(a) {
            continue;
        }
        let mut tails = Vec::new();
        if valid(b) {
            tails.push(vec![b]);
        }
        if word.contains('\'') {
            for j in 1..b.len() {
                let (c, d) = b.split_at(j);
                if valid(c) && valid(d) {
                    tails.push(vec![c, d]);
                }
            }
        }
        for tail in tails {
            let mut parts = vec![a];
            parts.extend(tail);
            if parts.len() == 2 && parts[1] == "one" && !function(a) && flags(a) & 8 == 0 {
                continue;
            }
            if parts.iter().any(|p| p.len() < 4 && !function(p))
                && !parts.iter().any(|p| function(p))
                && !(flags(a) & 8 != 0 && parts[parts.len() - 1].len() >= 4)
            {
                continue;
            }
            if [
                "in", "on", "at", "by", "for", "of", "with", "from", "before", "after", "during",
                "a", "an", "the",
            ]
            .contains(&parts[parts.len() - 1])
                && (following.is_empty()
                    || !following.chars().all(char::is_alphabetic)
                    || new_sentence)
            {
                continue;
            }
            if ["a", "an"].contains(&a)
                && flags(parts[parts.len() - 1]) & 8 != 0
                && (following_flags & 2 == 0 || function(following))
            {
                continue;
            }
            if ["a", "an", "the", "my", "your", "our", "their"].contains(&prev)
                && function(a)
                && !["a", "an"].contains(&a)
            {
                continue;
            }
            if ["am", "is", "are", "was", "were", "be", "been"].contains(&prev)
                && flags(a) & 8 == 0
                && !morphology::verb(a).is_some_and(|v| v.participle == a || v.gerund == a)
                && !["not", "too", "very"].contains(&a)
            {
                continue;
            }
            let mut score = parts
                .windows(2)
                .map(|p| context::score(p[0], p[1]))
                .sum::<i32>()
                + context::score(prev, a)
                + context::score(parts[parts.len() - 1], following)
                + 30
                - 20 * (parts.len() as i32 - 2);
            if ["a", "an"].contains(&a) && following_flags & 2 != 0 && flags(b) & 8 != 0 {
                score += 230;
            }
            if b == "so"
                && flags(a) & 2 != 0
                && ["a", "an", "the"].contains(&prev)
                && (following_flags & 16 != 0 || following.ends_with("ly"))
            {
                score += 350;
            }
            if prev == "to"
                && a == "be"
                && morphology::verb(parts[parts.len() - 1])
                    .is_some_and(|v| v.participle == parts[parts.len() - 1])
            {
                score += 80;
            }
            // A missing space before an article has a strong syntactic anchor:
            // the exact base verb on its left and a noun on its right. Do not
            // discard the article to prefer a nearby inflected spelling.
            if parts.len() == 2
                && ["a", "an"].contains(&parts[1])
                && following_flags & 2 != 0
                && morphology::verb(a).is_some_and(|v| v.base == a && morphology::predicate(a))
            {
                score += 320;
            }
            if ["i", "we", "you", "they", "he", "she"].contains(&a)
                && ["", ",", ".", "!", "?", "yesterday", "today"].contains(&prev)
                && parts.len() == 2
                && morphology::verb(parts[1]).is_some_and(|v| {
                    morphology::predicate(&v.base)
                        && [v.base.as_str(), &v.past, &v.third].contains(&parts[1])
                })
            {
                score += 180;
            }
            splits.push((score, parts.join(" ")));
        }
    }
    splits.sort_by(|a, b| b.0.cmp(&a.0).then_with(|| a.1.cmp(&b.1)));
    if splits.len() == 1 || splits.len() > 1 && splits[0].0 > splits[1].0 {
        splits.first().cloned()
    } else {
        None
    }
}
const COMMON: [&str; 15] = [
    "is", "it", "the", "and", "to", "of", "on", "in", "as", "at", "so", "no", "for", "was", "has",
];
const SUBJECT_WORDS: [&str; 19] = [
    "this",
    "that",
    "it",
    "he",
    "she",
    "there",
    "here",
    "what",
    "who",
    "which",
    "everything",
    "something",
    "nothing",
    "anything",
    "everyone",
    "someone",
    "nobody",
    "somebody",
    "whatever",
];
const DETERMINERS: [&str; 16] = [
    "the", "a", "an", "my", "your", "his", "her", "our", "their", "this", "that", "each", "every",
    "some", "any", "no",
];
const ARTICLE_LIKE: [&str; 21] = [
    "the", "a", "an", "my", "your", "his", "her", "our", "their", "this", "that", "these", "those",
    "its", "all", "each", "every", "some", "any", "most", "many",
];
const COPULAS: [&str; 15] = [
    "is", "are", "was", "were", "am", "be", "been", "being", "it's", "that's", "he's", "she's",
    "there's", "here's", "what's",
];
const ADJECTIVES: [&str; 33] = [
    "bad",
    "great",
    "nice",
    "hard",
    "easy",
    "big",
    "small",
    "late",
    "early",
    "long",
    "short",
    "hot",
    "cold",
    "loud",
    "quiet",
    "fast",
    "slow",
    "important",
    "difficult",
    "sad",
    "happy",
    "tired",
    "busy",
    "boring",
    "expensive",
    "cheap",
    "annoying",
    "terrible",
    "awful",
    "sorry",
    "glad",
    "funny",
    "weird",
];
pub fn adjective(token: &Token<'_>) -> bool {
    // Fix-time tagging of damaged text is noisy; the list backs up the OS part-of-speech hint.
    // "do good", "do right" and "do well" are real verb phrases, so they never qualify.
    !["good", "right", "wrong", "well", "better", "best"].contains(&token.normalized.as_str())
        && (token.pos == "Adjective" || ADJECTIVES.contains(&token.normalized.as_str()))
}
/// A word that can be the subject of "is": a pronoun, name, or determiner + singular noun.
fn singular_subject(tokens: &[Token<'_>], at: usize) -> bool {
    let token = &tokens[at];
    let word = token.normalized.as_str();
    if !token.is_word || word == "i" {
        return false;
    }
    if SUBJECT_WORDS.contains(&word) {
        return true;
    }
    let initial = at == 0 || [".", "!", "?"].contains(&tokens[at - 1].surface);
    if token.proper_name
        || token.surface.chars().next().is_some_and(char::is_uppercase)
            && (!initial || name_only(word))
    {
        return true;
    }
    let noun = flags(word) & 2 != 0 && flags(word) & 16 == 0 && !word.ends_with('s');
    noun && (at >= 1 && DETERMINERS.contains(&tokens[at - 1].normalized.as_str())
        || at >= 2
            && adjective(&tokens[at - 1])
            && DETERMINERS.contains(&tokens[at - 2].normalized.as_str()))
}
/// Whether `candidate` fits the slot of `tokens[index]`. Each entry is a deliberately narrow
/// syntactic frame, so a real word (a musical "si", "On" opening a sentence) keeps its meaning.
fn slot_fits(candidate: &str, tokens: &[Token<'_>], index: usize) -> bool {
    let text = |i: Option<usize>| {
        i.and_then(|i| tokens.get(i))
            .filter(|t| t.is_word)
            .map_or("", |t| t.normalized.as_str())
    };
    let (prev, next) = (text(index.checked_sub(1)), text(Some(index + 1)));
    let ahead = text(Some(index + 2));
    match candidate {
        "is" => {
            let subject = index > 0 && singular_subject(tokens, index - 1);
            // "si note is" is a noun phrase with its own verb, not a damaged copula.
            let phrase = ["is", "are", "was", "were"].contains(&ahead);
            let predicate = [
                "too", "so", "very", "really", "not", "still", "already", "quite", "pretty",
                "always", "never", "just", "also", "ready", "going",
            ]
            .contains(&next)
                && !prev.is_empty()
                && ![
                    "i", "you", "we", "they", "the", "a", "an", "of", "to", "in", "on", "at",
                ]
                .contains(&prev);
            (subject && !phrase) || predicate
        }
        "it" => {
            [
                "is", "was", "has", "had", "will", "would", "can", "could", "should", "does",
                "did", "seems", "looks", "might", "may", "must", "isn't", "wasn't", "doesn't",
            ]
            .contains(&next)
                && !DETERMINERS.contains(&prev)
        }
        "in" => !prev.is_empty() && ARTICLE_LIKE.contains(&next),
        "at" => {
            !prev.is_empty()
                && (ARTICLE_LIKE.contains(&next)
                    || [
                        "least", "once", "home", "work", "school", "night", "noon", "first", "last",
                    ]
                    .contains(&next))
        }
        "of" => {
            [
                "lot", "lots", "couple", "number", "kind", "type", "sort", "part", "bit", "piece",
                "one", "all", "most", "many", "some", "out", "because", "instead", "front",
                "middle", "end", "top", "rest", "member", "members", "version", "list", "side",
                "group", "set",
            ]
            .contains(&prev)
                && ARTICLE_LIKE.contains(&next)
        }
        "as" => {
            !prev.is_empty()
                && [
                    "if", "soon", "well", "much", "many", "long", "far", "though", "a", "an", "the",
                ]
                .contains(&next)
        }
        "so" => {
            [
                "i", "we", "you", "they", "he", "she", "it", "is", "are", "was", "were", "am",
                "be", "been", "and", "but", "not", "that", "this",
            ]
            .contains(&prev)
                && (tokens.get(index + 1).is_some_and(adjective)
                    || ["much", "many", "long", "far"].contains(&next))
        }
        "was" => {
            [
                "i", "he", "she", "it", "this", "that", "there", "who", "what",
            ]
            .contains(&prev)
                && !next.is_empty()
        }
        "has" => {
            ["he", "she", "it", "who", "that", "this"].contains(&prev)
                && ([
                    "been", "a", "an", "the", "no", "not", "never", "already", "just", "also",
                    "always",
                ]
                .contains(&next)
                    || morphology::verb(next).is_some_and(|v| v.participle == next))
        }
        _ => false,
    }
}
/// Slot-aware corrections that need neighbouring tokens: a rare word that is one adjacent
/// transposition (or, when unknown to the dictionary, one edit) from a top-frequency function
/// word becomes that word where its slot fits, and "do" becomes "so" before an adjective.
/// Returns the rule id, replacement and reason. `to`, `the`, `and`, `for`, `on`
/// and `no` have no frame here, so they win a tie and leave the token to `suggest`.
pub fn slot_fix(
    tokens: &[Token<'_>],
    index: usize,
) -> Option<(&'static str, String, &'static str)> {
    let token = &tokens[index];
    let word = token.normalized.as_str();
    if token.proper_name || token.surface != word || !word.bytes().all(|b| b.is_ascii_lowercase()) {
        return None;
    }
    if word == "do" {
        let prev = index.checked_sub(1).map(|i| &tokens[i])?;
        let next = tokens.get(index + 1)?;
        let plural_noun = tokens
            .get(index + 2)
            .is_some_and(|t| t.is_word && flags(&t.normalized) & 16 != 0);
        return (prev.is_word
            && COPULAS.contains(&prev.normalized.as_str())
            && adjective(next)
            && !plural_noun)
            .then(|| {
                (
                    "spelling.copula_do_intensifier",
                    "so".to_string(),
                    "Use so before this adjective; do cannot modify it.",
                )
            });
    }
    if !(2..=3).contains(&word.len()) {
        return None;
    }
    let unknown = !lexicon().lowercase.contains(word);
    let mut near: Vec<&str> = COMMON
        .into_iter()
        // Far more frequent: a gap of 1.5 Zipf points (about 30 times) in the frequency prior.
        .filter(|c| frequency(c) >= frequency(word).saturating_add(150))
        .filter(|c| transposed(word, c) || unknown && distance_one(word, c))
        .collect();
    // A transposition is the stronger evidence ("ot" is "to", not "at").
    if near.iter().any(|c| transposed(word, c)) {
        near.retain(|c| transposed(word, c));
    }
    let fits: Vec<&str> = near
        .into_iter()
        .filter(|c| slot_fits(c, tokens, index))
        .collect();
    match fits[..] {
        // A name one letter away from a function word ("ta" is a typo, "tia" may be a person).
        [only] if !transposed(word, only) && lowercase_name(tokens, index) => None,
        [only] => Some((
            "spelling.frequent_word",
            only.to_string(),
            "A far more common word fits here; this looks like a typo.",
        )),
        _ => None,
    }
}
/// Words after which a lowercase unknown word is a person being greeted, thanked or addressed
/// ("hi aman", "ask aman about it"), not a typo.
const ADDRESSING: [&str; 36] = [
    "hi",
    "hello",
    "hey",
    "hiya",
    "dear",
    "thanks",
    "thank",
    "regards",
    "cheers",
    "bye",
    "ask",
    "asked",
    "tell",
    "told",
    "ping",
    "pinged",
    "cc",
    "ccd",
    "see",
    "saw",
    "meet",
    "met",
    "call",
    "called",
    "best",
    "sincerely",
    "yours",
    "love",
    "greetings",
    "invite",
    "invited",
    "inviting",
    "email",
    "emailed",
    "bcc",
    "thx",
];
/// Greetings and closings only (no verbs): a word after these that ends its phrase is a person.
const GREETINGS: [&str; 14] = [
    "hi",
    "hello",
    "hey",
    "hiya",
    "dear",
    "thanks",
    "thank",
    "regards",
    "cheers",
    "bye",
    "best",
    "sincerely",
    "yours",
    "love",
];
/// Closing words: a name on the next line is the signature ("Regards,\naman").
const SIGNOFF: [&str; 13] = [
    "regards",
    "thanks",
    "cheers",
    "best",
    "sincerely",
    "thank",
    "you",
    "yours",
    "love",
    "bye",
    "wishes",
    "faithfully",
    "again",
];
/// Words that introduce a person; they weigh less than ADDRESSING because they also precede
/// ordinary words, so they need a word of 4+ letters that is not typo-shaped.
const LEADS: [&str; 7] = [
    "with", "from", "message", "messaged", "texted", "join", "tag",
];
const TITLES: [&str; 14] = [
    "mr",
    "mrs",
    "ms",
    "mx",
    "dr",
    "prof",
    "professor",
    "shri",
    "sri",
    "shree",
    "smt",
    "kumari",
    "sardar",
    "janab",
];
const HONORIFICS: [&str; 14] = [
    "ji", "sir", "madam", "maam", "bhai", "bhaiya", "didi", "da", "dada", "anna", "akka", "sahab",
    "saheb", "garu",
];
/// Words that open a clause, so an unknown word after them followed by a verb is its subject.
const CLAUSE_LEADS: [&str; 26] = [
    "that", "and", "but", "so", "because", "if", "when", "while", "then", "think", "thought",
    "guess", "hope", "know", "knew", "said", "says", "heard", "whether", "though", "since",
    "until", "maybe", "perhaps", "also", "actually",
];
const FINITE: [&str; 13] = [
    "is", "was", "has", "had", "will", "would", "can", "could", "should", "does", "did", "are",
    "were",
];
/// Words that can precede an article + noun phrase, so a missing space in "aclear statement" or
/// "is aman" can be read as "a clear statement" or "is a man". Perception, address and
/// communication verbs are left out on purpose: "saw aman" is as likely a name as a man.
const ARTICLE_LEAD: [&str; 60] = [
    "am", "is", "are", "was", "were", "be", "been", "being", "it's", "that's", "he's", "she's",
    "there's", "here's", "what's", "for", "with", "in", "on", "at", "by", "from", "of", "into",
    "like", "as", "than", "have", "has", "had", "having", "need", "needs", "needed", "want",
    "wants", "wanted", "get", "gets", "got", "make", "makes", "made", "take", "takes", "took",
    "find", "finds", "found", "give", "gives", "gave", "buy", "and", "or", "but", "than", "that",
    "if", "because",
];
fn line_start(tokens_before: &[Token<'_>], token: &Token<'_>) -> bool {
    tokens_before
        .last()
        .is_none_or(|p| p.paragraph != token.paragraph || [".", "!", "?"].contains(&p.surface))
}
/// Capital letters the engine itself added when it opened a sentence say nothing about how the
/// text was typed; the pipeline marks them so every pass reads the same evidence.
const AUTO_CAPITAL: &str = "AutoCapital";
pub const AUTO_CAPITAL_HINT: &str = AUTO_CAPITAL;
fn typed_capital(t: &Token<'_>) -> bool {
    t.surface.chars().next().is_some_and(char::is_uppercase) && t.pos != AUTO_CAPITAL
}
fn unknown_alphabetic(token: &Token<'_>) -> bool {
    let word = names::base(&token.normalized);
    token.is_word && word.chars().all(|c| c.is_alphabetic() || c == '\'') && !known(word)
}
/// Strong typo evidence for an unknown word: it is one adjacent swap, one extra letter or one
/// missing letter away from a frequent word, or it is two frequent words run together. A name
/// like "aman" has none of these (the one-letter edits it has, "a man" or "amen", are exactly
/// the false positives), so typo-shaped words keep their corrections even beside names.
fn swaps_to_common(word: &str) -> bool {
    let bytes = word.as_bytes();
    word.is_ascii()
        && (0..bytes.len().saturating_sub(1)).any(|i| {
            let mut swapped = bytes.to_vec();
            swapped.swap(i, i + 1);
            let swapped = String::from_utf8_lossy(&swapped).into_owned();
            swapped != word && ordinary(&swapped) && frequency(&swapped) >= 600
        })
}
pub(crate) fn typo_shaped(word: &str) -> bool {
    // Frequency prior 400 is Zipf 4.0, about the 6,000 most frequent words.
    let frequent = |w: &str| known(w) && frequency(w) >= 400;
    if !word.is_ascii() || word.len() < 4 {
        return false;
    }
    let bytes = word.as_bytes();
    let text = |b: &[u8]| String::from_utf8_lossy(b).into_owned();
    for i in 0..bytes.len() - 1 {
        let mut swapped = bytes.to_vec();
        swapped.swap(i, i + 1);
        if bytes[i] != bytes[i + 1] && frequent(&text(&swapped)) {
            return true;
        }
    }
    // Names are short; one-letter edits to a word of 6+ letters are real typos.
    if word.len() >= 6 {
        for i in 0..bytes.len() {
            let mut shorter = bytes.to_vec();
            shorter.remove(i);
            if frequent(&text(&shorter)) {
                return true;
            }
        }
        for i in 0..=bytes.len() {
            for letter in b'a'..=b'z' {
                let mut longer = bytes.to_vec();
                longer.insert(i, letter);
                if frequent(&text(&longer)) {
                    return true;
                }
            }
        }
    }
    // One wrong letter in a long word ("experiance"); long names are rarely one letter from a word.
    if word.len() >= 7 {
        for i in 0..bytes.len() {
            for letter in b'a'..=b'z' {
                let mut other = bytes.to_vec();
                other[i] = letter;
                if other != bytes && frequent(&text(&other)) {
                    return true;
                }
            }
        }
    }
    (2..word.len() - 1).any(|i| {
        let (a, b) = word.split_at(i);
        let glue = |w: &str| {
            [
                "the", "to", "of", "in", "on", "at", "by", "for", "and", "with",
            ]
            .contains(&w)
        };
        (frequent(a) && frequent(b) && a.len() >= 3 && b.len() >= 3)
            || (glue(a) && b.len() >= 4 && frequent(b))
            || (glue(b) && a.len() >= 4 && frequent(a))
    })
}
/// A word beside `token` (no punctuation or line break between) that is a name, an unknown word
/// that is not a typo, or a capitalized word in mid-sentence ("I" and its contractions are not
/// names). Neighbouring unknown words only count on a line
/// typed without capitals ("aman jain"): someone who capitalizes sentences would capitalize
/// names, so an unknown lowercase word there is a typo, and typos cluster ("rzview alreazy").
fn name_neighbor(
    neighbor: &Token<'_>,
    before_neighbor: &[Token<'_>],
    token: &Token<'_>,
    casual: bool,
) -> bool {
    // A capitalized word that opens a sentence is no evidence: "Clara atean apple".
    let counts = !line_start(before_neighbor, neighbor) || !typed_capital(neighbor);
    neighbor.is_word
        && neighbor.paragraph == token.paragraph
        && counts
        && (namey(&neighbor.normalized) && !name_only_typo(&neighbor.normalized, "")
            || casual && unknown_alphabetic(neighbor) && !typo_shaped(&neighbor.normalized)
            || typed_capital(neighbor)
                && neighbor.normalized != "i"
                && !neighbor.normalized.starts_with("i'"))
}
/// Words a bare name never follows or precedes ("the tran", "Clara wite the introduction").
const DETERMINERS_AND_ARTICLES: [&str; 14] = [
    "the", "a", "an", "my", "your", "his", "her", "our", "their", "its", "this", "that", "these",
    "those",
];
/// Whether a lowercase word that the system lexicon accepts only as a name ("tran", "neds",
/// "appel") is really a typo here: a determiner precedes it, one swap gives a frequent word, or
/// one missing letter gives a very frequent word (tran/train, neds/needs).
pub fn hinted_name_is_typo(word: &str, prev: &str) -> bool {
    if names::is_name_typo(word) || name_only_typo(word, prev) || typo_shaped(word) {
        return true;
    }
    // Frequency 600 is Zipf 6.0-equivalent in this table: only very common words qualify.
    word.is_ascii()
        && (0..=word.len()).any(|i| {
            (b'a'..=b'z').any(|letter| {
                let mut longer = word.as_bytes().to_vec();
                longer.insert(i, letter);
                let longer = String::from_utf8_lossy(&longer).into_owned();
                ordinary(&longer) && frequency(&longer) >= 600
            })
        })
}
/// Whether a lexicon entry listed only as a name ("Tran", "OT", "Peron") is really a damaged
/// common word here: a determiner precedes it, or it is one swap from a top-1000 word ("ot").
fn name_only_typo(word: &str, prev: &str) -> bool {
    DETERMINERS_AND_ARTICLES.contains(&prev)
        || word.is_ascii()
            && (0..word.len().saturating_sub(1)).any(|i| {
                let mut swapped = word.as_bytes().to_vec();
                swapped.swap(i, i + 1);
                let swapped = String::from_utf8_lossy(&swapped).into_owned();
                swapped != word
                    && lexicon().lowercase.contains(&swapped)
                    && frequency(&swapped) >= 500
            })
}
/// The word before `token`, read through the given punctuation. A word on an earlier line only
/// counts when it closes a letter ("Regards,\naman").
fn lead<'a>(history: &'a [Token<'a>], token: &Token<'_>, skip: &[&str]) -> Option<&'a Token<'a>> {
    let p = history
        .iter()
        .rev()
        .take(3)
        .find(|t| !skip.contains(&t.surface))?;
    (p.is_word && (p.paragraph == token.paragraph || SIGNOFF.contains(&p.normalized.as_str())))
        .then_some(p)
}
const PUNCT_BEFORE: [&str; 4] = [",", ":", "-", "!"];
/// Whether the word after `tokens[index]` ends the name: nothing, punctuation, or a preposition
/// or conjunction ("thanks, will for the help"), not a pronoun that starts a new clause.
pub fn closes_name(tokens: &[Token<'_>], index: usize) -> bool {
    tokens.get(index + 1).is_none_or(|n| {
        !n.is_word
            || n.paragraph != tokens[index].paragraph
            || function(&n.normalized)
                && !["i", "you", "we", "they", "he", "she", "it", "there"]
                    .contains(&n.normalized.as_str())
    })
}
/// A greeting, title or sign-off just before `tokens[index]` ("Hi, hope!", "Dr. mark").
pub fn greeted(tokens: &[Token<'_>], index: usize) -> bool {
    let (history, token) = (&tokens[..index], &tokens[index]);
    lead(history, token, &PUNCT_BEFORE).is_some_and(|p| GREETINGS.contains(&p.normalized.as_str()))
        || lead(history, token, &["."]).is_some_and(|p| TITLES.contains(&p.normalized.as_str()))
}
/// A greeting, address, title or sign-off just before `tokens[index]`.
pub fn addressed(tokens: &[Token<'_>], index: usize) -> bool {
    addressed_by(&tokens[..index], &tokens[index])
}
/// Another word of a name list ("aditya, prajakta and ketaki") one connector away.
fn list_member(neighbor: &Token<'_>, opens_line: bool, token: &Token<'_>) -> bool {
    neighbor.is_word
        && neighbor.paragraph == token.paragraph
        && (namey(&neighbor.normalized)
            // Two damaged-looking words side by side are two typos, not two names.
            || unknown_alphabetic(neighbor)
                && !(typo_shaped(&neighbor.normalized) && typo_shaped(&token.normalized))
            || typed_capital(neighbor) && !opens_line)
}
const CONNECTORS: [&str; 4] = [",", "and", "&", "or"];
fn in_list(history: &[Token<'_>], token: &Token<'_>, following: &[Token<'_>]) -> bool {
    let connector = |t: &Token<'_>| CONNECTORS.contains(&t.normalized.as_str());
    let left = match history {
        [rest @ .., w, c] if connector(c) => Some((w, line_start(rest, w))),
        [rest @ .., w, c, and] if connector(c) && connector(and) => Some((w, line_start(rest, w))),
        _ => None,
    };
    let right = match following {
        [c, w, ..] if connector(c) => Some(w),
        [c, and, w, ..] if connector(c) && connector(and) => Some(w),
        _ => None,
    };
    left.is_some_and(|(w, opens)| list_member(w, opens, token))
        || right.is_some_and(|w| list_member(w, false, token))
}
const PARTICLES: [&str; 12] = [
    "van", "von", "der", "den", "de", "zu", "bin", "ibn", "del", "della", "dos", "du",
];
/// A name part beside a surname particle with another unknown word on its far side.
fn particle_joined(history: &[Token<'_>], token: &Token<'_>, following: &[Token<'_>]) -> bool {
    let part = |t: &Token<'_>| {
        t.is_word
            && t.paragraph == token.paragraph
            && (unknown_alphabetic(t) || namey(&t.normalized) || typed_capital(t))
    };
    let particle = |t: &Token<'_>| {
        t.paragraph == token.paragraph && PARTICLES.contains(&t.normalized.as_str())
    };
    let after = match following {
        [p, w, ..] if particle(p) && part(w) => true,
        [p, p2, w, ..] if particle(p) && particle(p2) && part(w) => true,
        _ => false,
    };
    let before = match history {
        [.., w, p] if particle(p) && part(w) => true,
        [.., w, p2, p] if particle(p) && particle(p2) && part(w) => true,
        _ => false,
    };
    // The token may itself be the second particle ("van der berg").
    let inner = particle(token)
        && history.last().is_some_and(particle)
        && following.first().is_some_and(part);
    after || before || inner
}
/// A word that is not everyday vocabulary: unknown, a name, capitalized, or rare.
fn uncommon(t: &Token<'_>) -> bool {
    t.is_word
        && (unknown_alphabetic(t)
            || namey(&t.normalized)
            || typed_capital(t)
            || frequency(&t.normalized) < 400)
}
/// "anke, dirk and wim": a list of three or more single words whose other items are all
/// uncommon words is a list of people.
fn name_list(history: &[Token<'_>], token: &Token<'_>, following: &[Token<'_>]) -> bool {
    let connector = |t: &Token<'_>| CONNECTORS.contains(&t.normalized.as_str());
    let same = |t: &Token<'_>| t.paragraph == token.paragraph;
    let mut items = vec![];
    let mut i = history.len();
    loop {
        let mut j = i;
        while j > 0 && i - j < 2 && connector(&history[j - 1]) && same(&history[j - 1]) {
            j -= 1;
        }
        if j == i || j == 0 || !history[j - 1].is_word || !same(&history[j - 1]) {
            break;
        }
        items.push(&history[j - 1]);
        i = j - 1;
    }
    let mut k = 0;
    loop {
        let mut j = k;
        while j < following.len() && j - k < 2 && connector(&following[j]) && same(&following[j]) {
            j += 1;
        }
        if j == k || j >= following.len() || !following[j].is_word || !same(&following[j]) {
            break;
        }
        items.push(&following[j]);
        k = j + 1;
    }
    let shaped = typo_shaped(&token.normalized);
    items.len() >= 2
        && items
            .into_iter()
            .all(|t| uncommon(t) && !(shaped && typo_shaped(&t.normalized)))
}
/// Whether a lowercase unknown word is most likely a person's name typed without capitals.
/// Turning a name into unrelated common words is worse than leaving a typo alone, so every
/// respelling and word split is skipped for these.
fn name_like(token: &Token<'_>, history: &[Token<'_>], following: &[Token<'_>]) -> bool {
    let word = names::base(&token.normalized);
    if names::is_name_typo(word) {
        return false;
    }
    // A word that looks like a typo ("farhad" is "far had") is still a name where the context
    // names a person: only the weaker signals below give way to its shape.
    let shaped = typo_shaped(word);
    let previous = history.last();
    let next = following.first();
    let before_previous = &history[..history.len().saturating_sub(1)];
    let line: Vec<_> = history
        .iter()
        .rev()
        .take_while(|t| t.paragraph == token.paragraph)
        .chain(
            following
                .iter()
                .take_while(|t| t.paragraph == token.paragraph),
        )
        .filter(|t| t.is_word)
        .collect();
    let casual = !line
        .iter()
        .any(|t| typed_capital(t) && t.normalized != "i" && !t.normalized.starts_with("i'"));
    let next_word = next.filter(|n| n.is_word && n.paragraph == token.paragraph);
    let next_is = |list: &[&str]| next_word.is_some_and(|n| list.contains(&n.normalized.as_str()));
    // "thanks aman", "Mr aman", "aman ji", "alice, aman and ravi". After a comma the next word must
    // not be another content word: "hi, plase call me" is a typo, "hi, aman how are you" a name.
    let punctuated = previous.is_some_and(|p| !p.is_word);
    let closes_phrase = next_word.is_none_or(|n| {
        function(&n.normalized)
            || FINITE.contains(&n.normalized.as_str())
            || [
                "how", "what", "when", "where", "why", "hope", "please", "thanks",
            ]
            .contains(&n.normalized.as_str())
    });
    if addressed_by(history, token)
        && (!punctuated || closes_phrase)
        && (!shaped || !punctuated || next_word.is_none())
        || next_is(&HONORIFICS)
    {
        return true;
    }
    // A vocative: "wim, could you...", "...before lunch, sai?".
    let comma_before = previous.is_some_and(|p| p.surface == ",");
    let ends_clause =
        next.is_none_or(|n| n.paragraph != token.paragraph || ["?", "!", "."].contains(&n.surface));
    if comma_before && ends_clause
        || next.is_some_and(|n| n.surface == ",")
            && previous.is_none_or(|p| !p.is_word || p.paragraph != token.paragraph)
    {
        return true;
    }
    // A signature: one to three words on the line after "Regards,".
    let signed = line.len() <= 3
        && line
            .iter()
            .all(|t| unknown_alphabetic(t) || namey(&t.normalized))
        && history
            .iter()
            .rev()
            .find(|t| t.paragraph != token.paragraph)
            .is_some_and(|t| SIGNOFF.contains(&t.normalized.as_str()));
    if signed {
        return true;
    }
    if in_list(history, token, following) || name_list(history, token, following) {
        return true;
    }
    if !shaped
        && (previous.is_some_and(|p| name_neighbor(p, before_previous, token, casual))
            || next.is_some_and(|n| name_neighbor(n, history, token, casual)))
        && !next.is_some_and(|n| DETERMINERS_AND_ARTICLES.contains(&n.normalized.as_str()))
    {
        return true;
    }
    // "jean-luc", "jae-won": an unknown word hyphenated to another word is a name part.
    let before_dash = !shaped
        && previous.zip(before_previous.last()).is_some_and(|(d, o)| {
            d.surface == "-"
                && o.is_word
                && o.end_byte == d.start_byte
                && d.end_byte == token.start_byte
        });
    let after_dash = !shaped
        && next.zip(following.get(1)).is_some_and(|(d, o)| {
            d.surface == "-"
                && o.is_word
                && token.end_byte == d.start_byte
                && d.end_byte == o.start_byte
        });
    if before_dash || after_dash {
        return true;
    }
    // A lone word on the last line of a message is its signature ("Thanks for the update.\npieter").
    if line.is_empty()
        && following.iter().all(|t| t.paragraph == token.paragraph)
        && history.iter().any(|t| t.paragraph != token.paragraph)
        && previous.is_none_or(|p| p.paragraph != token.paragraph)
    {
        return true;
    }
    // "joost van dijk", "pieter von trapp": a surname particle joins two name parts.
    if particle_joined(history, token, following) {
        return true;
    }
    // "taht" is "that": one swap of a top-frequency word is a typo, whatever follows it.
    if shaped && swaps_to_common(word) {
        return false;
    }
    let after_determiner = previous.is_some_and(|p| {
        DETERMINERS_AND_ARTICLES.contains(&p.normalized.as_str())
            || [
                "very", "so", "too", "more", "most", "less", "quite", "really",
            ]
            .contains(&p.normalized.as_str())
    });
    let clause_lead = previous.is_none_or(|p| {
        !p.is_word
            || p.paragraph != token.paragraph
            || CLAUSE_LEADS.contains(&p.normalized.as_str())
            || ADDRESSING.contains(&p.normalized.as_str())
    }) && !after_determiner;
    let boundary = previous.is_none_or(|p| !p.is_word || p.paragraph != token.paragraph);
    // "anoop said hi", "I think anoop said": an unknown word that opens a clause and takes a
    // finite verb is a subject.
    // A damaged word ("someonehad") after a conjunction ("if someonehad called") is no subject.
    let shaped_ok = !shaped
        || boundary
        || previous.is_some_and(|p| {
            [
                "think", "thought", "guess", "hope", "know", "knew", "said", "says", "heard",
                "maybe", "perhaps", "also", "actually",
            ]
            .contains(&p.normalized.as_str())
        });
    if clause_lead
        && shaped_ok
        && next_word.is_some_and(|n| {
            // A damaged subject ("if soeone had called") also precedes an auxiliary, so an
            // auxiliary only counts when the word opens its line or sentence.
            !shaped && boundary && FINITE.contains(&n.normalized.as_str())
                || !FINITE.contains(&n.normalized.as_str())
                    && morphology::verb(&n.normalized).is_some_and(|v| {
                        v.past == n.normalized || !shaped && v.third == n.normalized
                    })
        })
    {
        return true;
    }
    // "aman from design", "aman about the launch"; "to/at/for" only when the word opens its clause.
    if !after_determiner && next_is(&["from", "about"]) || boundary && next_is(&["to", "at", "for"])
    {
        return true;
    }
    // "lunch with farhad yesterday": a damaged-looking word between "with" and a time or place.
    if shaped
        && previous.is_some_and(|p| ["with", "from"].contains(&p.normalized.as_str()))
        && next_is(&[
            "yesterday",
            "today",
            "tomorrow",
            "tonight",
            "later",
            "at",
            "on",
            "in",
            "and",
            "last",
            "this",
            "next",
            "before",
            "after",
            "about",
            "earlier",
        ])
    {
        return true;
    }
    // Below here only a word that is not typo-shaped is a name on weaker evidence.
    if shaped {
        return false;
    }
    // "with aman", "invite aman": a person is the object of a preposition or a verb of contact.
    if word.chars().count() >= 4
        && previous.is_some_and(|p| LEADS.contains(&p.normalized.as_str()))
        && next_word.is_none_or(|n| !DETERMINERS_AND_ARTICLES.contains(&n.normalized.as_str()))
    {
        return true;
    }
    // The last line of the text: one to three words.
    let last_line = line.len() <= 3
        && line
            .iter()
            .all(|t| unknown_alphabetic(t) && !typo_shaped(&t.normalized) || namey(&t.normalized))
        && following.iter().all(|t| t.paragraph == token.paragraph)
        && history.iter().any(|t| t.paragraph != token.paragraph);
    // A greeting target: a whole line of at most two unknown or name-only words.
    last_line
        || line.len() < 3
            && line
                .iter()
                .all(|t| unknown_alphabetic(t) || namey(&t.normalized))
}
/// The greeting, address, title or honorific context before a name ("thanks, aman", "Dr. aman").
fn addressed_by(history: &[Token<'_>], token: &Token<'_>) -> bool {
    lead(history, token, &PUNCT_BEFORE).is_some_and(|p| ADDRESSING.contains(&p.normalized.as_str()))
        || lead(history, token, &["."]).is_some_and(|p| TITLES.contains(&p.normalized.as_str()))
        || looped_in(history)
}
/// Workplace phrases that bring a person into a thread: "looping in X", "loop in X", "adding X".
fn looped_in(history: &[Token<'_>]) -> bool {
    let words: Vec<&str> = history
        .iter()
        .rev()
        .filter(|t| t.is_word)
        .take(2)
        .map(|t| t.normalized.as_str())
        .collect();
    match words.as_slice() {
        ["in", verb, ..] => [
            "loop", "looping", "looped", "bring", "bringing", "brought", "pull", "pulling",
        ]
        .contains(verb),
        [verb, ..] => [
            "adding",
            "tagging",
            "tagged",
            "welcoming",
            "welcome",
            "including",
        ]
        .contains(verb),
        [] => false,
    }
}
/// A lowercase word that is a person's name typed without capitals: listed only as a name, or
/// unknown and name-like in context. Callers must not respell it into a different word.
pub fn lowercase_name(tokens: &[Token<'_>], index: usize) -> bool {
    let token = &tokens[index];
    let word = names::base(&token.normalized);
    token.is_word
        && token
            .surface
            .chars()
            .all(|c| c.is_lowercase() || c == '\'' || c == '’')
        && !names::is_name_typo(word)
        && !names::never_a_name(token.surface)
        // "the tran" and "ot" are damaged common words, whatever the lexicon lists them as.
        && (namey(word)
            && !name_only_typo(word, index.checked_sub(1).map_or("", |i| &tokens[i].normalized))
            || unknown_alphabetic(token)
                && name_like(token, &tokens[..index], &tokens[index + 1..]))
}
/// Whether splitting an unknown word into "a"/"an" + noun/adjective is safe. Names such as
/// "aman" or "anoop" split into real words ("a man"), so the phrase must read as a determiner
/// phrase: the tail is a frequent word (frequency prior 450 is Zipf 4.5, roughly the 2,800 most
/// common words; "man", "lot", "clear", "separate" and "updated" pass, "kit" and "jay" do not)
/// and a noun or adjective, the word before
/// is a verb or preposition (or the split opens a line and more words follow), and the word
/// after is not another unknown, name-only or capitalized word.
fn article_split_ok(
    split: &str,
    token: &Token<'_>,
    prev: &str,
    history: &[Token<'_>],
    following: &[Token<'_>],
) -> bool {
    let mut parts = split.split(' ');
    let (Some(a), Some(tail), None) = (parts.next(), parts.next(), parts.next()) else {
        return true;
    };
    if !["a", "an"].contains(&a) {
        return true;
    }
    let next = following
        .first()
        .filter(|n| n.is_word && n.paragraph == token.paragraph);
    frequency(tail) >= 450
        && flags(tail) & (2 | 8) != 0
        && (ARTICLE_LEAD.contains(&prev) || line_start(history, token) && next.is_some())
        && !next.is_some_and(|n| {
            unknown_alphabetic(n)
                || name_only(&n.normalized)
                || n.surface.chars().next().is_some_and(char::is_uppercase)
        })
}
pub fn suggest(
    token: &Token<'_>,
    dialect: &str,
    previous: Option<&Token<'_>>,
    next: Option<&Token<'_>>,
    history: &[Token<'_>],
    following_context: &[Token<'_>],
) -> Option<String> {
    let word = &token.normalized;
    if token.proper_name
        || token.surface.chars().any(char::is_uppercase)
        || word.len() > 24
        || !word.bytes().all(|b| b.is_ascii_lowercase() || b == b'\'')
    {
        return None;
    }
    fn contextual_word(word: &str) -> &str {
        if known(word) {
            return word;
        }
        let nearby: Vec<_> = [
            "the", "and", "not", "to", "my", "your", "our", "their", "his", "her", "its", "any",
            "some", "will", "with", "before", "after",
        ]
        .into_iter()
        .filter(|w| distance_one(word, w))
        .collect();
        if nearby.len() == 1 { nearby[0] } else { word }
    }
    let prev = contextual_word(previous.map(|t| t.normalized.as_str()).unwrap_or(""));
    let following = contextual_word(
        next.filter(|t| !t.surface.chars().next().is_some_and(char::is_uppercase))
            .map(|t| t.normalized.as_str())
            .unwrap_or(""),
    );
    let next_flags = if following.is_empty() {
        0
    } else if flags(following) != 0 || !following.is_ascii() {
        flags(following)
    } else {
        let mut nearby = HashSet::new();
        if let Some(values) = lexicon().deletes.get(following) {
            nearby.extend(values.iter());
        }
        for deleted in deletions(following) {
            if let Some((w, _)) = lexicon().words.get_key_value(&deleted) {
                nearby.insert(w);
            }
            if let Some(values) = lexicon().deletes.get(&deleted) {
                nearby.extend(values.iter());
            }
        }
        let candidates: Vec<_> = nearby
            .into_iter()
            .filter(|w| distance_one(following, w))
            .collect();
        candidates
            .iter()
            .fold(0, |combined, candidate| combined | flags(candidate))
    };
    // Reviewed short transpositions. Preserve valid interjections and 'to and fro'.
    let short = match word.as_str() {
        "adn" => Some("and"),
        "wsa" => Some("was"),
        "hda" => Some("had"),
        "hsa" => Some("has"),
        "wlil" => Some("will"),
        "wiht" => Some("with"),
        "cna" => Some("can"),
        "nto" => Some("not"),
        "shold" | "sould" => Some("should"),
        "cannt" => Some("cannot"),
        "ot" if function(following)
            || morphology::verb(following).is_some()
            || [
                "everyone",
                "anyone",
                "someone",
                "nobody",
                "everybody",
                "somebody",
            ]
            .contains(&following) =>
        {
            Some("to")
        }
        "fro" if prev != "and" && !following.is_empty() && next.is_some_and(|t| t.is_word) => {
            Some("for")
        }
        "ew" if (morphology::verb(following).is_some_and(|v| morphology::predicate(&v.base))
            && [
                "when", "while", "if", "because", "since", "that", "week", "month", "night", "day",
                ",",
            ]
            .contains(&prev))
            || (["has", "have", "had"].contains(&prev)
                && morphology::verb(following).is_some())
            || [
                "will", "would", "have", "had", "can", "could", "should", "are", "were", "do",
                "did", "look", "need",
            ]
            .contains(&following) =>
        {
            Some("we")
        }
        _ => None,
    };
    if let Some(s) = short {
        return Some(s.into());
    }
    if lexicon().lowercase.contains(word) || names::is_shorthand(word) {
        return None;
    }
    // "jain" is only listed as "Jain": a lowercase name is never respelled into another word.
    if namey(word) && !name_only_typo(names::base(word), prev)
        || name_like(token, history, following_context)
    {
        return None;
    }
    let split = joined(
        word,
        prev,
        following,
        next.is_some_and(|t| t.surface.chars().next().is_some_and(char::is_uppercase)),
        next_flags,
    );
    // "aclear" beside a damaged word waits for the next pass, when "planningand" is "planning
    // and" and the split has a clear anchor.
    let split =
        split.filter(|(_, split)| article_split_ok(split, token, prev, history, following_context));
    if word.len() < 3 {
        return None;
    }
    let lexicon = lexicon();
    let mut candidates = HashSet::new();
    if let Some(values) = lexicon.deletes.get(word) {
        candidates.extend(values.iter().cloned());
    }
    for deleted in deletions(word) {
        if lexicon.words.contains_key(&deleted) {
            candidates.insert(deleted.clone());
        }
        if let Some(values) = lexicon.deletes.get(&deleted) {
            candidates.extend(values.iter().cloned());
        }
    }
    let dialect_flag = if dialect == "british" { 128 } else { 64 };
    let mut candidates: Vec<String> = candidates
        .into_iter()
        // Never offer a name ("rahul" to "raul") or acronym ("neha" to "neh") for a lowercase word.
        .filter(|candidate| {
            distance_one(word, candidate)
                && flags(candidate) & dialect_flag != 0
                && lexicon.lowercase.contains(candidate.as_str())
        })
        // "aman" to "man" or "aclear" to "clear" drops a word's first letter and either loses an
        // article or erases a name; neither is a correction.
        .filter(|candidate| word.strip_prefix('a') != Some(candidate))
        .collect();
    let score = |candidate: &str| -> i32 {
        let mut score = i32::from(morphology::common(candidate)) * 14
            + i32::from(frequency(candidate) / 5)
            + i32::from(transposed(word, candidate)) * 80;
        // Prefer a dictionary compound such as everyone over an incidental
        // adverb + one split when both explain the same damaged token.
        if candidate.ends_with("one")
            && candidate.len() > word.len()
            && split
                .as_ref()
                .is_some_and(|(_, value)| value.ends_with(" one"))
        {
            score += 250;
        }
        let f = flags(candidate);
        if ["am", "is", "are", "was", "were", "be", "been"].contains(&prev) {
            score += i32::from(f & 8 != 0) * 15;
            score += i32::from(
                morphology::verb(candidate)
                    .is_some_and(|v| v.participle == candidate || v.gerund == candidate),
            ) * 35;
        }
        if [
            "can", "could", "may", "might", "should", "must", "will", "would", "did", "does",
            "don't", "doesn't", "didn't", "to",
        ]
        .contains(&prev)
        {
            score +=
                i32::from(morphology::verb(candidate).is_some_and(|v| v.base == candidate)) * 25;
        }
        if ["a", "an", "the", "my", "your", "our", "their"].contains(&prev) {
            score += i32::from(f & 2 != 0 || f & 8 != 0) * 10;
        }
        if ["is", "was", "are", "were"].contains(&following) {
            score += i32::from(f & 2 != 0) * 15;
        }
        score += context::score(prev, candidate) + context::score(candidate, following);
        if known(prev) && known(following) {
            score -= i32::from(frequency(candidate) / 20);
        }
        if candidate.len() > word.len() {
            score += 35;
        }
        if word.len() > candidate.len() && word.get(1..) == Some(candidate) {
            score -= 40;
        }
        if token.pos == "Verb" {
            score += i32::from(
                morphology::verb(candidate).is_some_and(|v| morphology::predicate(&v.base)),
            ) * 35;
            score -= i32::from(function(candidate)) * 50;
        }
        // Prefer grammatical word classes in clear noun and auxiliary slots.
        let noun_slot = [
            "a", "an", "the", "my", "your", "our", "their", "its", "some", "any", "no",
        ]
        .contains(&prev)
            || ["is", "are", "was", "were"].contains(&following)
            || previous.is_some_and(|t| flags(&t.normalized) & (2 | 8) != 0)
                && history.iter().rev().nth(1).is_some_and(|t| {
                    [
                        "a", "an", "the", "teh", "any", "no", "some", "my", "your", "our", "their",
                    ]
                    .contains(&t.normalized.as_str())
                });
        let noun_slot = noun_slot
            && !(prev == "one"
                && history.iter().rev().take(4).any(|t| {
                    ["seen", "heard", "watched", "see", "hear", "watch"]
                        .contains(&t.normalized.as_str())
                }))
            && !(token.pos == "Verb"
                && history.iter().rev().nth(2).is_some_and(|t| {
                    ["before", "after", "when", "while"].contains(&t.normalized.as_str())
                }));
        if noun_slot {
            let adjective_slot = next_flags & 2 != 0 || following == "one";
            score += if f & 2 != 0 || adjective_slot && f & 8 != 0 {
                90
            } else {
                -75
            };
        }
        if prev == "the"
            && history
                .iter()
                .rev()
                .nth(1)
                .is_some_and(|t| t.normalized == "of")
            && history.iter().rev().nth(2).is_some_and(|t| {
                ["each", "one", "either", "both", "several", "many", "some"]
                    .contains(&t.normalized.as_str())
            })
            && f & 16 != 0
        {
            score += 160;
        }
        if flags(following) & 16 != 0 && ["any", "no", "some", "the", "a", "an"].contains(&prev) {
            score += i32::from(f & 8 != 0) * 100;
        }
        let auxiliary_slot = history.iter().rev().take(3).any(|t| {
            [
                "did", "does", "can", "could", "must", "should", "will", "would",
            ]
            .contains(&t.normalized.as_str())
        });
        if auxiliary_slot && ["a", "an", "the"].contains(&following) {
            score +=
                i32::from(morphology::verb(candidate).is_some_and(|v| v.base == candidate)) * 45;
            score -= i32::from(function(candidate)) * 70;
        }
        if following == "by"
            && morphology::verb(candidate).is_some_and(|v| {
                ["want", "waive", "waste", "raise", "revise", "protect"].contains(&v.base.as_str())
            })
            && !["was", "were", "is", "are", "be", "been"].contains(&prev)
        {
            score -= 310;
        }
        if word.chars().next() != candidate.chars().next() {
            score -= 35;
        }
        // Topic and argument preferences only rank unknown-word candidates. They do
        // not replace valid words or prescribe a reference paragraph.
        let nearby_topic = |topics: &[&str]| {
            history
                .iter()
                .rev()
                .take(18)
                .chain(following_context.iter().take(8))
                .any(|t| {
                    topics.contains(&t.normalized.as_str())
                        || !known(&t.normalized)
                            && topics
                                .iter()
                                .any(|topic| distance_one(&t.normalized, topic))
                })
        };
        let topical = match candidate {
            "stall" => nearby_topic(&["fruit", "vegetable", "market", "vendor"]),
            "cakes" => nearby_topic(&["bakery", "baker", "pastry"]),
            "chairs" => nearby_topic(&["furniture", "seating", "dining"]),
            "drums" => nearby_topic(&["music", "band", "percussion"]),
            "concert" => nearby_topic(&["charity", "music", "orchestra"]),
            "theater" => ["opening", "stage", "performance", "audience"].contains(&following),
            "printer" => nearby_topic(&["battery", "print", "ink", "paper", "cartridge"]),
            "spare" => {
                ["folders", "folder", "copies", "parts", "keys", "battery"]
                    .iter()
                    .any(|w| *w == following || !known(following) && distance_one(following, w))
                    || ["foldersin", "folderin", "folderand", "foldersand"].contains(&following)
            }
            "delay" => following_context.iter().take(3).any(|t| {
                ["meeting", "appointment", "departure", "event"]
                    .iter()
                    .any(|w| {
                        *w == t.normalized
                            || !known(&t.normalized) && distance_one(&t.normalized, w)
                    })
            }),
            "improves" => ["weather", "health", "condition", "quality"].contains(&prev),
            "starts" => ["meeting", "class", "event", "concert", "session", "match"]
                .iter()
                .any(|w| *w == prev || !known(prev) && distance_one(prev, w)),
            "dates" => prev == "the" && nearby_topic(&["check", "schedule", "calendar", "confirm"]),
            "bought" => {
                nearby_topic(&["store", "shop", "market", "purchase", "bakery"])
                    && !following_context
                        .iter()
                        .take(6)
                        .any(|t| ["to", "into"].contains(&t.normalized.as_str()))
            }
            "brought" => following_context
                .iter()
                .take(6)
                .any(|t| ["to", "into", "toward"].contains(&t.normalized.as_str())),
            "store" => nearby_topic(&["hardware", "clothing", "grocery", "furniture", "book"]),
            "earlier" => {
                next.is_some_and(|t| t.surface == ",")
                    && nearby_topic(&["had", "prepared", "finished", "arrived"])
            }
            "every" => {
                ["morning", "evening", "day", "night", "week", "month"].contains(&following)
                    || following_context
                        .first()
                        .is_some_and(|t| distance_one(&t.normalized, "morning"))
            }
            "fewer" => next_flags & 2 != 0 && following.ends_with('s'),
            "ready" => {
                ["is", "was", "are", "were"].contains(&prev)
                    && (following.is_empty() || ["for", "to"].contains(&following))
            }
            _ => false,
        };
        if topical {
            score += 230;
        }
        if ["revised", "revise"].contains(&candidate)
            && !noun_slot
            && following_context.iter().take(3).any(|t| {
                [
                    "brief",
                    "record",
                    "review",
                    "memo",
                    "plan",
                    "statement",
                    "notice",
                    "draft",
                    "report",
                    "document",
                    "letter",
                    "summary",
                ]
                .contains(&t.normalized.as_str())
            })
        {
            score += 190;
        }
        // Reviewed semantic constraints disambiguate otherwise grammatical candidates.
        if candidate == "plants"
            && history
                .iter()
                .rev()
                .take(9)
                .any(|t| ["garden", "nursery", "seed", "seeds"].contains(&t.normalized.as_str()))
        {
            score += 50;
        }
        if !noun_slot
            && ["revise", "review", "edit", "write"].contains(&candidate)
            && following_context.iter().take(3).any(|t| {
                [
                    "report",
                    "proposal",
                    "schedule",
                    "application",
                    "summary",
                    "document",
                    "draft",
                    "letter",
                    "manuscript",
                ]
                .contains(&t.normalized.as_str())
            })
        {
            score += 160;
        }
        if candidate == "stationery"
            && ["shop", "store", "supplies", "items", "paper", "pens"].contains(&following)
        {
            score += 160;
        }
        if candidate == "event"
            && ["museum", "gallery", "festival", "school", "community"].contains(&prev)
        {
            score += 130;
        }
        // A superlative fits a definite determiner followed by "one".
        if candidate.ends_with("est") && prev == "the" && following == "one" {
            score += 80;
        }
        // Preserve local past narration when recovering a damaged finite verb.
        let past_context = history.iter().rev().take(20).any(|t| {
            ["yesterday", "had", "ago"].contains(&t.normalized.as_str())
                || morphology::verb(&t.normalized).is_some_and(|v| {
                    v.past == t.normalized && v.past != v.base && morphology::predicate(&v.base)
                })
        });
        let preceding_finite = history
            .iter()
            .rev()
            .take_while(|t| {
                ![
                    ".", "?", "!", ",", "before", "after", "when", "while", "that", "and", "but",
                    "so",
                ]
                .contains(&contextual_word(&t.normalized))
            })
            .any(|t| {
                morphology::verb(&t.normalized).is_some_and(|v| {
                    morphology::predicate(&v.base)
                        && (v.past == t.normalized || v.third == t.normalized)
                        && v.base != t.normalized
                })
            });
        if past_context
            && (!noun_slot
                || history.iter().rev().nth(2).is_some_and(|t| {
                    ["before", "after", "when", "while"].contains(&contextual_word(&t.normalized))
                }))
            && !preceding_finite
            && (token.pos == "Verb" || previous.is_some_and(|t| flags(&t.normalized) & 2 != 0))
            && ![
                "can", "could", "may", "might", "will", "would", "should", "must", "did", "does",
                "to",
            ]
            .contains(&prev)
            && morphology::verb(candidate).is_some_and(|v| v.past == candidate && v.past != v.base)
        {
            score += 180;
        }
        // Temporal connectors can follow a noun phrase; a finite verb cannot.
        if ["after", "before", "during"].contains(&candidate)
            && ["a", "an", "the"].contains(&following)
            && (preceding_finite || previous.is_some_and(|t| flags(&t.normalized) & 2 != 0))
        {
            score += 180;
        }
        score
    };
    candidates.sort_by(|a, b| score(b).cmp(&score(a)).then_with(|| a.cmp(b)));
    if let Some((split_score, split)) = split.as_ref()
        && candidates.first().is_none_or(|c| *split_score > score(c))
    {
        return Some(split.clone());
    }
    if candidates.len() == 1
        || (candidates.len() > 1
            && score(&candidates[0]) >= 40
            && score(&candidates[0]) > score(&candidates[1]))
    {
        candidates.first().cloned()
    } else {
        None
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn one_edit() {
        assert!(distance_one("teh", "the"));
        assert!(distance_one("mesage", "message"));
        assert!(!distance_one("mesage", "me sage"));
        assert!(!distance_one("a", "abc"));
    }
    #[test]
    fn name_only_words_keep_their_spelling() {
        let tokens = crate::tokenizer::tokenize("ask jain about it", &[]);
        assert!(name_only("jain") && lowercase_name(&tokens, 1));
        // A determiner or a swap of a frequent word shows the entry is a damaged common word.
        assert!(
            name_only_typo("tran", "the")
                && name_only_typo("ot", "")
                && !name_only_typo("jain", "")
        );
    }
    #[test]
    fn dictionary_assets() {
        assert!(known("message"));
        assert!(known("configuration"));
    }
    #[test]
    fn system_lexicon_names_yield_only_to_clear_typos() {
        // Typos that are also surnames (Tran, Appel) or one letter from a very common word.
        assert!(hinted_name_is_typo("tran", "the"));
        assert!(hinted_name_is_typo("neds", "she"));
        assert!(hinted_name_is_typo("appel", "an"));
        assert!(hinted_name_is_typo("aquire", "to"));
        // Real names keep their protection.
        for name in ["rakesh", "aman", "minji", "hao", "priya", "jatin"] {
            assert!(!hinted_name_is_typo(name, "with"), "{name}");
        }
    }
}
