//! Grammar → tone → grammar, retaining original scalar anchors for minimal UTF-16 edits.
#[cfg(feature = "local-model")]
use crate::name_guard_ranges;
use crate::{
    Edit, MAX_TEXT_BYTES, Mode, Request, RewriteResult, TextRange, apply_edits, byte_at,
    protected_ranges, rewrite_once,
};
use std::{
    collections::{HashMap, HashSet},
    time::Instant,
};

/// A typing check's warning when sentence swaps still wait for the model: the app checks again shortly.
#[cfg(feature = "local-model")]
pub const PENDING_WARNING: &str = "context.pending";
/// log P(yes) - log P(no) at or above which a word the rules would respell is kept as a name.
/// Calibrated on benchmarks/names: protects 94.9% of held-out names and spares 98.7% of typos.
const JUDGE_THRESHOLD: f32 = -0.9;
/// Model queries per request, which bounds the latency the judge can add.
const JUDGE_CAP: usize = 12;
type Scorer = fn(&str, usize, usize) -> Option<f32>;
/// Asks the local model whether a word the rules would respell is a person's name (explicit path
/// only). One verdict per word per request; a name is dropped from the edit plan and protected.
struct Judge {
    score: Option<Scorer>,
    verdicts: HashMap<String, bool>,
    asked: usize,
}
/// The word a rule or model edit would respell or split: one lowercase alphabetic token (optionally with a
/// possessive) the lexicon does not know. Case-only edits, known words and anything else are not.
fn judged_word(text: &str, e: &Edit) -> Option<String> {
    let (a, b) = (byte_at(text, e.start_utf16)?, byte_at(text, e.end_utf16)?);
    let token = text.get(a..b)?;
    let word = ["'s", "’s"]
        .iter()
        .find_map(|s| token.strip_suffix(s))
        .unwrap_or(token);
    let edge = |c: Option<char>| c.is_some_and(|c| c.is_alphanumeric() || c == '\'' || c == '’');
    ((e.category == "Spelling" || e.rule_id == "local-model")
        && word.chars().count() >= 2
        && word.chars().all(|c| c.is_alphabetic() && !c.is_uppercase())
        && !crate::spelling::known(word)
        // Known misspellings (freind, recieve) are always corrected; never ask the judge.
        && !crate::names::is_name_typo(word)
        // A frequent word with one letter doubled, dropped or swapped ("giirls", "someonse")
        // is a slip, not a name the model should vouch for.
        && !crate::spelling::edit_shaped(word)
        && e.replacement.to_lowercase() != token
        && !edge(text[..a].chars().next_back())
        && !edge(text[b..].chars().next()))
    .then(|| word.to_owned())
}
impl Judge {
    fn new(enabled: bool, score: Scorer) -> Self {
        Self {
            score: enabled.then_some(score),
            verdicts: HashMap::new(),
            asked: 0,
        }
    }
    fn is_name(&mut self, text: &str, e: &Edit, word: &str) -> bool {
        let Some(score) = self.score else {
            return false;
        };
        if let Some(known) = self.verdicts.get(word) {
            return *known;
        }
        if self.asked >= JUDGE_CAP {
            return false;
        }
        self.asked += 1;
        let start = e.start_utf16;
        let verdict = score(text, start, start + word.encode_utf16().count())
            .is_some_and(|v| v >= JUDGE_THRESHOLD);
        self.verdicts.insert(word.to_owned(), verdict);
        verdict
    }
    /// Removes the edits that respell a name, and edits linked to them, from one pass over the
    /// document; the names found are protected (original coordinates) for the passes that follow.
    fn screen(
        &mut self,
        document: &Document,
        edits: &mut Vec<Edit>,
        protected: &mut Vec<TextRange>,
    ) {
        if self.score.is_none() {
            return;
        }
        let text = document.text();
        let mut groups = HashSet::new();
        let mut dropped = vec![];
        for (i, e) in edits.iter().enumerate() {
            if let Some(word) = judged_word(&text, e)
                && self.is_name(&text, e, &word)
                && let Some((a, b)) = document.origin_range(e.start_utf16, e.end_utf16)
            {
                dropped.push(i);
                groups.extend(e.group_id.clone());
                protected.push(TextRange {
                    start_utf16: a,
                    end_utf16: b,
                });
            }
        }
        let mut i = 0;
        edits.retain(|e| {
            i += 1;
            !dropped.contains(&(i - 1)) && !e.group_id.as_ref().is_some_and(|g| groups.contains(g))
        });
    }
}
#[cfg(feature = "local-model")]
fn name_score(text: &str, start: usize, end: usize) -> Option<f32> {
    crate::model::name_log_odds(text, start, end)
}
#[cfg(not(feature = "local-model"))]
fn name_score(_: &str, _: usize, _: usize) -> Option<f32> {
    None
}

/// "Pls" to "Please", "thx" to "thanks": Smart grammar leaves chat shorthand as typed.
#[cfg(feature = "local-model")]
fn shorthand(e: &Edit) -> bool {
    let word = e.original.trim();
    !word.contains(char::is_whitespace)
        && crate::names::is_shorthand(&word.to_lowercase())
        && e.replacement.trim().to_lowercase() != word.to_lowercase()
}
/// An edit to a word stretched for emphasis ("sooo", "yesss") is only its plain form ("so", "yes").
#[cfg(feature = "local-model")]
fn stretch_kept(e: &Edit) -> bool {
    let word = e.original.trim();
    if word.contains(char::is_whitespace) || !crate::names::stretched(word) {
        return true;
    }
    let letters: Vec<char> = word.to_lowercase().chars().collect();
    let fixed = e.replacement.trim().to_lowercase();
    (1..=2).any(|keep| fixed == crate::names::squeeze(&letters, keep))
        && crate::spelling::known(&fixed)
}
/// The model's Fix pass keeps what people type on purpose: chat shorthand ("pls", "idk", "lmk"),
/// repeated marks ("!!", "??"), a sign-off's comma ("All the best,"), contractions ("it's" stays,
/// and "its" becomes "it's", never "it is"), and the shape of tokens: no code formatting added, no
/// space removed after an @mention or between words into a non-word, none added around a slash.
#[cfg(feature = "local-model")]
fn keep_typed_voice(text: &str, edits: &mut Vec<Edit>) {
    let word_char = |c: char| c.is_alphanumeric() || c == '\'' || c == '’';
    let marks = |c: char| c == '!' || c == '?';
    edits.retain_mut(|e| {
        if !e.rule_id.contains("local-model") {
            return true;
        }
        let (Some(a), Some(b)) = (byte_at(text, e.start_utf16), byte_at(text, e.end_utf16)) else {
            return true;
        };
        let wa = text[..a]
            .char_indices()
            .rev()
            .take_while(|(_, c)| word_char(*c))
            .last()
            .map_or(a, |(i, _)| i);
        let wb = b + text[b..]
            .char_indices()
            .take_while(|(_, c)| word_char(*c))
            .last()
            .map_or(0, |(i, c)| i + c.len_utf8());
        let old = &text[wa..wb];
        let new = format!("{}{}{}", &text[wa..a], e.replacement, &text[b..wb]);
        // "pls" to "Please", "idk" to "I'd", "lmk" to "LMK".
        if !old.is_empty()
            && !old.contains(char::is_whitespace)
            && crate::names::is_shorthand(&old.to_lowercase())
        {
            return false;
        }
        // "!!" to "!", "??" to "?".
        if !e.original.is_empty()
            && e.original.chars().all(marks)
            && e.replacement.chars().all(marks)
            && text[..a].chars().rev().take_while(|c| marks(*c)).count()
                + text[b..].chars().take_while(|c| marks(*c)).count()
                + e.original.chars().count()
                >= 2
        {
            return false;
        }
        // "pricing." to "pricing..": a mark doubled beside one already there.
        if e.original.is_empty()
            && !e.replacement.is_empty()
            && e.replacement.chars().all(|c| ".!?".contains(c))
            && (text[..a].ends_with(['.', '!', '?']) || text[b..].starts_with(['.', '!', '?']))
        {
            return false;
        }
        // "Their office is on the floor" to "Their office on the floor": the model's Fix pass
        // never drops a verb (a doubled "is is" is the rules' to remove).
        if e.replacement.trim().is_empty()
            && [
                "is", "are", "was", "were", "am", "be", "been", "has", "have", "had", "do", "does",
                "did", "will", "can", "would", "should", "could",
            ]
            .contains(&e.original.trim().to_lowercase().as_str())
        {
            return false;
        }
        // "Dr. Patel" to "Dr, Patel": a title's full stop stays.
        if e.original == "."
            && [
                "dr", "mr", "mrs", "ms", "mx", "prof", "st", "jr", "sr", "vs", "etc",
            ]
            .contains(&old.to_lowercase().as_str())
        {
            return false;
        }
        // "(and love)" to "and love": brackets the user typed stay.
        if ['(', ')', '[', ']']
            .iter()
            .any(|b| e.original.contains(*b) && !e.replacement.contains(*b))
        {
            return false;
        }
        // "waitin'" to "waiting": a dropped g marked with its apostrophe is meant.
        let bare = old.trim_end_matches(['\'', '’']);
        if bare.len() > 3
            && bare.ends_with("in")
            && (bare.len() < old.len() || text[wb..].starts_with(['\'', '’']))
        {
            return false;
        }
        // 'said that "It was fine': a quotation mark the user did not type.
        if ['"', '“', '”']
            .iter()
            .any(|q| e.replacement.contains(*q) && !e.original.contains(*q))
        {
            return false;
        }
        // "rwtries" to "rwtrts": one unknown word turned into another is no correction.
        if !old.is_empty()
            && !old.contains(char::is_whitespace)
            && !new.contains(char::is_whitespace)
            && !old.eq_ignore_ascii_case(&new)
            && !crate::spelling::known(old.trim_matches('\''))
            && !crate::spelling::known(new.trim_matches('\''))
            // "betwde en": a word split by a space is repaired in two steps.
            && !text[wb..]
                .strip_prefix(' ')
                .and_then(|r| r.split(|c: char| !c.is_alphabetic()).next())
                .is_some_and(|piece| {
                    (1..=3).contains(&piece.len())
                        && ![
                            "to", "a", "an", "in", "on", "at", "of", "is", "it", "be", "by", "or",
                            "as", "we", "i", "so", "up", "my", "me", "us", "do", "go", "no", "if",
                            "for", "the", "and", "but", "are", "was", "you", "can", "not", "our",
                            "has", "had", "his", "her", "all", "any", "out", "off", "too", "now",
                        ]
                        .contains(&piece.to_lowercase().as_str())
                })
        {
            return false;
        }
        // "Refactor auth middleware" to "Refactor the auth middleware": a line without a final
        // mark (a commit message, a note, a status) leaves out articles and subjects on purpose.
        let line_end = text[b..].find('\n').map_or(text.len(), |n| b + n);
        let telegraphic = !text[..line_end].trim_end().ends_with(['.', '!', '?']);
        if telegraphic
            && e.original.trim().is_empty()
            && ["the", "a", "an", "it", "i", "we"]
                .contains(&e.replacement.trim().to_lowercase().as_str())
        {
            return false;
        }
        // "Run `git pull`": formatting the user did not type.
        if ["`", "**", "__"]
            .iter()
            .any(|m| e.replacement.contains(m) && !e.original.contains(m))
        {
            return false;
        }
        // "credit /legal", "processing/ prioritizing".
        if e.replacement.trim().is_empty()
            && !e.replacement.is_empty()
            && (text[b..].starts_with('/') || text[..a].ends_with('/'))
        {
            return false;
        }
        // "@alex I think" to "@alexI think", "ahahaha ive" to "ahahahaI've".
        if e.original.contains(char::is_whitespace) && !e.replacement.contains(char::is_whitespace)
        {
            let ra = text[..a]
                .char_indices()
                .rev()
                .take_while(|(_, c)| !c.is_whitespace())
                .last()
                .map_or(a, |(i, _)| i);
            let rb = b + text[b..]
                .char_indices()
                .take_while(|(_, c)| !c.is_whitespace())
                .last()
                .map_or(0, |(i, c)| i + c.len_utf8());
            let glued = format!("{}{}{}", &text[ra..a], e.replacement, &text[b..rb]);
            let core = glued.trim_matches(|c: char| !c.is_alphanumeric());
            if glued.starts_with(['@', '#']) || !crate::spelling::known(core) {
                return false;
            }
        }
        // "All the best," to "All the best.": a short closing line keeps its comma.
        if e.original == ","
            && (e.replacement == "." || e.replacement.is_empty())
            && {
                let rest = text[b..].trim_start_matches([' ', '\t']);
                rest.is_empty() || rest.starts_with('\n')
            }
            && text[..a]
                .rsplit('\n')
                .next()
                .is_some_and(|line| line.split_whitespace().count() <= 4)
        {
            return false;
        }
        // "it's" to "it is", "its" to "it is": the contraction stays (and gets its apostrophe).
        if !old.is_empty() && !old.contains(char::is_whitespace) && new.split(' ').count() == 2 {
            let joined = old.to_lowercase().replace(['\'', '’'], "");
            if let Some(full) = crate::contractions::contraction(&joined)
                && expansions(full).contains(&new.to_lowercase())
            {
                let apostrophe = if old.contains('’') { "’" } else { "'" };
                let mut cased = full.replace('\'', apostrophe);
                if full.starts_with("i'") || old.starts_with(char::is_uppercase) {
                    cased = crate::upper_first(&cased);
                }
                if cased == old {
                    return false;
                }
                e.start_utf16 = crate::utf16_at(text, wa);
                e.end_utf16 = crate::utf16_at(text, wb);
                e.original = old.to_string();
                e.replacement = cased;
            }
        }
        true
    });
}
/// What a contraction stands for: "it's" is "it is" or "it has", "can't" is "cannot".
#[cfg(feature = "local-model")]
fn expansions(contraction: &str) -> Vec<String> {
    match contraction {
        "won't" => return vec!["will not".into()],
        "can't" => return vec!["cannot".into(), "can not".into()],
        "shan't" => return vec!["shall not".into()],
        "let's" => return vec!["let us".into()],
        _ => {}
    }
    if let Some(stem) = contraction.strip_suffix("n't") {
        return vec![format!("{stem} not")];
    }
    let Some((stem, tail)) = contraction.split_once('\'') else {
        return vec![];
    };
    let full: &[&str] = match tail {
        "s" => &["is", "has"],
        "re" => &["are"],
        "ll" => &["will"],
        "ve" => &["have"],
        "d" => &["would", "had", "did"],
        "m" => &["am"],
        _ => &[],
    };
    full.iter().map(|f| format!("{stem} {f}")).collect()
}
#[derive(Clone)]
struct Cell {
    ch: char,
    origin: Option<(usize, usize)>,
    cause: Option<usize>,
}
struct Document {
    cells: Vec<Cell>,
    causes: Vec<Edit>,
}
impl Document {
    fn new(text: &str) -> Self {
        let mut offset = 0;
        let cells = text
            .chars()
            .map(|ch| {
                let start = offset;
                offset += ch.len_utf16();
                Cell {
                    ch,
                    origin: Some((start, offset)),
                    cause: None,
                }
            })
            .collect();
        Self {
            cells,
            causes: vec![],
        }
    }
    fn text(&self) -> String {
        self.cells.iter().map(|c| c.ch).collect()
    }
    /// The original-text range of unedited cells covering `start..end` (current UTF-16 offsets).
    fn origin_range(&self, start: usize, end: usize) -> Option<(usize, usize)> {
        let mut offset = 0;
        let mut range: Option<(usize, usize)> = None;
        for c in &self.cells {
            if offset >= start && offset < end {
                let (a, b) = c.origin?;
                range = Some(range.map_or((a, b), |(x, y)| (x.min(a), y.max(b))));
            }
            offset += c.ch.len_utf16();
        }
        range
    }
    fn request(&self, original: &Request, protected: &[TextRange], mode: Mode) -> Request {
        // Indexed by original UTF-16 offset: where that offset starts or ends now.
        let size = self
            .cells
            .iter()
            .filter_map(|c| c.origin)
            .map(|o| o.1 + 1)
            .max();
        let mut starts = vec![None; size.unwrap_or(0)];
        let mut ends = vec![None; size.unwrap_or(0)];
        let mut offset = 0;
        for c in &self.cells {
            if let Some((a, b)) = c.origin {
                starts[a] = Some(offset);
                ends[b] = Some(offset + c.ch.len_utf16());
            }
            offset += c.ch.len_utf16();
        }
        let remap = |a: usize, b: usize| -> Option<(usize, usize)> {
            let x = (*starts.get(a)?)?;
            let y = (*ends.get(b)?)?;
            (y - x == b - a).then_some((x, y))
        };
        let mut req = original.clone();
        req.text = self.text();
        req.mode = mode;
        req.protected_ranges = protected
            .iter()
            .filter_map(|r| {
                remap(r.start_utf16, r.end_utf16).map(|(a, b)| TextRange {
                    start_utf16: a,
                    end_utf16: b,
                })
            })
            .collect();
        req.tokens = original
            .tokens
            .iter()
            .filter_map(|t| {
                remap(t.start_utf16, t.end_utf16).map(|(a, b)| {
                    let mut t = t.clone();
                    t.start_utf16 = a;
                    t.end_utf16 = b;
                    t
                })
            })
            .collect();
        // Sentence capitals this engine added are not evidence about how the text was typed.
        let mut offset = 0;
        let mut auto = vec![];
        for (i, c) in self.cells.iter().enumerate() {
            if let Some(k) = c.cause
                && self.causes[k].rule_id == "grammar.sentence_capitalization"
                && c.origin.is_none()
                && i.checked_sub(1)
                    .is_none_or(|p| self.cells[p].cause != c.cause)
            {
                let rest: usize = self.cells[i..]
                    .iter()
                    .take_while(|x| x.ch.is_alphabetic() || x.ch == '\'' || x.ch == '’')
                    .map(|x| x.ch.len_utf16())
                    .sum();
                auto.push((offset, offset + rest));
            }
            offset += c.ch.len_utf16();
        }
        req.tokens
            .extend(auto.into_iter().map(|(a, b)| crate::TokenHint {
                start_utf16: a,
                end_utf16: b,
                pos: crate::AUTO_CAPITAL_HINT.into(),
                lemma: String::new(),
                name: false,
                ..Default::default()
            }));
        req
    }
    fn apply(&mut self, edits: &[Edit]) -> Result<(), String> {
        // Cell index at each UTF-16 offset that starts a cell (or ends the text).
        let mut boundaries = vec![];
        for (i, c) in self.cells.iter().enumerate() {
            boundaries.push(Some(i));
            boundaries.resize(boundaries.len() + c.ch.len_utf16() - 1, None);
        }
        boundaries.push(Some(self.cells.len()));
        for edit in edits.iter().rev() {
            let a = boundaries
                .get(edit.start_utf16)
                .copied()
                .flatten()
                .ok_or("Invalid pipeline boundary.")?;
            let b = boundaries
                .get(edit.end_utf16)
                .copied()
                .flatten()
                .ok_or("Invalid pipeline boundary.")?;
            let mut intervals: Vec<(usize, usize)> = self.cells[a..b]
                .iter()
                .filter_map(|c| {
                    c.origin.or_else(|| {
                        c.cause.map(|i| {
                            let e = &self.causes[i];
                            (e.start_utf16, e.end_utf16)
                        })
                    })
                })
                .collect();
            if intervals.is_empty() {
                let point = self.cells[..a]
                    .iter()
                    .rev()
                    .find_map(|c| c.origin.map(|(_, b)| b))
                    .unwrap_or(0);
                intervals.push((point, point));
            }
            let mut cause = edit.clone();
            cause.start_utf16 = intervals.iter().map(|x| x.0).min().unwrap_or(0);
            cause.end_utf16 = intervals.iter().map(|x| x.1).max().unwrap_or(0);
            let index = self.causes.len();
            self.causes.push(cause);
            self.cells.splice(
                a..b,
                edit.replacement.chars().map(|ch| Cell {
                    ch,
                    origin: None,
                    cause: Some(index),
                }),
            );
        }
        if self.text().len() > MAX_TEXT_BYTES {
            return Err("The rewritten passage exceeds 64 KB.".into());
        }
        Ok(())
    }
    fn plan(&self, original: &str) -> Result<Vec<Edit>, String> {
        let mut edits = vec![];
        let mut cursor = 0;
        let mut replacement = String::new();
        let mut causes = vec![];
        let mut flush = |cursor: &mut usize,
                         end: usize,
                         replacement: &mut String,
                         causes: &mut Vec<usize>|
         -> Result<(), String> {
            let a = byte_at(original, *cursor).ok_or("Invalid source anchor.")?;
            let b = byte_at(original, end).ok_or("Invalid source anchor.")?;
            // Overlapping edits once left the cursor past the end here and the slice panicked.
            if a > b {
                return Err("The composed edit plan is inconsistent.".into());
            }
            if original[a..b] != *replacement {
                for (i, c) in self.causes.iter().enumerate() {
                    if (c.start_utf16 < end && c.end_utf16 > *cursor)
                        || (c.start_utf16 == c.end_utf16
                            && c.start_utf16 >= *cursor
                            && c.start_utf16 <= end)
                    {
                        causes.push(i);
                    }
                }
                causes.sort_unstable();
                causes.dedup();
                let records: Vec<_> = causes.iter().map(|i| &self.causes[*i]).collect();
                let first = records
                    .iter()
                    .find(|e| e.category != "Tone")
                    .or(records.first())
                    .ok_or("Missing edit provenance.")?;
                let mut reasons = Vec::new();
                let mut ids = Vec::new();
                for r in &records {
                    if !reasons.contains(&r.explanation) {
                        reasons.push(r.explanation.clone());
                        ids.push(r.rule_id.clone());
                    }
                }
                edits.push(Edit {
                    start_utf16: *cursor,
                    end_utf16: end,
                    original: original[a..b].into(),
                    replacement: replacement.clone(),
                    category: first.category.clone(),
                    rule_id: ids.join("+"),
                    explanation: reasons.join(" "),
                    confidence: records.iter().map(|r| r.confidence).fold(1.0, f32::min),
                    group_id: records.iter().find_map(|r| r.group_id.clone()),
                });
            }
            replacement.clear();
            causes.clear();
            *cursor = end;
            Ok(())
        };
        let mut prev_cause: Option<usize> = None;
        for c in &self.cells {
            if let Some((a, b)) = c.origin {
                prev_cause = None;
                if cursor != a || !replacement.is_empty() {
                    flush(&mut cursor, a, &mut replacement, &mut causes)?;
                }
                cursor = b;
            } else {
                // A name capitalization stays its own edit, never merged with a neighbour.
                if let Some(i) = c.cause
                    && let Some(p) = prev_cause
                    && p != i
                    && !replacement.is_empty()
                    // "noahs" to "Noah's": an apostrophe put inside the capitalized name is part
                    // of the same word, and a split there would end before the cursor.
                    && !within(&self.causes[i], &self.causes[p])
                    && !within(&self.causes[p], &self.causes[i])
                    && self.causes[p].end_utf16 >= cursor
                    && (self.causes[p].rule_id == "names.capitalize"
                        || self.causes[i].rule_id == "names.capitalize")
                {
                    flush(
                        &mut cursor,
                        self.causes[p].end_utf16,
                        &mut replacement,
                        &mut causes,
                    )?;
                }
                if c.cause.is_some() {
                    prev_cause = c.cause;
                }
                if replacement.is_empty()
                    && let Some(i) = c.cause
                    && self.causes[i].start_utf16 > cursor
                {
                    flush(
                        &mut cursor,
                        self.causes[i].start_utf16,
                        &mut replacement,
                        &mut causes,
                    )?;
                }
                replacement.push(c.ch);
                if let Some(i) = c.cause {
                    causes.push(i);
                }
            }
        }
        flush(
            &mut cursor,
            original.encode_utf16().count(),
            &mut replacement,
            &mut causes,
        )?;
        if edits.len() > 512 {
            return Err("This passage has too many changes. Select a shorter passage.".into());
        }
        Ok(edits)
    }
}

/// `inner` lies inside the source span of `outer`.
fn within(inner: &Edit, outer: &Edit) -> bool {
    inner.start_utf16 >= outer.start_utf16 && inner.end_utf16 <= outer.end_utf16
}

fn grammar(
    document: &mut Document,
    req: &Request,
    protected: &mut Vec<TextRange>,
    judge: &mut Judge,
) -> Result<(), String> {
    for _ in 0..6 {
        let mut pass = rewrite_once(&document.request(req, protected, Mode::Fix), false)?.edits;
        judge.screen(document, &mut pass, protected);
        if pass.is_empty() {
            return Ok(());
        }
        document.apply(&pass)?;
    }
    if !rewrite_once(&document.request(req, protected, Mode::Fix), false)?
        .edits
        .is_empty()
    {
        return Err("Corrections did not stabilize. Select a shorter passage.".into());
    }
    Ok(())
}
pub fn rewrite(req: &Request) -> Result<RewriteResult, String> {
    let start = Instant::now();
    // Fold names and dictionary once; every pass below shares the index.
    let req = &req.indexed();
    #[cfg(feature = "local-model")]
    if req.mode != Mode::Fix {
        return tone(req, start);
    }
    check(req, start, req.deep)
}
/// The check itself. `contextual` runs the model's context pass over the whole passage (an
/// explicit Fix check); a tone rewrite's correction pass skips it, as the tone model corrects
/// the passage again anyway.
#[cfg_attr(not(feature = "local-model"), allow(unused_variables))]
fn check(req: &Request, start: Instant, contextual: bool) -> Result<RewriteResult, String> {
    let mut first = rewrite_once(req, false)?.edits;
    // No edit leaves the text as it was, so the confirmation pass below would only repeat this one.
    let unchanged = first.is_empty() && req.mode == Mode::Fix;
    let mut protected = protected_ranges(req);
    let mut document = Document::new(&req.text);
    // Explicit checks ask the model about words the rules would respell; the automatic path
    // stays model-free.
    let mut judge = Judge::new(cfg!(feature = "local-model") && req.deep, name_score);
    judge.screen(&document, &mut first, &mut protected);
    document.apply(&first)?;
    if !unchanged {
        grammar(&mut document, req, &mut protected, &mut judge)?;
    }
    #[allow(unused_mut)]
    let mut warnings = vec![];
    #[cfg(feature = "local-model")]
    if contextual {
        // The model gets no instructions about names, so every name candidate is masked.
        let mut masked = protected.clone();
        masked.extend(name_guard_ranges(req));
        match crate::model::rewrite(&document.request(req, &masked, req.mode)) {
            Ok(mut contextual) => {
                keep_typed_voice(&document.text(), &mut contextual.edits);
                // The model respells lowercase names the rules left alone ("ritesh's" to "Rish's").
                judge.screen(&document, &mut contextual.edits, &mut protected);
                document.apply(&contextual.edits)?;
                grammar(&mut document, req, &mut protected, &mut judge)?;
            }
            Err(error) => {
                // Keep verified grammar edits when contextual refinement cannot safely
                // preserve links/mentions. Never report the refinement as successful.
                warnings.push(format!(
                    "Grammar checked; context refinement unavailable. {error}"
                ));
            }
        }
    }
    #[cfg(not(feature = "local-model"))]
    if req.mode != Mode::Fix {
        let tone = rewrite_once(&document.request(req, &protected, req.mode), true)?;
        document.apply(&tone.edits)?;
        grammar(&mut document, req, &mut protected, &mut judge)?;
    }
    let mut edits = document.plan(&req.text)?;
    if req.mode != Mode::Fix {
        edits = crate::wording::phrases(&req.text, edits, &protected);
    }
    let (text, source_map) = apply_edits(&req.text, &edits)?;
    if text != document.text() {
        return Err("The composed edit plan is inconsistent.".into());
    }
    // The grammar model's corrections ride on top of the rules' plan (Fix mode only).
    #[cfg(feature = "local-model")]
    let (text, source_map, edits) = if req.gec && req.mode == Mode::Fix {
        let mut merged = crate::gec::combine(req, &protected, edits.clone());
        // "Yesss" to "Yess": a stretched word may only lose its stretch ("goood" to "good").
        merged.retain(|e| !e.rule_id.starts_with("gector") || stretch_kept(e) && !shorthand(e));
        match apply_edits(&req.text, &merged) {
            Ok((text, source_map)) => (text, source_map, merged),
            Err(_) => (text, source_map, edits),
        }
    } else {
        (text, source_map, edits)
    };
    // Short-word swaps the whole sentence decides (explicit checks, and typing with Smart grammar on).
    #[cfg(feature = "local-model")]
    let (text, source_map, edits) = if req.mode == Mode::Fix && (req.gec || req.deep) {
        crate::confusion::take_pending();
        let mut merged = crate::confusion::combine(req, &protected, edits.clone());
        // "the best day every" to "ever day": Smart grammar's edit beside a word the sentence
        // swap replaced was made for the old word; the swap decides alone.
        let swaps: Vec<(usize, usize)> = merged
            .iter()
            .filter(|e| e.rule_id.starts_with("context."))
            .map(|e| (e.start_utf16, e.end_utf16))
            .collect();
        // "nit: rename this var", "todo: tests": a label opening its line is typed as meant.
        merged.retain(|e| {
            !e.rule_id.starts_with("context.")
                || !byte_at(&req.text, e.end_utf16).is_some_and(|b| {
                    req.text[b..].starts_with(':')
                        && byte_at(&req.text, e.start_utf16).is_some_and(|a| {
                            req.text[..a]
                                .trim_end_matches([' ', '\t', '-', '*'])
                                .ends_with('\n')
                                || req.text[..a]
                                    .trim_start_matches([' ', '\t', '-', '*'])
                                    .is_empty()
                        })
                })
        });
        merged.retain(|e| {
            !e.rule_id.starts_with("gector")
                || !swaps
                    .iter()
                    .any(|&(a, b)| e.start_utf16 <= b + 1 && e.end_utf16 + 1 >= a)
        });
        if crate::confusion::take_pending() {
            warnings.push(PENDING_WARNING.into());
        }
        match apply_edits(&req.text, &merged) {
            Ok((text, source_map)) => (text, source_map, merged),
            Err(_) => (text, source_map, edits),
        }
    } else {
        (text, source_map, edits)
    };
    // Hinglish: Roman Hindi words keep their spelling, and a code-mixed sentence keeps only the
    // rules' spelling, capitalization and punctuation fixes (see `hinglish::screen`).
    #[cfg(feature = "local-model")]
    let mut edits = edits;
    let (text, source_map) = if crate::hinglish::screen(
        &crate::tokenizer::tokenize(&req.text, &req.tokens),
        &mut edits,
    ) {
        apply_edits(&req.text, &edits)?
    } else {
        (text, source_map)
    };
    Ok(RewriteResult {
        version: VERSION.into(),
        text,
        edits,
        source_map,
        elapsed_ms: start.elapsed().as_secs_f64() * 1000.0,
        protected_count: protected.len(),
        warnings,
    })
}
const VERSION: &str = if cfg!(feature = "local-model") {
    concat!(
        "parzr-",
        env!("CARGO_PKG_VERSION"),
        "/hybrid-qwen3.5-0.8b-q5"
    )
} else {
    concat!("parzr-", env!("CARGO_PKG_VERSION"), "/rules-3")
};
/// A tone rewrite: the explicit check corrects the passage first (rules, Smart grammar when on
/// and sentence swaps, without the model's context pass), then the model rewrites the corrected text
/// sentence by sentence under the meaning guard, and the rules check the result once more.
#[cfg(feature = "local-model")]
fn tone(req: &Request, start: Instant) -> Result<RewriteResult, String> {
    // The rules and Smart grammar correct the passage first; the model's own context pass is
    // left out, as the tone model corrects spelling itself. It cost 150 to 450 ms a request, and
    // with a larger model it joined placeholders ("3, PRs") and answered requests in the text.
    let fixed = check(
        &Request {
            mode: Mode::Fix,
            deep: true,
            ..req.clone()
        },
        start,
        false,
    )?;
    let mut warnings = fixed.warnings;
    let mut protected = protected_ranges(req);
    let mut document = Document::new(&req.text);
    document.apply(&fixed.edits)?;
    let mut judge = Judge::new(true, name_score);
    // The model rewrites finished writing too: "is marketing still waiting on the copy" reaches
    // it (and the meaning check) as the question it is, with its capital and question mark.
    let current = document.request(req, &protected, Mode::Fix);
    let floor = crate::tone_format::floor(&current, &current.protected_ranges);
    if !floor.is_empty() {
        document.apply(&floor)?;
        grammar(&mut document, req, &mut protected, &mut judge)?;
    }
    // What the writer is shown if the model's rewrite is withheld: this corrected text, and
    // whatever the mode's own rules do to it below.
    let corrected = document.text();
    // The model gets no instructions about names, so every name candidate is masked.
    let mut masked = protected.clone();
    masked.extend(name_guard_ranges(req));
    // A rewrite the model cannot write safely (it changed protected text, a name or the meaning)
    // leaves the corrected text, with a warning, instead of failing the whole check.
    match crate::model::rewrite(&document.request(req, &masked, req.mode)) {
        Ok(mut contextual) => {
            // The model respells lowercase names the rules left alone ("ritesh's" to "Rish's").
            judge.screen(&document, &mut contextual.edits, &mut protected);
            document.apply(&contextual.edits)?;
            grammar(&mut document, req, &mut protected, &mut judge)?;
            warnings.extend(contextual.warnings);
        }
        Err(error) => warnings.push(format!("Kept the corrected text. {error}")),
    }
    // The rewrite is finished writing, whatever the model managed: never formatted worse than
    // Fix (sentence capitals and a final mark, chat included), and a Professional one spells
    // out chat shorthand. Names and protected text are left as they are.
    let mut fenced = protected.clone();
    fenced.extend(name_guard_ranges(req));
    // The mode's own wording rules (tone.json and the packs scoped to the mode, such as the
    // clarity pack in Concise) say plainly what the model kept padded ("due to the fact that",
    // "on a daily basis"): the same deterministic pass the rules-only build runs.
    let current = document.request(req, &fenced, req.mode);
    let wording = rewrite_once(&current, true)?;
    if !wording.edits.is_empty() {
        document.apply(&wording.edits)?;
        grammar(&mut document, req, &mut protected, &mut judge)?;
    }
    if req.mode == Mode::Professional {
        let current = document.request(req, &fenced, Mode::Fix);
        document.apply(&crate::tone_format::professional_forms(
            &current,
            &current.protected_ranges,
        ))?;
    }
    // A padded opener the model kept ("I wanted to take a moment to let you know that…") is
    // said plainly (Friendly, Concise, Direct).
    let current = document.request(req, &fenced, req.mode);
    document.apply(&crate::tone_format::opener_forms(
        &current,
        &current.protected_ranges,
    ))?;
    let current = document.request(req, &protected, Mode::Fix);
    let floor = crate::tone_format::floor(&current, &current.protected_ranges);
    if !floor.is_empty() {
        document.apply(&floor)?;
        grammar(&mut document, req, &mut protected, &mut judge)?;
    }
    // Direct asks for an action plainly ("Hey, can you send me the file?" is "Send me the
    // file."): the model mostly keeps a polite request as it is.
    if req.mode == Mode::Direct {
        let current = document.request(req, &fenced, Mode::Fix);
        let direct = crate::tone_format::direct_forms(&current, &current.protected_ranges);
        if !direct.is_empty() {
            document.apply(&direct)?;
            grammar(&mut document, req, &mut protected, &mut judge)?;
        }
    }
    // A withheld rewrite is reported to the writer only when the mode did nothing at all ("No safe
    // version"): when its own rules already said it in the tone (chat shorthand spelled out, a
    // padded phrase cut, a request made direct), that text is the version offered.
    if document.text() != corrected {
        warnings.retain(|w| w != crate::model::TONE_WITHHELD);
    }
    let edits = crate::wording::phrases(&req.text, document.plan(&req.text)?, &protected);
    let (text, source_map) = apply_edits(&req.text, &edits)?;
    if text != document.text() {
        return Err("The composed edit plan is inconsistent.".into());
    }
    Ok(RewriteResult {
        version: VERSION.into(),
        text,
        edits,
        source_map,
        elapsed_ms: start.elapsed().as_secs_f64() * 1000.0,
        protected_count: protected.len(),
        warnings,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::cell::Cell;
    thread_local!(static QUERIES: Cell<usize> = const { Cell::new(0) });
    /// Words that start with "zq" are names; everything else is a typo.
    fn fake(text: &str, start: usize, end: usize) -> Option<f32> {
        QUERIES.with(|q| q.set(q.get() + 1));
        Some(if text[start..end].starts_with("zq") {
            1.0
        } else {
            -5.0
        })
    }
    fn queries() -> usize {
        QUERIES.with(Cell::get)
    }
    fn edit(text: &str, original: &str, replacement: &str, category: &str) -> Edit {
        let start = text.find(original).expect("original is in the text");
        Edit {
            start_utf16: text[..start].encode_utf16().count(),
            end_utf16: text[..start + original.len()].encode_utf16().count(),
            replacement: replacement.into(),
            original: original.into(),
            category: category.into(),
            rule_id: "spelling.test".into(),
            explanation: String::new(),
            confidence: 0.8,
            group_id: None,
        }
    }
    fn spelling(text: &str, original: &str, replacement: &str) -> Edit {
        edit(text, original, replacement, "Spelling")
    }

    #[test]
    fn slips_of_frequent_words_never_reach_the_name_judge() {
        let word = |text: &str, original: &str, replacement: &str| {
            judged_word(text, &spelling(text, original, replacement))
        };
        assert_eq!(word("The giirls won.", "giirls", "girls"), None);
        assert_eq!(
            word("refer you to someonse who can", "someonse", "someone"),
            None
        );
        assert_eq!(
            word("I talked to ritesh today", "ritesh", "rites").as_deref(),
            Some("ritesh")
        );
    }
    #[cfg(feature = "local-model")]
    #[test]
    fn stretched_words_only_lose_their_stretch() {
        let gector = |text: &str, original: &str, replacement: &str| {
            let mut e = edit(text, original, replacement, "Grammar");
            e.rule_id = "gector.agreement".into();
            e
        };
        assert!(!stretch_kept(&gector("Yesss we did it!", "Yesss", "Yess")));
        assert!(stretch_kept(&gector("She's goood at it.", "goood", "good")));
        assert!(stretch_kept(&gector("He go home.", "go", "goes")));
    }
    #[cfg(feature = "local-model")]
    #[test]
    fn the_model_fix_pass_keeps_typed_voice() {
        let model = |text: &str, original: &str, replacement: &str| {
            let mut e = edit(text, original, replacement, "Style");
            e.rule_id = "local-model".into();
            e
        };
        let kept = |text: &str, e: Edit| {
            let mut edits = vec![e];
            keep_typed_voice(text, &mut edits);
            edits
        };
        for (text, original, replacement) in [
            ("pls review it", "pls", "Please"),
            ("thx for that", "thx", "Thank"),
            ("lmk if so", "lmk", "LMK"),
            ("How was it??", "?", ""),
            ("Run git pull now.", "git pull", "`git pull`"),
            ("All the best,", ",", "."),
        ] {
            assert!(
                kept(text, model(text, original, replacement)).is_empty(),
                "{text}"
            );
        }
        // "@alex I" to "@alexI": the space after a mention stays.
        let text = "@alex I think so";
        let start = text.find(' ').unwrap();
        let mut e = model(text, " ", "");
        e.start_utf16 = start;
        e.end_utf16 = start + 1;
        assert!(kept(text, e).is_empty());
        // "its" to "it is" becomes "it's"; "it's" to "it is" is dropped.
        let text = "I think its broken";
        let at = text.find("its").unwrap() + 2;
        let mut e = model(text, "s", " is");
        e.start_utf16 = at;
        e.end_utf16 = at + 1;
        let out = kept(text, e);
        assert_eq!(out[0].replacement, "it's");
        let text = "I think it's broken";
        let at = text.find("'s").unwrap();
        let mut e = model(text, "'s", " is");
        e.start_utf16 = at;
        e.end_utf16 = at + 2;
        assert!(kept(text, e).is_empty());
        // "pricing." to "pricing..": no mark doubled beside another.
        let text = "See it. It works";
        let at = text.find('.').unwrap() + 1;
        let mut e = model(text, "See", "See");
        (e.start_utf16, e.end_utf16, e.original, e.replacement) =
            (at, at, String::new(), ".".into());
        assert!(kept(text, e).is_empty());
        // An article added to a commit message, a quote mark, an unknown word made another.
        let text = "Refactor auth middleware";
        let mut e = model(text, "Refactor", "Refactor");
        (e.start_utf16, e.end_utf16, e.original, e.replacement) =
            (9, 9, String::new(), "the ".into());
        assert!(kept(text, e).is_empty());
        let text = "She said that it was fine.";
        assert!(kept(text, model(text, "it", "\"It")).is_empty());
        let text = "Added rwtries to the handler.";
        assert!(kept(text, model(text, "rwtries", "rwtrts")).is_empty());
        // "been waitin' forever" stays.
        let text = "been waitin' forever";
        assert!(kept(text, model(text, "waitin'", "waiting")).is_empty());
        // A real fix still goes through.
        let text = "I has a question";
        assert_eq!(kept(text, model(text, "has", "have")).len(), 1);
    }
    #[test]
    fn only_respelled_unknown_lowercase_words_are_judged() {
        let word = |text: &str, original: &str, replacement: &str| {
            judged_word(text, &spelling(text, original, replacement))
        };
        assert_eq!(
            word("ask zqarav now", "zqarav", "zebra").as_deref(),
            Some("zqarav")
        );
        assert_eq!(
            word("ask zqarav now", "zqarav", "z qarav").as_deref(),
            Some("zqarav")
        );
        assert_eq!(
            word("zqarav's plan", "zqarav's", "zebra's").as_deref(),
            Some("zqarav")
        );
        assert_eq!(
            word("zqarav’s plan", "zqarav’s", "zebra’s").as_deref(),
            Some("zqarav")
        );
        // A known word, a capitalized word, a case-only edit, one letter and a partial token are not.
        assert_eq!(word("I goes home", "goes", "go"), None);
        assert_eq!(word("ask Zqarav now", "Zqarav", "Zebra"), None);
        assert_eq!(word("ask zqarav now", "zqarav", "Zqarav"), None);
        assert_eq!(word("ask q now", "q", "a"), None);
        assert_eq!(word("ask zqarav now", "zqara", "zebra"), None);
        assert_eq!(word("ask zq2rav now", "zq2rav", "zebra"), None);
        let other = edit("ask zqarav now", "zqarav", "zebra", "Grammar");
        assert_eq!(judged_word("ask zqarav now", &other), None);
        // A model respelling is judged whatever category it was described as.
        let mut model = edit("ask zqarav now", "zqarav", "zebra", "Grammar");
        model.rule_id = "local-model".into();
        assert_eq!(
            judged_word("ask zqarav now", &model).as_deref(),
            Some("zqarav")
        );
    }

    #[test]
    fn a_name_is_kept_and_protected_in_original_coordinates() {
        let text = "ok, thx zqarav and recieve it";
        let mut document = Document::new(text);
        // An earlier edit moves everything after it, so the protected range must map back.
        let earlier = edit(text, "ok", "okay", "Spelling");
        document.apply(&[earlier]).unwrap();
        let current = document.text();
        let mut edits = vec![
            spelling(&current, "zqarav", "zebra"),
            spelling(&current, "recieve", "receive"),
        ];
        let mut protected = vec![];
        let mut judge = Judge::new(true, fake);
        judge.screen(&document, &mut edits, &mut protected);
        assert_eq!(edits.len(), 1);
        assert_eq!(edits[0].original, "recieve");
        assert_eq!(protected.len(), 1);
        let (a, b) = (protected[0].start_utf16, protected[0].end_utf16);
        assert_eq!(&text[a..b], "zqarav");
    }

    #[test]
    fn linked_edits_leave_with_the_dropped_name() {
        let text = "zqarav recieve";
        let document = Document::new(text);
        let mut linked = spelling(text, "recieve", "receive");
        linked.group_id = Some("g".into());
        let mut name = spelling(text, "zqarav", "zebra");
        name.group_id = Some("g".into());
        let mut edits = vec![name, linked];
        let mut judge = Judge::new(true, fake);
        judge.screen(&document, &mut edits, &mut vec![]);
        assert!(edits.is_empty());
    }

    #[test]
    fn each_word_is_asked_once_per_request() {
        // "wqzkr" is an unknown word that is not on the always-correct list and no slip of a
        // frequent word, so the judge is consulted.
        let text = "zqarav said zqarav and wqzkr wqzkr";
        let document = Document::new(text);
        let mut judge = Judge::new(true, fake);
        let before = queries();
        for _ in 0..3 {
            let mut edits = vec![
                spelling(text, "zqarav", "zebra"),
                spelling(text, "wqzkr", "work"),
            ];
            judge.screen(&document, &mut edits, &mut vec![]);
            assert_eq!(edits.len(), 1);
        }
        assert_eq!(queries() - before, 2);
    }

    #[test]
    fn queries_stop_at_the_cap_and_later_edits_stay() {
        let words: Vec<String> = (0..JUDGE_CAP + 3)
            .map(|i| format!("zqw{}", "x".repeat(i + 1)))
            .collect();
        let text = words.join(" ");
        let document = Document::new(&text);
        let mut edits: Vec<Edit> = words.iter().map(|w| spelling(&text, w, "fixed")).collect();
        let mut judge = Judge::new(true, fake);
        let before = queries();
        judge.screen(&document, &mut edits, &mut vec![]);
        assert_eq!(queries() - before, JUDGE_CAP);
        // The first JUDGE_CAP words were names and are dropped; the rest were never asked.
        assert_eq!(edits.len(), 3);
    }

    #[test]
    fn a_disabled_judge_never_asks() {
        let text = "zqarav";
        let document = Document::new(text);
        let mut edits = vec![spelling(text, "zqarav", "zebra")];
        let before = queries();
        Judge::new(false, fake).screen(&document, &mut edits, &mut vec![]);
        assert_eq!((edits.len(), queries() - before), (1, 0));
    }

    #[test]
    fn a_failed_query_keeps_the_edit() {
        let text = "zqarav";
        let document = Document::new(text);
        let mut edits = vec![spelling(text, "zqarav", "zebra")];
        Judge::new(true, |_, _, _| None).screen(&document, &mut edits, &mut vec![]);
        assert_eq!(edits.len(), 1);
    }
}
