//! Parzr's hybrid writing engine. Every adapter shares UTF-16 edits and local language hints.
mod context;
#[cfg(feature = "local-model")]
mod model;
mod morphology;
mod pipeline;
mod punctuation;
mod rules;
mod spelling;
mod structure;
mod tokenizer;
use regex::Regex;
use serde::{Deserialize, Serialize};
use std::time::Instant;
use std::{
    ffi::{CStr, CString, c_char},
    panic::{AssertUnwindSafe, catch_unwind},
    sync::OnceLock,
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
}
impl Default for Request {
    fn default() -> Self {
        Self {
            text: String::new(),
            mode: Mode::Fix,
            dictionary: vec![],
            dialect: String::new(),
            protected_ranges: vec![],
            tokens: vec![],
            sentence_start: true,
            sentence_end: true,
            deep: false,
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
    RE.get_or_init(||Regex::new(r"(?ms)```.*?(?:```|\z)|~~~.*?(?:~~~|\z)|`[^`\n]*(?:`|$)|(?:https?://|www\.)[^\s<>]+|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|(?:^|\s)[@#][\w-]+|(?:/|~/|[A-Za-z]:\\)[\w./\\-]+|\b\d+(?:[.,:/-]\d+)*\b|(?m)^>[^\n]*|(?m)^-- ?$[\s\S]*|(?m)^\s*(?:curl|git|npm|npx|cargo|sudo|python3?|ssh|brew)\s[^\n]*(?:\\\n[^\n]*)*|[\u{FFFC}]").expect("constant protected-span regex"))
}
fn protected_ranges(req: &Request) -> Vec<TextRange> {
    let mut spans = req.protected_ranges.clone();
    for m in protection_regex().find_iter(&req.text) {
        spans.push(TextRange {
            start_utf16: utf16_at(&req.text, m.start()),
            end_utf16: utf16_at(&req.text, m.end()),
        });
    }
    let tokens = tokenizer::tokenize(&req.text, &req.tokens);
    for token in tokens {
        if token.proper_name
            || req
                .dictionary
                .iter()
                .any(|w| w.eq_ignore_ascii_case(token.surface))
        {
            spans.push(TextRange {
                start_utf16: token.start_utf16,
                end_utf16: if token.proper_name
                    && !req
                        .dictionary
                        .iter()
                        .any(|w| w.eq_ignore_ascii_case(token.surface))
                {
                    possessive_boundary(&token)
                        .map(|n| token.start_utf16 + n)
                        .unwrap_or(token.end_utf16)
                } else {
                    token.end_utf16
                },
            });
        }
    }
    // Multi-word dictionary names are also protected, with lexical boundary checks.
    for word in req
        .dictionary
        .iter()
        .filter(|w| w.chars().any(char::is_whitespace))
    {
        if let Ok(re) = Regex::new(&format!(r"(?i)\b{}\b", regex::escape(word))) {
            for m in re.find_iter(&req.text) {
                spans.push(TextRange {
                    start_utf16: utf16_at(&req.text, m.start()),
                    end_utf16: utf16_at(&req.text, m.end()),
                });
            }
        }
    }
    spans
}
fn possessive_boundary(token: &tokenizer::Token<'_>) -> Option<usize> {
    spelling::possessive_boundary(token)
}
/// Original-coordinate structural spans for adapters analyzing a document selection.
pub fn protected_spans(req: &Request) -> Vec<TextRange> {
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
fn upper_first(s: &str) -> String {
    let mut chars = s.chars();
    match chars.next() {
        Some(c) => c.to_uppercase().to_string() + chars.as_str(),
        None => String::new(),
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
}
fn rewrite_once(req: &Request, tone_only: bool) -> Result<RewriteResult, String> {
    let started = Instant::now();
    if req.text.len() > MAX_TEXT_BYTES {
        return Err("Select at most 64 KB of text.".into());
    }
    if req.dictionary.len() > 1000 || req.dictionary.iter().any(|x| x.len() > 128) {
        return Err("Dictionary exceeds its size limit.".into());
    }
    if !["", "american", "british"].contains(&req.dialect.as_str()) {
        return Err("Unsupported English variant.".into());
    }
    let length = req.text.encode_utf16().count();
    if req.protected_ranges.len() > 4096 || req.tokens.len() > 16_384 {
        return Err("Structural metadata exceeds its limit.".into());
    }
    if req.protected_ranges.iter().any(|r| {
        r.start_utf16 > r.end_utf16
            || r.end_utf16 > length
            || byte_at(&req.text, r.start_utf16).is_none()
            || byte_at(&req.text, r.end_utf16).is_none()
    }) || req.tokens.iter().any(|t| {
        t.start_utf16 > t.end_utf16
            || t.end_utf16 > length
            || byte_at(&req.text, t.start_utf16).is_none()
            || byte_at(&req.text, t.end_utf16).is_none()
    }) {
        return Err("Invalid structural range.".into());
    }
    let protected = protected_ranges(req);
    let tokens = tokenizer::tokenize(&req.text, &req.tokens);
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
        let mut replacement = match_case(&rule.replacement, original);
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
    for compiled in rules::contextual() {
        let rule = &compiled.rule;
        if tone_only == rule.modes.is_empty()
            || (!rule.modes.is_empty() && !rule.modes.contains(&req.mode))
        {
            continue;
        }
        for captures in compiled.regex.captures_iter(&req.text) {
            let Some(m) = captures.name("target").or_else(|| captures.get(0)) else {
                continue;
            };
            let mut replacement = String::new();
            captures.expand(&rule.replacement, &mut replacement);
            replacement = if rule.id == "grammar.between_you_i" {
                "me".into()
            } else {
                match_case(&replacement, m.as_str())
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
            .any(|r| overlaps(token.start_utf16, token.end_utf16, r))
        {
            continue;
        }
        if token.normalized == "i" && token.surface == "i" {
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
            && spelling::known(&token.normalized)
            && (req.text[token.start_byte..]
                .trim_end()
                .ends_with(['.', '!', '?'])
                || has_clause_start(&req.text[token.start_byte..]))
        {
            let first = token.surface.chars().next().unwrap_or(' ');
            if let Some(e) = make_edit(
                &req.text,
                token.start_utf16,
                token.start_utf16 + first.len_utf16(),
                first.to_uppercase().to_string(),
                "Capitalization",
                "grammar.sentence_capitalization",
                "Start the sentence with a capital letter.",
                0.97,
            ) {
                edits.push(e);
            }
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
                if !gap.is_empty()
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
            && !edits
                .iter()
                .any(|e| e.start_utf16 <= token.start_utf16 && e.end_utf16 >= token.end_utf16)
            && let Some((id, replacement, reason)) = spelling::slot_fix(&tokens, index).or_else(|| {
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
                        "The dictionary and local word context suggest this spelling or word boundary.",
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
                reason,
                0.80,
            )
        {
            edits.push(e);
        }
    }
    let blocked_groups: std::collections::HashSet<_> = edits
        .iter()
        .filter(|e| {
            protected
                .iter()
                .any(|r| overlaps(e.start_utf16, e.end_utf16, r))
        })
        .filter_map(|e| e.group_id.clone())
        .collect();
    edits.retain(|e| {
        !e.group_id
            .as_ref()
            .is_some_and(|g| blocked_groups.contains(g))
            && !protected
                .iter()
                .any(|r| overlaps(e.start_utf16, e.end_utf16, r))
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
        version: "parzr-0.1.0/rules-1".into(),
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
#[cfg(test)]
mod tests {
    use super::*;
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
}
