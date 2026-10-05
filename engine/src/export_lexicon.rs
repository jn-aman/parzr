//! Maintenance-only dictionary exporter; never linked into the app.
use harper_core::{
    Dialect,
    spell::{Dictionary, FstDictionary},
};
fn main() {
    let dictionary = FstDictionary::curated();
    let mut words = Vec::new();
    for chars in dictionary.words_iter() {
        let word: String = chars.iter().collect();
        if !word
            .chars()
            .all(|c| c.is_ascii_alphabetic() || c == '\'' || c == '-')
        {
            continue;
        }
        let Some(meta) = dictionary.get_word_metadata(chars) else {
            continue;
        };
        let mut flags = 0u8;
        if meta.common {
            flags |= 1;
        }
        if meta.is_noun() {
            flags |= 2;
        }
        if meta.is_verb() {
            flags |= 4;
        }
        if meta.is_adjective() {
            flags |= 8;
        }
        if meta.is_plural_noun() {
            flags |= 16;
        }
        if meta.is_proper_noun() {
            flags |= 32;
        }
        if meta.dialects.is_dialect_enabled(Dialect::American) {
            flags |= 64;
        }
        if meta.dialects.is_dialect_enabled(Dialect::British) {
            flags |= 128;
        }
        words.push((word, flags));
    }
    words.sort();
    words.dedup();
    println!("{}", serde_json::to_string(&words).expect("export fixture"));
}
