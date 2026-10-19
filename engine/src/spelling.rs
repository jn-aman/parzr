//! Inflection-aware deletion index with deterministic context ranking.
use crate::table::Table;
use crate::tokenizer::Token;
use crate::{context, morphology, names};
use std::{collections::HashSet, sync::OnceLock};
/// The spelling lexicon and its deletion index, built by `build.rs` from `rules/lexicon.json`
/// and `rules/frequency.json` and read in place (`table.rs`).
struct Lexicon {
    /// Lowercase word: flags (low byte) and whether the word is an ordinary lowercase entry
    /// (bit 8); then the arena offset and length of its canonical casing ("McDonald", "iPhone").
    words: Table,
    /// A common word with one byte deleted: the words it comes from (entry numbers in `words`,
    /// sorted by word).
    deletes: Table,
}
impl Lexicon {
    fn flags(&self, lower: &str) -> Option<u8> {
        self.words
            .find(lower)
            .map(|e| self.words.value_u32(e, 0) as u8)
    }
    fn contains(&self, lower: &str) -> bool {
        self.words.find(lower).is_some()
    }
    /// The dictionary's own copy of `lower`.
    fn word(&self, lower: &str) -> Option<&'static str> {
        self.words.find(lower).map(|e| self.words.key(e))
    }
    /// An entry spelled in lowercase in the dictionary ("hope", "rose"), not only as a name.
    fn ordinary(&self, word: &str) -> bool {
        self.words
            .find(word)
            .is_some_and(|e| self.words.value_u32(e, 0) & 0x100 != 0)
    }
    fn canonical(&self, lower: &str) -> Option<&'static str> {
        let entry = self.words.find(lower)?;
        let len = self.words.value_u32(entry, 2) as usize;
        (len > 0).then(|| {
            self.words
                .arena_str(self.words.value_u32(entry, 1) as usize, len)
        })
    }
    /// The common words that `deleted` is one deleted byte of, in sorted order.
    fn deletes(&self, deleted: &str) -> impl Iterator<Item = &'static str> + use<> {
        let (words, deletes) = (self.words, self.deletes);
        let (start, count) = deletes.find(deleted).map_or((0, 0), |e| {
            (
                deletes.value_u32(e, 0) as usize,
                deletes.value_u32(e, 1) as usize,
            )
        });
        (start..start + count).map(move |i| words.key(deletes.extra(i) as usize))
    }
}
pub(crate) fn frequency(word: &str) -> u16 {
    static FREQUENCIES: OnceLock<Table> = OnceLock::new();
    let table = FREQUENCIES.get_or_init(|| Table::new(crate::tables::get().frequency));
    table.find(word).map_or(0, |e| table.value_u32(e, 0) as u16)
}
fn lexicon() -> &'static Lexicon {
    static LEXICON: OnceLock<Lexicon> = OnceLock::new();
    LEXICON.get_or_init(|| Lexicon {
        words: Table::new(crate::tables::get().lexicon),
        deletes: Table::new(crate::tables::get().deletes),
    })
}
fn deletions(word: &str) -> HashSet<String> {
    (0..word.len())
        .map(|i| format!("{}{}", &word[..i], &word[i + 1..]))
        .collect()
}
pub fn known(word: &str) -> bool {
    lexicon().contains(&word.to_lowercase())
}
pub fn flags(word: &str) -> u8 {
    lexicon().flags(&word.to_lowercase()).unwrap_or(0)
}
pub fn name_only(word: &str) -> bool {
    known(word) && !lexicon().ordinary(word)
}
/// An ordinary lowercase dictionary word ("hope", "rose"), as opposed to a name or acronym.
pub fn ordinary(word: &str) -> bool {
    lexicon().ordinary(word)
}
/// "mcdonald" -> "McDonald", "iphone" -> "iPhone": the dictionary spelling of a word that is not
/// an ordinary lowercase word.
pub fn canonical_case(lower: &str) -> Option<&'static str> {
    lexicon().canonical(lower)
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
pub(crate) const COPULAS: [&str; 15] = [
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
    let unknown = !lexicon().ordinary(word);
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
pub(crate) fn swaps_to_common(word: &str) -> bool {
    let bytes = word.as_bytes();
    word.is_ascii()
        && (0..bytes.len().saturating_sub(1)).any(|i| {
            let mut swapped = bytes.to_vec();
            swapped.swap(i, i + 1);
            let swapped = String::from_utf8_lossy(&swapped).into_owned();
            swapped != word && ordinary(&swapped) && frequency(&swapped) >= 600
        })
}
/// A short unknown word ("thi", "ar", "teh", "ws") that one common slip (a dropped, doubled,
/// swapped or neighbouring key; see `slips_from`) makes of one of the ~200 most frequent words.
/// Names of two or three letters ("anh", "raj", "sam") are no such slip.
pub(crate) fn short_slip(word: &str) -> bool {
    (2..=3).contains(&word.len())
        && word.bytes().all(|b| b.is_ascii_lowercase())
        // Two letters listed only as a symbol or acronym ("Th", "AR") are no word in lowercase.
        && !ordinary(word)
        && (word.len() <= 2 || !known(word))
        && !names::is_bundled_name(word)
        // Two letters take only a cheap slip ("Bo" is no slip of "be").
        && if word.len() <= 2 { slips_within(word, 0.5) } else { slips_from(word) }
            .iter()
            .any(|c| frequency(c) >= 600)
}
/// A capitalized sentence opener that is a slip, not a name: a short slip (`short_slip`), or an
/// unknown word of four or more letters one cheap slip from a frequent word ("Trhe", "Thegy").
pub(crate) fn opening_slip(word: &str) -> bool {
    short_slip(word)
        || word.len() >= 4
            && word.bytes().all(|b| b.is_ascii_lowercase())
            && !known(word)
            && !names::is_bundled_name(word)
            && slips_from(word).iter().any(|c| frequency(c) >= 500)
}
/// Ways to read `word` as two words seen together at least ten million times in the pair table
/// ("can you", "out of", "i am"), each piece two letters or more ("I" may open), as
/// (left, right, log10 pair count).
fn glued_pairs(word: &str) -> Vec<(&str, &str, f64)> {
    if word.len() < 4 || !word.bytes().all(|b| b.is_ascii_lowercase() || b == b'\'') {
        return vec![];
    }
    let piece = |p: &str| ordinary(p) || p.contains('\'') && known(p);
    (1..word.len() - 1)
        .filter(|&i| word.is_char_boundary(i))
        .map(|i| word.split_at(i))
        .filter(|(a, b)| (a.len() >= 2 || *a == "i") && b.len() >= 2 && piece(a) && piece(b))
        .filter_map(|(a, b)| {
            let n = context::count(a, b);
            (n >= 10_000_000).then(|| (a, b, (n as f64).log10()))
        })
        .collect()
}
/// Whether `word` reads as two very common neighbouring words typed without the space.
pub(crate) fn glued_pair(word: &str) -> bool {
    !known(word) && !glued_pairs(word).is_empty()
}
/// The likeliest two-word reading of a glued `word` between `before` and `after` (either may be
/// empty), when every neighbour present was seen beside it: "canyou" is "can you".
fn common_split(word: &str, before: &str, after: &str) -> Option<String> {
    if known(word) {
        return None;
    }
    // "ofice" is "office", not "of ice"; "weas" is "was": a likely one-word slip is the likelier
    // reading when it makes the likelier sentence.
    let fix = slips_within(word, 1.0)
        .into_iter()
        .filter(|c| frequency(c) >= 300)
        .map(|c| phrase_logp(&[before, &c, after]) - slip_cost(word, &c))
        .fold(f64::NEG_INFINITY, f64::max);
    glued_pairs(word)
        .into_iter()
        .filter(|(a, b, _)| {
            (before.is_empty() || context::count(before, a) > 0)
                && (after.is_empty() || context::count(b, after) > 0)
        })
        .map(|(a, b, _)| (phrase_logp(&[before, a, b, after]) - 0.5, a, b))
        .max_by(|x, y| x.0.total_cmp(&y.0))
        .filter(|(split, _, _)| *split > fix)
        .map(|(_, a, b)| {
            let a = if a == "i" || a.starts_with("i'") {
                format!("I{}", &a[1..])
            } else {
                a.to_string()
            };
            format!("{a} {b}")
        })
}
/// A capitalized sentence opener the system tagger guesses is a name, that is really a slip: a
/// doubled, dropped or swapped key (cost 0.3 or less) away from one of the ~200 most frequent
/// words, which the next word was seen after ("Wwe watched", "Cna we", "Thi is"). A name the tagger
/// knows next to a word it does not fit ("Thi said", "Anh is", "Hoa is") keeps its spelling.
pub(crate) fn opening_name_slip(tokens: &[Token<'_>], index: usize) -> bool {
    let token = &tokens[index];
    let word = token.normalized.as_str();
    let next = tokens
        .get(index + 1)
        .filter(|n| n.is_word && n.sentence == token.sentence && ordinary(&n.normalized))
        .map(|n| n.normalized.as_str());
    let mut letters = token.surface.chars();
    letters.next().is_some_and(|c| c.is_ascii_uppercase())
        && letters.all(|c| c.is_ascii_lowercase())
        && line_start(&tokens[..index], token)
        && opening_slip(word)
        && next.is_some_and(|next| {
            slips_from(word).iter().any(|c| {
                frequency(c) >= 600 && doubled_or_swapped(word, c) && context::count(c, next) > 0
                    // "Thaks for", "Apologis for": one letter dropped from a frequent word that
                    // makes a very common pair with the next word (a name one letter short of
                    // such a word is rare).
                    // A name is usually followed by its verb or "and" ("Stans and he", "Bran said").
                    || frequency(c) >= 400
                        && c.len() >= 5
                        && word.len() + 1 == c.len()
                        && !["and", "or"].contains(&next)
                        && crate::morphology::verb(next).is_none()
                        && context::count(c, next) >= DROPPED_PAIR
            })
        })
}
/// Pair count above which a dropped-letter opener is read as the frequent word ("thanks for").
const DROPPED_PAIR: u64 = 1_000_000;
/// `typed` is `intended` with one key pressed twice ("wwe") or two neighbouring keys swapped
/// ("cna"): slips that leave no name-like shape, unlike a dropped letter ("Yu", "Tis").
fn doubled_or_swapped(typed: &str, intended: &str) -> bool {
    let (t, w) = (typed.as_bytes(), intended.as_bytes());
    if t.len() == w.len() {
        return transposed(typed, intended);
    }
    t.len() == w.len() + 1
        && (0..t.len()).any(|i| {
            t[..i] == w[..i]
                && t[i + 1..] == w[i..]
                && (i > 0 && t[i - 1] == t[i] || t.get(i + 1) == Some(&t[i]))
        })
}
/// Whether a cheap slip of a frequent word (`opening_slip`) fits between the neighbouring words:
/// some frequent slip target was seen beside every ordinary neighbour in the same sentence, and
/// there is at least one such neighbour.
pub(crate) fn slip_fits(
    word: &str,
    previous: Option<&Token<'_>>,
    next: Option<&Token<'_>>,
    token: &Token<'_>,
) -> bool {
    // A listed name ("Mme", "Ann") counts too: "asked mme to help" is "me".
    if !(opening_slip(word)
        || word.len() >= 2
            && word.bytes().all(|b| b.is_ascii_lowercase())
            && !ordinary(word)
            && !names::is_bundled_name(word))
    {
        return false;
    }
    fn side<'a>(t: Option<&'a Token<'_>>, sentence: usize) -> &'a str {
        t.filter(|t| t.is_word && t.sentence == sentence && ordinary(&t.normalized))
            .map_or("", |t| t.normalized.as_str())
    }
    // A neighbour that is no ordinary word ("sai raju", "rituparna sen") is more of the name.
    let odd = |t: Option<&Token<'_>>| {
        t.is_some_and(|t| {
            t.is_word
                && t.sentence == token.sentence
                && !ordinary(&t.normalized)
                && t.normalized != "i"
                && !t.normalized.starts_with("i'")
        })
    };
    if odd(previous) || odd(next) {
        return false;
    }
    let (before, after) = (side(previous, token.sentence), side(next, token.sentence));
    (!before.is_empty() || !after.is_empty())
        && slips_from(word).iter().any(|c| {
            frequency(c) >= 500
                && c != before
                && c != after
                && (before.is_empty() || context::count(before, c) > 0)
                && (after.is_empty() || context::count(c, after) > 0)
        })
}
/// A slip that leaves no doubt: a doubled, dropped, swapped or neighbouring key (cost 0.5 or less)
/// of one of the ~200 most frequent words ("thegy" for "they"). "hari" (hair) and "bo" (be) are not.
fn strong_slip(word: &str) -> bool {
    !ordinary(word) && slips_within(word, 0.6).iter().any(|c| frequency(c) >= 600)
}
/// The most frequent ordinary word (frequency prior at least 400) one cheap slip from `word`.
pub(crate) fn cheap_fix(word: &str) -> Option<String> {
    slips_from(word)
        .into_iter()
        .filter(|c| frequency(c) >= 400)
        .max_by_key(|c| (frequency(c), std::cmp::Reverse(c.clone())))
}
/// Ordinary words one cheap slip (cost at most 0.5) from `word`, and the ~35 most frequent words
/// also one neighbouring key away on the first letter ("ghe" for "the").
fn slips_from(word: &str) -> Vec<String> {
    slips_within(word, 1.0)
        .into_iter()
        .filter(|c| slip_cost(word, c) <= 0.5 || frequency(c) >= 650)
        .collect()
}
/// Ordinary words one edit from `word` whose slip costs at most `max_cost` (`slip_cost`).
fn slips_within(word: &str, max_cost: f64) -> Vec<String> {
    if word.is_empty() || !word.bytes().all(|b| b.is_ascii_lowercase()) {
        return vec![];
    }
    let lexicon = lexicon();
    let mut near: HashSet<String> = HashSet::new();
    near.extend(lexicon.deletes(word).map(String::from));
    for deleted in deletions(word) {
        if lexicon.ordinary(&deleted) {
            near.insert(deleted.clone());
        }
        near.extend(lexicon.deletes(&deleted).map(String::from));
    }
    near.into_iter()
        .filter(|c| lexicon.ordinary(c) && distance_one(word, c) && slip_cost(word, c) <= max_cost)
        .collect()
}
pub(crate) fn typo_shaped(word: &str) -> bool {
    edit_shaped(word) || glued_shaped(word)
}
/// One adjacent swap of a frequent word, or one letter from a frequent word of 6+ letters (one
/// wrong letter needs 7+): the typo shapes of `typo_shaped` without the run-together words.
pub(crate) fn edit_shaped(word: &str) -> bool {
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
    false
}
/// Two frequent words run together ("farhad" is "far had").
fn glued_shaped(word: &str) -> bool {
    let frequent = |w: &str| known(w) && frequency(w) >= 400;
    if !word.is_ascii() || word.len() < 4 {
        return false;
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
                swapped != word && lexicon().ordinary(&swapped) && frequency(&swapped) >= 500
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
            // A day or month ("Friday, so please") lists no person.
            || typed_capital(neighbor) && !opens_line && !names::never_a_name(neighbor.surface))
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
/// Common Roman Hindi words that are not English words: Hinglish is written, not misspelled.
const HINGLISH: &[&str] = &[
    "aa", "aaj", "aana", "aao", "aap", "aapka", "abhi", "accha", "acha", "achha", "aise", "aloo",
    "apna", "apne", "arey", "arre", "aur", "baad", "baat", "baba", "badhai", "bahot", "bahut",
    "baje", "bas", "bata", "batao", "behen", "beta", "beti", "bhabhi", "bhai", "bhaisaab",
    "bhaiya", "bhaiyya", "bhej", "bheje", "bhejo", "bhi", "bhool", "bilkul", "bohat", "bohot",
    "bolo", "chaat", "chahiye", "chahta", "chahti", "chal", "chala", "chalega", "chalein", "chalo",
    "chinta", "dekh", "dekha", "dekhna", "dekho", "dekhte", "dena", "dhyan", "didi", "diya",
    "dost", "ek", "ekdum", "galat", "garmi", "gaya", "gayi", "ghar", "haa", "haan", "hai", "hain",
    "haina", "hoga", "hoge", "hogi", "honge", "hoon", "hua", "hue", "hui", "hum", "humein",
    "humne", "isko", "itna", "jaana", "jaao", "jaise", "jaldi", "jaunga", "jayega", "ji", "jo",
    "jugaad", "ka", "kaafi", "kaam", "kab", "kahan", "kahin", "kaisa", "kaise", "kal", "kamaal",
    "karega", "karenge", "karna", "karo", "karte", "kaun", "ke", "kha", "khana", "ki", "kitna",
    "kitne", "kiya", "kiye", "koi", "kuch", "kya", "kyon", "kyonki", "kyu", "kyun", "kyunki",
    "ladoo", "laga", "lagega", "lagi", "lagta", "lekin", "liya", "maine", "mat", "matlab", "maza",
    "mein", "mera", "mere", "meri", "milte", "mujhe", "na", "nahi", "nahin", "nai", "ne", "nikal",
    "nikalna", "paas", "paisa", "pakka", "paratha", "pata", "pe", "peene", "pehle", "phir", "pura",
    "purana", "raha", "rahe", "rahi", "rakhna", "ruko", "sab", "sabko", "sabse", "sahi", "samajh",
    "samjha", "samjho", "se", "shaadi", "sirf", "sunna", "suno", "tak", "tera", "teri", "tha",
    "theek", "thi", "thik", "thoda", "thodi", "toh", "tujhe", "tumhara", "tumhe", "tumne", "unka",
    "usko", "usne", "vasool", "wah", "wahan", "wahi", "waisa", "waise", "wala", "wale", "wali",
    "woh", "wohi", "yaar", "yahan", "yahi", "yeh", "zyada",
];
/// Common Indian English vocabulary (food, kinship, culture) that no English dictionary lists: never a typo.
const INDIAN: &[&str] = &[
    "achar",
    "amma",
    "appa",
    "ashram",
    "aunty",
    "babu",
    "bazaar",
    "bhajan",
    "bhaji",
    "bindi",
    "biryani",
    "chacha",
    "chachi",
    "chai",
    "chapati",
    "chappal",
    "chole",
    "chowk",
    "chutney",
    "crore",
    "dabba",
    "dadi",
    "dal",
    "desi",
    "dhaba",
    "dharma",
    "dhoti",
    "dosa",
    "dupatta",
    "ghee",
    "gobi",
    "gulab",
    "guru",
    "halwa",
    "holi",
    "idli",
    "jalebi",
    "kebab",
    "kheer",
    "kirtan",
    "kulfi",
    "kurta",
    "lakh",
    "lakhs",
    "lassi",
    "lehenga",
    "mandir",
    "mantra",
    "masala",
    "matar",
    "mausi",
    "mehendi",
    "mehndi",
    "mithai",
    "naan",
    "nani",
    "paise",
    "pakora",
    "panchayat",
    "pandit",
    "paneer",
    "papad",
    "poha",
    "pooja",
    "prasad",
    "puja",
    "raita",
    "rajma",
    "rakhi",
    "rasam",
    "roti",
    "sabzi",
    "sadhu",
    "sahib",
    "salwar",
    "sambar",
    "samosa",
    "saree",
    "sari",
    "swami",
    "tabla",
    "thali",
    "tiffin",
    "tikka",
    "upma",
    "uttapam",
    "vada",
];
/// A Hinglish word ("yaar", "karo"), never a typo or a proper noun.
pub fn hinglish(word: &str) -> bool {
    HINGLISH.binary_search(&word).is_ok()
}
/// Short Roman Hindi words that stand alone in English chat ("bas, that's it", "ok ji").
const HINGLISH_ALONE: [&str; 5] = ["bas", "haa", "ji", "na", "wah"];
/// Whether `tokens[index]` is Roman Hindi here. A short Hinglish word ("thi", "aur", "se") is
/// also a slip of a frequent English word ("this", "our", "see"): alone in an English sentence it
/// is a typo, and it is Roman Hindi only beside other Roman Hindi.
pub fn roman_hindi(tokens: &[Token<'_>], index: usize) -> bool {
    let word = tokens[index].normalized.as_str();
    hinglish(word)
        && (word.len() > 3 || HINGLISH_ALONE.contains(&word) || hindi_beside(tokens, index))
}
/// Another Roman Hindi word within four words of `tokens[index]`, in the same paragraph.
fn hindi_beside(tokens: &[Token<'_>], index: usize) -> bool {
    tokens
        .iter()
        .enumerate()
        .skip(index.saturating_sub(4))
        .take(9)
        .any(|(j, t)| {
            j != index
                && t.paragraph == tokens[index].paragraph
                && hinglish(&t.normalized)
                && t.normalized != "thik"
        })
}
/// Chat spellings people type on purpose ("lil", "wanna", "imma"): a register, not a slip, so Fix
/// never respells them.
pub(crate) fn chat(word: &str) -> bool {
    [
        "abt", "bday", "bruh", "cmon", "convo", "coz", "cya", "dunno", "gimme", "gonna", "gotta",
        "ima", "imma", "kinda", "lemme", "lil", "luv", "nvm", "obvi", "outta", "probs", "sorta",
        "srsly", "tho", "thru", "totes", "wanna", "whatcha", "yall", "yup",
    ]
    .contains(&word)
}
/// Negative contractions without their apostrophe and the positive word each one negates.
const NEGATIVES: [(&str, &str, &str); 17] = [
    ("cant", "can't", "can"),
    ("dont", "don't", "do"),
    ("didnt", "didn't", "did"),
    ("doesnt", "doesn't", "does"),
    ("isnt", "isn't", "is"),
    ("arent", "aren't", "are"),
    ("wasnt", "wasn't", "was"),
    ("werent", "weren't", "were"),
    ("havent", "haven't", "have"),
    ("hasnt", "hasn't", "has"),
    ("hadnt", "hadn't", "had"),
    ("couldnt", "couldn't", "could"),
    ("wouldnt", "wouldn't", "would"),
    ("shouldnt", "shouldn't", "should"),
    ("mustnt", "mustn't", "must"),
    ("neednt", "needn't", "need"),
    ("wont", "won't", "won"),
];
/// The negative contraction an unknown word is a slip of, when the same slip could also have come
/// from the positive word ("canf": "cant" or "can"; "didn": "didnt" or "did"): reading it as the
/// positive would silently reverse the sentence.
fn kept_negation(word: &str) -> Option<String> {
    if word.len() < 4 || known(word) {
        return None;
    }
    // The negative must be at least as likely a slip: "cann" is a doubled key of "can".
    NEGATIVES
        .iter()
        .find(|(bare, _, positive)| {
            word != *bare
                && word.starts_with(positive)
                && distance_one(word, bare)
                && distance_one(word, positive)
                && typo_cost(word, bare) <= typo_cost(word, positive)
        })
        .map(|(_, negative, _)| (*negative).to_string())
}
/// Whether a result drops the negation the typed word carries ("didnt" read as "did").
fn drops_negation(word: &str, result: &str) -> bool {
    // A slip of a negative written without its apostrophe ("dosnt", "wouldnt") read as the
    // positive it negates ("does", "would") when the negative is the likelier slip; "wesnt" read
    // as "went" negates nothing, and "canj" is "can" with a neighbouring key.
    NEGATIVES.iter().any(|(bare, _, positive)| {
        (*bare == word || distance_one(word, bare))
            && result == *positive
            && typo_cost(word, bare) <= typo_cost(word, positive)
    })
}
/// A common prefix on an ordinary word ("refax", "preschedule", "unshare", "multiuser"): a word
/// formed on purpose, not a slip.
fn prefixed(word: &str) -> bool {
    [
        "re", "pre", "non", "multi", "sub", "over", "under", "mis", "post", "anti", "inter",
        "semi", "super", "self",
    ]
    .iter()
    .any(|p| {
        word.strip_prefix(p)
            .is_some_and(|rest| rest.len() >= 3 && ordinary(rest) && frequency(rest) >= 300)
    })
}
/// The day or month name (lowercase) that `word` is one or two cheap slips of ("wenesday",
/// "thurday"); short words need cheaper slips, so names like "Junie" or "Monda" stay.
pub(crate) fn calendar_word_slip(word: &str) -> Option<&'static str> {
    const CALENDAR: [&str; 18] = [
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
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
    ];
    if word.len() < 5 || !word.bytes().all(|b| b.is_ascii_lowercase()) || known(word) {
        return None;
    }
    let near: Vec<&str> = CALENDAR
        .iter()
        .copied()
        .filter(|day| {
            osa_within(word.as_bytes(), day.as_bytes(), 2)
                && typo_cost(word, day) <= 0.35 * word.len() as f64
        })
        .collect();
    match near[..] {
        [day] => Some(day),
        _ => None,
    }
}
/// A capitalized day or month name with one or two cheap slips ("Wenesday" is "Wednesday").
pub(crate) fn calendar_slip(token: &Token<'_>) -> Option<String> {
    let mut letters = token.surface.chars();
    if token.system_known
        || !letters.next().is_some_and(|c| c.is_ascii_uppercase())
        || !letters.all(|c| c.is_ascii_lowercase())
    {
        return None;
    }
    let day = calendar_word_slip(&token.normalized)?;
    let mut chars = day.chars();
    chars
        .next()
        .map(|c| c.to_uppercase().collect::<String>() + chars.as_str())
}
/// Acronyms, product codes and company names people type in lowercase ("aws", "hcl", "gcp"):
/// sorted for binary search.
const ACRONYMS: [&str; 136] = [
    "aks", "api", "apis", "aws", "bba", "bcom", "bpo", "btech", "cad", "cdn", "ceo", "cfo", "cgpa",
    "ci", "cicd", "cli", "cmo", "coo", "cpu", "crm", "css", "csv", "cto", "cv", "dba", "dbms",
    "dm", "dns", "docx", "dpi", "ecs", "eks", "emi", "erp", "eta", "evp", "faq", "faqs", "ftp",
    "gcp", "gdpr", "gke", "gmat", "gpa", "gpu", "gre", "grpc", "gst", "gui", "hcl", "hdd", "hdfc",
    "hdmi", "hod", "hr", "html", "http", "https", "iaas", "iam", "ibm", "icici", "ide", "ielts",
    "ifsc", "imap", "ios", "irctc", "isro", "jdk", "jre", "json", "jvm", "jwt", "kpmg", "llm",
    "llms", "lms", "mba", "mcq", "mtech", "mvc", "mvp", "mysql", "neft", "nlp", "nosql", "npm",
    "nvm", "oauth", "ocr", "okta", "orm", "paas", "pdf", "pdfs", "pnpm", "ppt", "pptx", "pwc",
    "qa", "rds", "rpc", "rtgs", "saas", "sbi", "sdk", "sdks", "seo", "sftp", "smtp", "sns", "sql",
    "sqs", "ssd", "ssh", "ssl", "svg", "svp", "tcp", "tcs", "tls", "toefl", "tsx", "udp", "ui",
    "upi", "url", "urls", "usb", "ux", "vpc", "vpn", "wipro", "xlsx", "yaml",
];
/// A listed acronym, product code or company name typed in lowercase ("aws", "hcl", "gcp"):
/// respelling one ("aws" to "as") breaks a name.
pub(crate) fn acronym(word: &str) -> bool {
    ACRONYMS.binary_search(&word).is_ok()
}
/// Whether a short word without a vowel ("hcl", "ppt", "frm") may become `choice`: only by
/// adding letters or by a neighbouring key in place of a vowel, to make a frequent word ("frm" is
/// "from", "thw" is "the", "cqll" is "call"), never by dropping a letter or changing one for a
/// far key ("hcl" is no "cl", "jvm" no "jam").
fn vowelless_slip(word: &str, choice: &str) -> bool {
    let mut rest = choice.bytes();
    let added = choice.len() > word.len() && word.bytes().all(|b| rest.any(|c| c == b));
    let neighbour = choice.len() == word.len() && slip_cost(word, choice) <= 1.0;
    (added || neighbour) && frequency(choice) >= 400
}
/// Words that must stay as typed: Roman Hindi, Indian English vocabulary, Latin and foreign
/// phrases, "etc". A damaged spelling is never inferred from these.
fn protected(word: &str) -> bool {
    hinglish(word)
        || INDIAN.binary_search(&word).is_ok()
        || [
            "al", "avant", "bona", "capita", "etc", "facto", "fide", "garde", "hoc", "inter",
            "ipso", "naive", "priori", "sic", "vitro", "vivo",
        ]
        .contains(&word)
        || acronym(word)
        // Everyday technical words the dictionary lacks ("cron" is not "corn").
        || [
            "cron", "crontab", "env", "fullstack", "proto", "qi", "hotfix", "kpi", "kpis", "kubectl", "navbar",
            "nginx", "okr", "okrs", "pytest", "signup", "signups", "stderr", "stdin", "stdout",
            "sudo", "todos", "uat", "wifi",
        ]
        .contains(&word)
}
pub const PARTICLES: [&str; 12] = [
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
    let shaped = typo_shaped(word) || opening_slip(word);
    // "thank yyou", "ask mme to help": a cheap slip of a frequent word that its neighbours were
    // seen beside is that word, even after a greeting or a verb of address.
    // "dirk and wim" is two people; "Hi Saoirse, thahks for" and "Friday, sko please" are slips.
    let joined_by_and = |t: Option<&Token<'_>>| {
        t.is_some_and(|t| ["and", "&", "or"].contains(&t.normalized.as_str()))
    };
    // After a greeting or a word of address only an unmistakable slip counts ("thank yyou", not
    // "looping in hari").
    if slip_fits(word, history.last(), following.first(), token)
        && (!addressed_by(history, token) || strong_slip(word))
        && !(in_list(history, token, following)
            && (joined_by_and(history.last()) || joined_by_and(following.first())))
        && !name_list(history, token, following)
        && !particle_joined(history, token, following)
    {
        return false;
    }
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
                        // "thegy went home" is "they went": a slip of a frequent word is no subject.
                        v.past == n.normalized
                            && !strong_slip(word)
                            && !(v.past == v.base && opening_slip(word))
                            || !shaped && v.third == n.normalized
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
/// Whether `word` is a regional or older spelling of `candidate` ("foetus"/"fetus", "colour"/"color").
fn variant_spelling(word: &str, candidate: &str) -> bool {
    // Short words ("sence") and "-ise", "-ss", "-lled" endings are ordinary typos, not variants.
    let regional = [("oe", "e"), ("ae", "e"), ("our", "or"), ("ogue", "og")];
    word.len() >= 6
        && (word.starts_with("premiss")
            || regional.iter().any(|(a, b)| {
                word.replacen(a, b, 1) == candidate || word.replacen(b, a, 1) == candidate
            }))
}
/// The frequent word an unknown word sounds like under one English sound-spelling swap ("nefew"
/// is "nephew", "enuf" is "enough", "nite" is "night", "shud" is "should"). Only a single
/// clear winner of 4+ letters is returned.
fn sounds_like(word: &str) -> Option<String> {
    // Single-letter swaps (k/c, s/c, z/s) are one edit and ranked in context by `suggest`.
    const SOUNDS: [(&str, &str); 7] = [
        ("f", "ph"),
        ("ph", "f"),
        ("uf", "ough"),
        ("ud", "ould"),
        ("ite", "ight"),
        ("kw", "qu"),
        ("shun", "tion"),
    ];
    if word.len() < 4 || !word.bytes().all(|b| b.is_ascii_lowercase()) {
        return None;
    }
    let mut found: Vec<String> = vec![];
    for (from, to) in SOUNDS {
        for (at, _) in word.match_indices(from) {
            let candidate = format!("{}{to}{}", &word[..at], &word[at + from.len()..]);
            if ordinary(&candidate)
                && frequency(&candidate) >= 380
                && !distance_one(word, &candidate)
                && !found.contains(&candidate)
            {
                found.push(candidate);
            }
        }
    }
    found.sort_by_key(|c| std::cmp::Reverse(frequency(c)));
    match found.as_slice() {
        [one] => Some(one.clone()),
        [a, b, ..] if frequency(a) >= frequency(b).saturating_add(100) => Some(a.clone()),
        _ => None,
    }
}
/// Whether two letters are neighbouring keys on a QWERTY keyboard (the rows are offset, so a key
/// touches two keys on each neighbouring row).
fn adjacent_keys(a: u8, b: u8) -> bool {
    const ROWS: [&[u8]; 3] = [b"qwertyuiop", b"asdfghjkl", b"zxcvbnm"];
    let at = |c: u8| {
        ROWS.iter().enumerate().find_map(|(r, row)| {
            row.iter()
                .position(|&k| k == c)
                .map(|i| (r as i32, i as i32))
        })
    };
    let (Some((ra, ia)), Some((rb, ib))) = (at(a), at(b)) else {
        return false;
    };
    match rb - ra {
        0 => (ia - ib).abs() == 1,
        1 => ib == ia || ib == ia - 1,
        -1 => ib == ia || ib == ia + 1,
        _ => false,
    }
}
/// How unlikely (log10) a slip turns `intended` into `typed`, one edit apart: a dropped,
/// doubled, swapped or neighbouring key is a common slip; a far key or a wrong first letter is not.
pub(crate) fn slip_cost(typed: &str, intended: &str) -> f64 {
    let (t, w) = (typed.as_bytes(), intended.as_bytes());
    let vowel = |c: u8| b"aeiou".contains(&c);
    let first = |i: usize| if i == 0 { 0.5 } else { 0.0 };
    // A doubled first letter ("tthe", "aare") is a doubled key, not a wrong first letter.
    let first_doubled = t.len() == w.len() + 1 && t.len() > 1 && t[0] == t[1];
    let first = |i: usize| if first_doubled { 0.0 } else { first(i) };
    if t.len() == w.len() {
        let diff: Vec<usize> = (0..t.len()).filter(|&i| t[i] != w[i]).collect();
        return match diff[..] {
            [i] => {
                first(i)
                    + if adjacent_keys(t[i], w[i]) {
                        0.5
                    } else if vowel(t[i]) && vowel(w[i]) {
                        1.2
                    } else {
                        1.5
                    }
            }
            [i, _] => 0.3 + first(i) / 2.0,
            _ => 3.0,
        };
    }
    let (short, long, dropped) = if t.len() < w.len() {
        (t, w, true)
    } else {
        (w, t, false)
    };
    (0..long.len())
        .filter(|&i| long[..i] == short[..i] && long[i + 1..] == short[i..])
        .map(|i| {
            let c = long[i];
            let beside = |j: Option<usize>| j.and_then(|j| long.get(j)).copied();
            let (left, right) = (beside(i.checked_sub(1)), beside(Some(i + 1)));
            let doubled = left == Some(c) || right == Some(c);
            first(i)
                + if dropped {
                    if doubled { 0.2 } else { 0.3 }
                } else if doubled {
                    0.3
                } else if [left, right]
                    .into_iter()
                    .flatten()
                    .any(|n| adjacent_keys(n, c))
                {
                    0.5
                } else {
                    1.5
                }
        })
        .fold(3.0, f64::min)
}
/// How well `word` fits between `prev` and `next` (log10, comparable only across candidates for
/// one slot; an empty side is unknown): word-pair counts on each side over the word's own
/// frequency, so a frequent word gains nothing from frequency alone where its neighbours rarely
/// meet it.
/// A word's frequency prior on the Zipf scale (log10 per billion words plus 3), at least 1.
fn zipf(word: &str) -> f64 {
    f64::from(frequency(word).max(100)) / 100.0
}
/// log10 of how often two words are seen side by side in the pair table (the same scale: a word
/// of Zipf z is seen about 10^(z + 4.3) times).
fn pair(a: &str, b: &str) -> f64 {
    match context::count(a, b) {
        0 => {
            // The pair table keeps pairs seen 6.4 million times or more; an absent pair is rarer
            // than that, and rarer still than two independent words of this frequency would be.
            (zipf(a) + zipf(b) - 4.7).min(6.8) - 0.3
        }
        n => (n as f64).log10(),
    }
}
/// log10 probability of a run of words under the pair model (empty words are skipped), for
/// comparing two readings of the same text that differ in their number of words.
pub(crate) fn phrase_logp(words: &[&str]) -> f64 {
    let words: Vec<&str> = words.iter().copied().filter(|w| !w.is_empty()).collect();
    let Some(first) = words.first() else {
        return 0.0;
    };
    zipf(first) - 9.0
        + words
            .windows(2)
            .map(|w| pair(w[0], w[1]) - zipf(w[0]) - 4.3)
            .sum::<f64>()
}
fn slot_fit(prev: &str, word: &str, next: &str) -> f64 {
    match (prev.is_empty(), next.is_empty()) {
        (false, false) => pair(prev, word) + pair(word, next) - zipf(word) - 4.3,
        (false, true) => pair(prev, word) - zipf(prev) - 4.3,
        (true, false) => pair(word, next) - zipf(next) - 4.3,
        (true, true) => zipf(word) - 9.0,
    }
}
/// How unlikely (in Zipf units, about log10) a writer who meant `intended` typed `typed`: a
/// weighted edit distance whose costs were fitted on real misspellings (Wikipedia edits, GitHub
/// typo fixes, Mitton's lists) against how often each kind of slip turns up. Dropped vowels and
/// doubled letters are cheap, vowel and sound-alike swaps ("seperate", "simular") and adjacent
/// swaps cost a little more, a letter typed in place of an unrelated one costs most, and a slip on
/// the first or last letter costs extra: "determins" is "determines", not "determine".
pub(crate) fn typo_cost(typed: &str, intended: &str) -> f64 {
    let (t, w) = (typed.as_bytes(), intended.as_bytes());
    let (n, m) = (t.len(), w.len());
    let vowel = |c: u8| b"aeiou".contains(&c);
    let sound = |a: u8, b: u8| {
        [b"cs", b"sz", b"ck", b"iy", b"gj", b"td", b"mn"]
            .iter()
            .any(|p| **p == [a, b] || **p == [b, a])
    };
    const FIRST: f64 = 2.2;
    const LAST: f64 = 2.2;
    let mut d = vec![vec![f64::INFINITY; m + 1]; n + 1];
    d[0][0] = 0.0;
    for i in 0..=n {
        for j in 0..=m {
            if i == 0 && j == 0 {
                continue;
            }
            let mut best = f64::INFINITY;
            if i > 0 && j > 0 {
                let (a, b) = (t[i - 1], w[j - 1]);
                let cost = if a == b {
                    0.0
                } else {
                    (if vowel(a) && vowel(b) {
                        2.2
                    } else if sound(a, b) {
                        2.0
                    } else if adjacent_keys(a, b) {
                        2.7
                    } else {
                        4.5
                    }) + if j == 1 { FIRST } else { 0.0 }
                        + if i == n && j == m { LAST } else { 0.0 }
                };
                best = best.min(d[i - 1][j - 1] + cost);
            }
            if j > 0 {
                // A letter of the intended word left out.
                let b = w[j - 1];
                let doubled = j > 1 && w[j - 2] == b || j < m && w[j] == b;
                let final_e = b == b'e' && j == m;
                let cost = if doubled {
                    1.45
                } else if final_e {
                    2.1
                } else if vowel(b) {
                    1.2
                } else if b == b'h' && j > 1 && b"cgstwr".contains(&w[j - 2]) {
                    2.0
                } else {
                    1.6
                } + if j == 1 { FIRST } else { 0.0 }
                    + if j == m && !final_e { LAST } else { 0.0 };
                best = best.min(d[i][j - 1] + cost);
                // A repeated syllable written once ("competion", "maintaing").
                for l in [2, 3] {
                    if j >= 2 * l && w[j - l..j] == w[j - 2 * l..j - l] {
                        best = best.min(d[i][j - l] + 2.2);
                    }
                }
            }
            if i > 0 {
                // A letter typed that the intended word lacks.
                let a = t[i - 1];
                let cost = if i > 1 && t[i - 2] == a || i < n && t[i] == a {
                    2.2
                } else if i > 1 && adjacent_keys(t[i - 2], a) || i < n && adjacent_keys(t[i], a) {
                    2.5
                } else if vowel(a) {
                    2.4
                } else {
                    3.0
                } + if i == 1 { FIRST } else { 0.0 }
                    + if i == n && j == m { LAST } else { 0.0 };
                best = best.min(d[i - 1][j] + cost);
            }
            if i > 1
                && j > 1
                && t[i - 1] == w[j - 2]
                && t[i - 2] == w[j - 1]
                && t[i - 1] != t[i - 2]
            {
                let ie = [t[i - 1], t[i - 2]] == *b"ie" || [t[i - 1], t[i - 2]] == *b"ei";
                let cost = if ie { 1.8 } else { 1.5 } + if j == 2 { FIRST } else { 0.0 };
                best = best.min(d[i - 2][j - 2] + cost);
            }
            d[i][j] = best;
        }
    }
    d[n][m]
}
/// Optimal string alignment distance (edits with adjacent swaps), stopping early past `limit`.
fn osa_within(a: &[u8], b: &[u8], limit: usize) -> bool {
    if a.len().abs_diff(b.len()) > limit {
        return false;
    }
    let mut d = vec![vec![0usize; b.len() + 1]; a.len() + 1];
    for (i, row) in d.iter_mut().enumerate() {
        row[0] = i;
    }
    for (j, cell) in d[0].iter_mut().enumerate() {
        *cell = j;
    }
    for i in 1..=a.len() {
        for j in 1..=b.len() {
            let mut v = (d[i - 1][j] + 1)
                .min(d[i][j - 1] + 1)
                .min(d[i - 1][j - 1] + usize::from(a[i - 1] != b[j - 1]));
            if i > 1 && j > 1 && a[i - 1] == b[j - 2] && a[i - 2] == b[j - 1] {
                v = v.min(d[i - 2][j - 2] + 1);
            }
            d[i][j] = v;
        }
    }
    d[a.len()][b.len()] <= limit
}
/// Frequent ordinary words (frequency prior 300 or more) at most two edits from `word`: every
/// one-edit variant of the word, looked up in the one-deletion index of frequent words.
fn within_two(word: &str) -> Vec<String> {
    let lexicon = lexicon();
    let mut variants: HashSet<String> = HashSet::new();
    let bytes = word.as_bytes();
    let text = |b: Vec<u8>| String::from_utf8(b).unwrap_or_default();
    variants.insert(word.to_string());
    for i in 0..bytes.len() {
        let mut v = bytes.to_vec();
        v.remove(i);
        variants.insert(text(v));
        if i + 1 < bytes.len() {
            let mut v = bytes.to_vec();
            v.swap(i, i + 1);
            variants.insert(text(v));
        }
    }
    for i in 0..=bytes.len() {
        for c in b'a'..=b'z' {
            let mut v = bytes.to_vec();
            v.insert(i, c);
            variants.insert(text(v));
            if i < bytes.len() && bytes[i] != c {
                let mut v = bytes.to_vec();
                v[i] = c;
                variants.insert(text(v));
            }
        }
    }
    let mut near: HashSet<&'static str> = HashSet::new();
    for v in &variants {
        if let Some(w) = lexicon.word(v) {
            near.insert(w);
        }
        near.extend(lexicon.deletes(v));
    }
    near.into_iter()
        .filter(|c| {
            lexicon.ordinary(c)
                && frequency(c) >= 300
                && *c != word
                && osa_within(bytes, c.as_bytes(), 2)
        })
        .map(String::from)
        .collect()
}
/// How likely `candidate` is the word meant by the unknown `word` between `before` and `after`
/// (either may be empty): its frequency less the cost of the slip (`typo_cost`), plus how well it
/// fits its neighbours. The weights were fitted on real misspellings in context.
fn typo_score(word: &str, candidate: &str, before: &str, after: &str) -> f64 {
    let fit = if before.is_empty() && after.is_empty() {
        0.0
    } else {
        slot_fit(before, candidate, after)
    };
    0.45 * (zipf(candidate) - typo_cost(word, candidate)) + 0.83 * fit
}
/// The words within two edits of an unknown `word`, best first by `typo_score`.
fn typo_ranking(word: &str, before: &str, after: &str, dialect_flags: u8) -> Vec<(f64, String)> {
    let mut ranked: Vec<(f64, String)> = within_two(word)
        .into_iter()
        // "rethrown" is no slip of "thrown": a whole word inside it is a word with an affix.
        .filter(|c| flags(c) & dialect_flags != 0 && c != before && c != after)
        .filter(|c| !word.starts_with(c.as_str()) && !word.ends_with(c.as_str()))
        .map(|c| (typo_score(word, &c, before, after), c))
        .collect();
    ranked.sort_by(|a, b| b.0.total_cmp(&a.0).then_with(|| a.1.cmp(&b.1)));
    ranked
}
/// The one candidate that the neighbouring words and the shape of the slip clearly favour, or
/// None when context cannot decide (the runner-up is within `margin`, log10).
fn context_choice<'c>(
    word: &str,
    candidates: &'c [String],
    prev: &str,
    next: &str,
    margin: f64,
) -> Option<&'c String> {
    let mut ranked: Vec<(f64, &String)> = candidates
        .iter()
        .map(|c| (slot_fit(prev, c, next) - slip_cost(word, c), c))
        .collect();
    ranked.sort_by(|a, b| b.0.total_cmp(&a.0).then_with(|| a.1.cmp(b.1)));
    match ranked[..] {
        [(_, only)] => Some(only),
        [(best, c), (second, _), ..] if best - second >= margin => Some(c),
        _ => None,
    }
}
/// A word that is clearly a damaged common word, not a name, when capitalized at a sentence
/// start: a listed misspelling, or one edit from a frequent word (`edit_shaped`).
pub fn opening_typo(word: &str) -> bool {
    !known(word)
        && !names::is_bundled_name(word)
        && (names::is_name_typo(word) || names::is_known_misspelling(word) || edit_shaped(word))
}
/// A misspelled word that opens a sentence ("Waht time is it?", "Hopefuly not"). Its capital is
/// the sentence's, not a name's, so it is respelled like the lowercase word, but only to a
/// frequent word one edit away and only with clear typo evidence: a listed misspelling, one
/// adjacent swap of a frequent word, or one letter from a frequent word of six or more letters.
/// Names the lexicon, the bundled list or the system tagger know keep their spelling.
pub fn suggest_capitalized(
    token: &Token<'_>,
    dialect: &str,
    previous: Option<&Token<'_>>,
    next: Option<&Token<'_>>,
    history: &[Token<'_>],
    following_context: &[Token<'_>],
) -> Option<String> {
    let word = token.normalized.as_str();
    let mut letters = token.surface.chars();
    // "Thi is fine", "Trhe recipe": an opening word that is a cheap slip of a frequent word,
    // unless the tagger or the bundled list calls it a name.
    let short = opening_slip(word);
    let index = history.len();
    let tagger_guess = token.proper_name && {
        let mut tokens = history.to_vec();
        tokens.push(token.clone());
        tokens.extend(following_context.iter().take(1).cloned());
        opening_name_slip(&tokens, index)
    };
    // "Canyou help?", "Letme know": a glued pair opening the sentence.
    if !token.proper_name
        && !token.system_known
        && token
            .surface
            .chars()
            .next()
            .is_some_and(|c| c.is_ascii_uppercase())
        && token
            .surface
            .chars()
            .skip(1)
            .all(|c| c.is_ascii_lowercase() || c == '\'')
        && line_start(history, token)
        && !namey(word)
        && !names::is_bundled_name(word)
        && let Some(split) = common_split(
            word,
            "",
            next.filter(|n| n.is_word && n.sentence == token.sentence && ordinary(&n.normalized))
                .map_or("", |n| n.normalized.as_str()),
        )
    {
        let mut chars = split.chars();
        return chars
            .next()
            .map(|c| c.to_uppercase().collect::<String>() + chars.as_str());
    }
    if token.proper_name && !tagger_guess
        || token.system_known
        || word.len() < 2
        || word.len() > 24
        || !letters.next().is_some_and(|c| c.is_ascii_uppercase())
        || !letters.all(|c| c.is_ascii_lowercase())
        || !line_start(history, token)
        || namey(word) && !(short_slip(word) && word.len() <= 2)
        || protected(word) && !short
        || !(short || word.len() >= 4 && opening_typo(word))
    {
        return None;
    }
    let mut lowered = token.clone();
    lowered.surface = word;
    lowered.proper_name = false;
    let candidate = suggest(
        &lowered,
        dialect,
        previous,
        next,
        history,
        following_context,
    )?;
    // A short opener becomes only a word one cheap slip away ("Anh" is no slip of "And").
    // With no tagger to tell a name ("Hoa is fine"), only a doubled or swapped key counts.
    let cheap = word.len() > 3
        || slips_from(word).contains(&candidate)
            && (!token.pos.is_empty() || doubled_or_swapped(word, &candidate));
    (!candidate.contains(' ')
        && distance_one(word, &candidate)
        && cheap
        && (names::is_name_typo(word) || frequency(&candidate) >= 400))
        .then(|| {
            let mut chars = candidate.chars();
            chars
                .next()
                .map(|c| c.to_uppercase().collect::<String>() + chars.as_str())
                .unwrap_or_default()
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
    // "requirements.txt", "example.org": a word glued after a dot is an extension or a domain.
    // "os.path.join": a word glued before a dot and another word is code.
    let dotted = previous.is_some_and(|p| p.surface == "." && p.end_byte == token.start_byte)
        || matches!(following_context, [dot, after, ..]
            if dot.surface == "."
                && dot.start_byte == token.end_byte
                && after.start_byte == dot.end_byte
                && after.surface.starts_with(char::is_alphanumeric));
    if token.proper_name
        || token.surface.chars().any(char::is_uppercase)
        || word.len() > 24
        || !word.bytes().all(|b| b.is_ascii_lowercase() || b == b'\'')
        || dotted
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
        let mut nearby: HashSet<&'static str> = HashSet::new();
        nearby.extend(lexicon().deletes(following));
        for deleted in deletions(following) {
            if let Some(w) = lexicon().word(&deleted) {
                nearby.insert(w);
            }
            nearby.extend(lexicon().deletes(&deleted));
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
    // A lone letter ("reasons t switch", "let m know") is a short word missing a letter. Letters
    // that usually label something ("plan b", "option c", "vitamin d", "x is 5") are left alone.
    let letter = word.len() == 1 && "fghjlmnopqstvw".contains(word.as_str());
    // A proper noun typed in lowercase ("lyft", "duolingo") is capitalized, never respelled.
    if lexicon().ordinary(word) && !letter || names::is_shorthand(word) || chat(word) {
        return None;
    }
    let proper_noun = crate::capitalization::proper_noun(names::base(word)).is_some();
    // "i canf do it" is "can't", not "can": a slip that sits one edit from both a negative and
    // its positive keeps the negation, since dropping it reverses what was meant.
    // "aren 't" is a contraction typed with a space, not a slip.
    let apostrophe_next = following_context
        .first()
        .is_some_and(|t| t.surface.starts_with(['\'', '’']));
    if !apostrophe_next && let Some(negative) = kept_negation(word) {
        return Some(negative);
    }
    // "bron bron": a word typed twice in a row is a nickname or a sound, not a slip.
    if [previous, next]
        .into_iter()
        .flatten()
        .any(|t| t.normalized == *word)
    {
        return None;
    }
    // "dont" is "don't", whatever else it is one letter from ("done").
    if let Some(stem) = word.strip_suffix("nt")
        && [
            "do", "did", "does", "is", "was", "were", "are", "has", "have", "had", "should",
            "would", "could", "need",
        ]
        .contains(&stem)
    {
        return Some(format!("{stem}n't"));
    }
    // Roman Hindi, Indian English and Latin words are never respelled; only the reviewed
    // misspellings above and the name typos stay correctable.
    // "thik" is also a typo of "think" unless Roman Hindi surrounds it.
    let hindi_near = history
        .iter()
        .rev()
        .take(3)
        .chain(following_context.iter().take(3))
        .any(|t| hinglish(&t.normalized) && t.normalized != "thik");
    // A short Hinglish word with no Roman Hindi beside it is an English slip ("thi" for "this").
    let lone_hindi = hinglish(word)
        && word.len() <= 3
        && !HINGLISH_ALONE.contains(&word.as_str())
        && !hindi_near;
    if protected(word)
        && (word != "thik" || hindi_near)
        && !lone_hindi
        && !names::is_name_typo(word)
    {
        return None;
    }
    // The system spell checker also accepts "statin" and "offie", so what it accepts is respelled
    // only to a very common word, never split.
    let accepted = token.system_known && !names::is_name_typo(word);
    // "waiters" is "waiter" and "laceless" is "lace" and "less": a regular form of a known word.
    if accepted
        && ["s", "es", "ed", "ing", "er", "ers", "ly", "less", "ness"]
            .iter()
            .any(|suffix| {
                word.strip_suffix(suffix).is_some_and(|stem| {
                    stem.len() >= 4 && (ordinary(stem) || ordinary(&format!("{stem}e")))
                })
            })
    {
        return None;
    }
    // "jain" is only listed as "Jain": a lowercase name is never respelled into another word.
    // Two lowercase letters are never a name ("ar" is no "Ar" or "AR"; see names::never_a_name).
    let tiny = word.len() <= 2;
    let neighbour = |t: Option<&Token<'_>>| -> String {
        t.filter(|t| t.is_word && t.sentence == token.sentence && t.paragraph == token.paragraph)
            .map(|t| contextual_word(&t.normalized).to_string())
            .filter(|w| ordinary(w))
            .unwrap_or_default()
    };
    let (before, after) = (neighbour(previous), neighbour(next));
    // "covers moe than", "before tue deadline": a word listed only as a name ("Moe", "Tue") that
    // one slip makes of a frequent word both neighbours were seen beside is that word.
    let slipped_name = || {
        let pool: Vec<String> = slips_within(word, 1.0)
            .into_iter()
            .filter(|c| frequency(c) >= 400)
            .collect();
        let seen = |a: &str, b: &str| !a.is_empty() && !b.is_empty() && context::count(a, b) > 0;
        // Both neighbours agree, or one does on a doubled, dropped or swapped key that the
        // neighbours favour by far ("timeout iss set", "some mlk and").
        (!before.is_empty() || !after.is_empty())
            && (context_choice(word, &pool, &before, &after, 1.0)
                .is_some_and(|c| seen(&before, c) && seen(c, &after))
                || context_choice(word, &pool, &before, &after, 1.5).is_some_and(|c| {
                    // The other side unseen only where two words that rare would be.
                    let fair = |a: &str, b: &str| {
                        a.is_empty() || b.is_empty() || seen(a, b) || zipf(a) + zipf(b) < 11.5
                    };
                    slip_cost(word, c) <= 0.3
                        && (seen(&before, c) || seen(c, &after))
                        && fair(&before, c)
                        && fair(c, &after)
                }))
    };
    // "canyou", "letme", "atthe": two words that very often go together, typed without the space
    // and fitting their neighbours, are split even where a name could stand ("meet atthe door").
    // "arjun menon" is a full name, not "men on": a neighbour that is no ordinary word blocks it.
    let name_beside = [previous, next].into_iter().flatten().any(|t| {
        t.is_word
            && t.sentence == token.sentence
            && t.surface.chars().all(|c| c.is_lowercase())
            && !ordinary(&t.normalized)
            && t.normalized != "i"
            && !t.normalized.starts_with("i'")
    });
    if !accepted
        && !namey(word)
        && !name_beside
        && let Some(split) = common_split(word, &before, &after)
    {
        return Some(split);
    }
    // A proper noun typed in lowercase ("lyft", "ios") is capitalized, not respelled, unless both
    // neighbours show a slip ("which ios confusing" is "which is confusing").
    if (namey(word) && !tiny && !name_only_typo(names::base(word), prev) || proper_noun)
        && !slipped_name()
        || name_like(token, history, following_context)
    {
        return None;
    }
    // "familys" is "families" and "wifes" is "wives", not "family" and "wife".
    let plural = word
        .strip_suffix("ys")
        .filter(|stem| stem.ends_with(|c| !"aeiou".contains(c)))
        .map(|stem| format!("{stem}ies"))
        .or_else(|| word.strip_suffix("fes").map(|stem| format!("{stem}ves")));
    if let Some(plural) = plural
        && !accepted
        && lexicon().ordinary(&plural)
    {
        return Some(plural);
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
    let split = split.filter(|(_, split)| {
        !accepted && article_split_ok(split, token, prev, history, following_context)
    });
    // Two letters ("ar", "th") are one edit from dozens of words, and many are abbreviations and
    // units ("hr", "km"): only a word the neighbours clearly favour is offered.
    if tiny && (accepted || !two_letter_slot(token, previous, next, history)) {
        return None;
    }
    let lexicon = lexicon();
    let mut candidates = HashSet::new();
    candidates.extend(lexicon.deletes(word).map(String::from));
    for deleted in deletions(word) {
        if lexicon.contains(&deleted) {
            candidates.insert(deleted.clone());
        }
        candidates.extend(lexicon.deletes(&deleted).map(String::from));
    }
    // With no dialect chosen, British and American spellings are both valid.
    let dialect_flags = match dialect {
        "british" => 128,
        "american" => 64,
        _ => 192,
    };
    let mut candidates: Vec<String> = candidates
        .into_iter()
        // Never offer a name ("rahul" to "raul") or acronym ("neha" to "neh") for a lowercase word.
        .filter(|candidate| {
            distance_one(word, candidate)
                && flags(candidate) & dialect_flags != 0
                && lexicon.ordinary(candidate.as_str())
        })
        // "foetuses" and "fetuses", "premisses" and "premises" are two valid spellings.
        .filter(|candidate| !dialect.is_empty() || !variant_spelling(word, candidate))
        // "aman" to "man" or "aclear" to "clear" drops a word's first letter and either loses an
        // article or erases a name; neither is a correction. A doubled "a" ("aare") is a slip.
        .filter(|candidate| word.starts_with("aa") || word.strip_prefix('a') != Some(candidate))
        // A slip into the neighbouring word would double it ("sai said").
        .filter(|candidate| *candidate != before && *candidate != after)
        .collect();
    // "the eigth floor" is "eighth", "eigth apples" is "eight": a number and its ordinal one slip
    // apart are told apart by the slot.
    const ORDINALS: [(&str, &str); 7] = [
        ("four", "fourth"),
        ("six", "sixth"),
        ("seven", "seventh"),
        ("eight", "eighth"),
        ("nine", "ninth"),
        ("ten", "tenth"),
        ("eleven", "eleventh"),
    ];
    if let Some((cardinal, ordinal)) = ORDINALS
        .iter()
        .find(|(c, o)| candidates.iter().any(|x| x == c) && candidates.iter().any(|x| x == o))
    {
        let ordinal_slot = [
            "the", "his", "her", "its", "their", "our", "my", "your", "every", "each",
        ]
        .contains(&prev)
            || [
                "century",
                "floor",
                "grade",
                "place",
                "time",
                "day",
                "year",
                "row",
                "round",
                "edition",
                "anniversary",
                "birthday",
                "street",
                "season",
                "chapter",
                "generation",
                "largest",
                "biggest",
                "most",
            ]
            .contains(&following);
        let drop = if ordinal_slot { cardinal } else { ordinal };
        candidates.retain(|c| c != drop);
    }
    // "refax", "preschedule": a common prefix on an ordinary word is a word formed on purpose,
    // unless one likely slip makes it another word ("reovation" is "renovation").
    if prefixed(word) && candidates.iter().all(|c| typo_cost(word, c) > 4.0) {
        return None;
    }
    // Topic and argument preferences only rank unknown-word candidates; the context choice below
    // never overrides a ranking they decided ("cazes" near a bakery is "cakes").
    let topical = |candidate: &str| -> bool {
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
        match candidate {
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
        }
    };
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
        if topical(candidate) {
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
    // A split of two content words ("bio diesel", "new papers") is a clear typo only when no
    // single word is one edit away; a bound prefix is no word ("anti violence").
    let split = split.as_ref().filter(|(_, split)| {
        let prefix = [
            "anti", "con", "cont", "don", "inter", "non", "out", "over", "semi", "sub", "under",
        ];
        !split.split(' ').next().is_some_and(|p| prefix.contains(&p))
            && (split.split(' ').any(function) || candidates.is_empty())
    });
    if let Some((split_score, split)) = split
        && candidates.first().is_none_or(|c| *split_score > score(c))
    {
        // "befor" is "before", not "be for"; "restor" is "restore": a split with a piece of three
        // letters or fewer gives way to one word a single cheap slip away (a dropped or doubled
        // letter). A dropped final "g" ("talkin", "feelin") is a way of speaking, kept as typed.
        // The neighbours decide between the two readings ("the plan is away", not "the plains").
        let short_piece = split.split(' ').any(|p| p.len() <= 3);
        let pieces: Vec<&str> = split.split(' ').collect();
        let as_split = phrase_logp(&[&[before.as_str()], &pieces[..], &[after.as_str()]].concat());
        if short_piece
            && !accepted
            && let Some((_, top)) = typo_ranking(word, &before, &after, dialect_flags)
                .into_iter()
                .find(|(_, c)| typo_cost(word, c) <= 2.2)
            && phrase_logp(&[&before, &top, &after]) > as_split + 1.0
        {
            if word.ends_with("in") && top == format!("{word}g") {
                return None;
            }
            return Some(top);
        }
        return Some(split.clone());
    }
    // A spelling by sound ("nefew", "enuf", "shud") is no single edit from its word; it is
    // respelled only to a frequent word far more common than any one-edit neighbour.
    if !accepted
        && let Some(sounded) = sounds_like(word)
        && candidates
            .first()
            .is_none_or(|c| frequency(&sounded) >= frequency(c).saturating_add(60))
    {
        return Some(sounded);
    }
    // A word one edit from a rare candidate ("chinese" and "chines") is not a typo, and one the
    // system checker accepts is respelled only to a very common word ("statin" and "station").
    // Several frequent words fit the slip ("thi": this, the, thin; "ar": are, art, at): the
    // neighbouring words decide, by how often each candidate meets them and how likely each slip
    // is, and the word stays when they cannot.
    // A neighbour that is itself damaged ("ot collectthe") is no context yet: the word waits for
    // the pass that repairs it.
    let damaged = |t: Option<&Token<'_>>| {
        t.is_some_and(|t| {
            t.is_word
                && t.sentence == token.sentence
                && t.surface.chars().all(|c| c.is_lowercase() || c == '\'')
                && !known(&t.normalized)
                && !names::is_shorthand(&t.normalized)
                && !hinglish(&t.normalized)
        })
    };
    let seen = |a: &str, b: &str| !a.is_empty() && !b.is_empty() && context::count(a, b) > 0;
    let in_context = || -> Option<String> {
        if accepted || word.len() <= 3 && (damaged(previous) || damaged(next)) {
            return None;
        }
        let pool: Vec<String> = candidates
            .iter()
            .filter(|c| frequency(c) >= if tiny { 500 } else { 300 })
            .cloned()
            .collect();
        let choice = context_choice(word, &pool, &before, &after, if tiny { 0.5 } else { 0.4 })?;
        // The winner must have been seen beside its neighbours, not only be frequent.
        let seen = |a: &str, b: &str| !a.is_empty() && !b.is_empty() && context::count(a, b) > 0;
        // A lone letter may be a label, a variable or a grade ("plan b", "x"): both neighbours
        // must have been seen beside the word it stands for.
        if letter && !(seen(&before, choice) && seen(choice, &after)) {
            return None;
        }
        // "This si note is difficult": a verb chosen for a slot whose clause has its own verb
        // just after is a guess that breaks the clause ("si note" is a noun phrase).
        let clause_verb = FINITE.contains(&choice.as_str())
            && following_context
                .iter()
                .take(3)
                .take_while(|t| t.sentence == token.sentence && t.is_word)
                .any(|t| {
                    FINITE.contains(&t.normalized.as_str())
                        || COPULAS.contains(&t.normalized.as_str())
                });
        // Seen beside a neighbour, or a likely slip (a doubled, dropped or swapped key) of a word
        // of three letters or more that the neighbours clearly favour ("forgot ihs keys").
        // A changed first letter ("emi" read as "semi") needs both neighbours.
        let first_changed =
            word.as_bytes().first() != choice.as_bytes().first() && slip_cost(word, choice) > 0.6;
        let attested = if first_changed {
            (before.is_empty() || seen(&before, choice))
                && (after.is_empty() || seen(choice, &after))
                && (!before.is_empty() || !after.is_empty())
        } else {
            seen(&before, choice)
                || seen(choice, &after)
                || word.len() >= 3 && slip_cost(word, choice) <= 0.6 && frequency(choice) >= 400
        };
        (!clause_verb && attested).then(|| choice.clone())
    };
    // A short word beside an unknown lowercase word may be half of a name ("sai raju").
    if word.len() <= 3 && (damaged(previous) || damaged(next)) {
        return None;
    }
    // A one-edit pick that a likelier slip two edits away contradicts is a guess: "competion" is
    // "competition" (a syllable written once), not "completion"; "containg" is "containing", not
    // "contains". A clearly likelier word replaces it; a close one leaves the word as typed.
    let likeliest = |choice: String| -> Option<String> {
        if drops_negation(word, &choice) {
            return None;
        }
        // A short word is respelled only into a real word with a vowel ("cl" is no word), and a
        // dropped letter needs both neighbours to back the shorter word ("migrate to aws" is not
        // "to as"); a doubled letter ("andd") is a clear slip.
        let vowelless = !word.bytes().any(|b| b"aeiouy".contains(&b));
        if word.len() <= 4 && vowelless && !vowelless_slip(word, &choice) {
            return None;
        }
        if word.len() <= 4 {
            let doubled = word.as_bytes().windows(2).any(|w| w[0] == w[1]);
            let shorter = choice.len() < word.len();
            // Four letters may drop a final "e" ("nowe") or a cheap extra key on their own; three
            // letters only a neighbouring key before one of the most frequent words ("kon").
            let cheap = word.len() == 4 && (word.ends_with('e') || slip_cost(word, &choice) <= 0.5)
                || slip_cost(word, &choice) <= 1.0 && frequency(&choice) >= 600;
            let backed = seen(&before, &choice) && seen(&choice, &after);
            let dropped_ok = !shorter || doubled || cheap || backed;
            if !choice.bytes().any(|b| b"aeiouy".contains(&b)) || !dropped_ok {
                return None;
            }
        }
        // Short words have many neighbours two edits away; the one-edit ranking stands for them.
        if accepted || word.len() < 6 {
            return Some(choice);
        }
        let mine = typo_score(word, &choice, &before, &after);
        // Only a rival two edits away that is a clearly likelier slip ("containing" for
        // "containg", not "wanted" for "watied"): between one-edit words the ranking above already
        // weighed the neighbours and the slot.
        if topical(&choice) {
            return Some(choice);
        }
        let slip = typo_cost(word, &choice);
        let rival = typo_ranking(word, &before, &after, dialect_flags)
            .into_iter()
            .find(|(_, c)| {
                *c == choice || !distance_one(word, c) && typo_cost(word, c) + 1.0 <= slip
            });
        match rival.as_ref() {
            Some((score, top))
                if *top != choice
                    && *score >= mine + TYPO_MARGIN
                    && typo_cost(word, top) <= 0.35 * word.len() as f64 =>
            {
                Some(top.clone())
            }
            Some((score, top)) if *top != choice && *score > mine => None,
            _ => Some(choice),
        }
    };
    if !tiny
        && let Some(best) = candidates
            .first()
            .filter(|c| frequency(c) >= if accepted { 400 } else { 250 })
    {
        // Close scores between the neighbours of a short word ("bos": box, bus, boy) are a guess.
        let margin = if accepted {
            20
        } else if word.len() <= 3 {
            100
        } else {
            0
        };
        if candidates.len() == 1
            || (score(best) >= 40 && score(best) > score(&candidates[1]) + margin)
        {
            // An unlikely slip ("arre" read as "acre") yields to a likely one the neighbours
            // were seen beside ("are").
            if slip_cost(word, best) >= 1.5
                && !topical(best)
                && let Some(choice) = in_context()
                && slip_cost(word, &choice) <= 0.5
                // A best word seen beside both neighbours stays ("the lztter was" is "letter").
                && !(seen(&before, best) && seen(best, &after))
                // Seen beside a neighbour, or close to the best in the general ranking too.
                && (seen(&before, &choice)
                    || seen(&choice, &after)
                    || score(&choice) + 100 >= score(best))
            {
                return likeliest(choice);
            }
            return likeliest(best.clone());
        }
    }
    if let Some(choice) = in_context() {
        return likeliest(choice);
    }
    // No frequent word is one edit away ("competion", "maintaing" are two): the likeliest word
    // within two edits, when it clearly beats the next one and the slips are cheap for the word's
    // length. Two costly changes to a short word ("linguae", "decisis") are a foreign or rare
    // word more often than a typo.
    if !accepted && word.len() >= 6 && candidates.is_empty() {
        let ranked = typo_ranking(word, &before, &after, dialect_flags);
        if let Some((score, top)) = ranked.first()
            && ranked
                .get(1)
                .is_none_or(|(next, _)| score - next >= TYPO_MARGIN)
            && typo_cost(word, top) <= 0.35 * word.len() as f64
        {
            return Some(top.clone());
        }
    }
    None
}
/// How far (log10-like `typo_score` units) the likeliest word must lead the next one.
const TYPO_MARGIN: f64 = 1.0;
/// A two-letter word that may be a slip of a frequent word: not glued to or after a number
/// ("5th", "10 km"), which makes it a unit or an ordinal, and not beside another uncommon short
/// word ("la si do", "fa so"), which makes it part of a sequence of syllables or codes.
fn two_letter_slot(
    token: &Token<'_>,
    previous: Option<&Token<'_>>,
    next: Option<&Token<'_>>,
    history: &[Token<'_>],
) -> bool {
    const COMMON_SHORT: [&str; 28] = [
        "a", "i", "am", "an", "as", "at", "be", "by", "do", "go", "he", "if", "in", "is", "it",
        "me", "my", "no", "of", "oh", "ok", "on", "or", "so", "to", "up", "us", "we",
    ];
    let odd = |t: Option<&Token<'_>>| {
        t.is_some_and(|t| {
            t.is_word && t.normalized.len() <= 2 && !COMMON_SHORT.contains(&t.normalized.as_str())
        })
    };
    let number = |t: &Token<'_>| t.surface.starts_with(|c: char| c.is_ascii_digit());
    !odd(previous)
        && !odd(next)
        && !previous.is_some_and(|p| number(p) || !p.is_word && p.end_byte == token.start_byte)
        && !history
            .iter()
            .rev()
            .nth(1)
            .is_some_and(|t| number(t) && previous.is_some_and(|p| !p.is_word))
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
    /// `suggest` for `word` in `text`, as the engine calls it, with the system spell checker's verdict.
    fn suggest_at(text: &str, word: &str, known: bool) -> Option<String> {
        let start = text.find(word).unwrap();
        let hint = crate::TokenHint {
            start_utf16: start,
            end_utf16: start + word.len(),
            known,
            ..Default::default()
        };
        let tokens = crate::tokenizer::tokenize(text, &[hint]);
        let i = tokens.iter().position(|t| t.normalized == word).unwrap();
        suggest(
            &tokens[i],
            "",
            i.checked_sub(1).map(|j| &tokens[j]),
            tokens.get(i + 1),
            &tokens[..i],
            &tokens[i + 1..],
        )
    }
    #[test]
    fn acronyms_and_codes_keep_their_letters() {
        // Lowercase acronyms, brand codes and tech terms never lose a letter or become a word.
        for (text, word) in [
            ("VP in hcl salary", "hcl"),
            ("migrate to aws", "aws"),
            ("call the api over ssh", "api"),
            ("the jvm crashed", "jvm"),
            ("use the cli", "cli"),
            ("joined tcs last year", "tcs"),
            ("send the ppt", "ppt"),
            ("gst is due", "gst"),
            ("kpmg audit", "kpmg"),
            ("he works at ibm", "ibm"),
            ("we use gcp", "gcp"),
            ("run npm install", "npm"),
            ("the sql query", "sql"),
            ("check the crm", "crm"),
        ] {
            assert_eq!(suggest_at(text, word, false), None, "{word}");
        }
        for word in ACRONYMS {
            assert!(acronym(word), "{word}");
        }
        // Real three-letter slips are still fixed.
        for (text, word, fixed) in [
            ("adn then we left", "adn", "and"),
            ("pet hte dog", "hte", "the"),
            ("wht is this", "wht", "what"),
            ("it wass broken", "wass", "was"),
        ] {
            assert_eq!(
                suggest_at(text, word, false).as_deref(),
                Some(fixed),
                "{word}"
            );
        }
    }
    #[test]
    fn likely_slips_beat_a_closer_rare_reading() {
        // Two edits that a writer often makes beat one edit that they rarely make.
        let mut wrong = vec![];
        for (text, word, fixed) in [
            ("A file containg the data.", "containg", "containing"),
            ("Call me befor the meeting.", "befor", "before"),
            ("The algotihms are fast.", "algotihms", "algorithms"),
        ] {
            let got = suggest_at(text, word, false);
            if got.as_deref() != Some(fixed) {
                wrong.push(format!("{word}: {got:?}"));
            }
        }
        assert!(wrong.is_empty(), "{wrong:?}");
        // A negation survives the slip; a prefixed word and a nickname stay as typed.
        assert_eq!(
            suggest_at("i canf do it", "canf", false).as_deref(),
            Some("can't")
        );
        assert_eq!(suggest_at("Please refax the form.", "refax", false), None);
        assert_eq!(suggest_at("hey bron bron", "bron", false), None);
        assert_eq!(
            suggest_at("It is on the eigth floor.", "eigth", false).as_deref(),
            Some("eighth")
        );
        // Chat spellings and costly changes to short rare words stay as typed.
        for (text, word) in [
            ("come here lil bit", "lil"),
            ("It is the plural linguae here.", "linguae"),
            ("Stare decisis applies.", "decisis"),
        ] {
            assert_eq!(suggest_at(text, word, false), None, "{word}");
        }
        assert!(typo_cost("seperate", "separate") < typo_cost("seperate", "desperate"));
        assert!(typo_cost("determins", "determines") < typo_cost("determins", "determine"));
    }
    #[test]
    fn words_the_system_checker_accepts_are_not_respelled() {
        // A closed compound the checker knows is never split.
        let text = "The honeyeater is a small bird.";
        assert_eq!(
            suggest_at(text, "honeyeater", false).as_deref(),
            Some("honey eater")
        );
        assert_eq!(suggest_at(text, "honeyeater", true), None);
        // It accepts "waiters" too, a regular plural; a very common word one edit away still wins
        // over a rare word the checker happens to accept ("statin" for "station").
        assert_eq!(suggest_at("The waiters are kind.", "waiters", true), None);
        assert_eq!(
            suggest_at("Meet at the statin tomorrow.", "statin", true).as_deref(),
            Some("station")
        );
        // Reviewed misspellings stay correctable whatever the checker says.
        assert_eq!(
            suggest_at("Please recieve it.", "recieve", true).as_deref(),
            Some("receive")
        );
    }
    #[test]
    fn roman_hindi_indian_and_latin_words_stay() {
        for (text, word) in [
            ("Bhai yaar kya hai.", "yaar"),
            ("Bhai yaar kya hai.", "hai"),
            ("We ate paneer and dosa.", "paneer"),
            ("My aunty came to the puja.", "puja"),
            ("It is true a priori.", "priori"),
            ("Pens, paper, etc. for class.", "etc"),
        ] {
            assert_eq!(suggest_at(text, word, false), None, "{word}");
        }
        assert!(HINGLISH.windows(2).all(|w| w[0] < w[1]) && INDIAN.windows(2).all(|w| w[0] < w[1]));
    }
    #[test]
    fn contractions_keep_their_apostrophe() {
        for (word, fixed) in [("dont", "don't"), ("didnt", "didn't"), ("isnt", "isn't")] {
            let text = format!("I {word} know.");
            assert_eq!(suggest_at(&text, word, false).as_deref(), Some(fixed));
        }
    }
    #[test]
    fn valid_variants_and_plurals() {
        // Both spellings are valid by default; a misspelt plural gets its plural.
        assert!(
            variant_spelling("foetuses", "fetuses") && variant_spelling("premisses", "premises")
        );
        assert!(!variant_spelling("sence", "sense"));
        assert_eq!(suggest_at("The foetuses grew.", "foetuses", false), None);
        assert_eq!(
            suggest_at("The familys met.", "familys", false).as_deref(),
            Some("families")
        );
        assert_eq!(
            suggest_at("Two wifes agreed.", "wifes", false).as_deref(),
            Some("wives")
        );
    }
    #[test]
    fn one_word_beats_a_split() {
        let text = "It was wonderfull today.";
        assert_eq!(
            suggest_at(text, "wonderfull", false).as_deref(),
            Some("wonderful")
        );
        assert_eq!(
            suggest_at("Read the newpapers daily.", "newpapers", false).as_deref(),
            Some("newspapers")
        );
        assert_eq!(suggest_at("I donnot know.", "donnot", false), None);
    }
    #[test]
    fn spellings_by_sound_and_technical_words() {
        for (text, word, fixed) in [
            ("My nefew came over.", "nefew", "nephew"),
            ("That is enuf for now.", "enuf", "enough"),
            ("See you tonite then.", "tonite", "tonight"),
            ("I shud call her.", "shud", "should"),
        ] {
            assert_eq!(
                suggest_at(text, word, false).as_deref(),
                Some(fixed),
                "{word}"
            );
        }
        assert_eq!(suggest_at("The cron job failed.", "cron", false), None);
        assert_eq!(suggest_at("Turn the wifi off.", "wifi", false), None);
    }
    #[test]
    fn misspellings_that_open_a_sentence_are_respelled() {
        let at_start = |text: &str| {
            let tokens = crate::tokenizer::tokenize(text, &[]);
            suggest_capitalized(&tokens[0], "", None, tokens.get(1), &[], &tokens[1..])
        };
        assert_eq!(at_start("Waht time is it?").as_deref(), Some("What"));
        assert_eq!(at_start("Becuase it rained.").as_deref(), Some("Because"));
        assert_eq!(at_start("Probaly not.").as_deref(), Some("Probably"));
        // Names, known words and words with no clear typo shape keep their capital and spelling.
        for text in [
            "Anoop called.",
            "Priya said yes.",
            "Zorblat is here.",
            "Paris is big.",
        ] {
            assert_eq!(at_start(text), None, "{text}");
        }
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
/// The compiled tables (`build.rs`) answer every lookup exactly as the maps the engine used to
/// build from the JSON at first use: every word, every deletion key, every frequency and pair.
#[cfg(test)]
mod compiled_tables {
    use super::*;
    use std::collections::HashMap;

    #[test]
    fn the_compiled_lexicon_matches_the_json_it_was_built_from() {
        let prior: serde_json::Value =
            serde_json::from_str(include_str!("../rules/frequency.json")).unwrap();
        let mut frequencies: HashMap<String, u16> = HashMap::new();
        for e in prior["entries"].as_array().unwrap() {
            frequencies.insert(e[0].as_str().unwrap().into(), e[1].as_u64().unwrap() as u16);
        }
        for (word, value) in &frequencies {
            assert_eq!(frequency(word), *value, "{word}");
        }
        assert_eq!(frequency("zzzqqx"), 0);

        let entries: Vec<(String, u8)> =
            serde_json::from_str(include_str!("../rules/lexicon.json")).unwrap();
        let mut words: HashMap<String, u8> = HashMap::new();
        let mut lowercase: HashSet<String> = HashSet::new();
        let mut canonical: HashMap<String, String> = HashMap::new();
        for (word, flags) in entries {
            let lower = word.to_lowercase();
            if word == lower {
                lowercase.insert(word.clone());
            } else if word.chars().skip(1).any(char::is_uppercase)
                && word.chars().any(char::is_lowercase)
            {
                let capitals = |w: &str| w.chars().filter(|c| c.is_uppercase()).count();
                if canonical
                    .get(&lower)
                    .is_none_or(|old| capitals(&word) > capitals(old))
                {
                    canonical.insert(lower.clone(), word.clone());
                }
            }
            *words.entry(lower).or_insert(0) |= flags;
        }
        canonical.retain(|lower, _| !lowercase.contains(lower));
        let mut deletes: HashMap<String, Vec<String>> = HashMap::new();
        for (word, flags) in &words {
            let common_form = flags & 1 != 0
                || frequencies.get(word).copied().unwrap_or(0) >= 250
                || ["s", "es", "ed", "ing"].iter().any(|suffix| {
                    word.strip_suffix(suffix).is_some_and(|stem| {
                        words.get(stem).is_some_and(|f| f & 1 != 0)
                            || words.get(&format!("{stem}e")).is_some_and(|f| f & 1 != 0)
                    })
                });
            if !common_form || word.len() > 24 || !word.bytes().all(|b| b.is_ascii_lowercase()) {
                continue;
            }
            for i in 0..word.len() {
                let deleted = format!("{}{}", &word[..i], &word[i + 1..]);
                deletes.entry(deleted).or_default().push(word.clone());
            }
        }
        let lexicon = lexicon();
        for (word, flags) in &words {
            assert_eq!(lexicon.flags(word), Some(*flags), "{word}");
            assert_eq!(lexicon.word(word), Some(word.as_str()));
            assert_eq!(lexicon.ordinary(word), lowercase.contains(word), "{word}");
            assert_eq!(
                lexicon.canonical(word),
                canonical.get(word).map(String::as_str),
                "{word}"
            );
        }
        for (deleted, values) in &mut deletes {
            values.sort();
            values.dedup();
            assert_eq!(
                &lexicon.deletes(deleted).collect::<Vec<_>>(),
                values,
                "{deleted}"
            );
        }
        assert_eq!(deletes.len(), lexicon.deletes.len());
        assert_eq!(words.len(), lexicon.words.len());
        assert_eq!(lexicon.deletes("zzzqqx").count(), 0);
        assert!(
            !lexicon.contains("zzzqqx") && !lexicon.ordinary("Hope") && lexicon.ordinary("hope")
        );

        let pairs: serde_json::Value =
            serde_json::from_str(include_str!("../rules/bigrams.json")).unwrap();
        let mut counts: HashMap<String, u64> = HashMap::new();
        for e in pairs["entries"].as_array().unwrap() {
            counts.insert(e[0].as_str().unwrap().into(), e[1].as_u64().unwrap());
        }
        for (pair, count) in &counts {
            if let Some((a, b)) = pair.split_once(' ') {
                assert_eq!(context::count(a, b), *count, "{pair}");
            }
        }
        assert_eq!(context::count("zzzqqx", "the"), 0);
    }
}
