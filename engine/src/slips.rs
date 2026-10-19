//! The typing-time word-choice slip check: "I hat it" (hate), "better then before" (than), "its
//! late" (it's), "don't loose it" (lose). The candidates are the sentence-swap checker's own
//! (`confusion::sentence_swaps`: keyboard, vowel and one-letter neighbours among frequent words,
//! homophones, contractions); this module only scores them, with a small masked language model
//! (distilroberta-base, 82M parameters, int8 Core ML on the Neural Engine, about 7 ms per batch of
//! eight rows) instead of the 0.6 GB writing model, so a check can run at every word boundary.
//!
//! A word's score is its pseudo-log-likelihood (PLL-word-l2r, Kauf & Ivanova 2023): with the word
//! masked in its sentence, the log-probability of its first sub-token; then, with that token
//! written in and the rest still masked, of the second; and so on. The gain of a swap is the
//! candidate's score less the typed word's, in nats, the sign convention of the writing model's
//! sentence gains. Most short words are one sub-token, so the typed word and all its one-token
//! candidates share one masked row. The decision (threshold, slip cost, margin to the next
//! candidate, one swap per sentence) and every guard (names, quotes, code, the user's words) stay
//! in `confusion`. The model is a downloaded pack (role `slip_model`); without it nothing changes.
use crate::{
    confusion::{Scored, Swap, Unscored, Use},
    gec_text::Bpe,
    model::{self, MlmShape},
};
use std::{
    collections::HashMap,
    path::{Path, PathBuf},
    sync::Mutex,
};

const BOS: i32 = 0;
const PAD: i32 = 1;
const EOS: i32 = 2;
const MASK: i32 = 50264;
/// Rows a sentence may cost: a typing check (about 1 ms a row) and an explicit one.
const TYPING_ROWS: usize = 96;
const EXPLICIT_ROWS: usize = 1024;
/// A word of more sub-tokens than this is not a slip of a common word (the candidates are short).
const MAX_WORD_TOKENS: usize = 6;

/// Where the slip checker's files live: PARZR_SLIP_DIR (development), else the downloaded pack's
/// folder. None while the pack is not on this Mac.
pub fn dir() -> Option<PathBuf> {
    if let Some(dir) = std::env::var_os("PARZR_SLIP_DIR").filter(|d| !d.is_empty()) {
        return Some(PathBuf::from(dir));
    }
    crate::packs::installed("slip_model")
}
/// True when the slip checker is on this Mac (a cheap file check; nothing loads).
pub fn available() -> bool {
    dir().is_some_and(|d| d.join("mlm.mlmodelc").is_dir())
}

struct Slips {
    bpe: Bpe,
}
static MODELS: Mutex<Vec<(PathBuf, Option<&'static Slips>)>> = Mutex::new(Vec::new());
/// The vocabularies of the installed pack (loaded once per folder) and the model's shape once it is
/// resident. None while the pack is missing or the runtime cannot load it.
fn shared() -> Option<(&'static Slips, MlmShape)> {
    let dir = dir()?;
    if !dir.is_dir() {
        return None;
    }
    let mut models = MODELS.lock().unwrap_or_else(|e| e.into_inner());
    if let Some((_, loaded)) = models.iter().find(|(d, _)| *d == dir) {
        // Prepare again: the runtime may have released the model under memory pressure.
        let loaded = (*loaded)?;
        return model::mlm_prepare(&dir).map(|shape| (loaded, shape));
    }
    let shape = model::mlm_prepare(&dir);
    let loaded = shape
        .and_then(|_| load(&dir).ok())
        .map(|s| &*Box::leak(Box::new(s)));
    models.push((dir, loaded));
    Some((loaded?, shape?))
}
fn load(dir: &Path) -> Result<Slips, String> {
    let read =
        |name: &str| std::fs::read_to_string(dir.join(name)).map_err(|e| format!("{name}: {e}"));
    Ok(Slips {
        bpe: Bpe::new(&read("vocab.json")?, &read("merges.txt")?)?,
    })
}
/// Loads everything now so the first check does not pay for it (the app calls this in the background).
pub fn warm() -> bool {
    shared().is_some()
}

/// The scorer `confusion` calls: the gain of each swap, or None for a word the window cannot hold.
pub fn scores(window: &str, swaps: &[Swap], how: Use) -> Result<Scored, Unscored> {
    let (slips, shape) = shared().ok_or(Unscored::Unavailable)?;
    let rows = match how {
        Use::Typing { .. } => TYPING_ROWS,
        Use::Explicit { .. } => EXPLICIT_ROWS,
    };
    let plan = Plan::new(&|t| slips.bpe.encode(t), window, swaps, shape, rows);
    if plan.rows.is_empty() {
        return Ok(Scored {
            gains: vec![None; swaps.len()],
            complete: plan.complete,
        });
    }
    let (ids, positions, targets) = plan.tensors(shape);
    let logp =
        model::mlm_forward(shape, &ids, &positions, &targets).ok_or(Unscored::Unavailable)?;
    Ok(Scored {
        gains: plan.gains(&logp, shape),
        complete: plan.complete,
    })
}

/// One masked row: the window's ids with the word's later sub-tokens masked, the masked position
/// scored, and the token ids to score there (every variant of the word that needs this row).
#[derive(Debug, PartialEq)]
struct Row {
    ids: Vec<i32>,
    position: usize,
    targets: Vec<i32>,
}
/// The rows a window needs, and for each variant of each word the (row, target slot) pairs whose
/// log-probabilities add up to its score.
struct Plan {
    rows: Vec<Row>,
    /// Per swap: the typed word's and the candidate's variant index (None: not scored).
    swaps: Vec<Option<(usize, usize)>>,
    variants: Vec<Vec<(usize, usize)>>,
    complete: bool,
}
impl Plan {
    fn new(
        encode: &dyn Fn(&str) -> Vec<i32>,
        window: &str,
        swaps: &[Swap],
        shape: MlmShape,
        max_rows: usize,
    ) -> Plan {
        let mut plan = Plan {
            rows: vec![],
            swaps: vec![None; swaps.len()],
            variants: vec![],
            complete: true,
        };
        let mut index: HashMap<(Vec<i32>, usize), Vec<usize>> = HashMap::new();
        // Words in the order they appear; each word's typed form and candidates.
        let mut words: Vec<(usize, usize)> = vec![];
        for s in swaps {
            if !words.contains(&(s.start, s.end)) {
                words.push((s.start, s.end));
            }
        }
        for (start, end) in words {
            let Some(typed) = window.get(start..end) else {
                continue;
            };
            let members: Vec<usize> = (0..swaps.len())
                .filter(|&i| (swaps[i].start, swaps[i].end) == (start, end))
                .collect();
            let spaced = window[..start].ends_with(' ');
            let left = encode(&straight(&window[..start - usize::from(spaced)]));
            let right = encode(&straight(&window[end..]));
            let middle =
                |w: &str| encode(&straight(&format!("{}{w}", if spaced { " " } else { "" })));
            let mut forms: Vec<(String, Vec<i32>)> = vec![(typed.to_owned(), middle(typed))];
            for &i in &members {
                let c = &swaps[i].candidate;
                if !forms.iter().any(|(w, _)| w == c) {
                    forms.push((c.clone(), middle(c)));
                }
            }
            if forms
                .iter()
                .any(|(_, t)| t.is_empty() || t.len() > MAX_WORD_TOKENS)
            {
                continue;
            }
            // One crop for every form of the word, so they are scored in the same context.
            let longest = forms.iter().map(|(_, t)| t.len()).max().unwrap_or(0);
            let Some((l, r)) = crop(left.len(), longest, right.len(), shape.length - 2) else {
                continue;
            };
            let (left, right) = (&left[left.len() - l..], &right[..r]);
            let before = plan.rows.len();
            let first_variant = plan.variants.len();
            for (_, tokens) in &forms {
                let mut parts = vec![];
                for k in 0..tokens.len() {
                    let mut ids = Vec::with_capacity(shape.length);
                    ids.push(BOS);
                    ids.extend_from_slice(left);
                    ids.extend_from_slice(&tokens[..k]);
                    ids.extend(std::iter::repeat_n(MASK, tokens.len() - k));
                    ids.extend_from_slice(right);
                    ids.push(EOS);
                    let position = 1 + left.len() + k;
                    let target = tokens[k];
                    parts.push(plan.slot(&mut index, ids, position, target, shape.targets));
                }
                plan.variants.push(parts);
            }
            if plan.rows.len() > max_rows {
                // Over budget: drop this word's new rows and leave the rest of the window unscored.
                plan.rows.truncate(before);
                plan.variants.truncate(first_variant);
                index.retain(|_, rows| {
                    rows.retain(|&r| r < before);
                    !rows.is_empty()
                });
                plan.complete = false;
                break;
            }
            for &i in &members {
                let candidate = forms
                    .iter()
                    .position(|(w, _)| *w == swaps[i].candidate)
                    .unwrap_or(0);
                plan.swaps[i] = Some((first_variant, first_variant + candidate));
            }
        }
        plan
    }
    /// The (row, target slot) scoring `target` at `position` of `ids`: an existing row when one
    /// has it or has room, else a new row.
    fn slot(
        &mut self,
        index: &mut HashMap<(Vec<i32>, usize), Vec<usize>>,
        ids: Vec<i32>,
        position: usize,
        target: i32,
        room: usize,
    ) -> (usize, usize) {
        let rows = index.entry((ids.clone(), position)).or_default();
        for &r in rows.iter() {
            if let Some(k) = self.rows[r].targets.iter().position(|&t| t == target) {
                return (r, k);
            }
        }
        if let Some(&r) = rows.last()
            && self.rows[r].targets.len() < room
        {
            self.rows[r].targets.push(target);
            return (r, self.rows[r].targets.len() - 1);
        }
        self.rows.push(Row {
            ids,
            position,
            targets: vec![target],
        });
        rows.push(self.rows.len() - 1);
        (self.rows.len() - 1, 0)
    }
    /// The runtime's flat inputs: ids padded to the model's length, positions, targets padded with
    /// the pad id.
    fn tensors(&self, shape: MlmShape) -> (Vec<i32>, Vec<i32>, Vec<i32>) {
        let mut ids = Vec::with_capacity(self.rows.len() * shape.length);
        let mut targets = Vec::with_capacity(self.rows.len() * shape.targets);
        for row in &self.rows {
            ids.extend_from_slice(&row.ids);
            ids.extend(std::iter::repeat_n(PAD, shape.length - row.ids.len()));
            targets.extend_from_slice(&row.targets);
            targets.extend(std::iter::repeat_n(PAD, shape.targets - row.targets.len()));
        }
        let positions = self.rows.iter().map(|r| r.position as i32).collect();
        (ids, positions, targets)
    }
    /// Each swap's gain (candidate's score less the typed word's) from the rows' log-probabilities.
    fn gains(&self, logp: &[f32], shape: MlmShape) -> Vec<Option<f64>> {
        let score = |v: usize| -> f64 {
            self.variants[v]
                .iter()
                .map(|&(r, k)| f64::from(logp[r * shape.targets + k]))
                .sum()
        };
        self.swaps
            .iter()
            .map(|s| s.map(|(typed, cand)| score(cand) - score(typed)))
            .collect()
    }
}
/// How many tokens of left and right context fit beside a word of `word` tokens in `room` tokens:
/// all of both when they fit, else an even share with the unused part of the shorter side given
/// to the other. None when the word alone does not leave room for context.
fn crop(left: usize, word: usize, right: usize, room: usize) -> Option<(usize, usize)> {
    if word * 2 > room {
        return None;
    }
    if left + word + right <= room {
        return Some((left, right));
    }
    let free = room - word;
    let r = right
        .min(free / 2)
        .max(free.saturating_sub(left))
        .min(right);
    let l = left.min(free - r);
    Some((l, r))
}
/// Curly apostrophes as straight ones, the form the model mostly saw ("it’s" and "it's").
fn straight(text: &str) -> String {
    text.replace('’', "'")
}

#[cfg(test)]
mod tests {
    use super::*;
    const SHAPE: MlmShape = MlmShape {
        batch: 8,
        length: 16,
        targets: 4,
    };
    /// A word-level fake vocabulary: each space-led word is one token, except words marked with a
    /// `+` split in two ("+" itself is not written in the text; "hate" is "ha" + "te").
    fn encode(text: &str) -> Vec<i32> {
        let mut out = vec![];
        for (i, w) in text.split(' ').enumerate() {
            if w.is_empty() {
                continue;
            }
            let spaced = i > 0 || text.starts_with(' ');
            let id = |s: &str| {
                (s.bytes()
                    .fold(7u32, |h, b| h.wrapping_mul(31).wrapping_add(u32::from(b)))
                    % 40_000
                    + 10) as i32
                    + if spaced { 1 } else { 0 }
            };
            if w == "hate" || w == "they're" {
                out.push(id(&w[..2]));
                out.push(id(&w[2..]));
            } else {
                out.push(id(w));
            }
        }
        out
    }
    fn swap(window: &str, word: &str, candidate: &str) -> Swap {
        let start = window.find(word).unwrap();
        Swap {
            start,
            end: start + word.len(),
            candidate: candidate.into(),
            cost: 0.0,
        }
    }
    #[test]
    fn one_token_forms_share_one_masked_row() {
        let w = "I hat it.";
        let swaps = [
            swap(w, "hat", "hit"),
            swap(w, "hat", "had"),
            swap(w, "hat", "hate"),
        ];
        let plan = Plan::new(&encode, w, &swaps, SHAPE, 100);
        // "hat", "hit", "had": one row with three targets; "hate" (two tokens): two more rows.
        assert_eq!(plan.rows.len(), 3);
        assert_eq!(plan.rows[0].targets.len(), 3);
        assert!(
            plan.rows
                .iter()
                .all(|r| r.ids[0] == BOS && *r.ids.last().unwrap() == EOS)
        );
        assert_eq!(plan.rows[0].ids.iter().filter(|&&t| t == MASK).count(), 1);
        assert_eq!(plan.rows[0].ids[plan.rows[0].position], MASK);
        // The two-token form's first row masks both tokens; its second writes the first in.
        assert_eq!(plan.rows[1].ids.iter().filter(|&&t| t == MASK).count(), 2);
        assert_eq!(plan.rows[2].ids.iter().filter(|&&t| t == MASK).count(), 1);
        assert_eq!(plan.rows[2].position, plan.rows[1].position + 1);
        assert!(plan.complete);
    }
    #[test]
    fn gains_are_candidate_score_less_typed_score() {
        let w = "I hat it.";
        let swaps = [swap(w, "hat", "hit"), swap(w, "hat", "hate")];
        let plan = Plan::new(&encode, w, &swaps, SHAPE, 100);
        // Row 0 slots: hat, hit. Rows 1 and 2: the two tokens of "hate".
        let mut logp = vec![0f32; plan.rows.len() * SHAPE.targets];
        logp[0] = -9.0; // hat
        logp[1] = -8.0; // hit
        logp[SHAPE.targets] = -1.5; // "ha" with both masked
        logp[2 * SHAPE.targets] = -0.5; // "te" after "ha"
        let gains = plan.gains(&logp, SHAPE);
        assert!((gains[0].unwrap() - 1.0).abs() < 1e-9);
        assert!((gains[1].unwrap() - 7.0).abs() < 1e-9);
        let (ids, positions, targets) = plan.tensors(SHAPE);
        assert_eq!(ids.len(), plan.rows.len() * SHAPE.length);
        assert_eq!(positions.len(), plan.rows.len());
        assert_eq!(targets.len(), plan.rows.len() * SHAPE.targets);
        assert_eq!(ids[SHAPE.length - 1], PAD);
    }
    #[test]
    fn a_full_row_of_targets_spills_into_another() {
        let w = "on the way";
        let swaps: Vec<Swap> = ["in", "an", "of", "or", "one", "no"]
            .iter()
            .map(|c| swap(w, "on", c))
            .collect();
        let plan = Plan::new(&encode, w, &swaps, SHAPE, 100);
        // Seven one-token forms, four targets per row: two rows with the same ids.
        assert_eq!(plan.rows.len(), 2);
        assert_eq!(plan.rows[0].ids, plan.rows[1].ids);
        assert!(plan.swaps.iter().all(Option::is_some));
    }
    #[test]
    fn long_windows_are_cropped_around_the_word() {
        let w = "one two three four five six seven eight nine ten eleven twelve thirteen fourteen \
                 fifteen sixteen hat seventeen eighteen nineteen twenty";
        let swaps = [swap(w, "hat", "hit")];
        let plan = Plan::new(&encode, w, &swaps, SHAPE, 100);
        assert_eq!(plan.rows.len(), 1);
        let row = &plan.rows[0];
        assert!(row.ids.len() <= SHAPE.length);
        // The mask sits mid-row: context on both sides.
        assert!(row.position > 3 && row.position < row.ids.len() - 4);
        assert_eq!(crop(3, 1, 4, 14), Some((3, 4)));
        assert_eq!(crop(20, 1, 2, 14), Some((11, 2)));
        assert_eq!(crop(2, 1, 20, 14), Some((2, 11)));
        assert_eq!(crop(20, 2, 20, 14), Some((6, 6)));
        assert_eq!(crop(5, 8, 5, 14), None);
    }
    #[test]
    fn the_row_budget_leaves_the_rest_unscored() {
        let w = "on the way to the of";
        let swaps = [
            swap(w, "on", "in"),
            swap(w, "way", "was"),
            swap(w, "of", "if"),
        ];
        let plan = Plan::new(&encode, w, &swaps, SHAPE, 2);
        assert!(!plan.complete);
        assert_eq!(plan.rows.len(), 2);
        assert_eq!(plan.swaps[2], None);
        assert!(plan.swaps[0].is_some() && plan.swaps[1].is_some());
    }
    #[test]
    fn curly_apostrophes_and_sentence_starts_tokenize_like_the_model_saw() {
        let w = "Its late";
        let swaps = [swap(w, "Its", "It’s")];
        let plan = Plan::new(&encode, w, &swaps, SHAPE, 100);
        assert_eq!(plan.rows.len(), 1);
        // No space before the first word: its token is the unspaced one.
        assert_eq!(plan.rows[0].targets[0], encode("Its")[0]);
        assert_eq!(plan.rows[0].targets[1], encode("It's")[0]);
    }
    /// The pack's vocabularies, when a converted model is at hand (PARZR_SLIP_DIR or dist/slips-build).
    fn real_bpe() -> Option<Bpe> {
        let dir = dir().unwrap_or_else(|| {
            Path::new(env!("CARGO_MANIFEST_DIR")).join("../dist/slips-build/slips")
        });
        load(&dir).ok().map(|s| s.bpe)
    }
    #[test]
    fn running_text_tokenizes_as_roberta_does() {
        let Some(bpe) = real_bpe() else {
            eprintln!("no slip checker vocabulary here: skipped");
            return;
        };
        // Reference ids from the Hugging Face tokenizer of distilroberta-base.
        for (text, ids) in [
            ("I hat it.", vec![100, 3988, 24, 4]),
            (
                "It's better then before, isn't it?",
                vec![243, 18, 357, 172, 137, 6, 965, 75, 24, 116],
            ),
            (
                "Two  spaces and (on) the 3rd.",
                vec![9058, 1437, 5938, 8, 36, 261, 43, 5, 155, 2586, 4],
            ),
            (" they're here", vec![51, 214, 259]),
        ] {
            assert_eq!(bpe.encode(text), ids, "{text}");
        }
    }
    /// Dev harness: PARZR_SLIPS_DEV=in.jsonl:out.jsonl (lines with "id" and "input" or "text") writes,
    /// for every window the checker scores (a sentence and the sentence before, as `confusion` scores
    /// it), every candidate swap with its masked-word gain and the time the window took, for
    /// scripts/eval-slips.py. Needs the native runtime (PARZR_MODEL_RUNTIME) and the model.
    #[test]
    #[ignore = "needs the slip checker and PARZR_SLIPS_DEV"]
    fn slips_dev() {
        use std::io::Write;
        let spec = std::env::var("PARZR_SLIPS_DEV").expect("PARZR_SLIPS_DEV=in:out");
        let (input, output) = spec.split_once(':').expect("in:out");
        assert!(warm(), "the slip checker did not load");
        let mut out = std::fs::File::create(output).unwrap();
        for line in std::fs::read_to_string(input).unwrap().lines() {
            let item: serde_json::Value = serde_json::from_str(line).unwrap();
            let text = item["input"].as_str().or(item["text"].as_str()).unwrap();
            let mut rows = vec![];
            let mut previous: Option<usize> = None;
            let mut sentences = 0;
            for (a, b) in crate::gec::pieces(text) {
                let piece = text[a..b].trim_end();
                if piece.is_empty() {
                    continue;
                }
                sentences += 1;
                if piece.len() > 400 {
                    previous = None;
                    continue;
                }
                let from = previous
                    .filter(|&p| !text[p..a].contains('\n') && a + piece.len() - p <= 640)
                    .unwrap_or(a);
                previous = Some(a);
                let window = &text[from..a + piece.len()];
                let swaps: Vec<Swap> = crate::confusion::sentence_swaps(piece, &[])
                    .into_iter()
                    .map(|mut w| {
                        w.start += a - from;
                        w.end += a - from;
                        w
                    })
                    .collect();
                if swaps.is_empty() {
                    continue;
                }
                let started = std::time::Instant::now();
                let scored = scores(window, &swaps, Use::Explicit { budget_ms: 20_000 });
                let ms = started.elapsed().as_secs_f64() * 1000.0;
                let gains = scored.map_or_else(|_| vec![None; swaps.len()], |s| s.gains);
                let list: Vec<_> = swaps
                    .iter()
                    .zip(gains)
                    .map(|(s, g)| {
                        serde_json::json!([
                            from + s.start,
                            from + s.end,
                            &window[s.start..s.end],
                            s.candidate,
                            s.cost,
                            g
                        ])
                    })
                    .collect();
                rows.push(
                    serde_json::json!({"window": [from, a + piece.len()], "ms": ms, "swaps": list}),
                );
            }
            let record =
                serde_json::json!({"id": item["id"], "sentences": sentences, "rows": rows});
            writeln!(out, "{record}").unwrap();
        }
    }
}
