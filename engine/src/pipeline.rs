//! Grammar → tone → grammar, retaining original scalar anchors for minimal UTF-16 edits.
#[cfg(feature = "local-model")]
use crate::name_guard_ranges;
use crate::{
    Edit, MAX_TEXT_BYTES, Mode, Request, RewriteResult, TextRange, apply_edits, byte_at,
    protected_ranges, rewrite_once,
};
use std::{collections::HashMap, time::Instant};

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

fn grammar(document: &mut Document, req: &Request, protected: &[TextRange]) -> Result<(), String> {
    for _ in 0..6 {
        let pass = rewrite_once(&document.request(req, protected, Mode::Fix), false)?;
        if pass.edits.is_empty() {
            return Ok(());
        }
        document.apply(&pass.edits)?;
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
    let first = rewrite_once(&initial, false)?;
    let protected = protected_ranges(req);
    let mut document = Document::new(&req.text);
    document.apply(&first.edits)?;
    grammar(&mut document, req, &protected)?;
    #[allow(unused_mut)]
    let mut warnings = vec![];
    #[cfg(feature = "local-model")]
    if req.mode != Mode::Fix || req.deep {
        // The model gets no instructions about names, so every name candidate is masked.
        let mut masked = protected.clone();
        masked.extend(name_guard_ranges(req));
        match crate::model::rewrite(&document.request(req, &masked, req.mode)) {
            Ok(contextual) => {
                document.apply(&contextual.edits)?;
                grammar(&mut document, req, &protected)?;
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
        grammar(&mut document, req, &protected)?;
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
