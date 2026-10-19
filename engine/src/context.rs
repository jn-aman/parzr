//! Pinned, attributed word-pair frequencies; no runtime downloads or writing logs.
use crate::table::Table;
use std::sync::OnceLock;

/// "a b" to its count, built by `build.rs` from `rules/bigrams.json` and read in place.
fn counts() -> &'static Table {
    static COUNTS: OnceLock<Table> = OnceLock::new();
    COUNTS.get_or_init(|| Table::new(include_bytes!(concat!(env!("OUT_DIR"), "/bigrams.bin"))))
}
pub fn count(a: &str, b: &str) -> u64 {
    let counts = counts();
    counts.find(&format!("{a} {b}")).map_or(0, |e| {
        u64::from_le_bytes(counts.value(e).try_into().expect("8-byte count"))
    })
}
pub fn score(a: &str, b: &str) -> i32 {
    // Smoothed floor for pairs absent from this truncated corpus. Counts are
    // evidence for candidate ranking, never a verdict that a phrase is invalid.
    ((count(a, b).max(1_000) as f64 / 1_000.0).log10() * 30.0).round() as i32
}
