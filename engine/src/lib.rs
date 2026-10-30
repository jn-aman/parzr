//! Parzr's hybrid writing engine. Every adapter shares UTF-16 edits and local language hints.
mod capitalization;
mod clause_repairs;
mod clauses;
mod compounds;
#[cfg(feature = "local-model")]
mod confusion;
mod context;
mod contractions;
mod determiners;
mod forms;
#[cfg(feature = "local-model")]
mod gec;
#[cfg(feature = "local-model")]
mod gec_text;
mod hinglish;
mod marks;
#[cfg_attr(not(feature = "local-model"), allow(dead_code))]
mod meaning;
#[cfg(feature = "local-model")]
mod model;
mod morphology;
mod names;
#[cfg_attr(not(feature = "local-model"), allow(dead_code))]
mod overrides;
pub mod packs;
mod pipeline;
mod punctuation;
mod real_word;
mod rules;
#[cfg(feature = "local-model")]
mod slips;
mod spelling;
mod structure;
mod table;
pub mod tables;
mod tokenizer;
#[cfg(feature = "local-model")]
mod tone_format;
#[cfg_attr(not(feature = "local-model"), allow(dead_code))]
mod tone_guard;
#[cfg(feature = "local-model")]
mod tone_insult;
mod wording;
pub use names::NameIndex;
use regex::Regex;
/// The lazy DFA cache each rule pattern may grow to. The regex crate's default (2 MB per regex)
/// would let the footprint of a long session climb with the rule patterns it compiles
/// (`rules::COMPILED_PATTERNS_KEPT`); past this bound a search clears the cache or falls back to
/// another of the crate's engines, with the same matches.
/// On the Mac the packs' long alternations need room to stay in the fast automaton (16 KB
/// makes a 12 KB passage cost a pattern ~10 ms in the fallback engines, ~0.3 ms with 192 KB).
#[cfg(target_os = "macos")]
pub(crate) const REGEX_CACHE_BYTES: usize = 192 * 1024;
#[cfg(not(target_os = "macos"))]
pub(crate) const REGEX_CACHE_BYTES: usize = 16 * 1024;
/// A rule regex with the engine's bounded cache (`REGEX_CACHE_BYTES`).
pub(crate) fn regex(pattern: &str) -> Result<Regex, regex::Error> {
    regex::RegexBuilder::new(pattern)
        .dfa_size_limit(REGEX_CACHE_BYTES)
        .build()
}
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
    /// The text comes from a chat app (Slack, Teams, Messages…): a short Friendly rewrite may end
    /// with one fitting emoji. Other modes and apps never get one.
    #[serde(default)]
    pub casual: bool,
    /// Use the typing-time slip checker (the optional slip pack's masked language model) when it is
    /// on this Mac. The app sends false while the user has switched the slip check off; clients that
    /// predate the switch (the browser host, the LSP) leave it out and keep the default, on.
    #[serde(default = "yes")]
    pub slips: bool,
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
            casual: false,
            slips: true,
            name_index: None,
        }
    }
}

pub fn rewrite(req: &Request) -> Result<RewriteResult, String> {
    tables::ready()?;
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

/// Whether `output`, a `mode` rewrite of `source`, says what `source` says: the check every
/// tone rewrite passes sentence by sentence. For evaluation tools (examples/tone_judge.rs).
#[cfg(feature = "local-model")]
#[doc(hidden)]
pub fn tone_keeps_meaning(mode: Mode, source: &str, output: &str) -> Result<(), String> {
    let hints = |s: &str| model::linguistic_hints(s).unwrap_or_default();
    meaning::keeps_meaning(mode, source, output, "", &hints(source), &hints(output))
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

/// Loads the slip checker (the masked language model of the typing-time word-choice check) so the
/// first check is fast. Safe to call from any thread, repeatedly. Returns 1 when it is ready, else 0.
#[unsafe(no_mangle)]
pub extern "C" fn parzr_slips_warm() -> i32 {
    #[cfg(feature = "local-model")]
    if catch_unwind(slips::warm).unwrap_or(false) {
        return 1;
    }
    0
}

/// The app holds the model packs (1) while it re-hashes them at launch and lets go (0) once they
/// verified: until then no pack is used in this process, whatever its marker says.
#[unsafe(no_mangle)]
pub extern "C" fn parzr_packs_hold(on: i32) {
    packs::hold(on != 0);
}

/// The pinned model manifest compiled into this engine (`engine/models.json`), as JSON. The app
/// downloads and verifies what it lists. Free the returned string with `parzr_string_free`.
#[unsafe(no_mangle)]
pub extern "C" fn parzr_model_manifest() -> *mut c_char {
    CString::new(packs::MANIFEST_JSON)
        .map(CString::into_raw)
        .unwrap_or(std::ptr::null_mut())
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
/// The part of an edit's original range that really changes: the whole words its replacement
/// repeats at the start or the end stay out of it ("ROM memory" to "ROM" changes " memory"). The
/// edit's own range when it is an insertion, or when trimming would cut inside a word.
fn changed_words(e: &Edit) -> (usize, usize) {
    let (old, new): (Vec<char>, Vec<char>) = (
        e.original.chars().collect(),
        e.replacement.chars().collect(),
    );
    let word = |c: char| c.is_alphanumeric() || c == '\'' || c == '’';
    let mut head = old.iter().zip(&new).take_while(|(a, b)| a == b).count();
    // The shared start counts only up to a word boundary.
    while head > 0 && old.get(head).is_some_and(|c| word(*c)) && word(old[head - 1]) {
        head -= 1;
    }
    let room = old.len().min(new.len()) - head;
    let mut tail = old
        .iter()
        .rev()
        .zip(new.iter().rev())
        .take_while(|(a, b)| a == b)
        .count()
        .min(room);
    while tail > 0
        && tail < old.len()
        && word(old[old.len() - tail])
        && word(old[old.len() - tail - 1])
    {
        tail -= 1;
    }
    if head + tail >= old.len() || old.is_empty() {
        return (e.start_utf16, e.end_utf16);
    }
    let units = |chars: &[char]| chars.iter().map(|c| c.len_utf16()).sum::<usize>();
    (
        e.start_utf16 + units(&old[..head]),
        e.end_utf16 - units(&old[old.len() - tail..]),
    )
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
    RE.get_or_init(||Regex::new(r"(?ms)```.*?(?:```|\z)|~~~.*?(?:~~~|\z)|`[^`\n]*(?:`|$)|(?:https?://|www\.)[^\s<>]+|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|\B[@#]\w(?:[\w.-]*\w)?|(?:/|~/|[A-Za-z]:\\)[\w./\\-]+|\b[\w.-]*[\w-]/[\w.-]*\w(?:/[\w.-]+)*|(?i:\b(?:[\w.-]+/)*[\w-]+(?:\.[\w-]+)*\.(?:png|jpe?g|gif|svg|webp|heic|tiff?|bmp|ico|pdf|docx?|xlsx?|pptx?|odt|rtf|csv|tsv|txt|md|json|ya?ml|toml|xml|html?|css|scss|less|js|mjs|cjs|jsx|ts|tsx|py|rb|rs|java|kt|swift|cpp|hpp|cs|php|sh|zsh|bash|sql|zip|tar|gz|tgz|rar|7z|dmg|pkg|app|exe|msi|apk|ipa|mp3|mp4|mov|wav|m4a|aac|flac|avi|mkv|webm|sketch|fig|psd|log|env|lock|ini|cfg|conf|ipynb|vsix|epub|gguf|dylib|so|dll|jar|wasm)\b)|\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:com|org|net|io|app|dev|ai|co|uk|tv|xyz|info|biz|edu|gov|ly|tech|site|online|store|cloud|page|gg)\b|\b\d+(?:[.,:/-]\d+)*\b|(?m)^>[^\n]*| ?(?:[:;=8][-^o']?[)(\]\[dDpPoO3/\\|*]+|[)(][-^']?[:;]|<3+|\^_?\^|\bxD\b|:'\()(?:\s|$)|(?m)^-- ?$[\s\S]*|(?m)^\s*(?:curl|git|npm|npx|cargo|sudo|python3?|ssh|brew)\s[^\n]*(?:\\\n[^\n]*)*|[\u{FFFC}]|\b\w+_\w+\b|\b[A-Za-z]+\d+[A-Za-z\d]*\b|\b[a-z]+[A-Z][A-Za-z\d]*\b").expect("constant protected-span regex"))
}
/// Command-line tools typed lowercase; "go", "make" and "node" are English words first.
const TOOLS: [&str; 26] = [
    "apt", "apt-get", "aws", "brew", "cargo", "conda", "curl", "docker", "gcloud", "gem", "git",
    "helm", "kubectl", "npm", "npx", "pip", "pip3", "pipx", "pnpm", "poetry", "python", "python3",
    "rustup", "ssh", "sudo", "yarn",
];
/// What follows a tool's name in a command ("git pull", "brew install", "npm run").
const SUBCOMMANDS: [&str; 52] = [
    "add",
    "apply",
    "build",
    "cask",
    "check",
    "checkout",
    "ci",
    "clone",
    "commit",
    "compose",
    "config",
    "create",
    "delete",
    "deploy",
    "describe",
    "diff",
    "doctor",
    "down",
    "exec",
    "fetch",
    "fmt",
    "freeze",
    "get",
    "i",
    "info",
    "init",
    "install",
    "list",
    "log",
    "login",
    "logs",
    "ls",
    "merge",
    "new",
    "outdated",
    "publish",
    "pull",
    "push",
    "rebase",
    "remove",
    "reset",
    "restart",
    "run",
    "search",
    "show",
    "start",
    "stash",
    "status",
    "stop",
    "test",
    "uninstall",
    "update",
];
/// A shell command inside a sentence ("Install it with brew install ffmpeg.", "use python3 -m venv
/// .venv", "Run git pull before you start."): the tool, its subcommand, and then flags, paths and
/// words no dictionary knows, up to the first ordinary word or the sentence's end.
fn command_spans(text: &str) -> Vec<TextRange> {
    static TOOL: OnceLock<Regex> = OnceLock::new();
    let tool = TOOL.get_or_init(|| {
        Regex::new(r"(?:^|[\s(`])([a-z][a-z0-9-]*[a-z0-9])\b").expect("constant tool regex")
    });
    let mut out = vec![];
    for c in tool.captures_iter(text) {
        let m = c.get(1).expect("tool");
        if !TOOLS.contains(&m.as_str()) || text[m.end()..].starts_with(['.', '/', '-', '_']) {
            continue;
        }
        let mut end = m.end();
        let mut subcommand = true;
        let mut after_flag = false;
        let mut args = 0;
        loop {
            let rest = &text[end..];
            let Some(gap) = rest.strip_prefix(' ') else {
                break;
            };
            let arg_len = gap.find([' ', '\n', '\t']).unwrap_or(gap.len());
            let raw = &gap[..arg_len];
            // A sentence's own mark after the last argument is not part of it.
            let arg = raw.trim_end_matches(['.', ',', ';', '!', '?', ')', ':']);
            let well_formed = !arg.is_empty()
                && arg
                    .chars()
                    .all(|c| c.is_ascii_alphanumeric() || "-_./@:=~+".contains(c));
            let flag = arg.starts_with('-');
            let pathish =
                arg.contains(['.', '/', '@', ':', '=', '~', '_']) || arg.contains(char::is_numeric);
            let bare = arg.chars().all(|c| c.is_ascii_lowercase() || c == '-');
            let plain_word = bare && spelling::ordinary(arg);
            if !well_formed
                || !(flag
                    || pathish
                    || subcommand && (SUBCOMMANDS.contains(&arg) || TOOLS.contains(&arg))
                    || after_flag && bare
                    || bare && !plain_word)
                || args >= 8
            {
                break;
            }
            subcommand = false;
            after_flag = flag;
            args += 1;
            end += 1 + arg.len();
            if arg.len() != raw.len() {
                break;
            }
        }
        if args > 0 {
            out.push(TextRange {
                start_utf16: utf16_at(text, m.start()),
                end_utf16: utf16_at(text, end),
            });
        }
    }
    out
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
    spans.extend(command_spans(&req.text));
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
/// Words typed the way people talk in chats: a stretched word ("sooo", "yesss", "pleaseee") is no
/// slip of another word ("soon", "yes's"), so a respelling may only shorten its stretch; a dropped
/// "-ing" g ("holdin", "billin") is never split into "hold in", it may only get its g back, and a
/// marked one ("doin'") is left as typed.
fn chat_forms(text: &str, edits: &mut Vec<Edit>) {
    edits.retain_mut(|e| {
        // "c u later", "r u ok": chat letters are words of their own, never one word.
        if e.rule_id.starts_with("spelling.")
            && e.original.contains(' ')
            && e.original
                .split_whitespace()
                .all(|p| p.chars().count() == 1 && "curykbn".contains(p.to_lowercase().as_str()))
        {
            return false;
        }
        if !e.rule_id.starts_with("spelling.") || e.original.contains(char::is_whitespace) {
            return true;
        }
        let word = e.original.as_str();
        // "ofc!", "pic?", "tho.": shorthand that is also a slip ("round ofc interviews") is the
        // shorthand when no word follows it.
        let ends_clause = byte_at(text, e.end_utf16).is_some_and(|b| {
            text[b..]
                .trim_start_matches([' ', '\t'])
                .chars()
                .next()
                .is_none_or(|c| !c.is_alphanumeric())
        });
        if ends_clause
            && ["ofc", "tho", "fr", "pic", "pics", "eta", "bae", "vid", "xo"]
                .contains(&word.to_lowercase().as_str())
        {
            return false;
        }
        if names::stretched(word) {
            let fixed = e.replacement.to_lowercase();
            let letters: Vec<char> = word.to_lowercase().chars().collect();
            return (1..=2).any(|keep| fixed == names::squeeze(&letters, keep))
                && spelling::known(&fixed);
        }
        let g_less =
            word.len() >= 4 && word.ends_with("in") && word.chars().all(|c| c.is_ascii_lowercase());
        if !g_less {
            return true;
        }
        let full = format!("{word}g");
        let stem = &word[..word.len() - 2];
        // "interestedin", "notin" are two words: only a verb ("hold", "bill") or no word at all
        // ("runn") whose "-ing" form is a word lost its g.
        if !spelling::known(&full)
            || spelling::known(stem) && morphology::verb(&full).is_none_or(|v| v.base != stem)
        {
            return true;
        }
        let marked = byte_at(text, e.end_utf16)
            .and_then(|b| text[b..].chars().next())
            .is_some_and(|c| c == '\'' || c == '’');
        if marked {
            return false;
        }
        // "the linkin my last message", "the guyin the shirt": "in" before a determiner is the
        // preposition, and the split stands.
        let next_word = byte_at(text, e.end_utf16)
            .map(|b| text[b..].split_whitespace().next().unwrap_or(""))
            .unwrap_or("")
            .to_lowercase();
        if e.replacement.to_lowercase() != format!("{} in", &word[..word.len() - 2])
            || [
                "the", "a", "an", "my", "your", "his", "her", "our", "their", "these", "those",
                "its",
            ]
            .contains(&next_word.as_str())
        {
            return true;
        }
        e.replacement = match_case(&full, &e.replacement);
        e.explanation = "Add the g this word dropped.".into();
        true
    });
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
    } else if original.chars().next().is_some_and(char::is_uppercase)
        // The capital of "I do" is the pronoun's own: a replacement that moves it ("do I") is not
        // a sentence start, which the caller adds where one is.
        && !(original.len() > 1
            && original.starts_with('I')
            && !original[1..].starts_with(|c: char| c.is_alphabetic()))
    {
        upper_first(replacement)
    } else {
        replacement.to_string()
    }
}
/// Words written twice on purpose: "that that", "had had", "very very", "bye bye", "no no".
pub(crate) const DOUBLED_ON_PURPOSE: [&str; 47] = [
    "had", "do", "very", "so", "really", "no", "yes", "yeah", "ha", "haha", "bye", "well", "blah",
    "bla", "knock", "night", "hush", "chop", "tsk", "ok", "okay", "oh", "ah", "uh", "um", "la",
    "there", "now", "go", "more", "many", "far", "again", "too", "much", "ho", "hey", "hi", "wow",
    "boo", "tick", "tock", "choo", "yum", "mm", "hmm", "pretty",
];
/// The word at `index` repeats the one before it by a slip ("the the", "call call"). Doubles that
/// can be meant are kept, and so is "is is" after "what it" ("what it is is").
fn repeated_by_mistake(tokens: &[tokenizer::Token<'_>], index: usize) -> bool {
    let token = &tokens[index];
    let w = token.normalized.as_str();
    let before = |k: usize| index >= k && tokens[index - k].sentence == token.sentence;
    // "jk jk", "sure sure", "lol lol", "thanks thanks": chat doubles are meant too.
    let meant = DOUBLED_ON_PURPOSE.contains(&w)
        || names::is_shorthand(w)
        || [
            "sure", "thanks", "thank", "please", "cool", "nice", "wait", "come", "stop", "fine",
        ]
        .contains(&w);
    token.is_word
        && !meant
        // "a A": an article and the letter it names.
        && !(token.surface.chars().count() == 1 && token.surface != tokens[index - 1].surface)
        // "what it is is", "all that is is": a clause about what something is, then its verb.
        && !(w == "is"
            && before(3)
            && ["it", "that", "this"].contains(&tokens[index - 2].normalized.as_str())
            && ["what", "all", "way", "how", "who", "where", "whatever"]
                .contains(&tokens[index - 3].normalized.as_str()))
        // "that that": a demonstrative after the conjunction ("I know that that works") is meant;
        // a pronoun, article or plural noun after both is not.
        // "put in in the model": the first "in" is "it", which the grammar pass restores.
        && !(w == "in"
            && before(2)
            && crate::forms::PUT_IN.contains(&tokens[index - 2].normalized.as_str())
            && !(before(3)
                && ["be", "been", "being", "is", "are", "was", "were", "get", "got"]
                    .contains(&tokens[index - 3].normalized.as_str()))
            && tokens.get(index + 1).is_some_and(|n| n.is_word))
        && (w != "that"
            // "what you mean by that that.": nothing follows to make it a demonstrative.
            || tokens
                .get(index + 1)
                .is_none_or(|n| n.sentence != token.sentence || [".", "!", "?"].contains(&n.surface))
            || tokens.get(index + 1).is_some_and(|n| {
                n.sentence == token.sentence
                    && ([
                        "i", "you", "he", "she", "we", "they", "there", "the", "a", "an", "my",
                        "your", "his", "our", "their", "its", "some", "many", "most", "these",
                        "those", "if", "when", "once",
                    ]
                    .contains(&n.normalized.as_str())
                        || (n.pos == "Noun" || spelling::flags(&n.normalized) & 2 != 0)
                            && structure::plural(n) == Some(true)
                            && !n.proper_name
                            // "the ethics that that implicates": a verb, not a plural noun.
                            && !morphology::verb(&n.normalized).is_some_and(|v| {
                                v.third == n.normalized && spelling::flags(&n.normalized) & 4 != 0
                            }))
            }))
        // A capitalized double inside a sentence is a name ("Bora Bora", "Walla Walla").
        && !(token.surface.starts_with(char::is_uppercase)
            && tokens[index - 1].surface.starts_with(char::is_uppercase)
            && before(2))
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
        // "Hmm... let me think": a lowercase word after an ellipsis goes on with the sentence.
        && !((before.ends_with("..") || before.ends_with('…'))
            && text[byte..].starts_with(char::is_lowercase))
        // "“Where are you? she asked": the mark ends the quotation, not the sentence.
        && !(before.ends_with(['!', '?'])
            && text[byte..].starts_with(char::is_lowercase)
            && marks::inside_open_quote(text, before.len() - 1))
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
    // Misspellings mined from real corrections, matched word by word ("Febuary", "existant").
    // A capital inside a sentence may be a name ("Siller", "Princip"): only a misspelt proper noun
    // ("Febuary", "Britian") the system checker does not accept is respelled there; capitals
    // throughout only on longer words ("INITALIZED").
    for (ti, t) in tokens.iter().enumerate().filter(|_| !tone_only) {
        // The writer's names and dictionary words (and links, code, file names) are never respelled.
        if protected
            .iter()
            .chain(guard.iter())
            .any(|r| overlaps(t.start_utf16, t.end_utf16, r))
        {
            continue;
        }
        // "Wenesday", "Thurday": a capitalized slip of a day or month name.
        let day = spelling::calendar_slip(t);
        let Some(correction) = (t.is_word && t.surface.is_ascii())
            .then(|| rules::mined_typo(&t.normalized))
            .flatten()
            .or(day.as_deref())
        else {
            continue;
        };
        // "two childrens" is "two children": the possessive of an irregular plural is right only
        // before the thing possessed ("my childrens school") or with its own apostrophe.
        let correction = correction
            .strip_suffix("'s")
            .filter(|base| ["children", "women", "men", "people"].contains(base))
            .filter(|_| !spelling::possessed_noun_follows(t, tokens.get(ti + 1)))
            .unwrap_or(correction);
        let original = t.surface;
        let mut letters = original.chars();
        let capital = letters.next().is_some_and(|c| c.is_ascii_uppercase());
        let rest_lower = letters.clone().all(|c| !c.is_ascii_uppercase());
        let all_caps = letters.all(|c| !c.is_ascii_lowercase());
        let allowed = if !capital {
            rest_lower
        } else if rest_lower {
            starts_sentence(&req.text, t.start_byte, req)
                || correction.starts_with(|c: char| c.is_ascii_uppercase()) && !t.system_known
        } else {
            all_caps && original.len() >= 6 && !t.system_known
        };
        if !allowed {
            continue;
        }
        let mut replacement = typo_capital(
            match_case(correction, original),
            original,
            starts_sentence(&req.text, t.start_byte, req),
        );
        if starts_sentence(&req.text, t.start_byte, req)
            && req.text.trim_end().ends_with(['.', '!', '?'])
        {
            replacement = upper_first(&replacement);
        }
        // "childrens' toys": the token already carries the apostrophe a possessive correction would
        // add ("children's"), so the correction takes the typed one with it. Any other correction
        // with an apostrophe would leave a stray mark ("children's'") and is dropped; a word in
        // single quotes ('recieve') is no such case.
        let mark = req.text[t.end_byte..]
            .chars()
            .next()
            .filter(|c| ['\'', '’'].contains(c) && correction.contains('\''));
        let mut end_utf16 = t.end_utf16;
        if let Some(mark) = mark {
            let after = req.text[t.end_byte + mark.len_utf8()..].chars().next();
            if !correction.ends_with("'s") || after.is_some_and(char::is_alphanumeric) {
                continue;
            }
            end_utf16 += 1;
            if mark == '’' {
                replacement = replacement.replace('\'', "’");
            }
        }
        if let Some(e) = make_edit(
            &req.text,
            t.start_utf16,
            end_utf16,
            replacement,
            "Spelling",
            "spelling.common_misspelling",
            "This is a common misspelling.",
            0.95,
        ) {
            edits.push(e);
        }
    }
    for (compiled, windows) in rules::contextual().iter().zip(rules::windows(&req.text)) {
        let rule = &compiled.rule;
        let Some(windows) = windows else { continue };
        if tone_only == rule.modes.is_empty()
            || (!rule.modes.is_empty() && !rule.modes.contains(&req.mode))
        {
            continue;
        }
        let regex = compiled.regex();
        // Each window is a slice of the text; positions below are made absolute with `ws`.
        // `is_match` runs the fast automaton; the capturing engines, which are much slower on the
        // long alternations the packs use, run only on a window that has a match.
        for captures in windows
            .iter()
            .filter(|&&(ws, we)| regex.is_match(&req.text[ws..we]))
            .flat_map(|&(ws, we)| regex.captures_iter(&req.text[ws..we]).map(move |c| (ws, c)))
        {
            let (ws, captures) = captures;
            let Some(m) = captures.name("target").or_else(|| captures.get(0)) else {
                continue;
            };
            let (m_start, m_end) = (ws + m.start(), ws + m.end());
            let mut replacement = String::new();
            captures.expand(&rule.replacement, &mut replacement);
            // "Me and Sarah are" to "Sarah and I are": the name only moves, never respelled. The
            // words before it go and the replacement follows it, as one linked pair of edits.
            if let Some(moved) = captures.name("moved") {
                let group = format!("{}@{}", rule.id, m_start);
                let at = |b| utf16_at(&req.text, b);
                let edit = |start, end, text: String| {
                    make_edit(
                        &req.text,
                        start,
                        end,
                        text,
                        &rule.category,
                        &rule.id,
                        &rule.explanation,
                        rule.confidence,
                    )
                };
                if let (Some(mut cut), Some(mut put)) = (
                    edit(at(m_start), at(ws + moved.start()), String::new()),
                    edit(at(ws + moved.end()), at(ws + moved.end()), replacement),
                ) {
                    cut.group_id = Some(group.clone());
                    put.group_id = Some(group);
                    edits.extend([cut, put]);
                }
                continue;
            }
            // "Jen and I" to "Jen and me": a lone "I" is capital by spelling, not by position.
            replacement = if rule.id == "grammar.between_you_i" {
                "me".into()
            } else if m.as_str() == "I" {
                replacement
            } else {
                typo_capital(
                    match_case(&replacement, m.as_str()),
                    m.as_str(),
                    starts_sentence(&req.text, m_start, req),
                )
            };
            if starts_sentence(&req.text, m_start, req) && !replacement.is_empty() {
                replacement = upper_first(&replacement);
            }
            if let Some(e) = make_edit(
                &req.text,
                utf16_at(&req.text, m_start),
                utf16_at(&req.text, m_end),
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
                    utf16_at(&req.text, ws + action.start()),
                    utf16_at(&req.text, ws + action.start() + first.len_utf8()),
                    first.to_uppercase().to_string(),
                    "Tone",
                    "tone.action_capitalization",
                    "Capitalize the action after removing the request wrapper.",
                    0.97,
                ) {
                    edits.push(e);
                }
            }
            // Direct turns a request into an instruction. Concise does so only for the wrapper
            // of a statement ("I was wondering if you could send it?"): a question stays one.
            if (req.mode == Mode::Direct && rule.id.ends_with(".request")
                || matches!(req.mode, Mode::Direct | Mode::Concise)
                    && rule.id.ends_with(".hedged_request"))
                && let Some((offset, c)) = req.text[m_end..]
                    .char_indices()
                    .find(|(_, c)| ['?', '!', '.', '\n'].contains(c))
                && c == '?'
            {
                let byte = m_end + offset;
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
        contractions::check(req, &tokens, &mut edits);
        capitalization::check(req, &tokens, &mut edits);
        compounds::check(req, &tokens, &mut edits);
        punctuation::check(req, &mut edits);
        structure::check(req, &mut edits);
        clause_repairs::check(req, &mut edits);
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
        // "i'm", "i’ll": the contracted pronoun takes its capital too, and only its first letter.
        let contracted_i = ["i'm", "i've", "i'll", "i'd"].contains(&token.normalized.as_str())
            && token.surface.starts_with('i')
            && token.surface[1..].chars().all(|c| !c.is_uppercase());
        // "c) What is covered?", "(i) a credit decision": a letter or numeral that labels a list item.
        let enumerator = token.surface.chars().count() <= 4
            && req.text[token.end_byte..].starts_with(')')
            && (token.surface.chars().count() == 1
                || token.surface.chars().all(|c| "ivxlc".contains(c)));
        if (token.normalized == "i" && token.surface == "i" || contracted_i)
            && !dotted_abbreviation
            && !enumerator
        {
            if let Some(e) = make_edit(
                &req.text,
                token.start_utf16,
                token.start_utf16 + 1,
                "I".into(),
                "Capitalization",
                "grammar.personal_pronoun",
                "Capitalize the first-person pronoun.",
                0.99,
            ) {
                edits.push(e);
            }
        } else if starts_sentence(&req.text, token.start_byte, req)
            && !enumerator
            // "fyi the build is green", "lmk if": chat acronyms stay as typed, never "Fyi".
            && !names::is_chat_acronym(&token.normalized)
            // "c u later", "k thanks": a chat letter is no word to capitalize.
            && (token.surface.chars().count() > 1 || token.normalized == "a")
            && token.surface.chars().next().is_some_and(char::is_lowercase)
            && (spelling::known(&token.normalized)
                || capitalization::interjection(&token.normalized)
                || capitalization::sign_off_name(&req.text, token)
                // "yaar kal meeting hai": Roman Hindi opens a sentence with a capital too.
                || spelling::roman_hindi(&tokens, index)
                || req.capitalize_names && level[index] >= names::MEDIUM)
            // Every sentence takes its capital, finished or not and in chat too ("yeah I think",
            // "the link? Thanks"): only a line of code or a command keeps its lowercase start.
            && !capitalization::code_start(&req.text, token)
        {
            let first = token.surface.chars().next().unwrap_or(' ');
            // "mcdonald" is "McDonald", "iphone" is "iPhone"; other words only need their first letter.
            let (end, replacement) = if token.surface == "ok" {
                // "ok sounds good": the opening "ok" is written "OK", as GECToR and the model write it.
                (token.end_utf16, "OK".to_string())
            } else if let Some(canonical) = spelling::canonical_case(&token.normalized) {
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
            // "we we're", "should shouldn't": the word and then its own contraction.
            let contracted = previous.normalized != "that"
                && previous.is_word
                && token
                    .normalized
                    .strip_prefix(previous.normalized.as_str())
                    .is_some_and(|rest| {
                        ["'re", "'s", "'d", "'ll", "'ve", "'m", "n't", "'t"].contains(&rest)
                    });
            if (previous.normalized == token.normalized && repeated_by_mistake(&tokens, index)
                || contracted)
                && previous.sentence == token.sentence
                && previous.paragraph == token.paragraph
            {
                let gap = &req.text[previous.end_byte..token.start_byte];
                // "a A$1.5 billion" and "US$ 5": the letter belongs to a currency or code token.
                // A word of two letters or more may run into a hyphen ("for for-profit").
                let code = req.text[token.end_byte..].starts_with(|c: char| {
                    c.is_ascii_digit()
                        || "$€£¥#/_".contains(c)
                        || c == '-' && token.surface.chars().count() < 2
                });
                // "the The Beatles", "we we're": the second copy is the one to keep. A capital
                // after a lowercase copy is kept only on a function word ("home arena Arena
                // Mexico" is a name, "as well as AS units" an acronym).
                let raised = token.surface.starts_with(char::is_uppercase)
                    && !previous.surface.starts_with(char::is_uppercase);
                let keep_second = contracted || raised;
                let name_like = raised
                    && (![
                        "the", "a", "an", "and", "of", "in", "on", "to", "for", "with", "at", "by",
                        "from",
                    ]
                    .contains(&token.normalized.as_str())
                        || token.surface.chars().count() > 1
                            && token.surface.chars().all(char::is_uppercase));
                let (start, end) = if keep_second {
                    (previous.start_utf16, token.start_utf16)
                } else {
                    (previous.end_utf16, token.end_utf16)
                };
                if !gap.is_empty()
                    && !code
                    && !name_like
                    && gap.chars().all(|c| c == ' ' || c == '\t')
                    && let Some(e) = make_edit(
                        &req.text,
                        start,
                        end,
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
                .or_else(|| {
                    spelling::suggest_capitalized(
                        token,
                        &req.dialect,
                        index.checked_sub(1).and_then(|i| tokens.get(i)),
                        tokens.get(index + 1),
                        &tokens[..index],
                        &tokens[index + 1..],
                    )
                })
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
        for c in names::lowercase_possessives(&req.text, &tokens) {
            if let Some(e) = make_edit(
                &req.text,
                c.start_utf16,
                c.end_utf16,
                c.replacement.clone(),
                "Style",
                "names.possessive",
                &format!("Write the name's possessive as “{}”.", c.replacement),
                0.88,
            ) {
                edits.push(e);
            }
        }
        for c in names::capitalizations(
            &req.text,
            &tokens,
            &level,
            &index.phrase_cover(&tokens),
            |b| utf16_at(&req.text, b),
        ) {
            // A word the spelling pass respelled ("covers moe than" to "more") is no name to capitalize.
            if edits.iter().any(|e| {
                e.category == "Spelling"
                    && e.start_utf16 < c.end_utf16
                    && e.end_utf16 > c.start_utf16
            }) {
                continue;
            }
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
    // A restored contraction changes what the next word agrees with ("Youll love" is not a
    // third-person subject): other edits to that word wait for the pass that reads the fix.
    // A respelled or rejoined word does the same ("T he build" is not "he build").
    let rewords = |e: &Edit| {
        [
            "spelling.contraction",
            "spelling.split_word",
            "spelling.delete_index",
        ]
        .contains(&e.rule_id.as_str())
    };
    // The word after a respelled word waits only for agreement edits; after a contraction, for all.
    let restored: Vec<(usize, usize, bool)> = edits
        .iter()
        .filter(|e| rewords(e))
        .filter_map(|e| {
            let next = tokens
                .iter()
                .find(|t| t.start_utf16 >= e.end_utf16 && t.is_word)?;
            Some((
                e.end_utf16,
                next.end_utf16,
                e.rule_id != "spelling.delete_index",
            ))
        })
        .collect();
    edits.retain(|e| {
        rewords(e)
            || !restored.iter().any(|(a, b, all)| {
                e.start_utf16 >= *a && e.start_utf16 < *b && (*all || e.category == "Grammar")
            })
    });
    chat_forms(&req.text, &mut edits);
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
    // The tagger calls some apostrophe-less contractions names ("Im", "Theyre"); a contraction
    // the user did not add to the dictionary is still restored.
    let contraction = |e: &Edit| {
        e.rule_id == "spelling.contraction"
            && !req
                .dictionary
                .iter()
                .chain(&req.names)
                .any(|w| w.eq_ignore_ascii_case(&e.original))
    };
    // "Sarahs laptop" to "Sarah's laptop": an apostrophe added to or dropped from a name keeps
    // every letter of it.
    let apostrophe_only = |e: &Edit| {
        let letters = |s: &str| s.replace(['\'', '’'], "");
        e.rule_id == "punctuation.apostrophe" && letters(&e.original) == letters(&e.replacement)
            // "noahs" to "Noah's": the name's capital and its apostrophe, no letter changed.
            || e.rule_id == "names.possessive"
                && letters(&e.original).to_lowercase() == letters(&e.replacement).to_lowercase()
    };
    // A sentence's first word is capitalized by position, so the tagger's name guess there is weak
    // evidence: an ordinary word that a context rule rewrites ("Hat makes sense", "Thy said", "Bit
    // honestly") is a slip, unless the user, the bundled list or a capital elsewhere makes it a name.
    let user_words = index.dictionary_hits(&tokens);
    let opens_sentence = |i: usize| {
        i == 0
            || tokens[i - 1].paragraph != tokens[i].paragraph
            || [".", "!", "?"].contains(&tokens[i - 1].surface)
    };
    let first_word_guess = |r: &TextRange| {
        tokens.iter().enumerate().any(|(i, t)| {
            t.proper_name
                && t.start_utf16 == r.start_utf16
                && t.end_utf16 == r.end_utf16
                && !user_words[i]
                && opens_sentence(i)
                && spelling::ordinary(&t.normalized)
                && !names::is_bundled_name(&t.normalized)
                && !req.names.iter().any(|n| n.to_lowercase() == t.normalized)
                && !tokens.iter().enumerate().any(|(j, o)| {
                    j != i
                        && o.normalized == t.normalized
                        && o.surface.starts_with(char::is_uppercase)
                        && !opens_sentence(j)
                })
        })
    };
    let slip = |e: &Edit| e.rule_id.starts_with("usage.") || e.rule_id == "spelling.real_word";
    // "Tha t is fine": the tagger's name guess on a piece of a word split by a space is no name;
    // the user's names and dictionary and the bundled list still win.
    // "Wwe watched", "Cna we": the tagger's name guess on a sentence opener that is a clear slip.
    let tagger_piece = |e: &Edit, r: &TextRange| {
        (e.rule_id == "spelling.split_word" || e.rule_id == "spelling.delete_index")
            && tokens.iter().enumerate().any(|(i, t)| {
                t.proper_name
                    && (e.rule_id == "spelling.split_word"
                        || spelling::opening_name_slip(&tokens, i))
                    && t.start_utf16 == r.start_utf16
                    && t.end_utf16 == r.end_utf16
                    && !user_words[i]
                    && !names::is_bundled_name(&t.normalized)
                    && !req.names.iter().any(|n| n.to_lowercase() == t.normalized)
            })
    };
    let exempt = |e: &Edit, r: &TextRange| {
        // "Hi again,Ken": a space put before a protected word leaves the word as typed.
        e.start_utf16 == e.end_utf16
            && e.start_utf16 == r.start_utf16
            && !e.replacement.is_empty()
            && e.replacement.chars().all(char::is_whitespace)
            || (raises_case(e) || contraction(e) || apostrophe_only(e)) && tagged(r)
            || slip(e) && first_word_guess(r)
            || tagger_piece(e, r)
    };
    let blocked = |e: &Edit| {
        // Whole words the edit leaves as they are do not count as touched: "ROM memory" to "ROM"
        // changes only " memory", and "please RSVP" to "RSVP" only "please ".
        let (from, to) = changed_words(e);
        protected
            .iter()
            .any(|r| overlaps(from, to, r) && !exempt(e, r))
            || !case_only(e)
                && !contraction(e)
                && !apostrophe_only(e)
                && if e.start_utf16 != e.end_utf16 {
                    guard.iter().any(|r| {
                        overlaps(from, to, r)
                            && !(slip(e) && first_word_guess(r))
                            && !tagger_piece(e, r)
                    })
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
/// What a request that panicked answers: the process keeps serving the next one.
pub const PANICKED: &str = r#"{"error":"The writing engine could not complete the request."}"#;
/// Runs one request's handling and turns a panic into the `PANICKED` error, so one bad request
/// never takes down a long-lived host (the browser host, the LSP, the stdin engine). The shared
/// state a request touches tolerates a panic part-way: its locks recover from poisoning.
pub fn guarded(handle: impl FnOnce() -> String) -> String {
    catch_unwind(AssertUnwindSafe(handle)).unwrap_or_else(|_| PANICKED.into())
}
/// `process_json`, with a panic answered as an error instead of unwinding into the caller.
pub fn process_json_guarded(input: &str) -> String {
    guarded(|| process_json(input))
}
/// # Safety
/// `input` must point to a valid NUL-terminated UTF-8 string alive for this call.
/// Free the returned owned string exactly once with `parzr_string_free`.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn parzr_rewrite_json(input: *const c_char) -> *mut c_char {
    if input.is_null() {
        return std::ptr::null_mut();
    }
    let result = guarded(|| {
        // SAFETY: the C ABI caller guarantees a valid NUL-terminated string.
        let input = unsafe { CStr::from_ptr(input) }.to_str().map_err(|_| ());
        input
            .map(process_json)
            .unwrap_or_else(|_| r#"{"error":"Input is not UTF-8."}"#.into())
    });
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
/// A rewrite written outside the engine (Apple Foundation Models on iOS) to check with the same
/// meaning guard the engine's own tone rewrites pass. The tokens are the caller's linguistic hints
/// for each text (as `Request::tokens`); without them the guard still runs on surface words.
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct GuardRequest {
    mode: Mode,
    source: String,
    output: String,
    #[serde(default)]
    source_tokens: Vec<TokenHint>,
    #[serde(default)]
    output_tokens: Vec<TokenHint>,
}
#[derive(Serialize)]
struct GuardVerdict {
    ok: bool,
    /// The output without an announcing preamble ("Here is the edited text:").
    output: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    reason: Option<String>,
}
fn guard(req: GuardRequest) -> GuardVerdict {
    if let Err(error) = tables::ready() {
        return GuardVerdict {
            ok: false,
            output: req.output,
            reason: Some(error),
        };
    }
    let mut output = req.output.trim().to_string();
    let mut output_tokens = req.output_tokens;
    if let Some(head) = meaning::preamble(&output) {
        output = output[head.len() + 1..].trim().to_string();
        // The caller's hints index the text with its preamble.
        output_tokens.clear();
    }
    let verdict = if output.is_empty() {
        Err("the rewrite is empty".to_string())
    } else if output == req.source.trim() {
        Ok(())
    } else {
        meaning::keeps_meaning(
            req.mode,
            &req.source,
            &output,
            "",
            &req.source_tokens,
            &output_tokens,
        )
    };
    GuardVerdict {
        ok: verdict.is_ok(),
        output,
        reason: verdict.err(),
    }
}
pub fn tone_guard_json(input: &str) -> String {
    if input.len() > MAX_TEXT_BYTES * 8 {
        return r#"{"error":"Request exceeds size limit."}"#.into();
    }
    match serde_json::from_str::<GuardRequest>(input) {
        Ok(req) if req.source.len() <= MAX_TEXT_BYTES && req.output.len() <= MAX_TEXT_BYTES => {
            serde_json::to_string(&guard(req))
                .unwrap_or_else(|_| r#"{"error":"Could not encode result."}"#.into())
        }
        Ok(_) => r#"{"error":"Select at most 64 KB of text."}"#.into(),
        Err(_) => r#"{"error":"Invalid guard request."}"#.into(),
    }
}
/// Checks a rewrite written outside the engine with the tone meaning guard. Input is JSON
/// `{"mode","source","output","source_tokens"?,"output_tokens"?}`; the result is
/// `{"ok":bool,"output":string,"reason"?:string}` or `{"error":string}`.
/// # Safety
/// `input` must point to a valid NUL-terminated UTF-8 string alive for this call.
/// Free the returned owned string exactly once with `parzr_string_free`.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn parzr_tone_guard_json(input: *const c_char) -> *mut c_char {
    if input.is_null() {
        return std::ptr::null_mut();
    }
    let result = catch_unwind(AssertUnwindSafe(|| {
        // SAFETY: the C ABI caller guarantees a valid NUL-terminated string.
        let input = unsafe { CStr::from_ptr(input) }.to_str().map_err(|_| ());
        input
            .map(tone_guard_json)
            .unwrap_or_else(|_| r#"{"error":"Input is not UTF-8."}"#.into())
    }))
    .unwrap_or_else(|_| r#"{"error":"The writing engine could not complete the request."}"#.into());
    CString::new(result)
        .map(CString::into_raw)
        .unwrap_or(std::ptr::null_mut())
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn a_capital_i_is_the_pronouns_not_a_sentence_start() {
        // "Neither I do" is moved to "do I": only a sentence start is capitalized, by its caller.
        assert_eq!(match_case("do I", "I do"), "do I");
        assert_eq!(match_case("do I", "I"), "Do I");
        assert_eq!(match_case("are not", "I'm not"), "are not");
        assert_eq!(match_case("Is it", "It is"), "Is it");
        assert_eq!(match_case("the", "The"), "The");
        assert_eq!(match_case("do I", "Is"), "Do I");
        assert_eq!(match_case("it", "IT'S"), "IT");
    }
    #[test]
    fn affective_and_reins_are_words() {
        for text in [
            "She has seasonal affective disorder.",
            "The affective response was strong.",
            "He took the reins of the company.",
        ] {
            assert_eq!(fix(text), text);
        }
    }
    #[test]
    fn the_slip_switch_defaults_on_and_requests_without_it_still_parse() {
        // The browser host and the LSP never send it: they keep the slip check.
        let old: Request = serde_json::from_str(r#"{"text":"I hat it."}"#).unwrap();
        assert!(old.slips);
        assert!(Request::default().slips);
        let off: Request = serde_json::from_str(r#"{"text":"I hat it.","slips":false}"#).unwrap();
        assert!(!off.slips);
        let on: Request = serde_json::from_str(r#"{"text":"I hat it.","slips":true}"#).unwrap();
        assert!(on.slips);
        // Other unknown fields are still refused (deny_unknown_fields), so a misspelt switch is caught.
        assert!(serde_json::from_str::<Request>(r#"{"text":"x","slip":false}"#).is_err());
    }
    #[test]
    fn capitalized_known_typos_mid_sentence_get_lowercase_fixes() {
        assert_eq!(typo_capital("The".into(), "Teh", false), "the");
        assert_eq!(typo_capital("Their".into(), "Thier", false), "their");
        assert_eq!(typo_capital("The".into(), "Teh", true), "The");
        assert_eq!(typo_capital("THE".into(), "TEH", false), "THE");
        // Not a known misspelling: keep the case match (a name or a deliberate capital).
        assert_eq!(typo_capital("Mark".into(), "Mark", false), "Mark");
    }
    #[test]
    fn the_tone_guard_checks_rewrites_written_outside_the_engine() {
        let check = |mode: &str, source: &str, output: &str| -> serde_json::Value {
            let input = serde_json::json!({"mode": mode, "source": source, "output": output});
            serde_json::from_str(&tone_guard_json(&input.to_string())).unwrap()
        };
        let kept = check(
            "professional",
            "can u send me the report by friday",
            "Could you send me the report by Friday?",
        );
        assert_eq!(kept["ok"], true, "{kept}");
        // A preamble is dropped before the check, and the clean output is returned.
        let announced = check(
            "professional",
            "can u send me the report by friday",
            "Here is the edited text: Could you send me the report by Friday?",
        );
        assert_eq!(
            announced["output"],
            "Could you send me the report by Friday?"
        );
        // A changed number, a dropped negation and a refusal never pass.
        assert_eq!(
            check(
                "concise",
                "We need 12 chairs for the meeting.",
                "We need 20 chairs for the meeting."
            )["ok"],
            false
        );
        assert_eq!(
            check(
                "direct",
                "I do not want to join the call.",
                "I want to join the call."
            )["ok"],
            false
        );
        let refusal = check(
            "professional",
            "Are you stupid?",
            "I cannot rewrite this text as it is offensive and disrespectful. Is there anything else I can help you with?",
        );
        assert_eq!(refusal["ok"], false, "{refusal}");
        assert!(tone_guard_json("{}").contains("error"));
    }
    #[test]
    fn a_dot_glued_to_a_lowercase_letter_is_not_a_sentence_end() {
        for text in [
            "Use os.path.join here.",
            "Visit example.com today.",
            "Open the file config.yaml now.",
        ] {
            assert_eq!(fix(text), text);
        }
        assert_eq!(
            fix("I left. then I came back."),
            "I left. Then I came back."
        );
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
    fn chat_spellings_are_not_slips_of_a_frequent_word() {
        // "abt" is "about" in chat, not a near miss of "at".
        for text in [
            "We need to talk abt the lease today.",
            "Call me abt the invoice.",
        ] {
            assert_eq!(fix(text), text);
        }
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
            "We met Zoë and ZOË"
        );
        assert_eq!(
            fix_request(with_names("send it to jean-luc today", &["Jean-Luc"], true)),
            "Send it to Jean-Luc today"
        );
        assert_eq!(
            fix_request(with_names("ask o'neil about it", &["O'Neil"], true)),
            "Ask O'Neil about it"
        );
        // Off by default: case is left alone mid-sentence.
        let text = "Ask aman jain about it";
        assert_eq!(fix_request(with_names(text, &["Aman Jain"], false)), text);
    }
    #[test]
    fn the_writers_names_are_never_respelled_by_the_misspelling_list() {
        assert_eq!(
            fix_request(with_names("I read the projet today.", &[], false)),
            "I read the project today."
        );
        assert_eq!(
            fix_request(with_names("I read the projet today.", &["projet"], false)),
            "I read the projet today."
        );
    }
    #[test]
    fn a_capital_you_inside_a_sentence_is_lowercased_but_headings_keep_theirs() {
        let fix = |t: &str| fix_request(with_names(t, &[], true));
        assert_eq!(
            fix("Hey, You have Clickhouse available now!"),
            "Hey, you have Clickhouse available now!"
        );
        assert_eq!(
            fix("Thanks, Your help was great."),
            "Thanks, your help was great."
        );
        assert_eq!(
            fix("Everything You Need To Know About Rust"),
            "Everything You Need To Know About Rust"
        );
        assert_eq!(
            fix("You did it. You really did."),
            "You did it. You really did."
        );
    }
    #[test]
    fn file_names_and_domains_are_never_capitalized() {
        for text in [
            "aman.png",
            "Rename it to aman.png",
            "Send AMAN.PNG and priya_notes.docx",
            "See parzr.app and github.com",
            "Message in devops-general",
            "Post in aman-notes please",
            "Using jn-aman/m365-agent-gateway: a local gateway",
        ] {
            assert_eq!(
                fix_request(with_names(text, &["Aman", "Priya"], true)),
                text
            );
        }
        assert_eq!(
            fix_request(with_names("send it to aman", &["Aman"], true)),
            "Send it to Aman"
        );
        assert_eq!(
            fix_request(with_names("send it to jean-luc", &["Jean-Luc"], true)),
            "Send it to Jean-Luc"
        );
    }
    #[test]
    fn contracted_i_gets_one_capital_and_possessive_names_do_not_crash() {
        assert_eq!(
            fix_request(with_names("i'm here and i've done it", &[], true)),
            "I'm here and I've done it"
        );
        // The pipeline once panicked here, splitting the name's capital from its apostrophe.
        let req = Request {
            gec: true,
            ..with_names("I like noahs life.", &[], true)
        };
        assert!(pipeline::rewrite(&req).is_ok());
    }
    #[test]
    fn greetings_capitalize_names_not_the_people_or_words_they_address() {
        for text in [
            "Hi again, Ken.",
            "Hey there, how are you?",
            "Thanks, everyone.",
            "Hi team, quick update.",
            "Dear team, please note the change.",
            "Hello world",
            "Hey, there's a bug.",
            "Hi guys",
            "Bye, folks!",
            "Hey buddy, what's up?",
            "Hi both, see attached.",
            "Hey, that's fine.",
        ] {
            assert_eq!(fix_request(with_names(text, &[], true)), text, "{text}");
        }
        for (input, output) in [
            ("hey hope!", "Hey Hope!"),
            // A letter outside ASCII once crashed the check for a slipped greeting word.
            (
                "Hey s\u{f8}ren! Long time no see.",
                "Hey S\u{f8}ren! Long time no see.",
            ),
            ("Thanks, rose.", "Thanks, Rose."),
            ("Hi mom", "Hi Mom"),
            ("Hey jack, can you check?", "Hey Jack, can you check?"),
        ] {
            assert_eq!(fix_request(with_names(input, &[], true)), output, "{input}");
        }
    }
    #[test]
    fn lowercase_names_with_a_bare_possessive_s_get_the_apostrophe() {
        for (input, output) in [
            ("I like noahs life.", "I like Noah's life."),
            ("That was sarahs idea.", "That was Sarah's idea."),
        ] {
            assert_eq!(fix_request(with_names(input, &[], true)), output, "{input}");
        }
        for text in [
            "I borrowed johns car.",
            "We met the joneses at noon.",
            "The jones family",
            "Their kids play here.",
        ] {
            assert_eq!(fix_request(with_names(text, &[], true)), text, "{text}");
        }
    }
    #[test]
    fn chat_words_lists_and_commands_are_left_as_typed() {
        for text in [
            "I'm sooo tired.",
            "Yesss we did it!",
            "Haha true",
            "idk... and idc either lmao",
            "His name is bullseye bc you see",
            "doin' fine, thanks",
            "c) What is covered?",
            "She said (i) this is fine and (ii) that is too.",
            "use python3 -m venv .venv",
            "Install it with brew install ffmpeg.",
            "The bug is in src/main.rs line 42.",
            "The error is coming from utils/date_helpers.py.",
            "fyi the build is green",
            "ofc!",
            "My username is jdoe42.",
            "She uploaded jen_headshot.jpeg",
            "The key is sk_test_abc123",
            "c u later",
            "jk jk",
            "See you there :)",
            "I was just saying (: do you need to talk",
            "Thanks ;) see you",
            "Love you <3",
            "Hey ppl can u text me",
        ] {
            assert_eq!(fix_request(with_names(text, &[], true)), text, "{text}");
        }
        for (input, output) in [
            ("he's not holdin you down", "He's not holding you down"),
            (
                "Need a reviewer on the billin change.",
                "Need a reviewer on the billing change.",
            ),
            (
                "Hasan was notin favor of it.",
                "Hasan was not in favor of it.",
            ),
            (
                "Run git pull before you staart.",
                "Run git pull before you start.",
            ),
        ] {
            assert_eq!(fix_request(with_names(input, &[], true)), output, "{input}");
        }
    }
    #[test]
    fn an_opening_word_one_letter_short_of_a_common_pair_is_a_slip() {
        let opened = |text: &str| {
            fix_request(Request {
                sentence_start: true,
                ..with_names(text, &[], false)
            })
        };
        assert_eq!(
            opened("Thaks for the reminder."),
            "Thanks for the reminder."
        );
        assert_eq!(opened("Belo you will find it."), "Below you will find it.");
        for text in ["Bran said hi.", "Tina will call.", "Mara will join."] {
            assert_eq!(opened(text), text, "{text}");
        }
    }
    #[test]
    fn list_items_names_and_titles_keep_their_number() {
        for text in [
            "Today: emails, code review, gym.",
            "Call mom, buy milk, finish report",
            "These Q&A Facts are regularly updated.",
            "Enron Net Works invites you to join us.",
            "Acme Industries invites you to our open house.",
        ] {
            assert_eq!(fix_request(with_names(text, &[], false)), text, "{text}");
        }
        for (input, output) in [
            ("My parents lives in Pune.", "My parents live in Pune."),
            ("These book is great.", "This book is great."),
            ("I am an experts in this.", "I am an expert in this."),
            ("Sorry, ill be late.", "Sorry, I'll be late."),
            (
                "I can't come, but ill watch it.",
                "I can't come, but I'll watch it.",
            ),
        ] {
            assert_eq!(
                fix_request(with_names(input, &[], false)),
                output,
                "{input}"
            );
        }
    }
    #[test]
    fn a_first_name_that_is_a_modal_is_not_an_inverted_auxiliary() {
        for text in [
            "Will Smith was great in that film.",
            "Will Ferrell was funny.",
            "May Lee has left.",
        ] {
            assert_eq!(fix_request(with_names(text, &[], false)), text, "{text}");
        }
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
            "Thanks, Will"
        );
        assert_eq!(
            fix_request(with_names("Hey Hope! how are you", &names, true)),
            "Hey Hope! How are you"
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
            ("Ask ZOË now", "zoë"),
            ("Ask Zoë’s team", "Zoë"),
            ("We met jean-luc today", "Jean-Luc"),
            ("Visit new yrk today", "new yrk"),
            ("See aman's mesage", "mesage"),
        ] {
            let req = Request {
                text: text.into(),
                dictionary: vec![dictionary.into()],
                ..Request::default()
            };
            assert_eq!(fix_request(req), text, "{text}");
        }
        let req = Request {
            text: "We met jean-luc and new yrk".into(),
            dictionary: vec!["Jean-Luc".into(), "new yrk".into()],
            ..Request::default()
        };
        assert_eq!(fix_request(req.clone()), req.text);
    }
    #[test]
    fn a_past_form_the_tagger_calls_a_verb_makes_a_clause() {
        // "hit", "shut", "cost" are also nouns, so without a hint their past form makes no clause
        // ("a straight bet"). The app's tagger reads them as verbs in a sentence, and then the two
        // clauses take their comma.
        let tagged = |text: &str, word: &str| -> Request {
            let start = text.find(word).unwrap();
            Request {
                text: text.into(),
                tokens: vec![TokenHint {
                    start_utf16: start,
                    end_utf16: start + word.len(),
                    pos: "Verb".into(),
                    lemma: String::new(),
                    name: false,
                    ..TokenHint::default()
                }],
                ..Request::default()
            }
        };
        for (text, word, expected) in [
            (
                "The storm hit the coast overnight and it knocked out the power.",
                "hit",
                "The storm hit the coast overnight, and it knocked out the power.",
            ),
            (
                "They shut the office early so we all went home.",
                "shut",
                "They shut the office early, so we all went home.",
            ),
        ] {
            assert_eq!(fix_request(tagged(text, word)), expected, "{text}");
        }
        // Without the hint the word may be a noun, and nothing changes.
        let text = "He placed a straight bet and it paid off.";
        assert_eq!(
            fix_request(Request {
                text: text.into(),
                ..Request::default()
            }),
            text
        );
        // The tagger calls a participle a verb too; without a subject before it, no clause.
        for (text, word) in [
            (
                "It often includes home movies and photographs shot by a couple for their own fun.",
                "shot",
            ),
            (
                "The car can be set up comfortably for street use and be set up for superb handling.",
                "set",
            ),
            (
                "Reading beat Derby County at Pride Park but still went down on goal difference.",
                "beat",
            ),
        ] {
            assert_eq!(fix_request(tagged(text, word)), text, "{text}");
        }
    }
    #[test]
    fn a_tagged_acronym_keeps_its_letters_and_loses_only_the_redundant_word() {
        // The tagger calls an all-caps acronym a name; a rule that deletes the word beside it
        // changes nothing of the name, so the edit stands. Changing the name itself still does not.
        let tagged = |text: &str, word: &str| -> Request {
            let start = text.find(word).unwrap();
            Request {
                text: text.into(),
                tokens: vec![TokenHint {
                    start_utf16: start,
                    end_utf16: start + word.len(),
                    pos: "Noun".into(),
                    lemma: String::new(),
                    name: true,
                    ..TokenHint::default()
                }],
                ..Request::default()
            }
        };
        for (text, word, expected) in [
            (
                "Check the ROM memory before the update.",
                "ROM",
                "Check the ROM before the update.",
            ),
            (
                "We use OCR recognition to read the scans.",
                "OCR",
                "We use OCR to read the scans.",
            ),
            ("Please RSVP by Friday.", "RSVP", "RSVP by Friday."),
        ] {
            assert_eq!(fix_request(tagged(text, word)), expected, "{text}");
        }
        // A name that a rule would respell is still left alone.
        let text = "I met Jonh yesterday and we talked.";
        assert_eq!(fix_request(tagged(text, "Jonh")), text);
    }
    #[test]
    fn changed_words_leaves_out_the_words_an_edit_repeats() {
        let edit = |original: &str, replacement: &str| Edit {
            start_utf16: 10,
            end_utf16: 10 + original.encode_utf16().count(),
            replacement: replacement.into(),
            original: original.into(),
            category: "Style".into(),
            rule_id: "test".into(),
            explanation: String::new(),
            confidence: 0.9,
            group_id: None,
        };
        // "ROM memory" to "ROM": only " memory" (10 + 3 ..) changes.
        assert_eq!(changed_words(&edit("ROM memory", "ROM")), (13, 20));
        // "please RSVP" to "RSVP": only "please ".
        assert_eq!(changed_words(&edit("please RSVP", "RSVP")), (10, 17));
        // Letters inside a word are never trimmed: "Amans" to "Aman" changes the name.
        assert_eq!(changed_words(&edit("Amans", "Aman")), (10, 15));
        // An insertion, and a replacement that keeps nothing, keep their own range.
        assert_eq!(changed_words(&edit("ROM", "ROMs")), (10, 13));
        assert_eq!(changed_words(&edit("ROM", "RAM")), (10, 13));
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
        // Ordinary words stay lowercase without a cue ("may" and "march" are verbs here; "in" is
        // the cue that "august" is the month), and a tagged name is still never respelled.
        assert_eq!(
            fix_request(named("I may march in august.", &[])),
            "I may march in August."
        );
        assert_eq!(
            fix_request(named("I may march with august company.", &[])),
            "I may march with august company."
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
        assert_eq!(fix("ok pls send it thx"), "OK pls send it thx");
        assert!(
            names::never_a_name("june")
                && names::never_a_name("Friday")
                && names::never_a_name("u")
        );
        assert!(!names::never_a_name("Li") && !names::never_a_name("aman"));
    }
    /// The pipeline's first pass on `text` with the tagger calling each of `words` a name, as the
    /// system tagger does for a capitalized word it does not know.
    fn tagged(text: &str, words: &[&str]) -> String {
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
        pipeline::rewrite(&Request {
            text: text.into(),
            tokens,
            ..Request::default()
        })
        .unwrap()
        .text
    }
    #[test]
    fn a_closing_line_is_no_name_even_when_the_tagger_says_so() {
        // "Sincerley" is capitalized and unknown, so the tagger calls it a name and a name takes
        // no edit; before a signature it is a closing, and its misspelling is fixed.
        assert_eq!(
            tagged(
                "Thanks for the update.\n\nSincerley,\nAman",
                &["Sincerley", "Aman"]
            ),
            "Thanks for the update.\n\nSincerely,\nAman"
        );
        assert_eq!(
            tagged("Sincerley,\nAman", &["Sincerley", "Aman"]),
            "Sincerely,\nAman"
        );
        assert_eq!(
            fix("Thanks for the update.\n\nBest regads,\nAman"),
            "Thanks for the update.\n\nBest regards,\nAman"
        );
        assert_eq!(
            fix("Thanks for the update.\n\nKind regads,\nPriya"),
            "Thanks for the update.\n\nKind regards,\nPriya"
        );
        // The signature stays as typed, and a greeting line is a person, not a closing.
        for (text, names) in [
            ("Hi Sarha,\nSee you soon.\nAman", ["Sarha", "Aman"]),
            (
                "Thanks for the update.\n\nBest regards,\naman",
                ["aman", "aman"],
            ),
            ("Dear Sarha,\nAman", ["Sarha", "Aman"]),
        ] {
            assert_eq!(tagged(text, &names).to_lowercase(), text.to_lowercase());
        }
    }
    #[test]
    fn two_to_four_capitals_are_an_acronym_unless_the_list_has_the_name() {
        for acronym in ["PC", "CD", "DVD", "CEO", "API", "FBI", "NASA"] {
            assert!(names::never_a_name(acronym), "{acronym}");
        }
        for name in ["Ali", "ALI", "AMAN", "Sam", "I", "Aman's"] {
            assert!(!names::never_a_name(name), "{name}");
        }
        // The tagger's name guess on "PC" or "API" is dropped at the tokenizer.
        let text = "The PC and the API are old.";
        let hints: Vec<TokenHint> = ["PC", "API"]
            .iter()
            .map(|w| {
                let start = text.find(w).unwrap();
                TokenHint {
                    start_utf16: start,
                    end_utf16: start + w.len(),
                    pos: "Noun".into(),
                    name: true,
                    ..TokenHint::default()
                }
            })
            .collect();
        assert!(
            tokenizer::tokenize(text, &hints)
                .iter()
                .all(|t| !t.proper_name)
        );
    }
    #[test]
    fn a_possessive_correction_takes_the_apostrophe_the_word_already_has() {
        // "childrens'" is "children's": the correction took the typed mark with it once, and left
        // "children's'", then fought another rule about "those children's" until the check gave up.
        for (input, expected) in [
            (
                "The childrens' toys are here.",
                "The children's toys are here.",
            ),
            (
                "Those childrens' books are old.",
                "Those children's books are old.",
            ),
            (
                "Those children's books are old.",
                "Those children's books are old.",
            ),
            ("He said 'recieve' is wrong.", "He said 'receive' is wrong."),
            // No noun follows: the plural. A noun follows: the possessive.
            ("I have two childrens.", "I have two children."),
            ("Both womens left early.", "Both women left early."),
            (
                "My childrens school is near.",
                "My children's school is near.",
            ),
            ("The womens room is open.", "The women's room is open."),
        ] {
            assert_eq!(pipe(input), expected, "{input}");
        }
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
            "Ping (@aman) about it",
            "cc @aman.jain and @a_b-c please",
            "Thanks @aman.",
            "See #teh and (#mesage) now",
        ] {
            assert_eq!(fix(input), input, "{input}");
        }
    }
    #[test]
    fn every_sentence_takes_its_capital_in_chat_too() {
        // The owner's rule (2026-10-19): no half fixes, chat included.
        for (input, expected) in [
            (
                "yeah i think we should push the release to monday",
                "Yeah I think we should push the release to Monday",
            ),
            (
                "Could you send me the link? thanks",
                "Could you send me the link? Thanks",
            ),
            (
                "can we sync tmrw at 3pm? i have a conflict",
                "Can we sync tmrw at 3pm? I have a conflict",
            ),
            ("sure. i can do it tomorrow", "Sure. I can do it tomorrow"),
            ("haha nice", "Haha nice"),
            ("ok sounds good", "OK sounds good"),
            (
                "hi mark,\ni've attached the report.\nthanks,",
                "Hi mark,\nI've attached the report.\nThanks,",
            ),
            ("teh build is green", "The build is green"),
            ("what should we do", "What should we do?"),
            ("i don't know what to do", "I don't know what to do"),
        ] {
            assert_eq!(fix(input), expected, "{input}");
            assert_eq!(fix(expected), expected, "idempotent: {expected}");
        }
        // Shorthand, handles, code, commands, links and list items keep their case.
        for text in [
            "lol that was funny",
            "fyi the build is green",
            "ty",
            "c u later",
            "@mike can you check this?",
            "git push origin main",
            "npm install --save-dev typescript",
            "make test && make lint",
            "open -a Safari",
            "main.py is where the bug is",
            "x-api-key goes in the header",
            "useEffect runs twice in dev mode",
            "https://example.com/docs is the link",
            "- buy milk\n- call the bank",
            "1. open the app\n2. tap settings",
            "a) yes\nb) no",
            "e.g. the second option",
            "echo \"Adding privileges to the cluster\"",
            "return \"zookeeper authenticated\"",
            "from browser import html, alert",
            "new Thread(this).start();",
            "it \"should create a new status\" do",
        ] {
            assert_eq!(fix(text), text, "{text}");
        }
    }
    #[test]
    fn a_question_after_a_chat_comma_is_its_own_sentence() {
        // v0.5.0 split these; batch 3's chat-comma rule must not keep them joined.
        for (input, expected) in [
            (
                "i'm not sure if this is the right approach, what do you think",
                "I'm not sure if this is the right approach. What do you think?",
            ),
            (
                "I'm not sure if this is the right approach, what do you think?",
                "I'm not sure if this is the right approach. What do you think?",
            ),
        ] {
            assert_eq!(fix(input), expected, "{input}");
            assert_eq!(fix(expected), expected, "idempotent: {expected}");
        }
        // A statement after the comma stays in chat; a yes/no question with its own mark too.
        for text in [
            "I'm at the store, do you need anything?",
            "Thanks for dinner last night, it was lovely",
        ] {
            assert_eq!(fix(text), text, "{text}");
        }
    }
    #[test]
    fn sign_off_names_take_their_capital() {
        for (input, expected) in [
            ("Thanks,\njen", "Thanks,\nJen"),
            ("Best regards,\npriya k", "Best regards,\nPriya k"),
            ("Cheers,\nsam", "Cheers,\nSam"),
            ("Regards,\naman", "Regards,\nAman"),
        ] {
            assert_eq!(fix(input), expected, "{input}");
        }
    }
    #[test]
    fn chat_commas_between_clauses_stay_without_a_full_stop() {
        assert_eq!(
            fix("thanks for dinner last night, it was lovely"),
            "Thanks for dinner last night, it was lovely"
        );
        assert_eq!(
            fix("Thanks for dinner last night, it was lovely."),
            "Thanks for dinner last night. It was lovely."
        );
    }
    #[test]
    fn batch_three_grammar_misses_and_false_alarms() {
        for (input, expected) in [
            ("Me and him was late.", "He and I were late."),
            ("My sister and I was late.", "My sister and I were late."),
            (
                "I bought a laptop last week and the screen has a dead pixel.",
                "I bought a laptop last week, and the screen has a dead pixel.",
            ),
            (
                "Him and me are on the same team.",
                "He and I are on the same team.",
            ),
            (
                "Him and Jake are coming later.",
                "He and Jake are coming later.",
            ),
            (
                "Me and the team finished the project early.",
                "The team and I finished the project early.",
            ),
            (
                "I seen the email this morning.",
                "I saw the email this morning.",
            ),
            (
                "I done the changes you asked for.",
                "I did the changes you asked for.",
            ),
            ("Thanks, your the best!", "Thanks, you're the best!"),
            (
                "If your free later, call me.",
                "If you're free later, call me.",
            ),
            ("Did you get you're invite?", "Did you get your invite?"),
            (
                "Their coming over for dinner.",
                "They're coming over for dinner.",
            ),
            ("Is their any coffee left?", "Is there any coffee left?"),
            (
                "Please reply me as soon as possible.",
                "Please reply to me as soon as possible.",
            ),
            (
                "I will call you once I will reach the office.",
                "I will call you once I reach the office.",
            ),
            ("She said me to wait.", "She told me to wait."),
            (
                "One of my friend lives there.",
                "One of my friends lives there.",
            ),
            (
                "Everyone have to sign the form.",
                "Everyone has to sign the form.",
            ),
            (
                "The quality of the photos are great.",
                "The quality of the photos is great.",
            ),
            ("That sound great!", "That sounds great!"),
            ("My laptop keep crashing.", "My laptop keeps crashing."),
            (
                "I am working here since 2019.",
                "I have been working here since 2019.",
            ),
            ("He is having a car.", "He has a car."),
            ("Sorry for late reply.", "Sorry for the late reply."),
            (
                "I am knowing him for a long time.",
                "I have known him for a long time.",
            ),
            (
                "We are wanting a car for a family trip.",
                "We want a car for a family trip.",
            ),
            (
                "If it will rain, we will cancel.",
                "If it rains, we will cancel.",
            ),
            (
                "I think there going to cancel the event.",
                "I think they're going to cancel the event.",
            ),
            (
                "Please send me you're slides.",
                "Please send me your slides.",
            ),
            (
                "Let me know if your available tomorrow.",
                "Let me know if you're available tomorrow.",
            ),
            (
                "Finish the report and than send it to me.",
                "Finish the report and then send it to me.",
            ),
            (
                "The report is done. Its due tomorrow.",
                "The report is done. It's due tomorrow.",
            ),
            (
                "Everyone in the office were surprised.",
                "Everyone in the office was surprised.",
            ),
            (
                "It crash when you open the settings.",
                "It crashes when you open the settings.",
            ),
            ("He learn really fast.", "He learns really fast."),
            (
                "I will discuss about it with my manager.",
                "I will discuss it with my manager.",
            ),
            (
                "Their happy with the design.",
                "They're happy with the design.",
            ),
        ] {
            assert_eq!(fix(input), expected, "{input}");
            assert_eq!(fix(expected), expected, "idempotent: {expected}");
        }
        for text in [
            "I could have finished it yesterday.",
            "You should've told me last week.",
            "Did you feed the cat?",
            "Have I seen this before?",
            "Are we done?",
            "Physics was my worst class.",
            "Fish and chips is on the menu.",
            "Our team lead, along with two engineers, is on the call.",
            "Anyone need anything else?",
            "@sarah thanks, merged",
            "Tell me when you will reach.",
            "I am having a meeting at 3.",
            "I'm staying for a few days.",
            "Their coming-of-age film won.",
            "Does that sound right?",
            // From the 40k correct mined sentences.
            "I visited your theatre and I was very disappointed.",
            "Everybody was shocked and I was trying to keep the faith.",
            "Usually, RSS feed readers have the right menu items.",
            "I have been keen on mountain biking since three years ago.",
            "This work, which sold very widely, had a big effect.",
            "The snowflakes, that look like bees, are called snow bees.",
            // Batch 3 emails.
            "This NDA would be similar to those that you put together for DealBench.",
            "Please see that final agreements are forwarded for signature.",
            "Attached is a list of RSVP's I have received so far for the seminar.",
            "Their happy hour starts at five.",
            "Did he learn fast?",
            "It is bigger than we need.",
        ] {
            assert_eq!(fix(text), text, "{text}");
        }
    }
    #[test]
    fn british_group_nouns_keep_their_plural_verb() {
        let british = |text: &str| {
            fix_request(Request {
                text: text.into(),
                dialect: "british".into(),
                ..Request::default()
            })
        };
        for text in [
            "The team are working on it.",
            "The committee are meeting on Tuesday.",
            "The band are playing tonight.",
        ] {
            assert_eq!(british(text), text, "{text}");
        }
        assert_eq!(
            fix("The team are working on it."),
            "The team is working on it."
        );
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
            "Thanks, jain",
            "aman jain\nStaff Software Engineer",
            "priya sharma",
            "rahul",
            "anoop said hi",
            "Ask aman about it",
            "Thanks aman",
            "Regards,\nAman",
            "Cheers\nanoop kumar",
            "Hey aman, are you free",
            "I want to see aman jain",
            "Please ask jain",
            "aman is here",
            "We met rahul sharma",
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
            ("teh cat", "The cat"),
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
    fn keystroke_slips_of_frequent_words_are_fixed() {
        for (input, fixed) in [
            // The owner's report: a dropped letter, a space inside a word and a bare verb.
            ("thi is no t do", "This is not done"),
            ("I like thi book.", "I like this book."),
            ("It is thi one.", "It is this one."),
            // A space typed inside a word.
            ("I do nt know.", "I don't know."),
            ("Wh at is it?", "What is it?"),
            ("Tha t is fine.", "That is fine."),
            ("I'l l be late.", "I'll be late."),
            (
                "I always check the weat her first.",
                "I always check the weather first.",
            ),
            (
                "The meeting has been moved to n ext week.",
                "The meeting has been moved to next week.",
            ),
            // Two words typed without the space.
            (
                "It took me an hour to gethere.",
                "It took me an hour to get here.",
            ),
            ("Didyou send it yet?", "Did you send it yet?"),
            // Short slips the neighbours settle, and slipped contractions.
            (
                "The kids ar playing outside.",
                "The kids are playing outside.",
            ),
            ("She ws here.", "She was here."),
            ("The kids aare here.", "The kids are here."),
            ("I'j writing to you.", "I'm writing to you."),
            ("Don'y wait up.", "Don't wait up."),
            (
                "There are many reasons t switch providers.",
                "There are many reasons to switch providers.",
            ),
        ] {
            assert_eq!(fix(input), fixed, "{input}");
        }
    }
    #[test]
    fn slips_leave_names_slang_code_and_labels_alone() {
        for input in [
            "Anh is late.",
            "Hoa is fine.",
            "Yu said yes.",
            "It is sai raju here.",
            // Without the system tagger to rule out a name, a short opener needs a doubled or
            // swapped key (the app passes the tagger, which reads "Thi is fine" as "This").
            "Thi is fine.",
            "I met arjun menon yesterday.",
            "Looping in hari for visibility.",
            "Tom and ann went home",
            "lol tbh idk",
            "thx, pls send it",
            "gtg, ttyl",
            "We need plan b now.",
            "Choose option c or d.",
            "The value of x is 5.",
            "Use os.path.join to build paths.",
            "We pin it in requirements.txt today.",
            "I can not believe it.",
            "Bhai yaar kya hai.",
            "Bas, that's it",
        ] {
            assert_eq!(fix(input), input, "{input}");
        }
        // A Hinglish sentence keeps its words and takes its capital like any other.
        assert_eq!(fix("bas, that's it"), "Bas, that's it");
        // A short Roman Hindi word alone in English is a slip; beside Roman Hindi it stays.
        assert_eq!(fix("I like aur house."), "I like our house.");
        assert_eq!(fix("aur kya chal raha hai"), "Aur kya chal raha hai");
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
    fn do_after_a_form_of_be_is_a_slip_for_so_and_the_adjective_is_kept() {
        assert_eq!(fix("I was do tired."), "I was so tired.");
        assert_eq!(fix("I am do happy."), "I am so happy.");
        assert_eq!(fix("She is do tired."), "She is so tired.");
        assert_eq!(fix("Did you saw it?"), "Did you see it?");
        assert_eq!(fix("I do not liked it."), "I do not like it.");
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
