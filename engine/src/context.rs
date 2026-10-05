//! Pinned, attributed word-pair frequencies; no runtime downloads or writing logs.
use std::{collections::HashMap, sync::OnceLock};

fn counts() -> &'static HashMap<String, u64> {
    static COUNTS: OnceLock<HashMap<String, u64>> = OnceLock::new();
    COUNTS.get_or_init(|| {
        #[derive(serde::Deserialize)]
        struct Data {
            metadata: serde_json::Value,
            entries: Vec<(String, u64)>,
        }
        let data: Data = serde_json::from_str(include_str!("../rules/bigrams.json"))
            .expect("valid attributed word pairs");
        assert!(
            data.metadata["source_sha256"]
                .as_str()
                .is_some_and(|s| s.len() == 64)
        );
        data.entries.into_iter().collect()
    })
}
pub fn count(a: &str, b: &str) -> u64 {
    counts().get(&format!("{a} {b}")).copied().unwrap_or(0)
}
pub fn score(a: &str, b: &str) -> i32 {
    // Smoothed floor for pairs absent from this truncated corpus. Counts are
    // evidence for candidate ranking, never a verdict that a phrase is invalid.
    ((count(a, b).max(1_000) as f64 / 1_000.0).log10() * 30.0).round() as i32
}
