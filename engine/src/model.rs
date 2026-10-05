//! Bundled context and style refinement between the engine’s correctness passes.
use crate::{Edit, Mode, Request, RewriteResult, apply_edits, byte_at, overlaps, protected_spans};
use similar::{ChangeTag, TextDiff};
use std::{
    ffi::{CStr, CString, c_char, c_void},
    path::{Path, PathBuf},
    sync::OnceLock,
    time::Instant,
};

type Generate = unsafe extern "C" fn(*const c_char, *const c_char) -> *mut c_char;
type Free = unsafe extern "C" fn(*mut c_char);
type Cancel = unsafe extern "C" fn();
type Hints = unsafe extern "C" fn(*const c_char) -> *mut c_char;
struct Runtime {
    generate: Generate,
    free: Free,
    cancel: Cancel,
    hints: Hints,
    model: PathBuf,
}
static RUNTIME: OnceLock<Result<Runtime, String>> = OnceLock::new();
#[cfg(target_os = "macos")]
#[link(name = "System")]
unsafe extern "C" {
    fn dlopen(path: *const c_char, mode: i32) -> *mut c_void;
    fn dlsym(handle: *mut c_void, symbol: *const c_char) -> *mut c_void;
}
fn runtime() -> Result<&'static Runtime, String> {
    RUNTIME
        .get_or_init(|| {
            let executable =
                std::env::current_exe().map_err(|_| "Could not locate the bundled model.")?;
            let directory = executable
                .parent()
                .ok_or("Could not locate the bundled model.")?;
            let library = std::env::var_os("PARZR_MODEL_RUNTIME")
                .map(PathBuf::from)
                .unwrap_or_else(|| directory.join("../Frameworks/libparzr_model.dylib"));
            let model = std::env::var_os("PARZR_MODEL_PATH")
                .map(PathBuf::from)
                .unwrap_or_else(|| directory.join("../Resources/Model/Qwen3.5-0.8B-Q5_K_M.gguf"));
            if !model.is_file() {
                return Err("The bundled writing model is missing. Reinstall Parzr.".into());
            }
            load(&library, model)
        })
        .as_ref()
        .map_err(Clone::clone)
}
#[cfg(target_os = "macos")]
fn load(path: &Path, model: PathBuf) -> Result<Runtime, String> {
    use std::os::unix::ffi::OsStrExt;
    let path = CString::new(path.as_os_str().as_bytes()).map_err(|_| "Invalid runtime path.")?;
    // SAFETY: verified NUL-terminated names; retain the handle for the process lifetime.
    unsafe {
        let handle = dlopen(path.as_ptr(), 2);
        if handle.is_null() {
            return Err("The bundled model runtime could not load. Reinstall Parzr.".into());
        }
        let generate = dlsym(handle, c"parzr_model_generate".as_ptr());
        let free = dlsym(handle, c"parzr_model_string_free".as_ptr());
        let cancel = dlsym(handle, c"parzr_model_cancel".as_ptr());
        let hints = dlsym(handle, c"parzr_model_token_hints".as_ptr());
        if generate.is_null() || free.is_null() || cancel.is_null() || hints.is_null() {
            return Err("The bundled model runtime is incompatible.".into());
        }
        Ok(Runtime {
            generate: std::mem::transmute::<*mut c_void, Generate>(generate),
            free: std::mem::transmute::<*mut c_void, Free>(free),
            cancel: std::mem::transmute::<*mut c_void, Cancel>(cancel),
            hints: std::mem::transmute::<*mut c_void, Hints>(hints),
            model,
        })
    }
}
pub fn linguistic_hints(text: &str) -> Result<Vec<crate::TokenHint>, String> {
    let r = runtime()?;
    let input = CString::new(text).map_err(|_| "Invalid passage.")?;
    // SAFETY: input lives through the call; returned owned JSON is freed exactly once.
    let output = unsafe { (r.hints)(input.as_ptr()) };
    if output.is_null() {
        return Err("The local language tagger could not respond.".into());
    }
    let result = serde_json::from_slice(unsafe { CStr::from_ptr(output) }.to_bytes())
        .map_err(|_| "The local language tagger returned invalid metadata.".into());
    unsafe { (r.free)(output) };
    result
}
#[cfg(not(target_os = "macos"))]
fn load(_: &Path, _: PathBuf) -> Result<Runtime, String> {
    Err("The bundled model runtime requires macOS.".into())
}
pub fn cancel() {
    if let Some(Ok(r)) = RUNTIME.get() {
        // SAFETY: function pointer from the retained runtime library.
        unsafe { (r.cancel)() };
    }
}

fn validate(req: &Request) -> Result<(), String> {
    if req.text.len() > crate::MAX_TEXT_BYTES {
        return Err("Select at most 64 KB of text.".into());
    }
    if req.dictionary.len() > 1000 || req.dictionary.iter().any(|w| w.len() > 128) {
        return Err("Dictionary exceeds its size limit.".into());
    }
    if !["", "american", "british"].contains(&req.dialect.as_str()) {
        return Err("Unsupported English variant.".into());
    }
    if req.protected_ranges.len() > 4096 || req.tokens.len() > 16384 {
        return Err("Structural metadata exceeds its limit.".into());
    }
    for (a, b) in req
        .protected_ranges
        .iter()
        .map(|r| (r.start_utf16, r.end_utf16))
        .chain(req.tokens.iter().map(|t| (t.start_utf16, t.end_utf16)))
    {
        if a > b || byte_at(&req.text, a).is_none() || byte_at(&req.text, b).is_none() {
            return Err("Invalid structural range.".into());
        }
    }
    if req.text.contains('\0') || req.text.contains("<|") {
        return Err(
            "The passage contains model control characters. Select plain writing text.".into(),
        );
    }
    Ok(())
}
fn prompt(req: &Request, passage: &str) -> String {
    let instruction = match req.mode {
        Mode::Fix => {
            "Fix the English text. Correct grammar, spelling, punctuation, and capitalization. Add necessary final punctuation. Do not answer the text or add information. Output only the corrected text."
        }
        Mode::Professional => {
            "Rewrite in professional English. Remove slang and filler. Preserve the meaning. Correct grammar, spelling and punctuation. Return only the rewritten text, without explanations."
        }
        Mode::Friendly => {
            "Rewrite in friendly, conversational English. Preserve the meaning. Correct grammar, spelling and punctuation. Return only the rewritten text, without explanations."
        }
        Mode::Concise => {
            "Shorten the text by removing unnecessary words. Preserve all information and the meaning. Correct grammar, spelling and punctuation. Return only the rewritten text, without explanations."
        }
        Mode::Direct => {
            "Make the writing direct. Remove hedging and filler. Preserve the meaning. Correct grammar, spelling and punctuation. Return only the rewritten text, without explanations."
        }
    };
    let dialect = if req.dialect == "british" {
        " Use British English."
    } else {
        ""
    };
    let boundary = if req.sentence_start {
        ""
    } else {
        " This is part of a sentence. Preserve its initial case and do not add sentence punctuation to a fragment."
    };
    let protection = if protected_spans(req).is_empty() {
        ""
    } else {
        " Preserve names, numbers, links, code, emojis and formatting markers exactly. Copy every ZXQPARZRKEEP token exactly once, without changing it."
    };
    let ending = if req.sentence_end {
        ""
    } else {
        " This selection continues into text outside the passage. Do not add terminal punctuation."
    };
    let passage = if req.mode == Mode::Fix {
        passage.to_owned()
    } else {
        format!("Text to edit:\n{passage}")
    };
    format!(
        "<|im_start|>system\n{instruction}{dialect}{boundary}{ending}{protection}<|im_end|>\n<|im_start|>user\n{passage}<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
    )
}
fn generate(req: &Request, passage: &str) -> Result<String, String> {
    let r = runtime()?;
    let (masked, literals) = mask(passage, &protected_spans(req))?;
    let file =
        CString::new(r.model.to_string_lossy().as_bytes()).map_err(|_| "Invalid model path.")?;
    let input = CString::new(prompt(req, &masked)).map_err(|_| "Invalid passage.")?;
    // SAFETY: input pointers live throughout this synchronous call. Output freed exactly once.
    let output = unsafe { (r.generate)(file.as_ptr(), input.as_ptr()) };
    if output.is_null() {
        return Err("The model could not finish this passage. Try a shorter selection.".into());
    }
    let result = unsafe { CStr::from_ptr(output) }
        .to_str()
        .map(str::to_owned)
        .map_err(|_| "The model returned invalid text.".to_string());
    unsafe { (r.free)(output) };
    let mut result = result?;
    if result.trim().is_empty() || result.contains("<|") || result.contains("<think>") {
        return Err("The model did not return a complete writing suggestion.".into());
    }
    for (marker, literal) in literals {
        if result.matches(&marker).count() != 1 {
            return Err("The model could not retain a protected editor element. This suggestion was withheld.".into());
        }
        result = result.replace(&marker, &literal);
    }
    let prefix = &passage[..passage.len() - passage.trim_start().len()];
    let suffix = &passage[passage.trim_end().len()..];
    let body = continuation(req, result.trim());
    Ok(format!("{prefix}{body}{suffix}"))
}

fn mask(
    passage: &str,
    protected: &[crate::TextRange],
) -> Result<(String, Vec<(String, String)>), String> {
    let mut ranges: Vec<_> = protected
        .iter()
        .filter(|r| r.start_utf16 < r.end_utf16)
        .collect();
    ranges.sort_by_key(|r| r.start_utf16);
    let mut merged: Vec<(usize, usize)> = vec![];
    for r in ranges {
        if let Some(last) = merged.last_mut()
            && r.start_utf16 < last.1
        {
            last.1 = last.1.max(r.end_utf16);
        } else {
            merged.push((r.start_utf16, r.end_utf16));
        }
    }
    let mut masked = String::new();
    let mut literals = vec![];
    let mut cursor = 0;
    for (a, b) in merged {
        let start = byte_at(passage, a).ok_or("Invalid protected range.")?;
        let end = byte_at(passage, b).ok_or("Invalid protected range.")?;
        let literal = &passage[start..end];
        // Keep paragraph boundaries as real whitespace in the model's context.
        if literal.trim().is_empty() {
            continue;
        }
        masked.push_str(&passage[cursor..start]);
        let mut serial = literals.len();
        let marker = loop {
            let candidate = format!("ZXQPARZRKEEP{serial}QXZ");
            if !passage.contains(&candidate) && !literals.iter().any(|(m, _)| m == &candidate) {
                break candidate;
            }
            serial += 1;
        };
        masked.push_str(&marker);
        literals.push((marker, literal.to_owned()));
        cursor = end;
    }
    masked.push_str(&passage[cursor..]);
    Ok((masked, literals))
}

fn continuation<'a>(req: &Request, output: &'a str) -> &'a str {
    if !req.sentence_end && !req.text.trim_end().ends_with(['.', '!', '?']) {
        output.trim_end_matches(['.', '!', '?'])
    } else {
        output
    }
}

/// Words of `long` that `short` lacks, when they form one run of at most 3 words.
fn extra_run(long: &[&str], short: &[&str]) -> Option<String> {
    let n = short.len();
    if n == 0 || long.len() <= n || long.len() - n > 3 {
        return None;
    }
    let k = long.len() - n;
    let same = |a: &[&str], b: &[&str]| {
        a.iter()
            .map(|w| w.to_lowercase())
            .eq(b.iter().map(|w| w.to_lowercase()))
    };
    (0..=n)
        .find(|&p| same(&long[..p], &short[..p]) && same(&long[p + k..], &short[p..]))
        .map(|p| long[p..p + k].join(" "))
}

fn confusable(original: &str, replacement: &str) -> Option<&'static str> {
    Some(match (original, replacement) {
        ("good", "well") => "Use the adverb “well” to describe how something is done.",
        ("your", "you're") => "Use “you're”, short for “you are”.",
        ("you're", "your") => "Use “your” to show that something belongs to you.",
        ("its", "it's") => "Use “it's”, short for “it is”.",
        ("it's", "its") => "Use “its” to show possession.",
        ("their" | "there", "they're") => "Use “they're”, short for “they are”.",
        ("there" | "they're", "their") => "Use “their” to show possession.",
        ("their" | "they're", "there") => "Use “there” to point to a place.",
        ("then", "than") => "Use “than” for comparisons.",
        ("than", "then") => "Use “then” for time or sequence.",
        ("to", "too") => "Use “too” to mean also or excessively.",
        ("too", "to") => "Use “to” before a verb or a destination.",
        ("affect", "effect") => "Use the noun “effect” for a result.",
        ("effect", "affect") => "Use the verb “affect” to mean to influence.",
        ("less", "fewer") => "Use “fewer” for things you can count.",
        ("lose", "loose") => "Use “loose” to mean not tight.",
        ("loose", "lose") => "Use “lose” to mean misplace or fail to win.",
        ("whose", "who's") => "Use “who's”, short for “who is”.",
        ("who's", "whose") => "Use “whose” to show possession.",
        ("a", "an") => "Use “an” before a vowel sound.",
        ("an", "a") => "Use “a” before a consonant sound.",
        _ => return None,
    })
}

/// Category and plain-language reason for one model correction in Fix mode.
fn describe(original: &str, replacement: &str) -> (String, String) {
    let (original, replacement) = (original.trim(), replacement.trim());
    let grammar = |text: String| ("Grammar".to_owned(), text);
    let punctuation = |text: &str| ("Punctuation".to_owned(), text.to_owned());
    let squash = |s: &str| s.split_whitespace().collect::<String>();
    if squash(original) == squash(replacement) {
        return punctuation("Fix the spacing.");
    }
    if original.to_lowercase() == replacement.to_lowercase() {
        return grammar(
            if replacement.chars().next().is_some_and(char::is_uppercase) {
                format!("Capitalize “{replacement}”.")
            } else {
                format!("Use lowercase “{replacement}”.")
            },
        );
    }
    let alnum = |s: &str| {
        s.chars()
            .filter(|c| c.is_alphanumeric())
            .collect::<String>()
    };
    if alnum(original) == alnum(replacement) {
        let count = |s: &str, set: &[char]| s.chars().filter(|c| set.contains(c)).count();
        let apostrophes = |s: &str| {
            s.chars()
                .filter(|c| ['\'', '’'].contains(c))
                .collect::<String>()
        };
        if count(replacement, &[',']) > count(original, &[',']) {
            return punctuation("Add a comma.");
        }
        if count(replacement, &[',']) < count(original, &[',']) {
            return punctuation("Remove the comma.");
        }
        if count(replacement, &['.', '!', '?']) > count(original, &['.', '!', '?']) {
            return punctuation("End the sentence with punctuation.");
        }
        if apostrophes(original) != apostrophes(replacement)
            && let Some(word) = replacement
                .split_whitespace()
                .find(|w| w.contains(['\'', '’']))
        {
            let word = word.trim_matches(|c: char| !c.is_alphanumeric());
            return punctuation(&format!("Add the apostrophe in “{word}”."));
        }
        return punctuation("Fix the punctuation.");
    }
    let single = !original.is_empty()
        && !replacement.is_empty()
        && !original.contains(char::is_whitespace)
        && !replacement.contains(char::is_whitespace);
    if single {
        let (lo, lr) = (
            original.to_lowercase().replace('’', "'"),
            replacement.to_lowercase().replace('’', "'"),
        );
        if let Some(text) = confusable(&lo, &lr) {
            return grammar(text.into());
        }
        if !crate::spelling::known(original) && crate::spelling::known(replacement) {
            return (
                "Spelling".into(),
                format!("Correct the spelling of “{original}”."),
            );
        }
        if let (Some(a), Some(b)) = (crate::morphology::verb(&lo), crate::morphology::verb(&lr))
            && a.base == b.base
        {
            let past = |w: &str| w == "were" || w == a.past || w == a.participle;
            return grammar(if lr == b.gerund && lo != b.gerund {
                format!("Use the -ing form “{replacement}”.")
            } else if past(&lo) != past(&lr) {
                format!("Use “{replacement}” to match the tense.")
            } else {
                format!("Use “{replacement}” to agree with the subject.")
            });
        }
    }
    let (ow, rw): (Vec<_>, Vec<_>) = (
        original.split_whitespace().collect(),
        replacement.split_whitespace().collect(),
    );
    if original.is_empty() || replacement.is_empty() {
        let (verb, text, words) = if original.is_empty() {
            ("Add", replacement, &rw)
        } else {
            ("Remove", original, &ow)
        };
        return grammar(if words.len() <= 3 {
            format!("{verb} “{text}”.")
        } else {
            format!(
                "{verb} the {} words.",
                if verb == "Add" { "missing" } else { "extra" }
            )
        });
    }
    if let Some(extra) = extra_run(&rw, &ow) {
        return grammar(format!("Add “{extra}”."));
    }
    if let Some(extra) = extra_run(&ow, &rw) {
        return grammar(format!("Remove “{extra}”."));
    }
    grammar(
        if original.chars().count() <= 40 && replacement.chars().count() <= 40 {
            format!("Use “{replacement}” instead of “{original}”.")
        } else {
            "Rewrite this phrase for correct grammar.".into()
        },
    )
}

/// Edit distance counting an adjacent transposition as one edit.
fn distance(a: &str, b: &str) -> usize {
    let (a, b): (Vec<char>, Vec<char>) = (a.chars().collect(), b.chars().collect());
    let mut rows: Vec<Vec<usize>> = (0..=a.len())
        .map(|i| {
            (0..=b.len())
                .map(|j| {
                    if i == 0 {
                        j
                    } else if j == 0 {
                        i
                    } else {
                        0
                    }
                })
                .collect()
        })
        .collect();
    for i in 1..=a.len() {
        for j in 1..=b.len() {
            let cost = usize::from(a[i - 1] != b[j - 1]);
            rows[i][j] = (rows[i - 1][j] + 1)
                .min(rows[i][j - 1] + 1)
                .min(rows[i - 1][j - 1] + cost);
            if i > 1 && j > 1 && a[i - 1] == b[j - 2] && a[i - 2] == b[j - 1] {
                rows[i][j] = rows[i][j].min(rows[i - 2][j - 2] + 1);
            }
        }
    }
    rows[a.len()][b.len()]
}

/// Function words a model may add or drop; any other inserted or deleted word is rejected.
const CLOSED_CLASS: [&str; 16] = [
    "a", "an", "the", "to", "of", "in", "on", "at", "for", "is", "are", "was", "were", "be", "it",
    "and",
];

fn plausible_word(original: &str, replacement: &str) -> bool {
    let bare = |s: &str| {
        s.trim_matches(|c: char| !c.is_alphanumeric())
            .to_lowercase()
            .replace('’', "'")
    };
    let (o, r) = (bare(original), bare(replacement));
    if o == r || confusable(&o, &r).is_some() {
        return true;
    }
    let d = distance(&o, &r);
    let known = crate::spelling::known;
    // A one-letter swap ("si" to "is") is a typo even when both are dictionary words.
    let sorted = |s: &str| {
        let mut c: Vec<char> = s.chars().collect();
        c.sort_unstable();
        c
    };
    if d == 1 && sorted(&o) == sorted(&r) {
        return true;
    }
    // An unknown word becomes a close known one.
    if !known(&o) && known(&r) && d <= 3 {
        return true;
    }
    // Between two known words, short words are too easily confused for a spelling fix.
    if o.chars().count().min(r.chars().count()) >= 4 && d <= 2 {
        return true;
    }
    matches!(
        (crate::morphology::verb(&o), crate::morphology::verb(&r)),
        (Some(a), Some(b)) if a.base == b.base
    )
}

/// Whether one Fix-mode model edit is a correction rather than a rewrite or hallucination:
/// spacing, case, punctuation, a close spelling, a known confusable, another form of the same
/// verb, or adding or dropping a single function word.
fn plausible(original: &str, replacement: &str) -> bool {
    let (original, replacement) = (original.trim(), replacement.trim());
    let alnum = |s: &str| {
        s.chars()
            .filter(|c| c.is_alphanumeric())
            .collect::<String>()
            .to_lowercase()
    };
    if alnum(original) == alnum(replacement) {
        return true;
    }
    let words = |s: &str| -> Vec<String> {
        s.split_whitespace()
            .filter(|w| w.chars().any(char::is_alphanumeric))
            .map(str::to_owned)
            .collect()
    };
    let (ow, rw) = (words(original), words(replacement));
    let closed = |w: &str| {
        CLOSED_CLASS.contains(
            &w.trim_matches(|c: char| !c.is_alphanumeric())
                .to_lowercase()
                .as_str(),
        )
    };
    if ow.is_empty() || rw.is_empty() {
        let only = if ow.is_empty() { &rw } else { &ow };
        return only.len() == 1 && closed(&only[0]);
    }
    if ow.len() == rw.len() {
        return ow.iter().zip(&rw).all(|(a, b)| plausible_word(a, b));
    }
    let (long, short) = if ow.len() > rw.len() {
        (&ow, &rw)
    } else {
        (&rw, &ow)
    };
    let (long, short): (Vec<&str>, Vec<&str>) = (
        long.iter().map(String::as_str).collect(),
        short.iter().map(String::as_str).collect(),
    );
    extra_run(&long, &short).is_some_and(|extra| !extra.contains(' ') && closed(&extra))
}

/// A small model hallucinates in Fix mode ("do" to "a", "bod" to "a body"). Keep only plausible
/// corrections. An edit touching a rejected one is part of the same rewrite and goes with it;
/// linked move pairs stay together. The caller recomposes the text from what remains.
fn plausible_edits(all: Vec<Edit>) -> Vec<Edit> {
    let mut keep: Vec<bool> = all
        .iter()
        .map(|e| e.group_id.is_some() || plausible(&e.original, &e.replacement))
        .collect();
    loop {
        let mut changed = false;
        for i in 1..all.len() {
            if all[i - 1].end_utf16 == all[i].start_utf16 && keep[i - 1] != keep[i] {
                for j in [i - 1, i] {
                    if all[j].group_id.is_none() {
                        keep[j] = false;
                        changed = true;
                    }
                }
            }
        }
        if !changed {
            break;
        }
    }
    all.into_iter()
        .zip(keep)
        .filter_map(|(e, keep)| keep.then_some(e))
        .collect()
}

/// Letters, digits and inner apostrophes belong to a word; widening never crosses protected text.
fn widen_to_words(
    source: &str,
    raw: Vec<Edit>,
    mode: Mode,
    protected: &[crate::TextRange],
) -> Vec<Edit> {
    let chars: Vec<char> = source.chars().collect();
    let n = chars.len();
    let mut units = Vec::with_capacity(n + 1);
    let mut sum = 0;
    for c in &chars {
        units.push(sum);
        sum += c.len_utf16();
    }
    units.push(sum);
    let index = |x: usize| units.binary_search(&x).ok();
    let Some(ranges) = raw
        .iter()
        .map(|e| Some((index(e.start_utf16)?, index(e.end_utf16)?)))
        .collect::<Option<Vec<_>>>()
    else {
        return raw;
    };
    let blocked = |i: usize| {
        protected
            .iter()
            .any(|p| units[i] >= p.start_utf16 && units[i] < p.end_utf16)
    };
    let apostrophe = |c: char| c == '\'' || c == '’';
    let inner = |i: usize| {
        i > 0 && i + 1 < n && chars[i - 1].is_alphanumeric() && chars[i + 1].is_alphanumeric()
    };
    // (start, end, first member, one past last member)
    let mut groups: Vec<(usize, usize, usize, usize)> = vec![];
    for (k, (e, &(mut s, mut t))) in raw.iter().zip(&ranges).enumerate() {
        let text = if e.original.is_empty() {
            &e.replacement
        } else {
            &e.original
        };
        let wordish = |c: char| c.is_alphanumeric() || apostrophe(c);
        if text.chars().next().is_some_and(wordish) {
            while s > 0
                && !blocked(s - 1)
                && (chars[s - 1].is_alphanumeric() || (apostrophe(chars[s - 1]) && inner(s - 1)))
            {
                s -= 1;
            }
        }
        if text.chars().next_back().is_some_and(wordish) {
            while t < n
                && !blocked(t)
                && (chars[t].is_alphanumeric() || (apostrophe(chars[t]) && inner(t)))
            {
                t += 1;
            }
        }
        match groups.last_mut() {
            Some(g) if s < g.1 => {
                g.0 = g.0.min(s);
                g.1 = g.1.max(t);
                g.3 = k + 1;
            }
            _ => groups.push((s, t, k, k + 1)),
        }
    }
    let mut result = vec![];
    for (s, t, a, b) in groups {
        let mut replacement = String::new();
        let mut cursor = s;
        for (e, &(cs, ce)) in raw[a..b].iter().zip(&ranges[a..b]) {
            replacement.extend(&chars[cursor..cs]);
            replacement.push_str(&e.replacement);
            cursor = ce;
        }
        replacement.extend(&chars[cursor..t]);
        let original: String = chars[s..t].iter().collect();
        if original == replacement {
            continue;
        }
        let mut edit = raw[a].clone();
        if mode == Mode::Fix {
            (edit.category, edit.explanation) = describe(&original, &replacement);
        }
        edit.start_utf16 = units[s];
        edit.end_utf16 = units[t];
        edit.original = original;
        edit.replacement = replacement;
        result.push(edit);
    }
    result
}

/// Character anchors preserve untouched rich-text runs and UTF-16 coordinates.
fn edits(source: &str, target: &str, mode: Mode, protected: &[crate::TextRange]) -> Vec<Edit> {
    // Preserve surviving character anchors across run boundaries (e.g. bold action words
    // beside a deleted request prefix). The composer still groups grammar corrections.
    let diff = TextDiff::from_chars(source, target);
    let mut result = vec![];
    let mut offset = 0;
    let mut original = String::new();
    let mut replacement = String::new();
    let flush = |result: &mut Vec<Edit>,
                 offset: &mut usize,
                 original: &mut String,
                 replacement: &mut String| {
        if original.is_empty() && replacement.is_empty() {
            return;
        }
        if mode != Mode::Fix
            && let Some(split) = original
                .rfind(char::is_whitespace)
                .map(|i| i + original[i..].chars().next().unwrap().len_utf8())
            && split < original.len()
            && original[split..].to_lowercase() == replacement.to_lowercase()
        {
            let tail = original.split_off(split);
            let prefix = std::mem::take(original);
            let end = *offset + prefix.encode_utf16().count();
            result.push(Edit {
                start_utf16: *offset,
                end_utf16: end,
                original: prefix,
                replacement: String::new(),
                category: "Style".into(),
                rule_id: "local-model".into(),
                explanation: "Suggested rewrite".into(),
                confidence: 1.,
                group_id: None,
            });
            *offset = end;
            *original = tail;
        }
        let end = *offset + original.encode_utf16().count();
        // Fix mode gets its real category and explanation once edits are widened to whole words.
        let (category, explanation) = if mode == Mode::Fix {
            ("Grammar".into(), "Suggested correction".into())
        } else {
            ("Style".into(), "Suggested rewrite".into())
        };
        result.push(Edit {
            start_utf16: *offset,
            end_utf16: end,
            original: std::mem::take(original),
            replacement: std::mem::take(replacement),
            category,
            rule_id: "local-model".into(),
            explanation,
            confidence: 1.0,
            group_id: None,
        });
        *offset = end;
    };
    for change in diff.iter_all_changes() {
        match change.tag() {
            ChangeTag::Delete => original.push_str(change.value()),
            ChangeTag::Insert => replacement.push_str(change.value()),
            ChangeTag::Equal => {
                flush(&mut result, &mut offset, &mut original, &mut replacement);
                offset += change.value().encode_utf16().count();
            }
        }
    }
    flush(&mut result, &mut offset, &mut original, &mut replacement);
    let mut result = widen_to_words(source, result, mode, protected);
    // Moved words must be accepted together, keeping protected names and grammar intact.
    for i in 0..result.len() {
        if !result[i].replacement.trim().is_empty()
            || result[i].original.trim().is_empty()
            || result[i].group_id.is_some()
        {
            continue;
        }
        if let Some(j) = (0..result.len()).find(|&j| {
            j != i
                && result[j].original.trim().is_empty()
                && result[j].replacement.trim() == result[i].original.trim()
                && result[j].group_id.is_none()
        }) {
            let group = format!("move-{i}-{j}");
            result[i].group_id = Some(group.clone());
            result[j].group_id = Some(group);
        }
    }
    result
}
pub fn rewrite(req: &Request) -> Result<RewriteResult, String> {
    validate(req)?;
    let started = Instant::now();
    let protected = protected_spans(req);
    let text = if req.text.trim().is_empty() {
        req.text.clone()
    } else {
        generate(req, &req.text)?
    };
    let all = edits(&req.text, &text, req.mode, &protected);
    if all.len() > 512 {
        return Err("This passage has too many changes. Select a shorter passage.".into());
    }
    if all.iter().any(|e| {
        protected.iter().any(|p| {
            if e.start_utf16 == e.end_utf16 {
                e.start_utf16 > p.start_utf16 && e.start_utf16 < p.end_utf16
            } else {
                overlaps(e.start_utf16, e.end_utf16, p)
            }
        })
    }) {
        return Err("The model changed protected text. This suggestion was withheld.".into());
    }
    if apply_edits(&req.text, &all)?.0 != text {
        return Err("The model returned an inconsistent edit plan.".into());
    }
    let changes = if req.mode == Mode::Fix {
        plausible_edits(all)
    } else {
        all
    };
    let (text, source_map) = apply_edits(&req.text, &changes)?;
    Ok(RewriteResult {
        version: "parzr-0.1.0/qwen3.5-0.8b-q5".into(),
        text,
        edits: changes,
        source_map,
        elapsed_ms: started.elapsed().as_secs_f64() * 1000.,
        protected_count: protected.len(),
        warnings: vec![],
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    fn d(original: &str, replacement: &str) -> (String, String) {
        describe(original, replacement)
    }
    #[test]
    fn describe_names_the_fix() {
        let cases: &[(&str, &str, &str, &str)] = &[
            ("a  b", "a b", "Punctuation", "Fix the spacing."),
            ("i", "I", "Grammar", "Capitalize “I”."),
            ("Hello", "hello", "Grammar", "Use lowercase “hello”."),
            ("a b", "a, b", "Punctuation", "Add a comma."),
            ("a, b", "a b", "Punctuation", "Remove the comma."),
            (
                "done",
                "done.",
                "Punctuation",
                "End the sentence with punctuation.",
            ),
            (
                "youre",
                "you're",
                "Punctuation",
                "Add the apostrophe in “you're”.",
            ),
            (
                "good",
                "well",
                "Grammar",
                "Use the adverb “well” to describe how something is done.",
            ),
            ("then", "than", "Grammar", "Use “than” for comparisons."),
            (
                "your",
                "you're",
                "Grammar",
                "Use “you're”, short for “you are”.",
            ),
            ("a", "an", "Grammar", "Use “an” before a vowel sound."),
            ("an", "a", "Grammar", "Use “a” before a consonant sound."),
            (
                "recieved",
                "received",
                "Spelling",
                "Correct the spelling of “recieved”.",
            ),
            ("goes", "went", "Grammar", "Use “went” to match the tense."),
            (
                "was",
                "were",
                "Grammar",
                "Use “were” to agree with the subject.",
            ),
            ("", "the", "Grammar", "Add “the”."),
            ("very", "", "Grammar", "Remove “very”."),
            ("go home", "go to home", "Grammar", "Add “to”."),
            ("go to home", "go home", "Grammar", "Remove “to”."),
            ("cat", "dog", "Grammar", "Use “dog” instead of “cat”."),
        ];
        for (o, r, category, explanation) in cases {
            assert_eq!(
                d(o, r),
                (category.to_string(), explanation.to_string()),
                "{o} -> {r}"
            );
        }
        let long = "red cat sat ".repeat(4);
        assert_eq!(
            d(&long, "blue dog ran").1,
            "Rewrite this phrase for correct grammar."
        );
    }
    #[test]
    fn fix_guard_keeps_corrections_and_drops_hallucinations() {
        for (o, r) in [
            ("good", "well"),
            ("recieved", "received"),
            ("goes", "went"),
            ("si", "is"),
            ("teh", "the"),
            ("i", "I"),
            ("your", "you're"),
            ("alot", "a lot"),
            ("done", "done."),
            ("", "the"),
            ("to", ""),
            ("go home", "go to home"),
            ("go to home", "go home"),
            ("definately", "definitely"),
            ("was", "were"),
        ] {
            assert!(plausible(o, r), "{o:?} -> {r:?}");
        }
        for (o, r) in [
            ("do", "a"),
            ("", " thing"),
            ("bod", "a body"),
            ("bod", "body"),
            ("cat", "dog"),
            ("an", "on"),
            ("", "a body"),
            ("so", "bad"),
            ("buy", "purchase"),
            ("go home", "go to the shop"),
        ] {
            assert!(!plausible(o, r), "{o:?} -> {r:?}");
        }
    }
    #[test]
    fn fix_guard_filters_edits_from_the_model_diff() {
        let kept = |a: &str, b: &str| {
            plausible_edits(edits(a, b, Mode::Fix, &[]))
                .into_iter()
                .map(|e| (e.original, e.replacement))
                .collect::<Vec<_>>()
        };
        assert_eq!(
            kept("This si do bad.", "This is a bad thing."),
            [("si".to_string(), "is".to_string())]
        );
        assert_eq!(
            kept("This si bod.", "This is a body."),
            [("si".to_string(), "is".to_string())]
        );
        assert_eq!(
            kept("I recieved the file", "I received the file."),
            [
                ("recieved".to_string(), "received".to_string()),
                ("".to_string(), ".".to_string())
            ]
        );
    }
    #[test]
    fn fix_edits_carry_specific_explanations() {
        let changes = edits("You are doing good", "You are doing well", Mode::Fix, &[]);
        assert!(
            changes
                .iter()
                .all(|e| e.explanation != "Suggested correction")
        );
    }
    #[test]
    fn char_fragments_widen_to_whole_words() {
        let one = |a: &str, b: &str| {
            let changes = edits(a, b, Mode::Fix, &[]);
            assert_eq!(changes.len(), 1, "{a} -> {b}");
            assert_eq!(apply_edits(a, &changes).unwrap().0, b);
            changes.into_iter().next().unwrap()
        };
        let swap = one("This si bad.", "This is bad.");
        assert_eq!(
            (swap.original.as_str(), swap.replacement.as_str()),
            ("si", "is")
        );
        assert_eq!((swap.start_utf16, swap.end_utf16), (5, 7));
        let grow = one("This do bad.", "This doing bad.");
        assert_eq!(
            (grow.original.as_str(), grow.replacement.as_str()),
            ("do", "doing")
        );
        let cap = one("so can you", "so Can you");
        assert_eq!(
            (cap.original.as_str(), cap.replacement.as_str()),
            ("can", "Can")
        );
        assert_eq!(cap.explanation, "Capitalize “Can”.");
    }
    #[test]
    fn separate_words_stay_separate_edits() {
        let source = "i hope your doing well";
        let changes = edits(source, "I hope you're doing well", Mode::Fix, &[]);
        let pairs: Vec<_> = changes
            .iter()
            .map(|e| (e.original.as_str(), e.replacement.as_str()))
            .collect();
        assert_eq!(pairs, [("i", "I"), ("your", "you're")]);
        assert_eq!(changes[1].explanation, "Use “you're”, short for “you are”.");
        assert_eq!(
            apply_edits(source, &changes).unwrap().0,
            "I hope you're doing well"
        );
    }
    #[test]
    fn widening_stops_at_protected_text() {
        // "Mira" (utf16 0..4) is protected; the edit on "42" beside it must not absorb it.
        let protected = [crate::TextRange {
            start_utf16: 0,
            end_utf16: 4,
        }];
        let changes = edits("Mira42 ok", "Mira43 ok", Mode::Fix, &protected);
        assert_eq!(changes.len(), 1);
        assert_eq!(
            (changes[0].start_utf16, changes[0].original.as_str()),
            (4, "42")
        );
    }
    #[test]
    fn editor_literals_keep_utf16_boundaries_and_paragraphs() {
        let (masked, literals) = mask(
            "😀 hello\n@Mira",
            &[
                crate::TextRange {
                    start_utf16: 0,
                    end_utf16: 2,
                },
                crate::TextRange {
                    start_utf16: 8,
                    end_utf16: 9,
                },
                crate::TextRange {
                    start_utf16: 9,
                    end_utf16: 14,
                },
            ],
        )
        .unwrap();
        assert!(masked.contains(" hello\n"));
        let mut restored = masked;
        for (marker, literal) in literals {
            restored = restored.replace(&marker, &literal);
        }
        assert_eq!(restored, "😀 hello\n@Mira");
    }
    #[test]
    fn partial_selection_cannot_gain_terminal_punctuation() {
        let req = Request {
            text: "i hope your doing well".into(),
            sentence_end: false,
            ..Request::default()
        };
        assert_eq!(
            continuation(&req, "I hope you're doing well."),
            "I hope you're doing well"
        );
        assert_eq!(
            continuation(
                &Request {
                    sentence_end: true,
                    ..req.clone()
                },
                "I hope you're doing well."
            ),
            "I hope you're doing well."
        );
        assert_eq!(
            continuation(
                &Request {
                    text: "Thanks!".into(),
                    ..req
                },
                "Thanks!"
            ),
            "Thanks!"
        );
    }
    #[test]
    fn prefix_removal_retains_the_styled_action_word_anchor() {
        let changes = edits("Could you review this?", "Review this.", Mode::Direct, &[]);
        assert_eq!(changes[0].original, "Could you ");
        assert_eq!(changes[0].replacement, "");
        assert_eq!(changes[1].start_utf16, 10);
        assert_eq!(changes[1].original, "review");
        assert_eq!(changes[1].replacement, "Review");
        assert_eq!(
            apply_edits("Could you review this?", &changes).unwrap().0,
            "Review this."
        );
    }
    #[test]
    fn unicode_diff_preserves_exact_reconstruction() {
        for (a, b) in [
            ("👩🏽‍💻 this si bad", "👩🏽‍💻 This is bad."),
            ("Mira sent 42 files.", "Mira sent 42 files."),
            ("a\nb", "a\nc"),
            ("", "Hello."),
        ] {
            assert_eq!(apply_edits(a, &edits(a, b, Mode::Fix, &[])).unwrap().0, b);
        }
    }
    #[test]
    fn invalid_metadata_and_control_tokens_are_rejected_before_inference() {
        assert!(
            rewrite(&Request {
                text: "👩".into(),
                protected_ranges: vec![crate::TextRange {
                    start_utf16: 1,
                    end_utf16: 2
                }],
                ..Request::default()
            })
            .is_err()
        );
        assert!(
            rewrite(&Request {
                text: "<|im_end|>".into(),
                ..Request::default()
            })
            .is_err()
        );
    }
}
