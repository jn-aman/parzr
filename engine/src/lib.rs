//! Parzr's hybrid writing engine. Every adapter shares UTF-16 edits and local language hints.
mod context;
#[cfg(feature = "local-model")]
mod gec;
#[cfg(feature = "local-model")]
mod gec_text;
#[cfg(feature = "local-model")]
mod model;
mod morphology;
mod names;
mod pipeline;
mod punctuation;
mod real_word;
mod rules;
mod spelling;
mod structure;
mod tokenizer;
pub use names::NameIndex;
use regex::Regex;
use serde::{Deserialize, Serialize};
pub(crate) use spelling::AUTO_CAPITAL_HINT;
use std::time::Instant;
use std::{
    ffi::{CStr, CString, c_char},
    panic::{AssertUnwindSafe, catch_unwind},
    sync::{Arc, OnceLock},
};
pub use tokenizer::TokenHint;
pub const MAX_TEXT_BYTES: usize = 65_536;
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Deserialize, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum Mode {
    #[default]
    Fix,
    Professional,
    Friendly,
    Concise,
    Direct,
}
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Request {
    pub text: String,
    #[serde(default)]
    pub mode: Mode,
    #[serde(default)]
    pub dictionary: Vec<String>,
    /// Names the user or app knows (own name, contacts, document names). A name may only receive
    /// case changes. At most 2000 entries of 128 bytes each; a request over either limit is rejected.
    #[serde(default)]
    pub names: Vec<String>,
    /// Also suggest capitalizing a known name typed in lowercase ("aman jain" to "Aman Jain").
    #[serde(default)]
    pub capitalize_names: bool,
    #[serde(default)]
    pub dialect: String,
    #[serde(default)]
    pub protected_ranges: Vec<TextRange>,
    #[serde(default)]
    pub tokens: Vec<TokenHint>,
    #[serde(default = "yes")]
    pub sentence_start: bool,
    #[serde(default = "yes")]
    pub sentence_end: bool,
    /// Explicit passage checks request model context; passive typing stays on the fast engine.
    #[serde(default)]
    pub deep: bool,
    /// Also run the on-device grammar model (GECToR) beside the rules in Fix mode. Without its
    /// files or the native runtime this does nothing.
    #[serde(default)]
    pub gec: bool,
    /// Names and dictionary folded once per request and shared by every pass.
    #[serde(skip)]
    #[doc(hidden)]
    pub name_index: Option<Arc<NameIndex>>,
}
impl Request {
    fn names_index(&self) -> Arc<names::NameIndex> {
        self.name_index
            .clone()
            .unwrap_or_else(|| Arc::new(names::NameIndex::new(self)))
    }
    /// A copy that carries its name index, so passes over rewritten text never rebuild it.
    fn indexed(&self) -> Request {
        Request {
            name_index: Some(self.names_index()),
            ..self.clone()
        }
    }
}
impl Default for Request {
    fn default() -> Self {
        Self {
            text: String::new(),
            mode: Mode::Fix,
            dictionary: vec![],
            names: vec![],
            capitalize_names: false,
            dialect: String::new(),
            protected_ranges: vec![],
            tokens: vec![],
            sentence_start: true,
            sentence_end: true,
            deep: false,
            gec: false,
            name_index: None,
        }
    }
}

pub fn rewrite(req: &Request) -> Result<RewriteResult, String> {
    #[cfg(feature = "local-model")]
    if req.tokens.is_empty() && !req.text.is_empty() {
        if req.text.len() > MAX_TEXT_BYTES {
            return Err("Select at most 64 KB of text.".into());
        }
        let mut enriched = req.clone();
        enriched.tokens = model::linguistic_hints(&req.text)?;
        return pipeline::rewrite(&enriched);
    }
    pipeline::rewrite(req)
}

/// Cancel an in-flight local inference. No editor mutation happens in the engine.
#[unsafe(no_mangle)]
pub extern "C" fn parzr_cancel_rewrite() {
    #[cfg(feature = "local-model")]
    model::cancel();
}

/// Loads the on-device grammar model (and compiles it on first use) so the first check is fast.
/// Safe to call from any thread, repeatedly. Returns 1 when the model is ready, else 0.
#[unsafe(no_mangle)]
pub extern "C" fn parzr_gec_warm() -> i32 {
    #[cfg(feature = "local-model")]
    if catch_unwind(gec::warm).unwrap_or(false) {
        return 1;
    }
    0
}

fn yes() -> bool {
    true
}
#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct TextRange {
    pub start_utf16: usize,
    pub end_utf16: usize,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Edit {
    pub start_utf16: usize,
    pub end_utf16: usize,
    pub replacement: String,
    pub original: String,
    pub category: String,
    pub rule_id: String,
    pub explanation: String,
    pub confidence: f32,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub group_id: Option<String>,
}
#[derive(Debug, Serialize, Deserialize)]
pub struct SourceMapping {
    pub input_start_utf16: usize,
    pub input_end_utf16: usize,
    pub output_start_utf16: usize,
    pub output_end_utf16: usize,
    pub changed: bool,
}
#[derive(Debug, Serialize, Deserialize)]
pub struct RewriteResult {
    pub version: String,
    pub text: String,
    pub edits: Vec<Edit>,
    pub source_map: Vec<SourceMapping>,
    pub elapsed_ms: f64,
    pub protected_count: usize,
    #[serde(default)]
    pub warnings: Vec<String>,
}
#[derive(Debug)]
pub struct ToneProfile {
    pub formality: f32,
    pub politeness: f32,
    pub directness: f32,
    pub contractions: f32,
    pub verbosity: f32,
    pub hedging: f32,
}
impl Mode {
    pub fn profile(self) -> ToneProfile {
        match self {
            Mode::Fix => ToneProfile {
                formality: 0.5,
                politeness: 0.5,
                directness: 0.5,
                contractions: 0.5,
                verbosity: 0.5,
                hedging: 0.5,
            },
            Mode::Professional => ToneProfile {
                formality: 1.0,
                politeness: 0.8,
                directness: 0.5,
                contractions: 0.0,
                verbosity: 0.5,
                hedging: 0.3,
            },
            Mode::Friendly => ToneProfile {
                formality: 0.3,
                politeness: 1.0,
                directness: 0.3,
                contractions: 1.0,
                verbosity: 0.6,
                hedging: 0.5,
            },
            Mode::Concise => ToneProfile {
                formality: 0.5,
                politeness: 0.6,
                directness: 0.8,
                contractions: 0.5,
                verbosity: 0.0,
                hedging: 0.0,
            },
            Mode::Direct => ToneProfile {
                formality: 0.5,
                politeness: 0.3,
                directness: 1.0,
                contractions: 0.5,
                verbosity: 0.1,
                hedging: 0.0,
            },
        }
    }
}
fn utf16_at(text: &str, byte: usize) -> usize {
    text[..byte].encode_utf16().count()
}
fn byte_at(text: &str, offset: usize) -> Option<usize> {
    let mut n = 0;
    for (byte, c) in text.char_indices() {
        if n == offset {
            return Some(byte);
        }
        n += c.len_utf16();
        if n > offset {
            return None;
        }
    }
    (n == offset).then_some(text.len())
}
fn overlaps(start: usize, end: usize, r: &TextRange) -> bool {
    if start == end {
        start >= r.start_utf16 && start < r.end_utf16
    } else {
        start < r.end_utf16 && end > r.start_utf16
    }
}
fn protection_regex() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(||Regex::new(r"(?ms)```.*?(?:```|\z)|~~~.*?(?:~~~|\z)|`[^`\n]*(?:`|$)|(?:https?://|www\.)[^\s<>]+|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|\B[@#]\w(?:[\w.-]*\w)?|(?:/|~/|[A-Za-z]:\\)[\w./\\-]+|\b\d+(?:[.,:/-]\d+)*\b|(?m)^>[^\n]*|(?m)^-- ?$[\s\S]*|(?m)^\s*(?:curl|git|npm|npx|cargo|sudo|python3?|ssh|brew)\s[^\n]*(?:\\\n[^\n]*)*|[\u{FFFC}]").expect("constant protected-span regex"))
}
fn protected_ranges(req: &Request) -> Vec<TextRange> {
    let tokens = tokenizer::tokenize(&req.text, &req.tokens);
    protected_ranges_for(req, &tokens, &req.names_index())
}
fn protected_ranges_for(
    req: &Request,
    tokens: &[tokenizer::Token<'_>],
    index: &names::NameIndex,
) -> Vec<TextRange> {
    let mut spans = req.protected_ranges.clone();
    for m in protection_regex().find_iter(&req.text) {
        spans.push(TextRange {
            start_utf16: utf16_at(&req.text, m.start()),
            end_utf16: utf16_at(&req.text, m.end()),
        });
    }
    // Dictionary words (also multi-word and hyphenated entries) stay exactly as typed; other names
    // the tagger found are protected up to their possessive boundary.
    let dictionary = index.dictionary_hits(tokens);
    for (i, token) in tokens.iter().enumerate() {
        if dictionary[i] {
            match spans.last_mut() {
                Some(last)
                    if i > 0 && dictionary[i - 1] && last.end_utf16 == tokens[i - 1].end_utf16 =>
                {
                    last.end_utf16 = token.end_utf16
                }
                _ => spans.push(TextRange {
                    start_utf16: token.start_utf16,
                    end_utf16: token.end_utf16,
                }),
            }
        } else if token.proper_name {
            spans.push(TextRange {
                start_utf16: token.start_utf16,
                end_utf16: possessive_boundary(token)
                    .map(|n| token.start_utf16 + n)
                    .unwrap_or(token.end_utf16),
            });
        }
    }
    spans
}
/// Original-coordinate spans of every name candidate (even a guess from context), for passes that
/// cannot be told to leave a name alone, such as the local model.
#[cfg(feature = "local-model")]
fn name_guard_ranges(req: &Request) -> Vec<TextRange> {
    let tokens = tokenizer::tokenize(&req.text, &req.tokens);
    let level = req.names_index().mark(&req.text, &tokens);
    tokens
        .iter()
        .zip(level)
        .filter(|(_, l)| *l >= names::WEAK)
        .map(|(t, _)| TextRange {
            start_utf16: t.start_utf16,
            end_utf16: t.end_utf16,
        })
        .collect()
}
fn possessive_boundary(token: &tokenizer::Token<'_>) -> Option<usize> {
    spelling::possessive_boundary(token)
}
/// Original-coordinate structural spans for adapters analyzing a document selection.
pub fn protected_spans(req: &Request) -> Vec<TextRange> {
    #[allow(unused_mut)]
    let mut spans = protected_ranges(req);
    #[cfg(feature = "local-model")]
    {
        static EMOJI: OnceLock<Regex> = OnceLock::new();
        for m in EMOJI
            .get_or_init(|| {
                Regex::new(r"[\p{Extended_Pictographic}\p{Emoji_Modifier}\u{200D}\u{FE0F}]+")
                    .expect("constant emoji regex")
            })
            .find_iter(&req.text)
        {
            spans.push(TextRange {
                start_utf16: utf16_at(&req.text, m.start()),
                end_utf16: utf16_at(&req.text, m.end()),
            });
        }
    }
    spans
}
#[expect(
    clippy::too_many_arguments,
    reason = "Constructor mirrors the edit contract; fields remain explicit at rule call sites."
)]
fn make_edit(
    text: &str,
    start: usize,
    end: usize,
    replacement: String,
    category: &str,
    id: &str,
    reason: &str,
    confidence: f32,
) -> Option<Edit> {
    let a = byte_at(text, start)?;
    let b = byte_at(text, end)?;
    let original = text.get(a..b)?.to_string();
    if original == replacement {
        return None;
    }
    Some(Edit {
        start_utf16: start,
        end_utf16: end,
        replacement,
        original,
        category: category.into(),
        rule_id: id.into(),
        explanation: reason.into(),
        confidence,
        group_id: None,
    })
}
/// Days and months that are never ordinary words ("may", "march" and "august" are).
const CALENDAR_PROPER: [&str; 16] = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
    "january",
    "february",
    "april",
    "june",
    "july",
    "september",
    "october",
    "november",
    "december",
];
fn upper_first(s: &str) -> String {
    let mut chars = s.chars();
    match chars.next() {
        Some(c) => c.to_uppercase().to_string() + chars.as_str(),
        None => String::new(),
    }
}
/// A capitalized known misspelling mid-sentence ("for Teh meeting") was a slip of the Shift key,
/// not a name: its correction is lowercase. Sentence starts and ALL-CAPS keep their case.
fn typo_capital(replacement: String, original: &str, at_start: bool) -> String {
    let letters: Vec<char> = original.chars().filter(|c| c.is_alphabetic()).collect();
    let capitalized = letters.first().is_some_and(|c| c.is_uppercase())
        && letters.iter().skip(1).all(|c| !c.is_uppercase());
    if !at_start && capitalized && names::is_name_typo(&original.to_lowercase()) {
        replacement.to_lowercase()
    } else {
        replacement
    }
}
fn match_case(replacement: &str, original: &str) -> String {
    if original
        .chars()
        .filter(|c| c.is_alphabetic())
        .all(char::is_uppercase)
        && original.chars().filter(|c| c.is_alphabetic()).count() > 1
    {
        replacement.to_uppercase()
    } else if original.chars().next().is_some_and(char::is_uppercase) {
        upper_first(replacement)
    } else {
        replacement.to_string()
    }
}
fn has_clause_start(text: &str) -> bool {
    // A typed clause can be capitalized before final punctuation. Keep standalone
    // fragments unchanged and respect sentence_start at the caller.
    static PREFIX: OnceLock<Regex> = OnceLock::new();
    PREFIX.get_or_init(|| Regex::new(r"(?i)^(?:this|that|it|he|she|we|they|you|there|here)\s+(?:am|is|are|was|were|have|has|had|do|does|did|can|could|will|would|should|must)\b").expect("constant clause prefix")).is_match(text)
}

fn starts_sentence(text: &str, byte: usize, req: &Request) -> bool {
    let before = text[..byte].trim_end_matches([' ', '\t']);
    if before.is_empty() {
        return req.sentence_start;
    }
    before.ends_with(['.', '!', '?', '\n'])
        && !(before.ends_with('.')
            && tokenizer::abbreviation_continues(text, before.len() - 1)
            && !text[byte..].starts_with(char::is_uppercase))
}
fn rewrite_once(req: &Request, tone_only: bool) -> Result<RewriteResult, String> {
    let started = Instant::now();
    if req.text.len() > MAX_TEXT_BYTES {
        return Err("Select at most 64 KB of text.".into());
    }
    if req.dictionary.len() > 1000 || req.dictionary.iter().any(|x| x.len() > 128) {
        return Err("Dictionary exceeds its size limit.".into());
    }
    if req.names.len() > names::MAX_NAMES
        || req.names.iter().any(|x| x.len() > names::MAX_NAME_BYTES)
    {
        return Err("Names exceed their size limit.".into());
    }
    if !["", "american", "british"].contains(&req.dialect.as_str()) {
        return Err("Unsupported English variant.".into());
    }
    let length = req.text.encode_utf16().count();
    if req.protected_ranges.len() > 4096 || req.tokens.len() > 16_384 {
        return Err("Structural metadata exceeds its limit.".into());
    }
    // One pass marks every valid UTF-16 boundary; a lookup per range end replaces a text scan.
    let mut boundary = vec![false; length + 1];
    let mut at = 0;
    for c in req.text.chars() {
        boundary[at] = true;
        at += c.len_utf16();
    }
    boundary[at] = true;
    let valid = |a: usize, b: usize| a <= b && b <= length && boundary[a] && boundary[b];
    if !req
        .protected_ranges
        .iter()
        .all(|r| valid(r.start_utf16, r.end_utf16))
        || !req.tokens.iter().all(|t| valid(t.start_utf16, t.end_utf16))
    {
        return Err("Invalid structural range.".into());
    }
    let index = req.names_index();
    let tokens = tokenizer::tokenize(&req.text, &req.tokens);
    let protected = protected_ranges_for(req, &tokens, &index);
    // A tagger name is protected from respelling, not from its capital ("rahul" to "Rahul"); the
    // case-only name guard below still blocks every other edit on it.
    let tagged = |r: &TextRange| {
        tokens
            .iter()
            .any(|t| t.proper_name && t.start_utf16 == r.start_utf16)
    };
    // A name candidate may receive only case changes: its level decides which passes skip it.
    let level = index.mark(&req.text, &tokens);
    // Neighbouring name tokens ("Aman Jain", "Jean-Luc") form one span, so nothing can be
    // inserted between a given and a family name.
    let name_ranges = |at_least: u8| -> Vec<TextRange> {
        let mut out: Vec<TextRange> = vec![];
        let mut last = None;
        for (i, t) in tokens
            .iter()
            .enumerate()
            .filter(|(i, _)| level[*i] >= at_least)
        {
            let joined = last == i.checked_sub(1)
                && last.is_some()
                && req.text[tokens[i - 1].end_byte..t.start_byte]
                    .chars()
                    .all(|c| c == ' ' || c == '\t');
            match out.last_mut() {
                Some(r) if joined => r.end_utf16 = t.end_utf16,
                _ => out.push(TextRange {
                    start_utf16: t.start_utf16,
                    end_utf16: t.end_utf16,
                }),
            }
            last = Some(i);
        }
        out
    };
    let guard = name_ranges(names::MEDIUM);
    let mut edits = Vec::new();
    let phrases = rules::phrases();
    for m in phrases
        .matcher
        .find_overlapping_iter(&req.text)
        .filter(|_| !tone_only)
    {
        let rule = &phrases.rules[m.pattern().as_usize()];
        let before = req.text[..m.start()].chars().next_back();
        let after = req.text[m.end()..].chars().next();
        if before.is_some_and(|c| c.is_alphanumeric() || c == '_' || c == '\'')
            || after.is_some_and(|c| c.is_alphanumeric() || c == '_' || c == '\'')
        {
            continue;
        }
        let original = &req.text[m.start()..m.end()];
        let mut replacement = typo_capital(
            match_case(&rule.replacement, original),
            original,
            starts_sentence(&req.text, m.start(), req),
        );
        if starts_sentence(&req.text, m.start(), req)
            && req.text.trim_end().ends_with(['.', '!', '?'])
        {
            replacement = upper_first(&replacement);
        }
        if let Some(e) = make_edit(
            &req.text,
            utf16_at(&req.text, m.start()),
            utf16_at(&req.text, m.end()),
            replacement,
            &rule.category,
            &rule.id,
            &rule.explanation,
            rule.confidence,
        ) {
            edits.push(e);
        }
    }
    for (compiled, hit) in rules::contextual().iter().zip(rules::candidates(&req.text)) {
        let rule = &compiled.rule;
        if !hit
            || tone_only == rule.modes.is_empty()
            || (!rule.modes.is_empty() && !rule.modes.contains(&req.mode))
        {
            continue;
        }
        for captures in compiled.regex().captures_iter(&req.text) {
            let Some(m) = captures.name("target").or_else(|| captures.get(0)) else {
                continue;
            };
            let mut replacement = String::new();
            captures.expand(&rule.replacement, &mut replacement);
            replacement = if rule.id == "grammar.between_you_i" {
                "me".into()
            } else {
                typo_capital(
                    match_case(&replacement, m.as_str()),
                    m.as_str(),
                    starts_sentence(&req.text, m.start(), req),
                )
            };
            if starts_sentence(&req.text, m.start(), req) && !replacement.is_empty() {
                replacement = upper_first(&replacement);
            }
            if let Some(e) = make_edit(
                &req.text,
                utf16_at(&req.text, m.start()),
                utf16_at(&req.text, m.end()),
                replacement.clone(),
                &rule.category,
                &rule.id,
                &rule.explanation,
                rule.confidence,
            ) {
                edits.push(e);
            }
            if replacement.is_empty()
                && let Some(action) = captures.name("action")
            {
                let first = action.as_str().chars().next().unwrap_or(' ');
                if let Some(e) = make_edit(
                    &req.text,
                    utf16_at(&req.text, action.start()),
                    utf16_at(&req.text, action.start() + first.len_utf8()),
                    first.to_uppercase().to_string(),
                    "Tone",
                    "tone.action_capitalization",
                    "Capitalize the action after removing the request wrapper.",
                    0.97,
                ) {
                    edits.push(e);
                }
            }
            if matches!(req.mode, Mode::Direct | Mode::Concise)
                && (rule.id.ends_with(".request") || rule.id.ends_with(".hedged_request"))
                && let Some((offset, c)) = req.text[m.end()..]
                    .char_indices()
                    .find(|(_, c)| ['?', '!', '.', '\n'].contains(c))
                && c == '?'
            {
                let byte = m.end() + offset;
                if let Some(e) = make_edit(
                    &req.text,
                    utf16_at(&req.text, byte),
                    utf16_at(&req.text, byte + 1),
                    ".".into(),
                    "Tone",
                    "tone.request_punctuation",
                    "Use a period for a direct request.",
                    0.97,
                ) {
                    edits.push(e);
                }
            }
        }
    }
    if !tone_only {
        punctuation::check(req, &mut edits);
        structure::check(req, &mut edits);
    }
    for (index, token) in tokens
        .iter()
        .enumerate()
        .filter(|(_, t)| t.is_word && !tone_only)
    {
        if let Some(boundary) = spelling::possessive_boundary(token)
            && let Some(edit) = make_edit(
                &req.text,
                token.start_utf16 + boundary,
                token.start_utf16 + boundary,
                " ".into(),
                "Spelling",
                "spelling.possessive_boundary",
                "Separate the possessive name from its following noun.",
                0.96,
            )
        {
            edits.push(edit);
        }
        if protected
            .iter()
            .any(|r| overlaps(token.start_utf16, token.end_utf16, r) && !tagged(r))
        {
            continue;
        }
        // "i.e." is an abbreviation, not the pronoun.
        let dotted_abbreviation = req.text[token.end_byte..]
            .strip_prefix('.')
            .is_some_and(|rest| rest.starts_with(char::is_alphabetic));
        if token.normalized == "i" && token.surface == "i" && !dotted_abbreviation {
            if let Some(e) = make_edit(
                &req.text,
                token.start_utf16,
                token.end_utf16,
                "I".into(),
                "Capitalization",
                "grammar.personal_pronoun",
                "Capitalize the first-person pronoun.",
                0.99,
            ) {
                edits.push(e);
            }
        } else if starts_sentence(&req.text, token.start_byte, req)
            && token.surface.chars().next().is_some_and(char::is_lowercase)
            && (spelling::known(&token.normalized)
                || req.capitalize_names && level[index] >= names::MEDIUM)
            && (req.text[token.start_byte..]
                .trim_end()
                .ends_with(['.', '!', '?'])
                || has_clause_start(&req.text[token.start_byte..]))
        {
            let first = token.surface.chars().next().unwrap_or(' ');
            // "mcdonald" is "McDonald", "iphone" is "iPhone"; other words only need their first letter.
            let (end, replacement) =
                if let Some(canonical) = spelling::canonical_case(&token.normalized) {
                    (token.end_utf16, canonical.to_string())
                } else if level[index] >= names::MEDIUM {
                    (token.end_utf16, names::title_case(token))
                } else {
                    (
                        token.start_utf16 + first.len_utf16(),
                        first.to_uppercase().to_string(),
                    )
                };
            if let Some(e) = make_edit(
                &req.text,
                token.start_utf16,
                end,
                replacement,
                "Capitalization",
                "grammar.sentence_capitalization",
                "Start the sentence with a capital letter.",
                0.97,
            ) {
                edits.push(e);
            }
        } else if CALENDAR_PROPER.contains(&token.surface)
            && let Some(e) = make_edit(
                &req.text,
                token.start_utf16,
                token.end_utf16,
                upper_first(token.surface),
                "Capitalization",
                "grammar.calendar_capitalization",
                "Days and months take a capital letter.",
                0.95,
            )
        {
            edits.push(e);
        }
        if index > 0 {
            let previous = &tokens[index - 1];
            if previous.normalized == token.normalized
                && previous.sentence == token.sentence
                && previous.paragraph == token.paragraph
                && [
                    "the", "a", "an", "to", "of", "in", "for", "with", "and", "you", "we",
                ]
                .contains(&token.normalized.as_str())
            {
                let gap = &req.text[previous.end_byte..token.start_byte];
                // "a A$1.5 billion" and "US$ 5": the letter belongs to a currency or code token.
                let code = req.text[token.end_byte..]
                    .starts_with(|c: char| c.is_ascii_digit() || "$€£¥#/_-".contains(c));
                if !gap.is_empty()
                    && !code
                    && gap.chars().all(|c| c == ' ' || c == '\t')
                    && let Some(e) = make_edit(
                        &req.text,
                        previous.end_utf16,
                        token.end_utf16,
                        String::new(),
                        "Repetition",
                        "grammar.repeated_word",
                        "Remove an accidental repeated word.",
                        0.99,
                    )
                {
                    edits.push(e);
                }
            }
        }
        let context_start = tokens[index.saturating_sub(2)].start_utf16;
        let pending_grammar_context = edits.iter().any(|e| {
            e.category == "Grammar"
                && e.start_utf16 < token.start_utf16
                && e.end_utf16 > context_start
        });
        if !pending_grammar_context
            && level[index] < names::MEDIUM
            && !edits
                .iter()
                .any(|e| e.start_utf16 <= token.start_utf16 && e.end_utf16 >= token.end_utf16)
            // Context-backed keyboard slips go first: "os" is "is" here, whatever else it transposes to.
            && let Some((id, replacement, reason)) = real_word::fix(&tokens, index)
                .map(|replacement| {
                    let reason =
                        format!("Did you mean “{replacement}”? This looks like a keyboard slip.");
                    ("spelling.real_word", replacement, reason)
                })
                .or_else(|| {
                    spelling::slot_fix(&tokens, index)
                        .map(|(id, replacement, reason)| (id, replacement, reason.to_string()))
                })
                .or_else(|| {
                spelling::suggest(
                    token,
                    &req.dialect,
                    index.checked_sub(1).and_then(|i| tokens.get(i)),
                    tokens.get(index + 1),
                    &tokens[..index],
                    &tokens[index + 1..],
                )
                .map(|replacement| {
                    (
                        "spelling.delete_index",
                        replacement,
                        "The dictionary and local word context suggest this spelling or word boundary."
                            .to_string(),
                    )
                })
            })
            && let Some(e) = make_edit(
                &req.text,
                token.start_utf16,
                token.end_utf16,
                replacement,
                "Spelling",
                id,
                &reason,
                0.80,
            )
        {
            edits.push(e);
        }
    }
    if req.capitalize_names && !tone_only {
        for c in names::capitalizations(
            &req.text,
            &tokens,
            &level,
            &index.phrase_cover(&tokens),
            |b| utf16_at(&req.text, b),
        ) {
            if let Some(e) = make_edit(
                &req.text,
                c.start_utf16,
                c.end_utf16,
                c.replacement.clone(),
                "Style",
                "names.capitalize",
                &format!("Capitalize the name “{}”.", c.replacement),
                0.90,
            ) {
                edits.push(e);
            }
        }
    }
    // Names take case changes only: any other edit touching one is dropped.
    let case_only = |e: &Edit| e.original.to_lowercase() == e.replacement.to_lowercase();
    // Only lowercase letters turned capital, nothing else changed.
    let raises_case = |e: &Edit| {
        e.original.chars().count() == e.replacement.chars().count()
            && e.original
                .chars()
                .zip(e.replacement.chars())
                .all(|(a, b)| a == b || a.is_lowercase() && b.to_lowercase().eq([a]))
    };
    let blocked = |e: &Edit| {
        protected
            .iter()
            .any(|r| overlaps(e.start_utf16, e.end_utf16, r) && !(raises_case(e) && tagged(r)))
            || !case_only(e)
                && if e.start_utf16 != e.end_utf16 {
                    guard
                        .iter()
                        .any(|r| overlaps(e.start_utf16, e.end_utf16, r))
                } else {
                    // An insertion may not split a name ("Aman. Jain"); a possessive space may.
                    e.rule_id != "spelling.possessive_boundary"
                        && guard
                            .iter()
                            .any(|r| e.start_utf16 > r.start_utf16 && e.start_utf16 < r.end_utf16)
                }
    };
    let blocked_groups: std::collections::HashSet<_> = edits
        .iter()
        .filter(|e| blocked(e))
        .filter_map(|e| e.group_id.clone())
        .collect();
    edits.retain(|e| {
        !e.group_id
            .as_ref()
            .is_some_and(|g| blocked_groups.contains(g))
            && !blocked(e)
    });
    // Objective fixes beat style; tone request wrappers own capitalization of their prefix.
    edits.sort_by(|a, b| {
        a.start_utf16
            .cmp(&b.start_utf16)
            .then_with(|| (a.category == "Capitalization").cmp(&(b.category == "Capitalization")))
            .then_with(|| b.confidence.total_cmp(&a.confidence))
            .then_with(|| a.end_utf16.cmp(&b.end_utf16))
            .then_with(|| a.rule_id.cmp(&b.rule_id))
    });
    let mut accepted: Vec<Edit> = Vec::new();
    for edit in edits {
        if accepted.iter().any(|e| {
            edit.start_utf16 == e.start_utf16
                || edit.start_utf16 < e.end_utf16 && edit.end_utf16 > e.start_utf16
        }) {
            continue;
        }
        accepted.push(edit);
    }
    // Coupled word-order edits must survive conflict/protection filtering together.
    let group_counts = accepted.iter().filter_map(|e| e.group_id.as_ref()).fold(
        std::collections::HashMap::new(),
        |mut counts, g| {
            *counts.entry(g.clone()).or_insert(0) += 1;
            counts
        },
    );
    accepted.retain(|e| {
        e.group_id
            .as_ref()
            .is_none_or(|g| group_counts.get(g) == Some(&2))
    });
    if accepted.len() > 512 {
        return Err("This passage has too many changes. Select a shorter passage.".into());
    }
    let (text, source_map) = apply_edits(&req.text, &accepted)?;
    Ok(RewriteResult {
        version: concat!("parzr-", env!("CARGO_PKG_VERSION"), "/rules-1").into(),
        text,
        edits: accepted,
        source_map,
        elapsed_ms: started.elapsed().as_secs_f64() * 1000.0,
        protected_count: protected.len(),
        warnings: vec![],
    })
}

pub fn apply_edits(text: &str, edits: &[Edit]) -> Result<(String, Vec<SourceMapping>), String> {
    let groups = edits.iter().filter_map(|e| e.group_id.as_ref()).fold(
        std::collections::HashMap::new(),
        |mut counts, g| {
            *counts.entry(g).or_insert(0) += 1;
            counts
        },
    );
    if groups.values().any(|n| *n != 2) {
        return Err("Apply linked correction parts together.".into());
    }
    let mut output = String::new();
    let mut map = Vec::new();
    let mut prev = 0;
    let mut out = 0;
    for edit in edits {
        if edit.start_utf16 < prev || edit.end_utf16 < edit.start_utf16 {
            return Err("Overlapping edit plan.".into());
        }
        let a = byte_at(text, prev).ok_or("Invalid UTF-16 boundary.")?;
        let b = byte_at(text, edit.start_utf16).ok_or("Invalid UTF-16 boundary.")?;
        let c = byte_at(text, edit.end_utf16).ok_or("Invalid UTF-16 boundary.")?;
        if text[b..c] != edit.original {
            return Err("Source text changed.".into());
        }
        output.push_str(&text[a..b]);
        let unchanged = edit.start_utf16 - prev;
        if unchanged > 0 {
            map.push(SourceMapping {
                input_start_utf16: prev,
                input_end_utf16: edit.start_utf16,
                output_start_utf16: out,
                output_end_utf16: out + unchanged,
                changed: false,
            });
            out += unchanged;
        }
        let size = edit.replacement.encode_utf16().count();
        output.push_str(&edit.replacement);
        map.push(SourceMapping {
            input_start_utf16: edit.start_utf16,
            input_end_utf16: edit.end_utf16,
            output_start_utf16: out,
            output_end_utf16: out + size,
            changed: true,
        });
        out += size;
        prev = edit.end_utf16;
    }
    let a = byte_at(text, prev).ok_or("Invalid UTF-16 boundary.")?;
    output.push_str(&text[a..]);
    let len = text.encode_utf16().count();
    if len > prev {
        map.push(SourceMapping {
            input_start_utf16: prev,
            input_end_utf16: len,
            output_start_utf16: out,
            output_end_utf16: out + len - prev,
            changed: false,
        });
    }
    Ok((output, map))
}
pub fn process_json(input: &str) -> String {
    let result = if input.len() > MAX_TEXT_BYTES * 8 {
        Err("Request exceeds size limit.".to_string())
    } else {
        serde_json::from_str::<Request>(input)
            .map_err(|_| "Invalid engine request.".to_string())
            .and_then(|r| rewrite(&r))
    };
    match result {
        Ok(result) => serde_json::to_string(&result)
            .unwrap_or_else(|_| r#"{"error":"Could not encode result."}"#.into()),
        Err(error) => serde_json::json!({"error":error}).to_string(),
    }
}
/// # Safety
/// `input` must point to a valid NUL-terminated UTF-8 string alive for this call.
/// Free the returned owned string exactly once with `parzr_string_free`.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn parzr_rewrite_json(input: *const c_char) -> *mut c_char {
    if input.is_null() {
        return std::ptr::null_mut();
    }
    let result = catch_unwind(AssertUnwindSafe(|| {
        // SAFETY: the C ABI caller guarantees a valid NUL-terminated string.
        let input = unsafe { CStr::from_ptr(input) }.to_str().map_err(|_| ());
        input
            .map(process_json)
            .unwrap_or_else(|_| r#"{"error":"Input is not UTF-8."}"#.into())
    }))
    .unwrap_or_else(|_| r#"{"error":"The writing engine could not complete the request."}"#.into());
    CString::new(result)
        .map(CString::into_raw)
        .unwrap_or(std::ptr::null_mut())
}
/// # Safety
/// The pointer must be NULL or an unfreed pointer returned by `parzr_rewrite_json`.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn parzr_string_free(ptr: *mut c_char) {
    if !ptr.is_null() {
        // SAFETY: ownership was transferred by CString::into_raw.
        drop(unsafe { CString::from_raw(ptr) });
    }
}
/// 1 when `word` is a reviewed misspelling (teh, recieved, alot) that must never be learned as a name.
/// # Safety
/// `word` must be NULL or a valid NUL-terminated string alive for this call.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn parzr_is_known_misspelling(word: *const c_char) -> i32 {
    if word.is_null() {
        return 0;
    }
    // SAFETY: the C ABI caller guarantees a valid NUL-terminated string.
    let word = unsafe { CStr::from_ptr(word) }.to_str();
    i32::from(word.is_ok_and(names::is_known_misspelling))
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn capitalized_known_typos_mid_sentence_get_lowercase_fixes() {
        assert_eq!(typo_capital("The".into(), "Teh", false), "the");
        assert_eq!(typo_capital("Their".into(), "Thier", false), "their");
        assert_eq!(typo_capital("The".into(), "Teh", true), "The");
        assert_eq!(typo_capital("THE".into(), "TEH", false), "THE");
        // Not a known misspelling: keep the case match (a name or a deliberate capital).
        assert_eq!(typo_capital("Mark".into(), "Mark", false), "Mark");
    }
    /// Rules only, repeated to a fixed point like the pipeline's grammar loop (no model needed).
    fn fix(text: &str) -> String {
        let mut text = text.to_string();
        for _ in 0..6 {
            let pass = rewrite_once(
                &Request {
                    text: text.clone(),
                    ..Request::default()
                },
                false,
            )
            .unwrap();
            if pass.edits.is_empty() {
                break;
            }
            text = pass.text;
        }
        text
    }
    #[test]
    fn frequent_word_replaces_rare_near_misses_in_fitting_slots() {
        for (input, expected) in [
            ("This si do bad.", "This is so bad."),
            ("This si bod.", "This is bad."),
            ("this si too bod", "This is too bad"),
            ("The weather si nice today.", "The weather is nice today."),
            ("There si a problem with it.", "There is a problem with it."),
            ("What si going on here?", "What is going on here?"),
            ("The big dog si very tired.", "The big dog is very tired."),
            ("Mira said it si ready.", "Mira said it is ready."),
            ("I think ti is fine.", "I think it is fine."),
            ("He looked ta the door.", "He looked at the door."),
            ("We left ni the morning.", "We left in the morning."),
            ("A lot fo the guests left.", "A lot of the guests left."),
            ("It runs sa well as before.", "It runs as well as before."),
            ("He went ot the market.", "He went to the market."),
            ("It is bod.", "It is bad."),
            ("Those were bod.", "Those were bad."),
            ("That's bod luck.", "That's bad luck."),
            ("They look so bod.", "They look so bad."),
            ("It is do hard.", "It is so hard."),
            ("The test was do boring.", "The test was so boring."),
        ] {
            assert_eq!(fix(input), expected, "{input}");
            assert_eq!(fix(expected), expected, "idempotent: {expected}");
        }
    }
    fn fix_request(req: Request) -> String {
        let mut req = req;
        for _ in 0..6 {
            let pass = rewrite_once(&req, false).unwrap();
            if pass.edits.is_empty() {
                break;
            }
            req.text = pass.text;
        }
        req.text
    }
    fn with_names(text: &str, names: &[&str], capitalize: bool) -> Request {
        Request {
            text: text.into(),
            names: names.iter().map(|s| s.to_string()).collect(),
            capitalize_names: capitalize,
            ..Request::default()
        }
    }
    /// The pipeline's passes, which keep the evidence of the first pass for the later ones.
    fn pipe(text: &str) -> String {
        pipeline::rewrite(&Request {
            text: text.into(),
            ..Request::default()
        })
        .unwrap()
        .text
    }
    #[test]
    fn names_are_unchanged_by_context_alone_without_any_list() {
        for input in [
            "it is sneha verma here, just checking in.",
            "I met jonas zu hohenlohe at the conference yesterday.",
            "Could you review this before lunch, sai?",
            "wim, could you review this before lunch?",
            "Hey meiling! Long time no see.",
            "I think harsha said the meeting moved to Friday.",
            "The new team includes anke, dirk and wim.",
            "Thanks for the update.\npieter",
            "Mr aman will come.",
            "Please ask rahul bhai about it.",
            "That works for me.\nthanks, jean-luc",
            "I borrowed deepak's laptop for the demo.",
        ] {
            // Only case may change (a sentence capital); no letter of a name does.
            assert_eq!(pipe(input).to_lowercase(), input.to_lowercase(), "{input}");
        }
    }
    #[test]
    fn request_names_only_take_case_changes() {
        // The request names are never respelled, split or punctuated, even next to each other.
        let text = "I met Aman Jain, and Aman's friend said aman jain was kind.";
        let got = fix_request(with_names(text, &["Aman", "Jain"], true));
        assert_eq!(
            got,
            "I met Aman Jain, and Aman's friend said Aman Jain was kind."
        );
        assert_eq!(
            fix_request(with_names("we met zoë and ZOË", &["Zoë"], true)),
            "we met Zoë and ZOË"
        );
        assert_eq!(
            fix_request(with_names("send it to jean-luc today", &["Jean-Luc"], true)),
            "send it to Jean-Luc today"
        );
        assert_eq!(
            fix_request(with_names("ask o'neil about it", &["O'Neil"], true)),
            "ask O'Neil about it"
        );
        // Off by default: case is left alone mid-sentence.
        let text = "ask aman jain about it";
        assert_eq!(fix_request(with_names(text, &["Aman Jain"], false)), text);
    }
    #[test]
    fn capitalize_names_adds_one_case_only_edit() {
        let req = with_names(
            "Hello from priya sharma and aman.",
            &["Priya Sharma", "Aman"],
            true,
        );
        let pass = rewrite_once(&req, false).unwrap();
        let ids: Vec<_> = pass
            .edits
            .iter()
            .map(|e| (e.rule_id.as_str(), e.replacement.as_str()))
            .collect();
        assert_eq!(
            ids,
            [
                ("names.capitalize", "Priya Sharma"),
                ("names.capitalize", "Aman")
            ]
        );
        assert!(pass.edits.iter().all(|e| e.category == "Style"));
        assert_eq!(
            pass.edits[0].explanation,
            "Capitalize the name “Priya Sharma”."
        );
    }
    #[test]
    fn names_that_are_ordinary_words_need_a_capital_or_a_cue() {
        let names = ["Will", "Mark", "Grace", "May", "Hope"];
        for text in [
            "I will go and mark the page.",
            "We may leave with grace and hope.",
            "I hope you will say hi, may we?",
        ] {
            let got = fix_request(with_names(text, &names, true));
            assert_eq!(got, text, "{text}");
        }
        assert_eq!(
            fix_request(with_names("thanks, will", &names, true)),
            "thanks, Will"
        );
        assert_eq!(
            fix_request(with_names("Hey Hope! how are you", &names, true)),
            "Hey Hope! how are you"
        );
        assert_eq!(
            fix_request(Request {
                text: "We should invite Rose to the call.".into(),
                ..Request::default()
            }),
            "We should invite Rose to the call."
        );
    }
    #[test]
    fn dictionary_matches_unicode_possessive_hyphen_and_phrases() {
        for (text, dictionary) in [
            ("ask ZOË now", "zoë"),
            ("ask Zoë’s team", "Zoë"),
            ("we met jean-luc today", "Jean-Luc"),
            ("visit new yrk today", "new yrk"),
            ("see aman's mesage", "mesage"),
        ] {
            let req = Request {
                text: text.into(),
                dictionary: vec![dictionary.into()],
                ..Request::default()
            };
            assert_eq!(fix_request(req), text, "{text}");
        }
        let req = Request {
            text: "we met jean-luc and new yrk".into(),
            dictionary: vec!["Jean-Luc".into(), "new yrk".into()],
            ..Request::default()
        };
        assert_eq!(fix_request(req.clone()), req.text);
    }
    #[test]
    fn tagged_and_dictionary_proper_nouns_get_capitals() {
        let named = |text: &str, words: &[&str]| -> Request {
            let tokens = words
                .iter()
                .map(|w| {
                    let start = text.find(w).unwrap();
                    TokenHint {
                        start_utf16: start,
                        end_utf16: start + w.len(),
                        pos: "Noun".into(),
                        lemma: String::new(),
                        name: true,
                        ..TokenHint::default()
                    }
                })
                .collect();
            Request {
                text: text.into(),
                tokens,
                capitalize_names: true,
                ..Request::default()
            }
        };
        assert_eq!(
            fix_request(named(
                "I met rahul and sneha at the office.",
                &["rahul", "sneha"]
            )),
            "I met Rahul and Sneha at the office."
        );
        assert_eq!(
            fix_request(named("Send it to sarah by friday.", &["sarah"])),
            "Send it to Sarah by Friday."
        );
        assert_eq!(
            fix_request(named("We flew to mumbai in june.", &[])),
            "We flew to Mumbai in June."
        );
        // Ordinary words stay lowercase without a cue, and a tagged name is still never respelled.
        assert_eq!(
            fix_request(named("I may march in august.", &[])),
            "I may march in august."
        );
        assert_eq!(
            fix_request(named("Ask rakesh about it.", &["rakesh"])),
            "Ask Rakesh about it."
        );
        // Greetings make a name only of an unusual word or one behind a comma; particles and
        // Hinglish stay lowercase.
        for text in [
            "Thanks for the fix.",
            "You're a lifesaver, thank you.",
            "It is the very best quality.",
            "A painting by Rogier van der Weyden.",
            "Chinta mat karo, I'll handle it.",
            "Thanks yaar, see you in mumbai.",
        ] {
            assert_eq!(fix_request(named(text, &[])), text);
        }
        assert_eq!(fix_request(named("Thanks, rose.", &[])), "Thanks, Rose.");
    }
    #[test]
    fn shorthand_days_and_months_are_not_names() {
        // A tagger hint on "u" must not protect it; pls is never respelled either.
        let hint = |text: &str, word: &str| {
            let start = text.find(word).unwrap();
            TokenHint {
                start_utf16: start,
                end_utf16: start + word.len(),
                pos: "Noun".into(),
                lemma: String::new(),
                name: true,
                ..TokenHint::default()
            }
        };
        let text = "hey Aman can u send the file on friday";
        let tokens = tokenizer::tokenize(text, &[hint(text, "u"), hint(text, "friday")]);
        assert!(tokens.iter().all(|t| !t.proper_name));
        assert_eq!(fix("ok pls send it thx"), "ok pls send it thx");
        assert!(
            names::never_a_name("june")
                && names::never_a_name("Friday")
                && names::never_a_name("u")
        );
        assert!(!names::never_a_name("Li") && !names::never_a_name("aman"));
    }
    #[test]
    fn surname_particles_join_name_parts() {
        for input in [
            "it is joost van dijk here, just checking in.",
            "I met pieter von trapp at the conference yesterday.",
            "I had lunch with farhad yesterday.",
        ] {
            assert_eq!(pipe(input).to_lowercase(), input.to_lowercase(), "{input}");
        }
    }
    #[test]
    fn mentions_and_handles_stay_exact() {
        for input in [
            "ping (@aman) about it",
            "cc @aman.jain and @a_b-c please",
            "Thanks @aman.",
            "see #teh and (#mesage) now",
        ] {
            assert_eq!(fix(input), input, "{input}");
        }
    }
    #[test]
    fn canonical_case_opens_sentences() {
        for (input, expected) in [
            ("mcdonald said hi.", "McDonald said hi."),
            ("o'neil said hi.", "O'Neil said hi."),
            ("iphone is great.", "iPhone is great."),
            ("iPhone is great.", "iPhone is great."),
            ("hello there.", "Hello there."),
        ] {
            assert_eq!(fix(input), expected, "{input}");
        }
    }
    #[test]
    fn a_name_is_never_offered_as_a_spelling_candidate() {
        // "rahul" and "neha" sit one edit from "raul" and "neh"; lowercase words never become names.
        for input in ["we talked to rahull today", "the nehaa file is here"] {
            let out = fix(input);
            assert!(
                !out.contains("raul") && !out.contains("Neh "),
                "{input}: {out}"
            );
        }
    }
    #[test]
    fn name_limit_is_enforced() {
        let req = Request {
            text: "hi".into(),
            names: vec!["a".into(); names::MAX_NAMES + 1],
            ..Request::default()
        };
        assert!(rewrite_once(&req, false).is_err());
        let req = Request {
            text: "hi".into(),
            names: vec!["a".repeat(129)],
            ..Request::default()
        };
        assert!(rewrite_once(&req, false).is_err());
        let ok: Request =
            serde_json::from_str(r#"{"text":"hi","names":["Aman"],"capitalize_names":true}"#)
                .unwrap();
        assert!(ok.capitalize_names && ok.names == ["Aman"]);
        assert!(serde_json::from_str::<Request>(r#"{"text":"hi","name_index":1}"#).is_err());
    }
    #[test]
    fn lowercase_names_are_never_respelled() {
        for input in [
            "aman jain",
            "Hi aman, thanks",
            "thanks, jain",
            "aman jain\nStaff Software Engineer",
            "priya sharma",
            "rahul",
            "anoop said hi",
            "ask aman about it",
            "Thanks aman",
            "Regards,\naman",
            "Cheers\nanoop kumar",
            "hey aman, are you free",
            "I want to see aman jain",
            "please ask jain",
            "aman is here",
            "we met rahul sharma",
            "I saw aman yesterday",
            "I met Priya sharma",
        ] {
            assert_eq!(fix(input), input, "{input}");
        }
    }
    #[test]
    fn known_misspelling_ffi_answers_for_typos_and_names() {
        let ask = |w: &str| {
            let w = CString::new(w).unwrap();
            unsafe { parzr_is_known_misspelling(w.as_ptr()) }
        };
        assert_eq!((ask("Recieved"), ask("teh"), ask("sentense")), (1, 1, 1));
        assert_eq!((ask("Aman"), ask("hope")), (0, 0));
        assert_eq!(unsafe { parzr_is_known_misspelling(std::ptr::null()) }, 0);
    }
    #[test]
    fn learned_misspellings_in_names_are_ignored_but_real_names_still_win() {
        let pass = rewrite_once(
            &Request {
                text: "i recieved teh file from aman".into(),
                names: ["teh", "recieved", "Aman"].map(String::from).to_vec(),
                capitalize_names: true,
                ..Request::default()
            },
            false,
        )
        .unwrap();
        let edit = |original: &str| pass.edits.iter().find(|e| e.original == original);
        assert_eq!(edit("recieved").unwrap().replacement, "received");
        assert_eq!(edit("teh").unwrap().replacement, "the");
        assert_eq!(edit("aman").unwrap().replacement, "Aman");
        assert!(
            pass.edits
                .iter()
                .all(|e| e.rule_id != "names.capitalize" || e.original == "aman")
        );
    }
    #[test]
    fn typos_beside_names_and_other_typos_are_still_fixed() {
        for (input, expected) in [
            ("I have alot of work.", "I have a lot of work."),
            ("I recieved the file.", "I received the file."),
            ("teh cat", "the cat"),
            ("This si bod.", "This is bad."),
            ("I goes ot the maret", "I go to the market"),
            (
                "Clara atean apple before leaving.",
                "Clara ate an apple before leaving.",
            ),
            (
                "Priya wriets a careful schedule.",
                "Priya writes a careful schedule.",
            ),
            (
                "The team needs aclear summary.",
                "The team needs a clear summary.",
            ),
            (
                "Its success depends on planningand aclear summary.",
                "Its success depends on planning and a clear summary.",
            ),
            ("We left rzview alreazy.", "We left review already."),
            (
                "The organizers brought tzeir summarimes.",
                "The organizers brought their summaries.",
            ),
            ("It was on the tran.", "It was on the train."),
            ("The peron is away.", "The person is away."),
            (
                "It should be clear ot everyzne.",
                "It should be clear to everyone.",
            ),
            ("She has aclear plan.", "She has a clear plan."),
        ] {
            assert_eq!(fix(input), expected, "{input}");
            assert_eq!(fix(expected), expected, "idempotent: {expected}");
        }
    }
    #[test]
    fn valid_uses_of_rare_words_are_kept() {
        for input in [
            "Do re mi fa so la si do.",
            "Si, no puedo ir.",
            "She sang si and then do.",
            "This si note is difficult.",
            "The si note rings clearly.",
            "On Monday we met.",
            "No, thanks.",
            "Ta very much.",
            "Ti is a metal.",
            "On the other hand, no one came.",
            "I did it in the morning.",
            "A friendly bod helped us.",
            "That sounds like a bod.",
            "Her bod is toned.",
            "The nickname is Bod.",
            "Their habit is do bad things.",
            "We do bad work sometimes.",
        ] {
            assert_eq!(fix(input), input, "{input}");
        }
    }
    #[test]
    fn precise_grammar_rules_leave_valid_prose_alone() {
        for input in [
            // Plural objects after a transitive verb or a do verb are not verbs to de-inflect.
            "Children play games after school.",
            "The company can give jobs to many people.",
            "You can get used to the noise quickly.",
            "They do sports every weekend.",
            "We do lots of work here.",
            "What he can do is wait.",
            // The head noun, not the nearest noun, agrees with the verb.
            "Our lives are busy these days.",
            "The world is a big place.",
            "The roads near the station get busy.",
            "All the teenagers continue to study.",
            "Reading these chapters is a pleasure.",
            "I sing a song and the world is perfect.",
            // Inversion, subjunctive and collective names.
            "Round the corner were three small shops.",
            "Inside the box were two old letters.",
            "He acted as though it were a game.",
            "If I were you, I would go.",
            "Leeds were beaten at home.",
            // Contractions, possessives, causatives and Hinglish.
            "Let's see what happens.",
            "My brother's work is hard.",
            "I saw him walk home.",
            "She makes Maya attend class.",
            "Thoda wait karo.",
            // Abbreviations do not end sentences.
            "We meet at 5 p.m. then walk home.",
            "He studies U.S. history at school.",
            "Bring pens and paper, etc. via the office.",
            "Use a loop, i.e. a repeated step.",
            // "but" meaning only, or sharing a subject.
            "He had nothing but time.",
            "It was all but over by noon.",
            "She came but left early.",
            // Codes and present-tense frames.
            "The firm won a A$1.5 billion contract.",
            "The report came out yesterday; it is only now that it has been possible to check it.",
            // Not a run-on: subordinate openers, relatives, short clauses, adverbial runs.
            "As I opened the gate I heard a low whistle from the garden.",
            "She kept the letters in a box which I found in the attic last week.",
            "He waited for an hour and then I joined him on the quay.",
        ] {
            assert_eq!(fix(input), input, "{input}");
        }
    }
    #[test]
    fn precise_grammar_rules_keep_their_real_fixes() {
        for (input, expected) in [
            ("Did she called him?", "Did she call him?"),
            ("Does he works here?", "Does he work here?"),
            ("My brothers is tall.", "My brothers are tall."),
            (
                "The fruit is cheap but the shop is far from our house.",
                "The fruit is cheap, but the shop is far from our house.",
            ),
            (
                "We should send the brief before the meeting starts Anika can finish the work today.",
                "We should send the brief before the meeting starts. Anika can finish the work today.",
            ),
        ] {
            assert_eq!(fix(input), expected, "{input}");
        }
    }
}
