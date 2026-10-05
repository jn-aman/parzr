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
        let mut starts = HashMap::new();
        let mut ends = HashMap::new();
        let mut offset = 0;
        for c in &self.cells {
            if let Some((a, b)) = c.origin {
                starts.insert(a, offset);
                ends.insert(b, offset + c.ch.len_utf16());
            }
            offset += c.ch.len_utf16();
        }
        let remap = |a: usize, b: usize| -> Option<(usize, usize)> {
            let x = *starts.get(&a)?;
            let y = *ends.get(&b)?;
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
            }));
        req
    }
    fn apply(&mut self, edits: &[Edit]) -> Result<(), String> {
        let mut boundaries = HashMap::new();
        let mut offset = 0;
        for (i, c) in self.cells.iter().enumerate() {
            boundaries.insert(offset, i);
            offset += c.ch.len_utf16();
        }
        boundaries.insert(offset, self.cells.len());
        for edit in edits.iter().rev() {
            let a = *boundaries
                .get(&edit.start_utf16)
                .ok_or("Invalid pipeline boundary.")?;
            let b = *boundaries
                .get(&edit.end_utf16)
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
    // Validate the original request before computing or remapping any structural ranges.
    #[allow(unused_mut)]
    let mut initial = req.clone();
    #[cfg(feature = "local-model")]
    {
        initial.mode = Mode::Fix;
    }
    let mut first = rewrite_once(&initial, false)?.edits;
    let mut protected = protected_ranges(req);
    let mut document = Document::new(&req.text);
    // Explicit checks and tone modes ask the model about words the rules would respell; the
    // automatic path stays model-free.
    let mut judge = Judge::new(
        cfg!(feature = "local-model") && (req.mode != Mode::Fix || req.deep),
        name_score,
    );
    judge.screen(&document, &mut first, &mut protected);
    document.apply(&first)?;
    grammar(&mut document, req, &mut protected, &mut judge)?;
    #[allow(unused_mut)]
    let mut warnings = vec![];
    #[cfg(feature = "local-model")]
    if req.mode != Mode::Fix || req.deep {
        // The model gets no instructions about names, so every name candidate is masked.
        let mut masked = protected.clone();
        masked.extend(name_guard_ranges(req));
        match crate::model::rewrite(&document.request(req, &masked, req.mode)) {
            Ok(mut contextual) => {
                // The model respells lowercase names the rules left alone ("ritesh's" to "Rish's").
                judge.screen(&document, &mut contextual.edits, &mut protected);
                document.apply(&contextual.edits)?;
                grammar(&mut document, req, &mut protected, &mut judge)?;
            }
            Err(error) if req.mode == Mode::Fix => {
                // Keep verified grammar edits when contextual refinement cannot safely
                // preserve links/mentions. Never report the refinement as successful.
                warnings.push(format!(
                    "Grammar checked; context refinement unavailable. {error}"
                ));
            }
            Err(error) => return Err(error),
        }
    }
    #[cfg(not(feature = "local-model"))]
    if req.mode != Mode::Fix {
        let tone = rewrite_once(&document.request(req, &protected, req.mode), true)?;
        document.apply(&tone.edits)?;
        grammar(&mut document, req, &mut protected, &mut judge)?;
    }
    let edits = document.plan(&req.text)?;
    let (text, source_map) = apply_edits(&req.text, &edits)?;
    if text != document.text() {
        return Err("The composed edit plan is inconsistent.".into());
    }
    Ok(RewriteResult {
        version: if cfg!(feature = "local-model") {
            "parzr-0.1.0/hybrid-qwen3.5-0.8b-q5"
        } else {
            "parzr-0.1.0/rules-3"
        }
        .into(),
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
        // "mangaer" is a typo that is not on the always-correct list, so the judge is consulted.
        let text = "zqarav said zqarav and mangaer mangaer";
        let document = Document::new(text);
        let mut judge = Judge::new(true, fake);
        let before = queries();
        for _ in 0..3 {
            let mut edits = vec![
                spelling(text, "zqarav", "zebra"),
                spelling(text, "mangaer", "manager"),
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
