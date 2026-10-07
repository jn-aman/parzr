//! Capitals the writer left out or added by mistake: proper nouns typed in lowercase ("paris",
//! "new york", "github"), months that are also words in a date frame ("march 3", "in august"),
//! seasons capitalized inside a sentence ("in Summer") and a list after a colon that opens with a
//! stray capital ("three options: Keep, merge, or delete").
use crate::tokenizer::Token;
use crate::{Edit, Request, make_edit, morphology, spelling, starts_sentence};
use std::{collections::HashMap, sync::OnceLock};

/// Lowercase proper nouns whose usual reading is the proper noun, though the lexicon also lists
/// a rare common word ("japan" lacquer, "french" a verb).
const USUALLY_PROPER: [&str; 4] = ["japan", "french", "thanksgiving", "christian"];
type Entries = HashMap<String, Vec<(Vec<String>, Vec<&'static str>)>>;
/// Gazetteer entries keyed by their first lowercase word, longest first.
fn gazetteer() -> &'static Entries {
    static ENTRIES: OnceLock<Entries> = OnceLock::new();
    ENTRIES.get_or_init(|| {
        let mut entries: Entries = HashMap::new();
        for line in include_str!("../rules/proper-nouns.txt").lines() {
            if line.starts_with('#') || line.trim().is_empty() {
                continue;
            }
            let parts: Vec<&'static str> = line.split(' ').collect();
            let lower: Vec<String> = parts.iter().map(|p| p.to_lowercase()).collect();
            entries
                .entry(lower[0].clone())
                .or_default()
                .push((lower, parts));
        }
        for list in entries.values_mut() {
            list.sort_by_key(|(lower, _)| std::cmp::Reverse(lower.len()));
        }
        entries
    })
}
/// The usual spelling of a one-word proper noun ("github" to "GitHub").
pub fn proper_noun(lower: &str) -> Option<&'static str> {
    gazetteer()
        .get(lower)?
        .iter()
        .find(|(parts, _)| parts.len() == 1)
        .map(|(_, canonical)| canonical[0])
}
/// Chat interjections that take the sentence's capital like any word ("lol" to "Lol").
pub fn interjection(word: &str) -> bool {
    [
        "lol", "haha", "hahaha", "hehe", "hmm", "hmmm", "ugh", "yay", "yup", "yep", "nope", "ok",
        "okay", "yeah", "nah", "wow", "oops", "aww", "meh",
    ]
    .contains(&word)
}
/// A salutation or closing that opens its own line ending in a comma ("dear Ms. Chen,",
/// "best regards,"): it takes a capital though the line has no sentence punctuation.
pub fn salutation(text: &str, token: &Token<'_>) -> bool {
    let line = text[token.start_byte..].split('\n').next().unwrap_or("");
    [
        "dear",
        "hi",
        "hello",
        "hey",
        "greetings",
        "regards",
        "sincerely",
        "best",
        "cheers",
        "thanks",
        "warm",
        "kind",
    ]
    .contains(&token.normalized.as_str())
        && line.trim_end().ends_with(',')
        && line.split_whitespace().count() <= 6
}
/// A token glued to code, a path, an address or a number ("x.paris", "github.com", "uk_2").
fn glued(text: &str, token: &Token<'_>) -> bool {
    let before = text[..token.start_byte].chars().next_back();
    let rest = &text[token.end_byte..];
    let after = rest.chars().next();
    before.is_some_and(|c| "._/@#\\-$".contains(c) || c.is_alphanumeric())
        || after.is_some_and(|c| "_/@\\".contains(c) || c.is_ascii_digit())
        || rest.starts_with('.') && rest[1..].starts_with(|c: char| c.is_alphanumeric())
}
fn upper_first(word: &str) -> String {
    let mut chars = word.chars();
    chars
        .next()
        .map(|c| c.to_uppercase().collect::<String>() + chars.as_str())
        .unwrap_or_default()
}
fn lower_first(word: &str) -> String {
    let mut chars = word.chars();
    chars
        .next()
        .map(|c| c.to_lowercase().collect::<String>() + chars.as_str())
        .unwrap_or_default()
}
fn push(
    req: &Request,
    edits: &mut Vec<Edit>,
    token: &Token<'_>,
    replacement: String,
    (id, reason): (&str, &str),
) {
    if let Some(e) = make_edit(
        &req.text,
        token.start_utf16,
        token.end_utf16,
        replacement,
        "Capitalization",
        id,
        reason,
        0.96,
    ) {
        edits.push(e);
    }
}
const PROPER: (&str, &str) = (
    "grammar.proper_noun_capitalization",
    "Names of places, languages, holidays and brands take a capital letter.",
);
const MONTH: (&str, &str) = (
    "grammar.calendar_capitalization",
    "Days and months take a capital letter.",
);
const SEASON: (&str, &str) = (
    "grammar.season_lowercase",
    "Seasons are not capitalized in running text.",
);
const AFTER_COLON: (&str, &str) = (
    "grammar.colon_lowercase",
    "A list or phrase after a colon starts with a lowercase letter.",
);
fn word_at<'t>(tokens: &'t [Token<'_>], at: Option<usize>, paragraph: usize) -> &'t str {
    at.and_then(|i| tokens.get(i))
        .filter(|t| t.is_word && t.paragraph == paragraph)
        .map_or("", |t| t.normalized.as_str())
}
/// A day of the month right after a token ("march 3", "may 5th"), not a time ("may 3:30").
fn day_number(text: &str, tokens: &[Token<'_>], at: usize) -> bool {
    let Some(t) = tokens.get(at) else {
        return false;
    };
    let rest = &text[t.end_byte..];
    t.surface
        .parse::<u32>()
        .is_ok_and(|n| (1..=31).contains(&n))
        && !rest.starts_with([':', '%', '/', '-'])
        && !(rest.starts_with('.') && rest[1..].starts_with(|c: char| c.is_ascii_digit()))
}
const MONTH_LEADS: [&str; 12] = [
    "in", "since", "until", "till", "during", "from", "through", "early", "late", "mid", "before",
    "after",
];
const WEEKDAYS: [&str; 7] = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
];
/// "march", "may" and "august" are words; as months they sit in a date frame.
fn month(text: &str, tokens: &[Token<'_>], i: usize) -> bool {
    let token = &tokens[i];
    let prev = word_at(tokens, i.checked_sub(1), token.paragraph);
    let next_number = day_number(text, tokens, i + 1);
    let prev_number = i > 0 && day_number(text, tokens, i - 1);
    let after_weekday = i >= 2
        && tokens[i - 1].surface == ","
        && WEEKDAYS.contains(&tokens[i - 2].normalized.as_str());
    let next = word_at(tokens, Some(i + 1), token.paragraph);
    match token.normalized.as_str() {
        "march" | "august" => next_number || prev_number || MONTH_LEADS.contains(&prev),
        // "may" is a modal: only a preposition or a date says it is the month.
        "may" => {
            // "put in may be lost" is a modal after a particle; "in may last year" is the month.
            MONTH_LEADS.contains(&prev)
                && !(morphology::verb(next).is_some_and(|v| v.base == next)
                    && spelling::flags(next) & (2 | 8) == 0)
                || next_number && (MONTH_LEADS.contains(&prev) || prev == "on" || after_weekday)
                || prev_number
        }
        _ => false,
    }
}
const SEASONS: [&str; 5] = ["summer", "winter", "spring", "fall", "autumn"];
const SEASON_LEADS: [&str; 19] = [
    "in", "this", "last", "next", "every", "the", "during", "of", "early", "late", "mid", "until",
    "since", "by", "for", "over", "through", "before", "after",
];
/// A season capitalized inside a sentence ("in Summer", "the Fall semester"), not a name or a
/// title ("Summer Olympics", "Fall 2025", "the Fall of Rome").
fn stray_season(req: &Request, tokens: &[Token<'_>], i: usize) -> bool {
    let token = &tokens[i];
    let surface = token.surface;
    let next = tokens.get(i + 1);
    let prev = word_at(tokens, i.checked_sub(1), token.paragraph);
    SEASONS.contains(&token.normalized.as_str())
        && surface.starts_with(char::is_uppercase)
        && surface.chars().skip(1).all(char::is_lowercase)
        && !token.proper_name
        && !starts_sentence(&req.text, token.start_byte, req)
        && SEASON_LEADS.contains(&prev)
        && match next {
            Some(n) if n.is_word && n.paragraph == token.paragraph => {
                n.surface.starts_with(char::is_lowercase) && n.normalized != "of"
            }
            Some(n) => prev != "the" && !n.surface.starts_with(|c: char| c.is_ascii_digit()),
            None => prev != "the",
        }
}
/// Words that make the text after a colon a clause of its own, which may keep its capital.
const CLAUSE_WORDS: [&str; 40] = [
    "is", "are", "was", "were", "am", "be", "been", "has", "have", "had", "will", "would", "can",
    "could", "should", "shall", "may", "might", "must", "do", "does", "did", "i", "you", "he",
    "she", "we", "they", "it", "there", "this", "that", "i'm", "it's", "we're", "they're",
    "you're", "he's", "she's", "that's",
];
/// A capital that opens a short lowercase list or phrase after a colon in running text ("three
/// options: Keep, merge, or delete"). A label ("Note: The office..."), a clause, a name or a
/// capitalized list keeps its capitals.
fn stray_capital_after_colon(req: &Request, tokens: &[Token<'_>], i: usize) -> bool {
    let token = &tokens[i];
    let word = token.normalized.as_str();
    let Some(colon) = i.checked_sub(1).map(|c| &tokens[c]) else {
        return false;
    };
    if colon.surface != ":"
        || req.text[colon.end_byte..token.start_byte] != *" "
        || token.proper_name
        || !token.surface.starts_with(char::is_uppercase)
        || !token.surface.chars().skip(1).all(char::is_lowercase)
        || !spelling::ordinary(word)
        || CLAUSE_WORDS.contains(&word)
    {
        return false;
    }
    let before = tokens[..i - 1]
        .iter()
        .rev()
        .take_while(|t| t.sentence == colon.sentence && t.paragraph == colon.paragraph)
        .filter(|t| t.is_word)
        .count();
    let rest: Vec<&Token<'_>> = tokens[i + 1..]
        .iter()
        .take_while(|t| t.sentence == token.sentence && t.paragraph == token.paragraph)
        .filter(|t| t.is_word)
        .collect();
    before >= 3
        && rest.len() <= 10
        && rest.iter().all(|t| {
            t.surface.starts_with(char::is_lowercase)
                && !CLAUSE_WORDS.contains(&t.normalized.as_str())
        })
}
pub fn check(req: &Request, tokens: &[Token<'_>], edits: &mut Vec<Edit>) {
    let text = req.text.as_str();
    // Roman Hindi is written in lowercase and shares words with the gazetteer ("maine" is "I
    // did"), so a sentence with Hinglish in it keeps the writer's case.
    let hinglish: Vec<(usize, usize)> = tokens
        .iter()
        .filter(|t| t.is_word && spelling::hinglish(&t.normalized))
        .map(|t| (t.paragraph, t.sentence))
        .collect();
    let mut i = 0;
    while i < tokens.len() {
        let token = &tokens[i];
        if !token.is_word
            || glued(text, token)
            || hinglish.contains(&(token.paragraph, token.sentence))
        {
            i += 1;
            continue;
        }
        // A proper noun from the gazetteer, one or more words separated by single spaces.
        let base = token
            .normalized
            .strip_suffix("'s")
            .unwrap_or(&token.normalized);
        let mut matched = 0;
        if let Some(list) = gazetteer()
            .get(token.normalized.as_str())
            .or_else(|| gazetteer().get(base))
        {
            for (lower, canonical) in list {
                let n = lower.len();
                let Some(span) = tokens.get(i..i + n) else {
                    continue;
                };
                let fits = span.iter().enumerate().all(|(k, t)| {
                    let word = if k + 1 == n {
                        t.normalized.strip_suffix("'s").unwrap_or(&t.normalized)
                    } else {
                        t.normalized.as_str()
                    };
                    t.is_word
                        && word == lower[k]
                        && (k == 0 || text[span[k - 1].end_byte..t.start_byte] == *" ")
                }) && !glued(text, &span[n - 1]);
                let ordinary_word =
                    n == 1 && spelling::ordinary(&lower[0]) && !USUALLY_PROPER.contains(&base);
                if !fits || ordinary_word {
                    continue;
                }
                // Lowercase words take the usual spelling; capitals the writer typed stay.
                for (k, t) in span.iter().enumerate() {
                    if t.surface.chars().any(char::is_uppercase) {
                        continue;
                    }
                    let suffix = &t.surface[lower[k].len().min(t.surface.len())..];
                    push(req, edits, t, format!("{}{suffix}", canonical[k]), PROPER);
                }
                matched = n;
                break;
            }
        }
        if matched > 0 {
            i += matched;
            continue;
        }
        if token.surface == token.normalized
            && ["march", "may", "august"].contains(&token.surface)
            && month(text, tokens, i)
        {
            push(req, edits, token, upper_first(token.surface), MONTH);
        } else if stray_season(req, tokens, i) {
            push(req, edits, token, lower_first(token.surface), SEASON);
        } else if stray_capital_after_colon(req, tokens, i) {
            push(req, edits, token, lower_first(token.surface), AFTER_COLON);
        }
        i += 1;
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
    fn gazetteer_entries_are_proper_nouns_only() {
        let mut seen = std::collections::HashSet::new();
        for line in include_str!("../rules/proper-nouns.txt").lines() {
            if line.starts_with('#') {
                continue;
            }
            let lower = line.to_lowercase();
            assert!(seen.insert(lower.clone()), "{line} listed twice");
            assert!(line.chars().any(char::is_uppercase), "{line}");
            if !lower.contains(' ') {
                assert!(
                    !spelling::ordinary(&lower) || USUALLY_PROPER.contains(&lower.as_str()),
                    "{line} is also an ordinary word"
                );
            }
        }
    }
    #[test]
    fn lowercase_proper_nouns_are_capitalized() {
        for (input, output) in [
            (
                "We moved to toronto last year.",
                "We moved to Toronto last year.",
            ),
            (
                "She speaks fluent portuguese.",
                "She speaks fluent Portuguese.",
            ),
            (
                "The office in new jersey is closed.",
                "The office in New Jersey is closed.",
            ),
            ("I bought a new ipad.", "I bought a new iPad."),
            (
                "Check the repo on gitlab first.",
                "Check the repo on GitLab first.",
            ),
            (
                "We celebrate diwali and christmas.",
                "We celebrate Diwali and Christmas.",
            ),
            (
                "Our kenya's office opens soon.",
                "Our Kenya's office opens soon.",
            ),
            (
                "The flight from Los angeles landed.",
                "The flight from Los Angeles landed.",
            ),
        ] {
            assert_eq!(fixed(input), output, "{input}");
        }
        for text in [
            "See https://example.com/paris for details.",
            "Open london.csv in the editor.",
            "The china cabinet is old.",
            "We need some polish on the slides.",
            "Use the new_york_data table.",
            "Tag it #texas.",
        ] {
            assert_eq!(fixed(text), text, "{text}");
        }
    }
    #[test]
    fn months_seasons_and_colon_lists() {
        for (input, output) in [
            ("The launch is on march 12.", "The launch is on March 12."),
            ("We met in august.", "We met in August."),
            ("Rent is due 1 march.", "Rent is due 1 March."),
            ("It opens in may next year.", "It opens in May next year."),
            ("The gym is busy in Winter.", "The gym is busy in winter."),
            (
                "Classes start this Autumn term.",
                "Classes start this autumn term.",
            ),
            (
                "Pick one of the colors: Red, blue or green.",
                "Pick one of the colors: red, blue or green.",
            ),
        ] {
            assert_eq!(fixed(input), output, "{input}");
        }
        for text in [
            "You may 3D print it.",
            "It may rain later.",
            "They march at dawn.",
            "I met Summer at the cafe.",
            "Applications for Fall 2025 are open.",
            "The Spring Festival starts soon.",
            "Note: The office is closed.",
            "We visited three cities: Rome, Florence and Venice.",
            "There is one rule here: Do not run.",
            "Here is the thing: It is broken.",
        ] {
            assert_eq!(fixed(text), text, "{text}");
        }
    }
}
