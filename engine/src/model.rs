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
type NameLogOdds = unsafe extern "C" fn(*const c_char, *const c_char, u32, u32) -> f64;
type SwapScores = unsafe extern "C" fn(
    *const c_char,
    *const c_char,
    u32,
    *const u32,
    *const *const c_char,
    f64,
    u32,
    u32,
    *mut f64,
    *mut f64,
) -> i32;
struct Runtime {
    generate: Generate,
    free: Free,
    cancel: Cancel,
    hints: Hints,
    /// Absent in a runtime built before the name judge existed: the explicit path then skips it.
    name_log_odds: Option<NameLogOdds>,
    /// Absent in a runtime built before sentence swaps existed: the swap checker then stays off.
    swap_scores: Option<SwapScores>,
    model: PathBuf,
}
static RUNTIME: OnceLock<Result<Runtime, String>> = OnceLock::new();
#[cfg(target_os = "macos")]
#[link(name = "System")]
unsafe extern "C" {
    fn dlopen(path: *const c_char, mode: i32) -> *mut c_void;
    fn dlsym(handle: *mut c_void, symbol: *const c_char) -> *mut c_void;
}
/// The runtime library and the Qwen model file next to the executable (or from the environment).
fn locations() -> Result<(PathBuf, PathBuf), String> {
    let executable = std::env::current_exe().map_err(|_| "Could not locate the bundled model.")?;
    let directory = executable
        .parent()
        .ok_or("Could not locate the bundled model.")?;
    let library = std::env::var_os("PARZR_MODEL_RUNTIME")
        .map(PathBuf::from)
        .unwrap_or_else(|| directory.join("../Frameworks/libparzr_model.dylib"));
    let model = std::env::var_os("PARZR_MODEL_PATH")
        .map(PathBuf::from)
        .unwrap_or_else(|| directory.join("../Resources/Model/Qwen3.5-0.8B-Q5_K_M.gguf"));
    Ok((library, model))
}
fn runtime() -> Result<&'static Runtime, String> {
    RUNTIME
        .get_or_init(|| {
            let (library, model) = locations()?;
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
        let judge = dlsym(handle, c"parzr_model_name_log_odds".as_ptr());
        let swaps = dlsym(handle, c"parzr_model_swap_scores".as_ptr());
        if generate.is_null() || free.is_null() || cancel.is_null() || hints.is_null() {
            return Err("The bundled model runtime is incompatible.".into());
        }
        Ok(Runtime {
            generate: std::mem::transmute::<*mut c_void, Generate>(generate),
            free: std::mem::transmute::<*mut c_void, Free>(free),
            cancel: std::mem::transmute::<*mut c_void, Cancel>(cancel),
            hints: std::mem::transmute::<*mut c_void, Hints>(hints),
            name_log_odds: (!judge.is_null())
                .then(|| std::mem::transmute::<*mut c_void, NameLogOdds>(judge)),
            swap_scores: (!swaps.is_null())
                .then(|| std::mem::transmute::<*mut c_void, SwapScores>(swaps)),
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
/// log P(yes) - log P(no) that the word at `start_utf16..end_utf16` is a person's name, from one
/// forward pass of the bundled model. None when the runtime lacks the judge or the model fails.
pub fn name_log_odds(text: &str, start_utf16: usize, end_utf16: usize) -> Option<f32> {
    let r = runtime().ok()?;
    let judge = r.name_log_odds?;
    let start = u32::try_from(byte_at(text, start_utf16)?).ok()?;
    let end = u32::try_from(byte_at(text, end_utf16)?).ok()?;
    let file = CString::new(r.model.to_string_lossy().as_bytes()).ok()?;
    let input = CString::new(text).ok()?;
    // SAFETY: both strings are NUL-terminated and live through this synchronous call.
    let value = unsafe { judge(file.as_ptr(), input.as_ptr(), start, end) };
    value.is_finite().then_some(value as f32)
}
/// Full-sentence log-probability gains of one-word swaps in `sentence` (None for a swap the left-context
/// screen rejected). A typing check never loads or waits for the model: a cold model starts loading in
/// the background and the check is unavailable, as it is when the runtime is busy.
pub fn swap_scores(
    sentence: &str,
    swaps: &[crate::confusion::Swap],
    screen: f64,
    how: crate::confusion::Use,
) -> Result<crate::confusion::Scored, crate::confusion::Unscored> {
    use crate::confusion::{Scored, Unscored, Use};
    let unavailable = |_| Unscored::Unavailable;
    let r = runtime().map_err(unavailable)?;
    let score = r.swap_scores.ok_or(Unscored::Unavailable)?;
    let file =
        CString::new(r.model.to_string_lossy().as_bytes()).map_err(|_| Unscored::Unavailable)?;
    let input = CString::new(sentence).map_err(|_| Unscored::Unavailable)?;
    let candidates: Vec<CString> = swaps
        .iter()
        .map(|s| CString::new(s.candidate.as_str()))
        .collect::<Result<_, _>>()
        .map_err(|_| Unscored::Unavailable)?;
    let pointers: Vec<*const c_char> = candidates.iter().map(|c| c.as_ptr()).collect();
    let mut spans = Vec::with_capacity(swaps.len() * 2);
    for s in swaps {
        spans.push(u32::try_from(s.start).map_err(|_| Unscored::Unavailable)?);
        spans.push(u32::try_from(s.end).map_err(|_| Unscored::Unavailable)?);
    }
    let count = u32::try_from(swaps.len()).map_err(|_| Unscored::Unavailable)?;
    // Flags: 1 load when cold, 2 warm in the background when cold, 4 wait when busy, 8 typing (keep warm
    // longer, score only the most promising swaps in one variant decode).
    let (flags, budget) = match how {
        Use::Typing { budget_ms } => (2 | 8, budget_ms),
        Use::Explicit { budget_ms } => (1 | 4, budget_ms),
    };
    let mut left = vec![f64::NAN; swaps.len()];
    let mut full = vec![f64::NAN; swaps.len()];
    // SAFETY: every pointer is valid for this synchronous call; the output buffers hold `count` values.
    let status = unsafe {
        score(
            file.as_ptr(),
            input.as_ptr(),
            count,
            spans.as_ptr(),
            pointers.as_ptr(),
            screen,
            budget,
            flags,
            left.as_mut_ptr(),
            full.as_mut_ptr(),
        )
    };
    match status {
        0 | 5 => Ok(Scored {
            gains: full
                .into_iter()
                .map(|g| g.is_finite().then_some(g))
                .collect(),
            complete: status == 0,
        }),
        4 => Err(Unscored::OutOfTime),
        _ => Err(Unscored::Unavailable),
    }
}
#[cfg(not(target_os = "macos"))]
fn load(_: &Path, _: PathBuf) -> Result<Runtime, String> {
    Err("The bundled model runtime requires macOS.".into())
}
type GecPrepare = unsafe extern "C" fn(*const c_char) -> i32;
type GecForward = unsafe extern "C" fn(*const i32, i32, *mut f32, *mut f32) -> i32;
/// The grammar model's entry points; absent in a runtime built without it (GECToR is then off).
struct GecApi {
    prepare: GecPrepare,
    forward: GecForward,
}
static GEC: OnceLock<Option<GecApi>> = OnceLock::new();
#[cfg(target_os = "macos")]
fn gec_api() -> Option<&'static GecApi> {
    GEC.get_or_init(|| {
        use std::os::unix::ffi::OsStrExt;
        // PARZR_GEC_RUNTIME points development runs at a separate build of the grammar model's runtime.
        let library = std::env::var_os("PARZR_GEC_RUNTIME")
            .map(PathBuf::from)
            .or_else(|| Some(locations().ok()?.0))?;
        let path = CString::new(library.as_os_str().as_bytes()).ok()?;
        // SAFETY: NUL-terminated names; the handle is kept for the process lifetime.
        unsafe {
            let handle = dlopen(path.as_ptr(), 2);
            if handle.is_null() {
                return None;
            }
            let prepare = dlsym(handle, c"parzr_gec_prepare".as_ptr());
            let forward = dlsym(handle, c"parzr_gec_forward".as_ptr());
            (!prepare.is_null() && !forward.is_null()).then(|| GecApi {
                prepare: std::mem::transmute::<*mut c_void, GecPrepare>(prepare),
                forward: std::mem::transmute::<*mut c_void, GecForward>(forward),
            })
        }
    })
    .as_ref()
}
#[cfg(not(target_os = "macos"))]
fn gec_api() -> Option<&'static GecApi> {
    GEC.get_or_init(|| None).as_ref()
}
/// Where the grammar model's files live: PARZR_GEC_DIR, else `gector` beside the Qwen model file.
pub fn gec_dir() -> Option<PathBuf> {
    std::env::var_os("PARZR_GEC_DIR")
        .map(PathBuf::from)
        .or_else(|| Some(locations().ok()?.1.parent()?.join("gector")))
}
/// Loads (or compiles) the resident grammar model. Idempotent; false when it is unavailable.
pub fn gec_prepare(directory: &Path) -> bool {
    let Some(api) = gec_api() else { return false };
    let Ok(dir) = CString::new(directory.to_string_lossy().as_bytes()) else {
        return false;
    };
    // SAFETY: NUL-terminated directory name alive for this synchronous call.
    unsafe { (api.prepare)(dir.as_ptr()) == 0 }
}
/// Label logits (count x 5001) and detection logits (count x 2) for 1 to 80 token ids.
pub fn gec_forward(ids: &[i32]) -> Option<(Vec<f32>, Vec<f32>)> {
    let api = gec_api()?;
    let count = i32::try_from(ids.len())
        .ok()
        .filter(|n| (1..=80).contains(n))?;
    let mut labels = vec![0f32; ids.len() * 5001];
    let mut detect = vec![0f32; ids.len() * 2];
    // SAFETY: the buffers hold count * 5001 and count * 2 floats, as the runtime requires.
    let status = unsafe {
        (api.forward)(
            ids.as_ptr(),
            count,
            labels.as_mut_ptr(),
            detect.as_mut_ptr(),
        )
    };
    (status == 0).then_some((labels, detect))
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
fn prompt(req: &Request, passage: &str, literals: &[Literal], strict: bool) -> String {
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
    let protection = if literals.is_empty() {
        String::new()
    } else {
        let mut text = " Preserve names, numbers, links, code, emojis and formatting markers exactly. Copy every ZXQPARZRKEEP token exactly once, without changing it.".to_owned();
        if strict {
            let list: Vec<_> = literals.iter().map(|l| l.marker.as_str()).collect();
            text.push_str(&format!(
                " Your answer is rejected unless it contains each of these tokens, exactly as written and in the same order: {}.",
                list.join(", ")
            ));
        }
        text
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
/// One model call. Output that is blank or carries control tokens is not a suggestion.
fn infer(r: &Runtime, prompt: &str) -> Result<String, String> {
    let file =
        CString::new(r.model.to_string_lossy().as_bytes()).map_err(|_| "Invalid model path.")?;
    let input = CString::new(prompt).map_err(|_| "Invalid passage.")?;
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
    let result = result?;
    if result.trim().is_empty() || result.contains("<|") || result.contains("<think>") {
        return Err("The model did not return a complete writing suggestion.".into());
    }
    Ok(result)
}
fn generate(req: &Request, passage: &str) -> Result<String, String> {
    let r = runtime()?;
    let (masked, literals) = mask(passage, &protected_spans(req), &name_spans(req))?;
    let mut result = String::new();
    // The first answer must keep every placeholder. If it does not, ask once more with the
    // placeholders spelled out; only then restore lost names by position.
    for strict in [false, true] {
        let output = infer(r, &prompt(req, &masked, &literals, strict))?;
        match restore(&masked, &output, &literals, strict) {
            Ok(text) => {
                result = text;
                break;
            }
            Err(error) if strict => return Err(error),
            Err(_) => {}
        }
    }
    let prefix = &passage[..passage.len() - passage.trim_start().len()];
    let suffix = &passage[passage.trim_end().len()..];
    let body = continuation(req, result.trim());
    Ok(format!("{prefix}{body}{suffix}"))
}

const LOST: &str =
    "The model could not retain a protected editor element. This suggestion was withheld.";

/// Text the model must hand back untouched, hidden behind a placeholder in the prompt.
struct Literal {
    marker: String,
    text: String,
    /// Only letters, spaces, hyphens and apostrophes: a person's name rather than a link or code.
    name: bool,
    /// A lowercase name found by the engine ("aman"); the model used to capitalize these.
    capitalize: bool,
}

fn name_chars(s: &str) -> bool {
    s.chars()
        .all(|c| c.is_alphabetic() || [' ', '-', '\'', '’'].contains(&c))
}

fn at_boundary(req: &Request, byte: usize) -> bool {
    let before =
        req.text[..byte].trim_end_matches([' ', '\t', '"', '“', '(', '[', '*', '•', '-', '>']);
    if before.is_empty() {
        return req.sentence_start;
    }
    before.ends_with(['.', '!', '?', ':', '\n'])
}

/// Words whose letters the model must never change: names (found, lowercase or capitalized
/// inside a sentence), anything with diacritics, and ALL-CAPS words. The flag marks the ones
/// that are also hidden from the model; capitalized ordinary words ("Hope", "Will") stay
/// visible for context and are guarded when the model's edits come back.
fn fixed_words(req: &Request, tokens: &[crate::tokenizer::Token<'_>]) -> Vec<(usize, bool, bool)> {
    let shout = |t: &crate::tokenizer::Token<'_>| {
        let head = t.surface.split(['\'', '’']).next().unwrap_or("");
        head.chars().count() >= 2 && head.chars().all(char::is_uppercase)
    };
    let words = tokens.iter().filter(|t| t.is_word).count();
    // A fully capitalized passage is shouting, not a list of names.
    let shouting = tokens.iter().filter(|t| shout(t)).count() * 2 > words;
    let mut out = vec![];
    for (i, t) in tokens.iter().enumerate().filter(|(_, t)| t.is_word) {
        // Chat shorthand such as "u" or "r" is not a name.
        let lower = t.surface.chars().count() > 2 && crate::spelling::lowercase_name(tokens, i);
        let accented = t
            .surface
            .chars()
            .any(|c| !c.is_ascii() && c.is_alphabetic());
        let capital = t.surface.chars().next().is_some_and(char::is_uppercase)
            && t.surface.chars().count() > 1
            && t.surface != "I"
            && !t.surface.starts_with("I'")
            && !t.surface.starts_with("I’")
            && !at_boundary(req, t.start_byte);
        let common = capital
            && crate::spelling::known(&t.normalized)
            && !crate::spelling::name_only(&t.normalized);
        if lower || accented || (shout(t) && !shouting) || capital {
            out.push((i, lower, !common || lower || accented));
        }
    }
    out
}

/// Names that the model sees only as placeholders. Ranges are in UTF-16 units; the flag marks
/// lowercase names.
fn name_spans(req: &Request) -> Vec<(crate::TextRange, bool)> {
    let tokens = crate::tokenizer::tokenize(&req.text, &req.tokens);
    fixed_words(req, &tokens)
        .into_iter()
        .filter(|&(_, _, hidden)| hidden)
        .map(|(i, lower, _)| {
            (
                crate::TextRange {
                    start_utf16: tokens[i].start_utf16,
                    end_utf16: tokens[i].end_utf16,
                },
                lower,
            )
        })
        .collect()
}

/// Replaces protected text and names with placeholders. Adjacent name words ("Aman Jain",
/// "Jean-Luc") share one placeholder so the model cannot split or reorder them.
fn mask(
    passage: &str,
    protected: &[crate::TextRange],
    names: &[(crate::TextRange, bool)],
) -> Result<(String, Vec<Literal>), String> {
    // (start, end, protected, lowercase name)
    let mut ranges: Vec<(usize, usize, bool, bool)> = protected
        .iter()
        .filter(|r| r.start_utf16 < r.end_utf16)
        .map(|r| (r.start_utf16, r.end_utf16, true, false))
        .chain(
            names
                .iter()
                .filter(|(r, _)| r.start_utf16 < r.end_utf16)
                .map(|(r, lower)| (r.start_utf16, r.end_utf16, false, *lower)),
        )
        .collect();
    ranges.sort_by_key(|r| (r.0, r.1));
    let mut merged: Vec<(usize, usize, bool, bool)> = vec![];
    for r in ranges {
        let join = |last: &(usize, usize, bool, bool)| {
            if r.0 < last.1 {
                return true;
            }
            let (Some(a), Some(b), Some(c), Some(d)) = (
                byte_at(passage, last.0),
                byte_at(passage, last.1),
                byte_at(passage, r.0),
                byte_at(passage, r.1),
            ) else {
                return false;
            };
            let gap = &passage[b..c];
            name_chars(&passage[a..b])
                && name_chars(&passage[c..d])
                && gap.chars().all(|ch| [' ', '-', '\'', '’'].contains(&ch))
                && gap.chars().count() <= 1
        };
        match merged.last_mut() {
            Some(last) if join(last) => {
                last.1 = last.1.max(r.1);
                last.2 |= r.2;
                last.3 &= r.3;
            }
            _ => merged.push(r),
        }
    }
    let mut masked = String::new();
    let mut literals: Vec<Literal> = vec![];
    let mut cursor = 0;
    for (a, b, protected, lower) in merged {
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
            if !passage.contains(&candidate) && !literals.iter().any(|l| l.marker == candidate) {
                break candidate;
            }
            serial += 1;
        };
        masked.push_str(&marker);
        literals.push(Literal {
            marker,
            text: literal.to_owned(),
            name: name_chars(literal),
            capitalize: lower
                && !protected
                && literal.chars().next().is_some_and(char::is_lowercase),
        });
        cursor = end;
    }
    masked.push_str(&passage[cursor..]);
    Ok((masked, literals))
}

fn words(s: &str) -> Vec<(usize, usize)> {
    let mut out = vec![];
    let mut start = None;
    for (i, c) in s.char_indices() {
        match (c.is_whitespace(), start) {
            (false, None) => start = Some(i),
            (true, Some(a)) => {
                out.push((a, i));
                start = None;
            }
            _ => {}
        }
    }
    if let Some(a) = start {
        out.push((a, s.len()));
    }
    out
}

/// Puts a lost placeholder back where the model dropped or mangled it, comparing the word
/// sequences of the masked source and the answer. `None` when the position is not clear.
fn place_lost(masked: &str, output: &str, marker: &str) -> Option<String> {
    let key = |w: &str| {
        w.trim_matches(|c: char| !c.is_alphanumeric())
            .to_lowercase()
    };
    let (old, new) = (words(masked), words(output));
    let old_keys: Vec<_> = old.iter().map(|&(a, b)| key(&masked[a..b])).collect();
    let new_keys: Vec<_> = new.iter().map(|&(a, b)| key(&output[a..b])).collect();
    let at = old
        .iter()
        .position(|&(a, b)| masked[a..b].contains(marker))?;
    let (a, b): (Vec<&str>, Vec<&str>) = (
        old_keys.iter().map(String::as_str).collect(),
        new_keys.iter().map(String::as_str).collect(),
    );
    let diff = TextDiff::from_slices(&a, &b);
    let op = diff.ops().iter().find(|op| op.old_range().contains(&at))?;
    let (o, n) = (op.old_range(), op.new_range());
    // The model wrote one or two words where the name was: put the name there.
    if o.len() == 1 && (1..=2).contains(&n.len()) {
        let (a, b) = (new[n.start].0, new[n.end - 1].1);
        let tail: String = output[a..b]
            .chars()
            .rev()
            .take_while(|c| !c.is_alphanumeric())
            .collect::<Vec<_>>()
            .into_iter()
            .rev()
            .collect();
        return Some(format!("{}{marker}{tail}{}", &output[..a], &output[b..]));
    }
    let greeted = old_keys[..at].iter().all(|k| {
        ["hey", "hi", "hello", "dear", "yo", "thanks", "ok", "okay"].contains(&k.as_str())
    });
    let spot = if n.is_empty() {
        new.get(n.start).map_or(output.len(), |w| w.0)
    } else if greeted {
        0
    } else {
        return None;
    };
    let (head, tail) = output.split_at(spot);
    if head.trim().is_empty() {
        // The name opens the passage: "aman can u check" becomes "Aman, can you check".
        let addressed = old_keys.get(at + 1).is_some_and(|k| {
            [
                "can", "could", "will", "would", "should", "please", "pls", "plz", "u", "you",
                "do", "did",
            ]
            .contains(&k.as_str())
        });
        let mut chars = tail.chars();
        let soften = chars.next().is_some_and(char::is_uppercase)
            && chars.next().is_some_and(char::is_lowercase);
        let tail = match tail.chars().next() {
            Some(c) if soften => c.to_lowercase().to_string() + &tail[c.len_utf8()..],
            _ => tail.to_owned(),
        };
        let sep = if tail.is_empty() {
            ""
        } else if addressed {
            ", "
        } else {
            " "
        };
        return Some(format!("{head}{marker}{sep}{tail}"));
    }
    let head = head.trim_end();
    Some(if tail.is_empty() {
        format!("{head} {marker}")
    } else {
        format!("{head} {marker} {tail}")
    })
}

/// Puts the original text back behind every placeholder. When a placeholder is missing or
/// repeated, only `recover` lets names (never links or code) be put back by position.
fn restore(
    masked: &str,
    output: &str,
    literals: &[Literal],
    recover: bool,
) -> Result<String, String> {
    // The model sometimes lowercases a token ("zxqparzrkeep0qxz"); the letters are all that matter.
    let mut result = output.to_owned();
    for l in literals {
        let lower = result.to_ascii_lowercase();
        let needle = l.marker.to_ascii_lowercase();
        let mut canonical = String::with_capacity(result.len());
        let mut at = 0;
        for (i, _) in lower.match_indices(&needle) {
            canonical.push_str(&result[at..i]);
            canonical.push_str(&l.marker);
            at = i + needle.len();
        }
        canonical.push_str(&result[at..]);
        result = canonical;
    }
    for l in literals {
        match result.matches(&l.marker).count() {
            1 => {}
            n if recover && l.name => {
                if n > 1 {
                    // A repeated name: keep the first and drop the rest with one neighbouring space.
                    let first = result.find(&l.marker).ok_or(LOST)? + l.marker.len();
                    let rest = result[first..].replace(&format!(" {}", l.marker), "");
                    let rest = rest.replace(&l.marker, "");
                    result = format!("{}{rest}", &result[..first]);
                } else {
                    result = place_lost(masked, &result, &l.marker).ok_or(LOST)?;
                }
            }
            _ => return Err(LOST.into()),
        }
    }
    for l in literals {
        let text = if l.capitalize {
            crate::upper_first(&l.text)
        } else {
            l.text.clone()
        };
        result = result.replace(&l.marker, &text);
    }
    Ok(result)
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

/// Names, accented words, ALL-CAPS words and capitalized words inside a sentence keep their
/// letters in every mode: an edit that changes more than case there is dropped, together with
/// the other half of a move. "aman" to "Am" passes the closeness test in Fix mode, so this runs
/// before it.
fn keep_names(req: &Request, all: Vec<Edit>) -> Vec<Edit> {
    let tokens = crate::tokenizer::tokenize(&req.text, &req.tokens);
    let fixed: Vec<_> = fixed_words(req, &tokens)
        .into_iter()
        .map(|(i, _, _)| (tokens[i].start_utf16, tokens[i].end_utf16))
        .collect();
    let alnum = |s: &str| {
        s.chars()
            .filter(|c| c.is_alphanumeric())
            .collect::<String>()
            .to_lowercase()
    };
    let words = |s: &str| {
        s.split_whitespace()
            .filter(|w| w.chars().any(char::is_alphanumeric))
            .count()
    };
    // "jurgen" to "Jurgen" is a recase, but "jurgen" to "Jürgen" respells an unknown word that
    // is most likely a name. Folding diacritics catches it.
    let fold = |s: &str| {
        s.chars()
            .map(|c| match c {
                'à'..='å' => 'a',
                'ç' => 'c',
                'è'..='ë' => 'e',
                'ì'..='ï' => 'i',
                'ñ' => 'n',
                'ò'..='ö' | 'ø' => 'o',
                'ù'..='ü' => 'u',
                'ý' | 'ÿ' => 'y',
                'š' | 'ş' => 's',
                'ž' => 'z',
                c => c,
            })
            .collect::<String>()
    };
    let accent_only = |e: &Edit| {
        let o = alnum(&e.original);
        words(&e.original) == 1
            && !crate::spelling::known(&o)
            && fold(&o) == fold(&alnum(&e.replacement))
            && o != alnum(&e.replacement)
    };
    let ok = |e: &Edit| {
        !accent_only(e)
            && (alnum(&e.original) == alnum(&e.replacement)
                && words(&e.original) == words(&e.replacement)
                || !fixed
                    .iter()
                    .any(|&(a, b)| a < e.end_utf16 && b > e.start_utf16))
    };
    let dropped: Vec<_> = all
        .iter()
        .filter(|e| !ok(e))
        .filter_map(|e| e.group_id.clone())
        .collect();
    all.into_iter()
        .filter(|e| ok(e) && !e.group_id.as_ref().is_some_and(|g| dropped.contains(g)))
        .collect()
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
                    // Only a real change counts: a grouped edit next to a dropped one never converges.
                    if all[j].group_id.is_none() && keep[j] {
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

const QUOTES: [char; 6] = ['\'', '"', '‘', '’', '“', '”'];
const MONTHS: [&str; 23] = [
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
    "jan",
    "feb",
    "mar",
    "apr",
    "jun",
    "jul",
    "aug",
    "sep",
    "sept",
    "oct",
    "nov",
];
/// Words that open a clause: ", and it" joins two independent clauses, ", and bikes" extends a list.
const SUBJECTS: [&str; 33] = [
    "i",
    "we",
    "you",
    "he",
    "she",
    "it",
    "they",
    "there",
    "this",
    "that",
    "these",
    "those",
    "the",
    "a",
    "an",
    "my",
    "our",
    "his",
    "her",
    "their",
    "its",
    "some",
    "many",
    "all",
    "most",
    "no",
    "one",
    "people",
    "everyone",
    "nobody",
    "everybody",
    "here",
    "who",
];
/// Openers whose comma is customary ("However," "For example,"): kept even though short.
const OPENERS: [&str; 52] = [
    "however",
    "therefore",
    "moreover",
    "furthermore",
    "nevertheless",
    "nonetheless",
    "firstly",
    "secondly",
    "thirdly",
    "finally",
    "thus",
    "hence",
    "consequently",
    "additionally",
    "instead",
    "meanwhile",
    "otherwise",
    "besides",
    "indeed",
    "similarly",
    "accordingly",
    "also",
    "first",
    "second",
    "third",
    "next",
    "lastly",
    "overall",
    "again",
    "still",
    "yes",
    "no",
    "well",
    "oh",
    "sure",
    "now",
    "for example",
    "for instance",
    "in addition",
    "in conclusion",
    "on the other hand",
    "in fact",
    "of course",
    "as a result",
    "in short",
    "in summary",
    "to sum up",
    "in other words",
    "on the one hand",
    "at last",
    "above all",
    "first of all",
];
const PREPOSITIONS: [&str; 13] = [
    "in", "on", "at", "by", "for", "from", "during", "with", "of", "to", "as", "under", "over",
];

/// Whether a comma inserted between `pre` and `post` is one the rules call optional or wrong:
/// inside a date, before "too" or a restrictive "that", after a short prepositional opener, or
/// ahead of a conjunction that joins no two clauses (the last comma of a list).
fn optional_comma(pre: &str, post: &str) -> bool {
    let bare = |w: &str| {
        w.trim_matches(|c: char| !c.is_alphanumeric())
            .to_lowercase()
    };
    let (prev, next) = (
        pre.split_whitespace()
            .next_back()
            .map(bare)
            .unwrap_or_default(),
        post.split_whitespace().next().map(bare).unwrap_or_default(),
    );
    let digit = |w: &str| !w.is_empty() && w.chars().next().is_some_and(|c| c.is_ascii_digit());
    let day = ["st", "nd", "rd", "th"]
        .iter()
        .find_map(|suffix| prev.strip_suffix(suffix))
        .unwrap_or(&prev);
    if (MONTHS.contains(&prev.as_str()) && digit(&next))
        || (!day.is_empty()
            && day.len() <= 2
            && day.bytes().all(|b| b.is_ascii_digit())
            && MONTHS.contains(&next.as_str()))
        || ["too", "that"].contains(&next.as_str())
    {
        return true;
    }
    let sentence = pre
        .rsplit(['.', '!', '?', '\n'])
        .next()
        .unwrap_or_default()
        .trim_start();
    if ["and", "but", "or", "so", "yet", "nor"].contains(&next.as_str()) {
        let after = post.split_whitespace().nth(1).map(bare).unwrap_or_default();
        return !(SUBJECTS.contains(&after.as_str())
            && !sentence.contains(',')
            && sentence.split_whitespace().count() >= 3);
    }
    let opener = sentence.to_lowercase();
    let opener = opener.trim_end();
    !opener.is_empty()
        && !opener.contains(|c: char| ",;:\"“‘()".contains(c))
        && opener.split_whitespace().count() <= 3
        && !OPENERS.contains(&opener)
        && opener
            .split_whitespace()
            .next()
            .is_some_and(|w| PREPOSITIONS.contains(&w))
}

/// Edits the model gets wrong on correct text: it straightens curly quotes, drops quote marks and
/// possessive apostrophes, adds date commas and optional commas, recases words the rules own and
/// respells words the dictionary knows. Returns the edit, with the author's quote style restored
/// inside it, or None when it should go.
fn vetted(source: &str, mut e: Edit) -> Option<Edit> {
    let (o, r) = (e.original.clone(), e.replacement.clone());
    let straight = |c: char| match c {
        '‘' | '’' => '\'',
        '“' | '”' => '"',
        c => c,
    };
    let quotes = |s: &str| s.chars().filter(|c| QUOTES.contains(c)).count();
    let alnum = |s: &str| {
        s.chars()
            .filter(|c| c.is_alphanumeric())
            .collect::<String>()
            .to_lowercase()
    };
    let lower = |s: &str| s.to_lowercase().replace('’', "'");
    let at = byte_at(source, e.start_utf16)?;
    let (before, after) = (&source[..at], &source[byte_at(source, e.end_utf16)?..]);
    if o.chars().map(straight).eq(r.chars().map(straight)) {
        return None;
    }
    let dashes = |s: &str| s.contains(['\u{2014}', '\u{2013}', '\u{2026}']) || s.contains("...");
    if quotes(&r) < quotes(&o)
        && alnum(&o) == alnum(&r)
        && confusable(&lower(&o), &lower(&r)).is_none()
        || o.is_empty() && !r.is_empty() && r.chars().all(|c| QUOTES.contains(&c))
        || dashes(&o) && !dashes(&r)
    {
        return None;
    }
    if quotes(&r) == quotes(&o) {
        let mut theirs = o.chars().filter(|c| QUOTES.contains(c));
        e.replacement = r
            .chars()
            .map(
                |c| match QUOTES.contains(&c).then(|| theirs.next()).flatten() {
                    Some(k) if straight(k) == c => k,
                    _ => c,
                },
            )
            .collect();
    }
    if o.is_empty() && r == "," && optional_comma(before, after) {
        return None;
    }
    if o != r && o.to_lowercase() == r.to_lowercase() {
        let lead = before.trim_end_matches(|c: char| " \"“‘'(".contains(c));
        let starts = (lead.is_empty() || lead.ends_with(['.', '!', '?', '\n']))
            && r.chars().next().is_some_and(char::is_uppercase);
        let shouting = o.chars().count() > 1 && o.chars().all(|c| !c.is_lowercase());
        let pronoun = o == "i" || o.starts_with("i'") || o.starts_with("i’");
        return (starts || shouting || pronoun).then_some(e);
    }
    let word = |s: &str| !s.is_empty() && s.chars().all(char::is_alphabetic);
    let (lo, lr) = (o.to_lowercase(), r.to_lowercase());
    if word(&o) && word(&r) && crate::spelling::known(&o) && crate::spelling::known(&r) {
        let sorted = |s: &str| {
            let mut c: Vec<char> = s.chars().collect();
            c.sort_unstable();
            c
        };
        let grows = |a: &str, b: &str| {
            ["s", "es", "ed", "d", "ing", "ly"]
                .iter()
                .any(|suffix| b == format!("{a}{suffix}"))
                || a.strip_suffix('y')
                    .is_some_and(|stem| b == format!("{stem}ies") || b == format!("{stem}ied"))
        };
        let swap = distance(&lo, &lr) == 1 && sorted(&lo) == sorted(&lr);
        let same_verb = matches!(
            (crate::morphology::verb(&lo), crate::morphology::verb(&lr)),
            (Some(a), Some(b)) if a.base == b.base
        );
        if lo.chars().count().min(lr.chars().count()) >= 4
            && distance(&lo, &lr) <= 2
            && (lo.starts_with(&lr) || lr.starts_with(&lo))
            && confusable(&lo, &lr).is_none()
            && !(swap || same_verb || grows(&lo, &lr) || grows(&lr, &lo))
        {
            return None;
        }
    }
    Some(e)
}

/// Fix mode keeps only plausible corrections, minus the ones the model gets wrong on correct text.
fn guard(source: &str, all: Vec<Edit>) -> Vec<Edit> {
    // A rejected edit takes the other half of its move with it.
    let vetted: Vec<_> = plausible_edits(all)
        .into_iter()
        .map(|e| (e.group_id.clone(), vetted(source, e)))
        .collect();
    let gone: Vec<_> = vetted
        .iter()
        .filter(|(_, e)| e.is_none())
        .filter_map(|(g, _)| g.clone())
        .collect();
    vetted
        .into_iter()
        .filter(|(g, _)| !g.as_ref().is_some_and(|g| gone.contains(g)))
        .filter_map(|(_, e)| e)
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
    let all = keep_names(req, all);
    let changes = if req.mode == Mode::Fix {
        guard(&req.text, all)
    } else {
        all
    };
    let (text, source_map) = apply_edits(&req.text, &changes)?;
    Ok(RewriteResult {
        version: concat!("parzr-", env!("CARGO_PKG_VERSION"), "/qwen3.5-0.8b-q5").into(),
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
    fn model_cannot_respell_or_split_a_lowercase_name() {
        let kept = |a: &str, b: &str| {
            let req = Request {
                text: a.into(),
                ..Request::default()
            };
            keep_names(&req, edits(a, b, Mode::Fix, &[]))
                .into_iter()
                .map(|e| (e.original, e.replacement))
                .collect::<Vec<_>>()
        };
        assert!(kept("aman jain", "Am jain").is_empty());
        assert_eq!(
            kept("aman jain", "Am An Jain"),
            [("jain".to_string(), "Jain".to_string())]
        );
        assert_eq!(
            kept("thanks, jain", "Thanks, join."),
            [
                ("thanks".to_string(), "Thanks".to_string()),
                ("".to_string(), ".".to_string())
            ]
        );
        assert_eq!(
            kept("hi aman, thanks", "Hi Aman, thanks"),
            [
                ("hi".to_string(), "Hi".to_string()),
                ("aman".to_string(), "Aman".to_string())
            ]
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
    fn grouped_edit_next_to_an_implausible_one_terminates() {
        let edit =
            |start: usize, end: usize, original: &str, replacement: &str, group: bool| Edit {
                start_utf16: start,
                end_utf16: end,
                replacement: replacement.to_string(),
                original: original.to_string(),
                category: String::new(),
                rule_id: String::new(),
                explanation: String::new(),
                confidence: 1.0,
                group_id: group.then(|| "g".to_string()),
            };
        let kept = plausible_edits(vec![
            edit(0, 3, "oin", "one", true),
            edit(3, 4, " ", " way or the other, the thing is ", false),
        ]);
        assert_eq!(kept.len(), 1);
        assert_eq!(kept[0].replacement, "one");
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
    /// The text the Fix-mode guard lets through for a model rewrite of `source`.
    fn guarded(source: &str, target: &str) -> String {
        let kept = guard(source, edits(source, target, Mode::Fix, &[]));
        apply_edits(source, &kept).unwrap().0
    }
    #[test]
    fn curly_quotes_stay_curly() {
        let s = "“Stay here,” said the pilot’s sister.";
        assert_eq!(guarded(s, "\"Stay here,\" said the pilot's sister."), s);
        // Inside a real correction the author's apostrophe survives.
        assert_eq!(
            guarded(
                "The farmer’s dog barkd all night.",
                "The farmer's dog barked all night."
            ),
            "The farmer’s dog barked all night."
        );
    }
    #[test]
    fn quote_marks_and_possessive_apostrophes_are_never_deleted() {
        let s = "Even 'virtual reality' needs good lighting.";
        assert_eq!(guarded(s, "Even virtual reality needs good lighting."), s);
        let s = "Ramirez' neighbours moved out last spring.";
        assert_eq!(guarded(s, "Ramirez neighbours moved out last spring."), s);
        // A confusable that happens to lose its apostrophe is still a fix.
        assert_eq!(
            guarded("The dog wagged it's tail.", "The dog wagged its tail."),
            "The dog wagged its tail."
        );
    }
    #[test]
    fn a_quote_mark_moved_elsewhere_stays_put() {
        let s = "He called it \"a fine job\", and left early.";
        assert_eq!(guarded(s, "He called it a fine job, and \"left early."), s);
    }
    #[test]
    fn dashes_and_ellipses_are_not_rewritten() {
        let s = "The tide came in\u{2014}slowly, then all at once.";
        assert_eq!(guarded(s, "The tide came in, slowly, then all at once."), s);
    }
    #[test]
    fn date_commas_are_never_added() {
        let s = "The bridge opened on 9 June 1932 after years of work.";
        assert_eq!(
            guarded(s, "The bridge opened on 9 June, 1932 after years of work."),
            s
        );
        let s = "She was born in October 1871 in a small village.";
        assert_eq!(
            guarded(s, "She was born in October, 1871 in a small village."),
            s
        );
        let s = "The vote was held on 3rd March and nobody objected.";
        assert_eq!(
            guarded(s, "The vote was held on 3rd, March and nobody objected."),
            s
        );
    }
    #[test]
    fn a_word_is_not_respelled_into_another_known_word() {
        let s = "The rustling of leaves carried across the field.";
        assert_eq!(
            guarded(s, "The rustling of leaves carried across the fields."),
            "The rustling of leaves carried across the fields."
        );
        let s = "The comic timing of the actor was perfect.";
        assert_eq!(
            guarded(s, "The comical timing of the actor was perfect."),
            s
        );
        let s = "Their economic plan failed within a year.";
        assert_eq!(guarded(s, "Their economical plan failed within a year."), s);
        // A different word of the same length is more likely a typo fix than a rewrite.
        assert_eq!(
            guarded("The cheep seats sold fast.", "The cheap seats sold fast."),
            "The cheap seats sold fast."
        );
        // Agreement and confusables are corrections, not respellings.
        assert_eq!(
            guarded("The nurses was tired.", "The nurses were tired."),
            "The nurses were tired."
        );
        assert_eq!(
            guarded("We left there coats behind.", "We left their coats behind."),
            "We left their coats behind."
        );
    }
    #[test]
    fn case_changes_are_left_to_the_rules_outside_sentence_starts() {
        let s = "We ordered a speed post parcel for Tuesday.";
        assert_eq!(guarded(s, "We ordered a Speed Post parcel for Tuesday."), s);
        let s = "The Garden was quiet at dawn.";
        assert_eq!(guarded(s, "The garden was quiet at dawn."), s);
        // A sentence start, a lone i and shouted words are still fixed.
        assert_eq!(
            guarded(
                "It rained. the road flooded.",
                "It rained. The road flooded."
            ),
            "It rained. The road flooded."
        );
        assert_eq!(guarded("Then i left.", "Then I left."), "Then I left.");
        assert_eq!(
            guarded("PLEASE CLOSE the door.", "Please close the door."),
            "Please close the door."
        );
    }
    #[test]
    fn optional_commas_are_dropped_and_needed_ones_kept() {
        // A short prepositional opener, "too", a restrictive "that" and a serial comma are optional.
        for (s, t) in [
            (
                "In the evening we walked home.",
                "In the evening, we walked home.",
            ),
            ("My brother came too.", "My brother came, too."),
            (
                "The book that I borrowed was dull.",
                "The book, that I borrowed was dull.",
            ),
            (
                "We packed tents, ropes and boots.",
                "We packed tents, ropes, and boots.",
            ),
        ] {
            assert_eq!(guarded(s, t), s);
        }
        // An independent clause after a coordinating conjunction, a conjunctive adverb and a
        // comma that ends a subordinate clause stay.
        for (s, t) in [
            (
                "The storm grew worse and we turned back.",
                "The storm grew worse, and we turned back.",
            ),
            ("However we agreed to wait.", "However, we agreed to wait."),
            (
                "When the bell rang we all stood up.",
                "When the bell rang, we all stood up.",
            ),
        ] {
            assert_eq!(guarded(s, t), t);
        }
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
            &[],
        )
        .unwrap();
        assert!(masked.contains(" hello\n"));
        let mut restored = masked;
        for l in literals {
            restored = restored.replace(&l.marker, &l.text);
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

    fn range(a: usize, b: usize) -> crate::TextRange {
        crate::TextRange {
            start_utf16: a,
            end_utf16: b,
        }
    }
    fn literal(marker: &str, text: &str, name: bool, capitalize: bool) -> Literal {
        Literal {
            marker: marker.into(),
            text: text.into(),
            name,
            capitalize,
        }
    }
    #[test]
    fn adjacent_name_words_share_one_placeholder() {
        let text = "hi Aman Jain and Jean-Luc, see 42";
        let (masked, literals) = mask(
            text,
            &[range(31, 33)],
            &[
                (range(3, 7), false),
                (range(8, 12), false),
                (range(17, 21), false),
                (range(22, 25), false),
            ],
        )
        .unwrap();
        let texts: Vec<_> = literals.iter().map(|l| l.text.as_str()).collect();
        assert_eq!(texts, ["Aman Jain", "Jean-Luc", "42"], "{masked}");
        assert_eq!(masked.matches("ZXQPARZRKEEP").count(), 3);
        assert!(literals[0].name && literals[1].name && !literals[2].name);
    }
    #[test]
    fn lost_names_are_restored_by_position_but_links_are_not() {
        let marker = "ZXQPARZRKEEP0QXZ";
        let masked = format!("hey {marker} can u send the file");
        let aman = [literal(marker, "Aman", true, false)];
        let back = |output: &str| restore(&masked, output, &aman, true);
        assert_eq!(
            back(&format!("Hey {marker}, can you send the file?")).unwrap(),
            "Hey Aman, can you send the file?"
        );
        assert_eq!(
            back("Could you please send the file?").unwrap(),
            "Aman, could you please send the file?"
        );
        assert_eq!(
            back("Hey, can you send the file?").unwrap(),
            "Hey, Aman can you send the file?"
        );
        // Without recovery, and for links, a lost placeholder withholds the suggestion.
        assert!(restore(&masked, "Could you send the file?", &aman, false).is_err());
        let link = [literal(marker, "https://a.b/c", false, false)];
        assert!(restore(&masked, "Could you send the file?", &link, true).is_err());
        // A repeated name keeps its first copy.
        assert_eq!(
            restore(
                &masked,
                &format!("{marker}, can {marker} send it"),
                &aman,
                true
            )
            .unwrap(),
            "Aman, can send it"
        );
    }
    #[test]
    fn a_lowercased_placeholder_still_counts() {
        let marker = "ZXQPARZRKEEP0QXZ";
        let tell = [literal(marker, "Harsha", true, false)];
        assert_eq!(
            restore(
                &format!("tell {marker} now"),
                "Tell zxqparzrkeep0qxz now.",
                &tell,
                false
            )
            .unwrap(),
            "Tell Harsha now."
        );
    }
    #[test]
    fn lowercase_names_are_capitalized_when_restored() {
        let marker = "ZXQPARZRKEEP0QXZ";
        let aman = [literal(marker, "aman", true, true)];
        assert_eq!(
            restore(
                &format!("hi {marker}"),
                &format!("Hi {marker}!"),
                &aman,
                false
            )
            .unwrap(),
            "Hi Aman!"
        );
    }
    #[test]
    fn names_are_fixed_words_in_every_mode() {
        let req = Request {
            text: "hey Hope can u ask jurgen and NITHYA, Ştefan or Bjørn at 9?".into(),
            ..Request::default()
        };
        let tokens = crate::tokenizer::tokenize(&req.text, &[]);
        let fixed: Vec<_> = fixed_words(&req, &tokens)
            .into_iter()
            .map(|(i, _, hidden)| (tokens[i].surface, hidden))
            .collect();
        assert_eq!(
            fixed,
            [
                ("Hope", false),
                ("jurgen", true),
                ("NITHYA", true),
                ("Ştefan", true),
                ("Bjørn", true)
            ]
        );
    }
    #[test]
    fn model_edits_may_recase_a_name_but_never_respell_or_drop_it() {
        for (a, b, expected) in [
            ("ask jurgen now", "Ask Jürgen now.", "Ask jurgen now."),
            ("ask jurgen now", "Ask Jurgen now.", "Ask Jurgen now."),
            ("NITHYA will go", "Nithya will go", "Nithya will go"),
            (
                "tell liam we are late",
                "Tell Liar we are late.",
                "Tell liam we are late.",
            ),
            ("I met jurgen", "I met Jürgen.", "I met jurgen."),
            (
                "hey Hope how r u",
                "Hey Hopes, how are you?",
                "Hey Hope how are you?",
            ),
        ] {
            let req = Request {
                text: a.into(),
                ..Request::default()
            };
            let kept = keep_names(&req, edits(a, b, Mode::Professional, &[]));
            assert_eq!(apply_edits(a, &kept).unwrap().0, expected, "{a} -> {b}");
        }
    }
}
