//! The macOS app's user dictionary and names (`known-words.json`), shared by the native host and LSP
//! through `#[path]` includes. Only that one file is read; absent or invalid means no extra words.
use std::{fs, path::PathBuf, sync::Mutex, time::SystemTime};
pub const MAX_DICTIONARY: usize = 1000;
pub const MAX_NAMES: usize = 2000;
const MAX_ENTRY_BYTES: usize = 128;
const MAX_FILE_BYTES: u64 = 1 << 20;
#[derive(Clone, Default)]
pub struct KnownWords {
    pub dictionary: Vec<String>,
    pub names: Vec<String>,
    stamp: Option<SystemTime>,
}
static CACHE: Mutex<Option<KnownWords>> = Mutex::new(None);
fn path() -> Option<PathBuf> {
    let home = std::env::var_os("HOME")?;
    Some(PathBuf::from(home).join("Library/Application Support/Parzr/known-words.json"))
}
fn strings(value: &serde_json::Value) -> Vec<String> {
    value
        .as_array()
        .map(|a| {
            a.iter()
                .filter_map(|x| x.as_str().map(String::from))
                .collect()
        })
        .unwrap_or_default()
}
/// Current words, re-read only when the file's modification time changes.
pub fn current() -> KnownWords {
    let mut cache = CACHE.lock().unwrap_or_else(|e| e.into_inner());
    let cached = cache.get_or_insert_with(KnownWords::default);
    let meta = path().and_then(|p| fs::metadata(p).ok());
    let stamp = meta.as_ref().and_then(|m| m.modified().ok());
    if stamp != cached.stamp {
        *cached = KnownWords {
            stamp,
            ..KnownWords::default()
        };
        let parsed = meta
            .filter(|m| m.len() <= MAX_FILE_BYTES)
            .and_then(|_| fs::read_to_string(path()?).ok())
            .and_then(|t| serde_json::from_str::<serde_json::Value>(&t).ok());
        if let Some(v) = parsed {
            cached.dictionary = strings(&v["dictionary"]);
            cached.names = strings(&v["names"]);
        }
    }
    cached.clone()
}
/// `own` first, then `extra`: case-insensitive dedupe, entries over 128 bytes dropped, at most `cap` kept.
pub fn merge(own: Vec<String>, extra: &[String], cap: usize) -> Vec<String> {
    let mut seen = std::collections::HashSet::new();
    own.into_iter()
        .chain(extra.iter().cloned())
        .filter(|w| {
            !w.trim().is_empty() && w.len() <= MAX_ENTRY_BYTES && seen.insert(w.to_lowercase())
        })
        .take(cap)
        .collect()
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn merge_dedupes_case_insensitively_and_caps() {
        let out = merge(
            vec!["Aman".into()],
            &["aman".into(), "Jain".into(), "x".repeat(129)],
            10,
        );
        assert_eq!(out, ["Aman", "Jain"]);
        assert_eq!(merge(vec!["a".into(), "b".into()], &[], 1), ["a"]);
    }
}
