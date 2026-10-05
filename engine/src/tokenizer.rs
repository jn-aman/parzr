use regex::Regex;
use serde::{Deserialize, Serialize};
use std::{collections::HashMap, sync::OnceLock};

#[derive(Clone, Debug, Serialize, Deserialize, Default)]
pub struct TokenHint {
    pub start_utf16: usize,
    pub end_utf16: usize,
    pub pos: String,
    #[serde(default)]
    pub lemma: String,
    #[serde(default)]
    pub name: bool,
}
#[derive(Clone, Debug)]
#[cfg_attr(feature = "local-model", allow(dead_code))] // Research checker metadata; production only uses protection coordinates.
pub struct Token<'a> {
    pub surface: &'a str,
    pub normalized: String,
    pub start_byte: usize,
    pub end_byte: usize,
    pub start_utf16: usize,
    pub end_utf16: usize,
    pub sentence: usize,
    pub paragraph: usize,
    pub is_word: bool,
    pub pos: String,
    pub lemma: String,
    pub proper_name: bool,
}
/// A period that closes an abbreviation ("p.m.", "U.S.", "Mr.", "etc.") rather than a sentence.
/// It ends a sentence only before a capitalized word, and never after a title.
pub fn abbreviation_continues(text: &str, dot: usize) -> bool {
    const TITLES: [&str; 6] = ["mr", "mrs", "ms", "dr", "prof", "mt"];
    const ABBREVIATIONS: [&str; 16] = [
        "vs", "etc", "approx", "incl", "inc", "ltd", "co", "cf", "viz", "esp", "fig", "dept",
        "govt", "st", "jr", "sr",
    ];
    let head = &text[..dot];
    let start = head
        .char_indices()
        .rev()
        .take_while(|(_, c)| c.is_alphabetic() || *c == '.')
        .last()
        .map_or(dot, |(i, _)| i);
    let run = &head[start..];
    let lower = run.to_lowercase();
    // The "p." of "p.m." is one letter, a dot and another letter with no space.
    if run.chars().count() == 1 && text[dot + 1..].starts_with(char::is_alphabetic) {
        return true;
    }
    let dotted = run.contains('.') && run.split('.').all(|part| part.chars().count() == 1);
    let title = TITLES.contains(&lower.as_str());
    // An initial ("B. subg.") but never the pronoun "I".
    let initial = run.chars().count() == 1 && run != "I" && run.starts_with(char::is_uppercase);
    if !(dotted || title || initial || ABBREVIATIONS.contains(&lower.as_str())) {
        return false;
    }
    title
        || !text[dot + 1..]
            .trim_start_matches([' ', '\t'])
            .starts_with(char::is_uppercase)
}
pub fn tokenize<'a>(text: &'a str, hints: &[TokenHint]) -> Vec<Token<'a>> {
    static RE: OnceLock<Regex> = OnceLock::new();
    let regex = RE.get_or_init(|| {
        Regex::new(r"[\p{L}]+(?:['’][\p{L}]+)*|\d+(?:[.,]\d+)*|[^\s]")
            .expect("constant token regex")
    });
    let indexed: HashMap<(usize, usize), &TokenHint> = hints
        .iter()
        .map(|h| ((h.start_utf16, h.end_utf16), h))
        .collect();
    let mut tokens = Vec::new();
    let mut offset = 0;
    let mut previous_byte = 0;
    let mut sentence = 0;
    let mut paragraph = 0;
    for m in regex.find_iter(text) {
        let gap = &text[previous_byte..m.start()];
        offset += gap.encode_utf16().count();
        let breaks = gap.chars().filter(|c| *c == '\n').count();
        if breaks > 0 {
            paragraph += breaks;
            sentence += 1;
        }
        let end = offset + m.as_str().encode_utf16().count();
        // "Aman's" is one token here but two for the tagger: the possessive inherits the base hint.
        let hint = indexed.get(&(offset, end)).copied().or_else(|| {
            let base = m.as_str().find(['\'', '’'])?;
            let base_end = offset + m.as_str()[..base].encode_utf16().count();
            indexed.get(&(offset, base_end)).copied()
        });
        tokens.push(Token {
            surface: m.as_str(),
            normalized: m.as_str().to_lowercase().replace('’', "'"),
            start_byte: m.start(),
            end_byte: m.end(),
            start_utf16: offset,
            end_utf16: end,
            sentence,
            paragraph,
            is_word: m.as_str().chars().next().is_some_and(char::is_alphabetic),
            pos: hint.map(|h| h.pos.clone()).unwrap_or_default(),
            lemma: hint.map(|h| h.lemma.clone()).unwrap_or_default(),
            proper_name: hint.is_some_and(|h| h.name) && !crate::names::never_a_name(m.as_str()),
        });
        if [".", "!", "?"].contains(&m.as_str())
            && !(m.as_str() == "." && abbreviation_continues(text, m.start()))
        {
            sentence += 1;
        }
        offset = end;
        previous_byte = m.end();
    }
    // A lowercase name hint comes only from the system-lexicon gate ("rakesh" fails, "Rakesh"
    // passes). Surnames such as Tran and Appel also pass, so clear typo evidence wins.
    for i in 0..tokens.len() {
        let t = &tokens[i];
        if t.proper_name && t.surface.chars().all(|c| !c.is_uppercase()) {
            let prev = tokens[..i]
                .iter()
                .rev()
                .find(|p| p.is_word)
                .map_or("", |p| p.normalized.as_str());
            if crate::spelling::hinted_name_is_typo(&t.normalized, prev) {
                tokens[i].proper_name = false;
            }
        }
    }
    tokens
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn abbreviation_periods_do_not_split_sentences() {
        let ids = |text: &str| -> Vec<usize> {
            tokenize(text, &[])
                .iter()
                .filter(|t| t.is_word)
                .map(|t| t.sentence)
                .collect()
        };
        // One sentence each: titles, dotted abbreviations, "etc." before a lowercase word.
        for text in [
            "We met Dr. Rao at 5 p.m. today.",
            "She teaches U.S. history.",
            "Bring tea, etc. and cake.",
            "Ask Mr. Lee about it.",
        ] {
            let ids = ids(text);
            assert!(ids.iter().all(|s| *s == ids[0]), "{text}");
        }
        // A real sentence end after an abbreviation still splits before a capital.
        let ids_end = ids("We left at 5 p.m. The rain stopped.");
        assert_ne!(ids_end[0], *ids_end.last().unwrap());
        let ids_plain = ids("I like tea. I like cake.");
        assert_ne!(ids_plain[0], *ids_plain.last().unwrap());
    }
}
