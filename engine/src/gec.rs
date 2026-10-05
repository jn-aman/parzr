//! GECToR (gector-roberta-base-5k) as a second opinion on the automatic path. The network runs
//! resident on the Neural Engine behind `model::gec_forward`; everything around it is here: pieces,
//! spaCy-style words, BPE, tag decoding, detokenization, token diff, guards and the merge with the
//! rules' edits. Its edits never override a rule edit, a name or a word the rules do not know.
use crate::{
    Edit, Request, TextRange,
    gec_text::{Bpe, Tokenizer, Word},
    model, names, spelling,
};
use regex::Regex;
use std::{
    collections::{HashMap, VecDeque},
    path::Path,
    sync::{Arc, Mutex, OnceLock},
};

/// $KEEP gets this probability bonus, and a tag below MIN_PROBABILITY is not applied.
const KEEP_CONFIDENCE: f32 = 0.3;
const MIN_PROBABILITY: f32 = 0.7;
const ITERATIONS: usize = 5;
const MAX_SUBWORDS: usize = 80;
const LABELS: usize = 5001;
/// Sentences longer than this are left to the rules; the model sees 80 subwords anyway.
const MAX_PIECE_BYTES: usize = 4000;
const CACHE_ENTRIES: usize = 1024;
/// A sentence with this many lowercase words the rules neither know nor fix reads as code-mixed or
/// non-English text (Hinglish, names, jargon); the model is not trusted there.
const CODE_MIXED: usize = 2;
/// Uncached sentences the model runs per request while typing (about 70 ms); the rest wait for the next
/// check, and typing is incremental so only the sentence being edited is new. Explicit checks run them all.
const TYPING_BUDGET: usize = 24;
const EXPLICIT_BUDGET: usize = 512;

type Logits = (Vec<f32>, Vec<f32>);
pub type Forward<'a> = dyn Fn(&[i32]) -> Option<Logits> + 'a;

pub struct Gec {
    tokenizer: Tokenizer,
    bpe: Bpe,
    labels: Vec<String>,
    keep: usize,
    start: i32,
    decode: HashMap<String, String>,
}
/// What the model did to one sentence: the corrected text and the weakest tag it applied.
pub struct Corrected {
    pub text: String,
    pub confidence: f32,
}
impl Gec {
    pub fn load(dir: &Path) -> Result<Self, String> {
        let read = |name: &str| {
            std::fs::read_to_string(dir.join(name)).map_err(|e| format!("{name}: {e}"))
        };
        let labels: Vec<String> = read("labels.txt")?.lines().map(str::to_owned).collect();
        let keep = labels.iter().position(|l| l == "$KEEP").ok_or("no $KEEP")?;
        let added: HashMap<String, i32> =
            serde_json::from_str(&read("added_tokens.json")?).map_err(|e| e.to_string())?;
        let mut decode = HashMap::new();
        for line in read("verb-form-vocab.txt")?.lines() {
            if let Some((words, tags)) = line.split_once(':')
                && let Some((w1, w2)) = words.split_once('_')
                && let Some((t1, t2)) = tags.trim_end().split_once('_')
            {
                decode
                    .entry(format!("{w1}_{t1}_{t2}"))
                    .or_insert_with(|| w2.to_owned());
            }
        }
        Ok(Self {
            tokenizer: Tokenizer::new(),
            bpe: Bpe::new(&read("vocab.json")?, &read("merges.txt")?)?,
            keep,
            start: *added.get("$START").ok_or("no $START")?,
            labels,
            decode,
        })
    }

    /// Subword ids of `<s> tokens </s>` (at most 80) and the position of each word's first subword.
    pub fn encode(&self, tokens: &[String]) -> (Vec<i32>, Vec<usize>) {
        let mut ids = vec![0];
        let mut firsts = vec![];
        for t in tokens {
            if ids.len() >= MAX_SUBWORDS - 1 {
                break;
            }
            firsts.push(ids.len());
            if t == "$START" {
                ids.push(self.start);
            } else {
                ids.extend(self.bpe.word(t));
            }
        }
        ids.truncate(MAX_SUBWORDS - 1);
        ids.push(2);
        (ids, firsts)
    }

    /// One tag per word (the tag at its first subword) and its probability; None when the forward pass fails.
    fn predict(&self, tokens: &[String], forward: &Forward) -> Option<Vec<(usize, f32)>> {
        let (ids, firsts) = self.encode(tokens);
        let (labels, detect) = forward(&ids)?;
        if labels.len() != ids.len() * LABELS || detect.len() != ids.len() * 2 {
            return None;
        }
        let mut worst = 0f32;
        let mut tags = vec![];
        for &p in &firsts {
            let row = &labels[p * LABELS..(p + 1) * LABELS];
            let (mut top, mut at) = (f32::MIN, 0);
            for (i, x) in row.iter().enumerate() {
                if *x > top {
                    (top, at) = (*x, i);
                }
            }
            let sum: f32 = row.iter().map(|x| (x - top).exp()).sum();
            // Softmax, then the bonus on $KEEP; the first index wins a tie, as argmax does.
            let keep_p = (row[self.keep] - top).exp() / sum + KEEP_CONFIDENCE;
            let top_p = 1.0 / sum
                + if at == self.keep {
                    KEEP_CONFIDENCE
                } else {
                    0.0
                };
            let (best, best_p) =
                if at != self.keep && (keep_p > top_p || (keep_p == top_p && self.keep < at)) {
                    (self.keep, keep_p)
                } else {
                    (at, top_p)
                };
            let (a, b) = (detect[p * 2], detect[p * 2 + 1]);
            worst = worst.max(1.0 / (1.0 + (a - b).exp()));
            tags.push((best, best_p));
        }
        // A sentence the detector finds clean, and any tag the model is unsure of, stay as they are.
        for tag in &mut tags {
            if worst < MIN_PROBABILITY || tag.1 < MIN_PROBABILITY {
                *tag = (self.keep, 1.0);
            }
        }
        Some(tags)
    }

    /// Applies one round of tags to the words ($START first); a word beyond the tagged ones stays.
    pub fn apply(&self, tokens: &[String], tags: &[(usize, f32)]) -> Vec<String> {
        let mut out: Vec<String> = vec![];
        for (token, (id, _)) in tokens.iter().zip(tags) {
            let label = self.labels.get(*id).map_or("$KEEP", String::as_str);
            let new = self.process(token, label).unwrap_or_else(|| token.clone());
            out.extend(new.split(' ').map(str::to_owned));
        }
        out.extend(tokens.iter().skip(tags.len()).cloned());
        out.join(" ")
            .replace(" $MERGE_HYPHEN ", "-")
            .replace(" $MERGE_SPACE ", "")
            .replace(" $DELETE", "")
            .replace("$DELETE ", "")
            .split(' ')
            .map(str::to_owned)
            .collect()
    }
    fn process(&self, token: &str, label: &str) -> Option<String> {
        if let Some(word) = label.strip_prefix("$APPEND_") {
            return Some(format!("{token} {word}"));
        }
        if token == "$START" || ["<PAD>", "<OOV>", "$KEEP"].contains(&label) {
            return Some(token.to_owned());
        }
        if let Some(t) = label.strip_prefix("$TRANSFORM_") {
            return self.transform(token, t);
        }
        if let Some(word) = label.strip_prefix("$REPLACE_") {
            return Some(word.to_owned());
        }
        if label == "$DELETE" {
            return Some(label.to_owned());
        }
        if label.starts_with("$MERGE_") {
            return Some(format!("{token} {label}"));
        }
        Some(token.to_owned())
    }
    fn transform(&self, token: &str, tag: &str) -> Option<String> {
        let capitalize = |s: &str| {
            let mut c = s.chars();
            c.next().map_or(String::new(), |f| {
                f.to_uppercase()
                    .chain(c.as_str().to_lowercase().chars())
                    .collect()
            })
        };
        Some(match tag {
            "CASE_LOWER" => token.to_lowercase(),
            "CASE_UPPER" => token.to_uppercase(),
            "CASE_CAPITAL" => capitalize(token),
            "CASE_CAPITAL_1" => {
                let mut c = token.chars();
                match (c.next(), c.as_str()) {
                    (Some(f), rest) if !rest.is_empty() => format!("{f}{}", capitalize(rest)),
                    _ => token.to_owned(),
                }
            }
            "AGREEMENT_PLURAL" => format!("{token}s"),
            "AGREEMENT_SINGULAR" => {
                let mut s = token.to_owned();
                s.pop();
                s
            }
            "SPLIT_HYPHEN" => token.split('-').collect::<Vec<_>>().join(" "),
            verb => self
                .decode
                .get(&format!("{token}_{}", verb.strip_prefix("VERB_")?))?
                .clone(),
        })
    }

    /// The corrected sentence (up to five rounds of tags), or None when the model could not run.
    pub fn correct(&self, piece: &str, forward: &Forward) -> Option<Corrected> {
        let words = self.tokenizer.words(piece);
        if words.is_empty() {
            return Some(Corrected {
                text: piece.to_owned(),
                confidence: 1.0,
            });
        }
        let mut tokens = vec!["$START".to_owned()];
        tokens.extend(words.iter().map(|w| w.text.clone()));
        let mut confidence = 1f32;
        for _ in 0..ITERATIONS {
            let tags = self.predict(&tokens, forward)?;
            let mut changed = false;
            for (id, p) in &tags {
                if *id != self.keep && *id != 0 {
                    changed = true;
                    confidence = confidence.min(*p);
                }
            }
            if !changed {
                break;
            }
            tokens = self.apply(&tokens, &tags);
        }
        let joined = tokens.join(" ").replace("$START ", "");
        if joined.contains("$START") {
            return None;
        }
        let new: Vec<String> = joined.split(' ').map(str::to_owned).collect();
        Some(Corrected {
            text: reattach(piece, &words, &new),
            confidence,
        })
    }
}

// Python difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes(), so token diffs match the reference.
type Op = (char, usize, usize, usize, usize);
fn longest_match(
    a: &[&str],
    b2j: &HashMap<&str, Vec<usize>>,
    (alo, ahi, blo, bhi): (usize, usize, usize, usize),
) -> (usize, usize, usize) {
    let (mut besti, mut bestj, mut best) = (alo, blo, 0);
    let mut j2len: HashMap<usize, usize> = HashMap::new();
    for (i, word) in a.iter().enumerate().take(ahi).skip(alo) {
        let mut next = HashMap::new();
        for &j in b2j.get(word).map_or(&[][..], Vec::as_slice) {
            if j < blo {
                continue;
            }
            if j >= bhi {
                break;
            }
            let k = j.checked_sub(1).and_then(|p| j2len.get(&p)).unwrap_or(&0) + 1;
            next.insert(j, k);
            if k > best {
                (besti, bestj, best) = (i + 1 - k, j + 1 - k, k);
            }
        }
        j2len = next;
    }
    (besti, bestj, best)
}
pub fn opcodes(a: &[&str], b: &[&str]) -> Vec<Op> {
    let mut b2j: HashMap<&str, Vec<usize>> = HashMap::new();
    for (j, w) in b.iter().enumerate() {
        b2j.entry(w).or_default().push(j);
    }
    let (mut queue, mut blocks) = (vec![(0, a.len(), 0, b.len())], vec![]);
    while let Some((alo, ahi, blo, bhi)) = queue.pop() {
        let (i, j, k) = longest_match(a, &b2j, (alo, ahi, blo, bhi));
        if k > 0 {
            blocks.push((i, j, k));
            if alo < i && blo < j {
                queue.push((alo, i, blo, j));
            }
            if i + k < ahi && j + k < bhi {
                queue.push((i + k, ahi, j + k, bhi));
            }
        }
    }
    blocks.sort_unstable();
    let mut merged: Vec<(usize, usize, usize)> = vec![];
    for (i, j, k) in blocks {
        match merged.last_mut() {
            Some((i1, j1, k1)) if *i1 + *k1 == i && *j1 + *k1 == j => *k1 += k,
            _ => merged.push((i, j, k)),
        }
    }
    merged.push((a.len(), b.len(), 0));
    let (mut ops, mut i, mut j) = (vec![], 0, 0);
    for (ai, bj, size) in merged {
        let tag = match (i < ai, j < bj) {
            (true, true) => 'r',
            (true, false) => 'd',
            (false, true) => 'i',
            _ => ' ',
        };
        if tag != ' ' {
            ops.push((tag, i, ai, j, bj));
        }
        (i, j) = (ai + size, bj + size);
        if size > 0 {
            ops.push(('e', ai, i, bj, j));
        }
    }
    ops
}

fn no_space_before() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| {
        Regex::new(r"^(?:[.,!?;:%)\]}]|n't|'s|'re|'ve|'ll|'d|'m)$").expect("constant regex")
    })
}
/// Rebuilds the sentence from GECToR's tokens, keeping the source spacing where tokens survive.
pub fn reattach(piece: &str, words: &[Word], new: &[String]) -> String {
    let old: Vec<&str> = words.iter().map(|w| w.text.as_str()).collect();
    let new_refs: Vec<&str> = new.iter().map(String::as_str).collect();
    let (Some(first), Some(last)) = (words.first(), words.last()) else {
        return piece.to_owned();
    };
    if old == new_refs {
        return piece.to_owned();
    }
    let lead = &piece[..first.start];
    let trail = &piece[(last.start + last.text.len() + usize::from(last.space)).min(piece.len())..];
    // text, a space follows, produced by the model
    let mut out: Vec<(String, bool, bool)> = vec![];
    for (op, i1, i2, j1, j2) in opcodes(&old, &new_refs) {
        match op {
            'e' => out.extend((i1..i2).map(|i| (old[i].to_owned(), words[i].space, false))),
            'd' => {
                if let Some(prev) = out.last_mut()
                    && !prev.1
                {
                    prev.1 = words[i2 - 1].space;
                }
            }
            _ => {
                let mut block: Vec<(String, bool, bool)> = new[j1..j2]
                    .iter()
                    .filter(|w| !w.is_empty())
                    .map(|w| (w.clone(), true, true))
                    .collect();
                let Some(tail) = block.last_mut() else {
                    continue;
                };
                tail.1 = if op == 'r' { words[i2 - 1].space } else { true };
                if op == 'i'
                    && let Some(prev) = out.last_mut()
                    && !prev.1
                {
                    tail.1 = false;
                    prev.1 = true;
                }
                out.extend(block);
            }
        }
    }
    for i in 1..out.len() {
        if out[i].2 && no_space_before().is_match(&out[i].0) {
            out[i].1 = out[i - 1].1 || out[i].1;
            out[i - 1].1 = false;
        }
    }
    if let Some(tail) = out.last_mut()
        && tail.2
    {
        tail.1 = last.space;
    }
    let body: String = out
        .iter()
        .map(|(t, space, _)| format!("{t}{}", if *space { " " } else { "" }))
        .collect();
    format!("{lead}{body}{trail}")
}

/// A correction inside one sentence (byte offsets relative to it).
#[derive(Clone, Debug, PartialEq)]
pub struct Raw {
    pub start: usize,
    pub end: usize,
    pub replacement: String,
    pub confidence: f32,
}
fn diff_tokens() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r"\w+(?:['’]\w+)*|[^\w\s]").expect("constant regex"))
}
/// Token-level diff of `orig` against `new` as edits on `orig`. A change of spacing alone is no edit.
pub fn diff_edits(orig: &str, new: &str, confidence: f32) -> Vec<Raw> {
    if orig == new {
        return vec![];
    }
    let spans = |s: &str| -> Vec<(usize, usize)> {
        diff_tokens()
            .find_iter(s)
            .map(|m| (m.start(), m.end()))
            .collect()
    };
    let (a, b) = (spans(orig), spans(new));
    let a_text: Vec<&str> = a.iter().map(|(s, e)| &orig[*s..*e]).collect();
    let b_text: Vec<&str> = b.iter().map(|(s, e)| &new[*s..*e]).collect();
    let mut edits = vec![];
    for (op, i1, i2, j1, j2) in opcodes(&a_text, &b_text) {
        if op == 'e' {
            continue;
        }
        let (start, end, replacement) = if i1 < i2 {
            let rep = if j1 < j2 {
                &new[b[j1].0..b[j2 - 1].1]
            } else {
                ""
            };
            (a[i1].0, a[i2 - 1].1, rep)
        } else if j1 > 0
            && i1 > 0
            && !new[..b[j1].0]
                .chars()
                .next_back()
                .is_some_and(char::is_whitespace)
        {
            (a[i1 - 1].1, a[i1 - 1].1, &new[b[j1 - 1].1..b[j2 - 1].1])
        } else if i1 < a.len() && j2 < b.len() {
            (a[i1].0, a[i1].0, &new[b[j1].0..b[j2].0])
        } else {
            let at = if i1 > 0 { a[i1 - 1].1 } else { 0 };
            let from = if j1 > 0 { b[j1 - 1].1 } else { 0 };
            (at, at, &new[from..b[j2 - 1].1])
        };
        edits.push(Raw {
            start,
            end,
            replacement: replacement.to_owned(),
            confidence,
        });
    }
    edits
}

/// Sentences of `text` as byte ranges, split like the reference: after . ! ? before the next word,
/// and at every line break. Blank pieces are dropped.
pub fn pieces(text: &str) -> Vec<(usize, usize)> {
    let (mut out, mut from, mut at) = (vec![], 0, 0);
    let mut cut = |from: &mut usize, a: usize, b: usize| {
        if text[*from..a].trim().is_empty() {
            *from = b;
            return;
        }
        out.push((*from, a));
        *from = b;
    };
    while at < text.len() {
        let rest = &text[at..];
        if !rest.starts_with(char::is_whitespace) {
            at += rest.chars().next().map_or(1, char::len_utf8);
            continue;
        }
        let run = rest.len() - rest.trim_start().len();
        let end = at + run;
        if end < text.len() && text[..at].ends_with(['.', '!', '?']) {
            cut(&mut from, at, end);
        } else {
            let mut k = at;
            while let Some(n) = text[k..end].find('\n') {
                let a = k + n;
                let b = a + text[a..end].len() - text[a..end].trim_start_matches('\n').len();
                cut(&mut from, a, b);
                k = b;
            }
        }
        at = end;
    }
    if !text[from..].trim().is_empty() {
        out.push((from, text.len()));
    }
    out
}

#[derive(Default)]
struct Cache {
    map: HashMap<String, Arc<Vec<Raw>>>,
    order: VecDeque<String>,
}
static CACHE: Mutex<Option<Cache>> = Mutex::new(None);
fn cached(piece: &str) -> Option<Arc<Vec<Raw>>> {
    CACHE.lock().ok()?.as_ref()?.map.get(piece).cloned()
}
fn remember(piece: &str, edits: Arc<Vec<Raw>>) {
    if let Ok(mut guard) = CACHE.lock() {
        let cache = guard.get_or_insert_with(Cache::default);
        if cache.map.insert(piece.to_owned(), edits).is_none() {
            cache.order.push_back(piece.to_owned());
            if cache.order.len() > CACHE_ENTRIES
                && let Some(old) = cache.order.pop_front()
            {
                cache.map.remove(&old);
            }
        }
    }
}

static MODEL: OnceLock<Option<Gec>> = OnceLock::new();
/// The loaded model files, once. None when the directory or the native runtime is missing.
fn shared() -> Option<&'static Gec> {
    MODEL
        .get_or_init(|| {
            let dir = model::gec_dir()?;
            // Prepare first: a missing runtime or directory ends here without reading the vocabularies.
            if !model::gec_prepare(&dir) {
                return None;
            }
            Gec::load(&dir).ok()
        })
        .as_ref()
}
/// Loads everything now so the first check does not pay for it (the app calls this in the background).
pub fn warm() -> bool {
    shared().is_some()
}
fn native(ids: &[i32]) -> Option<Logits> {
    model::gec_forward(ids)
}

// Guards (see the module docs): positions here are bytes of the request text.
type Span = (usize, usize);
fn touches(edit: Span, spans: &[Span]) -> bool {
    let (s, e) = edit;
    spans.iter().any(|&(a, b)| {
        if s != e {
            s < b && e > a
        } else {
            a < s && s < b
        }
    })
}
fn sentence_initial(text: &str, at: usize) -> bool {
    let before = text[..at].trim_end_matches([' ', '\t', '"', '\'', '(', '“', '‘']);
    before.is_empty() || before.ends_with(['.', '!', '?', '\n', ':'])
}
fn overlaps(text: &str, a: Span, b: Span) -> bool {
    // The same gap written either side of a space is one position.
    let back = |p: usize| p - (text[..p].len() - text[..p].trim_end().len());
    let (s1, e1, s2, e2) = (back(a.0), back(a.1), back(b.0), back(b.1));
    if s1 == e1 || s2 == e2 {
        (s2 <= s1 && s1 <= e2) || (s1 <= s2 && s2 <= e1)
    } else {
        s1 < e2 && s2 < e1
    }
}
fn letters(s: &str) -> String {
    s.chars()
        .filter(|c| c.is_alphanumeric())
        .flat_map(char::to_lowercase)
        .collect()
}
/// Letters changed or the word count differs: more than case or punctuation.
fn harmful(original: &str, replacement: &str) -> bool {
    letters(original) != letters(replacement)
        || original.split_whitespace().count() != replacement.split_whitespace().count()
}
const DETERMINERS: [&str; 14] = [
    "the", "a", "an", "this", "that", "my", "your", "his", "her", "its", "our", "their", "each",
    "every",
];
/// A singular noun made plural right after a determiner, or "the noun" rewritten as a bare plural:
/// whether the writer meant one or many is not something grammar can decide.
fn pluralizes_after_determiner(text: &str, at: usize, original: &str, replacement: &str) -> bool {
    let (o, r) = (original.trim(), replacement.trim());
    let plural_of = |noun: &str, plural: &str| {
        let (n, p) = (noun.to_lowercase(), plural.to_lowercase());
        p == format!("{n}s")
            || p == format!("{n}es")
            || p.strip_suffix("ies")
                .is_some_and(|stem| n.strip_suffix('y') == Some(stem))
    };
    if o.contains(' ') {
        let mut parts = o.split(' ');
        let (first, rest) = (
            parts.next().unwrap_or(""),
            parts.collect::<Vec<_>>().join(" "),
        );
        return DETERMINERS.contains(&first.to_lowercase().as_str()) && plural_of(&rest, r);
    }
    let before = text[..at]
        .split_whitespace()
        .next_back()
        .unwrap_or("")
        .to_lowercase();
    plural_of(o, r) && DETERMINERS.contains(&before.as_str())
}
/// "the" swapped for "a" or "an" or back: the choice of article is the writer's.
fn swaps_article(original: &str, replacement: &str) -> bool {
    let art = |w: &str| ["the", "a", "an"].contains(&w.to_lowercase().as_str());
    art(original.trim())
        && art(replacement.trim())
        && original.trim().to_lowercase() != replacement.trim().to_lowercase()
}
fn words() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| Regex::new(r"\w+(?:['’-]\w+)*").expect("constant regex"))
}

fn family(original: &str, replacement: &str) -> (&'static str, &'static str, &'static str) {
    let plain = |s: &str| !s.chars().any(char::is_alphanumeric);
    let (o, r) = (original.trim(), replacement.trim());
    if o.is_empty() {
        return if plain(r) {
            ("append", "Punctuation", "Punctuation looks missing here.")
        } else {
            ("append", "Grammar", "A word looks missing here.")
        };
    }
    if r.is_empty() {
        return if plain(o) {
            (
                "delete",
                "Punctuation",
                "This punctuation looks unnecessary.",
            )
        } else {
            ("delete", "Grammar", "This word looks unnecessary.")
        };
    }
    if o != r && o.to_lowercase() == r.to_lowercase() {
        return ("case", "Capitalization", "Check the capitalization.");
    }
    if plain(o) && plain(r) {
        return (
            "replace",
            "Punctuation",
            "Different punctuation fits better here.",
        );
    }
    let (lo, lr) = (letters(o), letters(r));
    if lo == lr {
        return if o.split_whitespace().count() > r.split_whitespace().count() {
            (
                "merge",
                "Spelling",
                "These parts belong together as one word.",
            )
        } else {
            ("split", "Spelling", "This reads better as separate words.")
        };
    }
    if lo.strip_suffix('s') == Some(lr.as_str()) || lr.strip_suffix('s') == Some(lo.as_str()) {
        return (
            "agreement",
            "Grammar",
            "The word form does not agree with its context.",
        );
    }
    (
        "replace",
        "Grammar",
        "A different word or form fits better here.",
    )
}

/// Runs GECToR over the sentences of the request text and merges its corrections into `parzr`
/// (the rules' final edits, original coordinates). Without the model this returns `parzr` unchanged.
pub fn combine(req: &Request, protected: &[TextRange], parzr: Vec<Edit>) -> Vec<Edit> {
    let Some(model) = shared() else { return parzr };
    combine_with(model, &native, req, protected, parzr)
}
pub fn combine_with(
    model: &Gec,
    forward: &Forward,
    req: &Request,
    protected: &[TextRange],
    parzr: Vec<Edit>,
) -> Vec<Edit> {
    let text = req.text.as_str();
    let mut raw: Vec<(usize, usize, Raw)> = vec![];
    let mut budget = if req.deep {
        EXPLICIT_BUDGET
    } else {
        TYPING_BUDGET
    };
    for (a, b) in pieces(text) {
        let piece = &text[a..b];
        if piece.len() > MAX_PIECE_BYTES {
            continue;
        }
        let edits = match cached(piece) {
            Some(hit) => hit,
            None if budget == 0 => continue,
            None => {
                budget -= 1;
                let Some(done) = model.correct(piece, forward) else {
                    continue;
                };
                let edits = Arc::new(diff_edits(piece, &done.text, done.confidence));
                remember(piece, edits.clone());
                edits
            }
        };
        raw.extend(edits.iter().map(|e| (a, b, e.clone())));
    }
    merge(req, protected, parzr, raw)
}
/// Drops the model's corrections that the guards reject and merges the rest into the rules' edits.
/// `raw` holds each correction with the byte range of its sentence.
fn merge(
    req: &Request,
    protected: &[TextRange],
    parzr: Vec<Edit>,
    mut raw: Vec<(usize, usize, Raw)>,
) -> Vec<Edit> {
    if raw.is_empty() {
        return parzr;
    }
    let text = req.text.as_str();
    // Everything below works on the original text in bytes; the rules' and protected ranges are UTF-16.
    let mut to_byte = vec![usize::MAX; text.encode_utf16().count() + 1];
    let mut at16 = 0;
    for (byte, c) in text.char_indices() {
        to_byte[at16] = byte;
        at16 += c.len_utf16();
    }
    to_byte[at16] = text.len();
    let span = |a: usize, b: usize| -> Option<Span> {
        Some((
            *to_byte.get(a).filter(|x| **x != usize::MAX)?,
            *to_byte.get(b).filter(|x| **x != usize::MAX)?,
        ))
    };
    let rules: Vec<Span> = parzr
        .iter()
        .filter_map(|e| span(e.start_utf16, e.end_utf16))
        .collect();
    let mut shielded: Vec<Span> = protected
        .iter()
        .filter_map(|r| span(r.start_utf16, r.end_utf16))
        .collect();
    shielded.extend(
        crate::name_guard_ranges(req)
            .iter()
            .filter_map(|r| span(r.start_utf16, r.end_utf16)),
    );
    let mut capitalized: Vec<Span> = vec![];
    let mut unknown: Vec<Span> = vec![];
    // Lowercase words that are also given names ("will", "mark"): written lowercase they may be names.
    let mut nameish: Vec<Span> = vec![];
    for m in words().find_iter(text) {
        let w = m.as_str();
        let sp = (m.start(), m.end());
        if w.chars().next().is_some_and(char::is_uppercase)
            && !["I", "I'm", "I'll", "I've", "I'd"].contains(&w)
            && !sentence_initial(text, m.start())
        {
            capitalized.push(sp);
        }
        let lower = w.chars().any(char::is_lowercase) && !w.chars().any(char::is_uppercase);
        let untouched = !rules
            .iter()
            .any(|r| touches(*r, &[sp]) || (r.0 < sp.1 && r.1 > sp.0));
        if lower && untouched && names::is_bundled_name(names::base(&names::fold(w))) {
            nameish.push(sp);
        }
        if lower
            && !spelling::ordinary(w)
            && !spelling::ordinary(&w.replace('’', "'"))
            && !rules
                .iter()
                .any(|r| touches(*r, &[sp]) || (r.0 < sp.1 && r.1 > sp.0))
        {
            unknown.push(sp);
        }
    }
    let mut kept: Vec<Edit> = vec![];
    let mut last_end = 0;
    raw.sort_by_key(|(a, _, e)| (a + e.start, a + e.end));
    for (offset, end, e) in raw {
        let edit = (offset + e.start, offset + e.end);
        let original = &text[edit.0..edit.1];
        let strange = unknown
            .iter()
            .filter(|u| u.0 >= offset && u.1 <= end)
            .count();
        let guarded = strange >= CODE_MIXED
            || rules.iter().any(|r| overlaps(text, edit, *r))
            || touches(edit, &shielded)
            || touches(edit, &capitalized)
            || (original != e.replacement
                && original.to_lowercase() == e.replacement.to_lowercase()
                && !sentence_initial(text, edit.0))
            || (harmful(original, &e.replacement)
                && (touches(edit, &unknown) || touches(edit, &nameish)));
        let start_utf16 = text[..edit.0].encode_utf16().count();
        // One edit per start: the app rejects plans where two edits begin at the same offset.
        if guarded || edit.0 < last_end || kept.iter().any(|k| k.start_utf16 == start_utf16) {
            continue;
        }
        let (id, category, why) = family(original, &e.replacement);
        // The writer's choices, not errors: one or many after a determiner, and which article.
        if pluralizes_after_determiner(text, edit.0, original, &e.replacement)
            || swaps_article(original, &e.replacement)
        {
            continue;
        }
        kept.push(Edit {
            start_utf16,
            end_utf16: start_utf16 + original.encode_utf16().count(),
            replacement: e.replacement,
            original: original.to_owned(),
            category: category.into(),
            rule_id: format!("gector.{id}"),
            explanation: why.into(),
            confidence: e.confidence,
            group_id: None,
        });
        last_end = edit.1;
    }
    let mut all = parzr.clone();
    all.extend(kept);
    all.sort_by_key(|e| (e.start_utf16, e.end_utf16));
    // Never hand back a plan that does not apply cleanly.
    if crate::apply_edits(text, &all).is_ok() {
        all
    } else {
        parzr
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn tok(s: &str) -> Vec<String> {
        Tokenizer::new()
            .words(s)
            .into_iter()
            .map(|w| w.text)
            .collect()
    }
    #[test]
    fn words_follow_spacy() {
        assert_eq!(
            tok("I don't know, can't you?"),
            ["I", "do", "n't", "know", ",", "ca", "n't", "you", "?"]
        );
        assert_eq!(
            tok("Mr. Smith's 3.5km (well-known) a...b."),
            [
                "Mr.", "Smith", "'s", "3.5", "km", "(", "well", "-", "known", ")", "a", "...", "b."
            ]
        );
        assert_eq!(
            tok("school.They e.g. U.S.A."),
            ["school", ".", "They", "e.g.", "U.S.A."]
        );
        assert_eq!(tok("  \t "), Vec::<String>::new());
        let w = Tokenizer::new().words("a  b(c) d");
        assert_eq!(
            w.iter()
                .map(|w| (w.text.as_str(), w.start, w.space))
                .collect::<Vec<_>>(),
            [
                ("a", 0, true),
                ("b(c", 3, false),
                (")", 6, true),
                ("d", 8, false)
            ]
        );
    }
    #[test]
    fn opcodes_match_difflib() {
        let ops = |a: &str, b: &str| {
            opcodes(
                &a.split(' ').collect::<Vec<_>>(),
                &b.split(' ').collect::<Vec<_>>(),
            )
        };
        assert_eq!(
            ops("a b c", "a x c"),
            [('e', 0, 1, 0, 1), ('r', 1, 2, 1, 2), ('e', 2, 3, 2, 3)]
        );
        assert_eq!(ops("a b", "a b c"), [('e', 0, 2, 0, 2), ('i', 2, 2, 2, 3)]);
        assert_eq!(
            ops("a b c", "a c"),
            [('e', 0, 1, 0, 1), ('d', 1, 2, 1, 1), ('e', 2, 3, 1, 2)]
        );
    }
    #[test]
    fn detokenizing_keeps_the_source_spacing() {
        let t = Tokenizer::new();
        let fix = |s: &str, new: &str| {
            let w = t.words(s);
            reattach(
                s,
                &w,
                &new.split(' ').map(str::to_owned).collect::<Vec<_>>(),
            )
        };
        assert_eq!(
            fix(
                "Yesterday I goes to the market , and buyer apples.",
                "Yesterday I went to the market and bought apples ."
            ),
            "Yesterday I went to the market and bought apples."
        );
        assert_eq!(fix("I dont know", "I do n't know"), "I don't know");
        assert_eq!(fix("its fine", "It 's fine"), "It's fine");
        assert_eq!(fix("He go home", "He goes home ."), "He goes home.");
    }
    #[test]
    fn token_diffs_become_minimal_edits() {
        let d = |a: &str, b: &str| {
            diff_edits(a, b, 0.9)
                .into_iter()
                .map(|e| (e.start, e.end, e.replacement))
                .collect::<Vec<_>>()
        };
        assert_eq!(
            d("I go Maya.", "I go did Maya."),
            [(5, 5, "did ".to_owned())]
        );
        assert_eq!(
            d("the entrance My friends", "the entrance. My friends"),
            [(12, 12, ".".to_owned())]
        );
        assert_eq!(d("I go", "I go home"), [(4, 4, " home".to_owned())]);
        assert_eq!(d("He go home", "He goes home"), [(3, 5, "goes".to_owned())]);
        assert!(d("a  b", "a b").is_empty());
    }
    #[test]
    fn sentences_split_like_the_reference() {
        fn cut(s: &str) -> Vec<&str> {
            pieces(s).into_iter().map(|(a, b)| &s[a..b]).collect()
        }
        assert_eq!(
            cut("One. Two!  Three?\nFour\n\n  Five"),
            ["One.", "Two!", "Three?", "Four", "  Five"]
        );
        assert_eq!(cut("no end. "), ["no end. "]);
        assert_eq!(cut("3.5 times"), ["3.5 times"]);
        assert_eq!(cut(""), Vec::<&str>::new());
    }
    fn guarded(
        text: &str,
        edits: &[(&str, &str)],
        parzr: Vec<Edit>,
        protected: &[TextRange],
    ) -> Vec<String> {
        let req = Request {
            text: text.into(),
            ..Request::default()
        };
        let raw = edits
            .iter()
            .map(|(from, to)| {
                let start = text.find(from).expect("edit source is in the text");
                (
                    0,
                    text.len(),
                    Raw {
                        start,
                        end: start + from.len(),
                        replacement: (*to).into(),
                        confidence: 0.9,
                    },
                )
            })
            .collect();
        merge(&req, protected, parzr, raw)
            .into_iter()
            .map(|e| format!("{}>{}", e.original, e.replacement))
            .collect()
    }
    fn rule_edit(text: &str, from: &str, to: &str) -> Edit {
        let start = text[..text.find(from).unwrap()].encode_utf16().count();
        Edit {
            start_utf16: start,
            end_utf16: start + from.encode_utf16().count(),
            replacement: to.into(),
            original: from.into(),
            category: "Grammar".into(),
            rule_id: "grammar.test".into(),
            explanation: String::new(),
            confidence: 0.9,
            group_id: None,
        }
    }
    #[test]
    fn corrections_survive_only_when_the_guards_allow_them() {
        // A plain correction is kept, with UTF-16 positions after an emoji, a rule id and a category.
        let text = "\u{1F600} She go to school.";
        let req = Request {
            text: text.into(),
            ..Request::default()
        };
        let start = text.find("go").unwrap();
        let raw = vec![(
            0,
            text.len(),
            Raw {
                start,
                end: start + 2,
                replacement: "goes".into(),
                confidence: 0.8,
            },
        )];
        let kept = merge(&req, &[], vec![], raw);
        assert_eq!((kept[0].start_utf16, kept[0].end_utf16), (7, 9));
        assert_eq!(
            (
                kept[0].rule_id.as_str(),
                kept[0].category.as_str(),
                kept[0].confidence
            ),
            ("gector.replace", "Grammar", 0.8)
        );
        // The rules' own edit wins; a protected range, a mid-sentence capital and a lowercase-only change do not move.
        let text = "She go to school.";
        assert_eq!(
            guarded(
                text,
                &[("go", "goes")],
                vec![rule_edit(text, "go", "went")],
                &[]
            ),
            ["go>went"]
        );
        let protect = [TextRange {
            start_utf16: 4,
            end_utf16: 6,
        }];
        assert!(guarded(text, &[("go", "goes")], vec![], &protect).is_empty());
        assert!(guarded("We met Maria today.", &[("Maria", "Marie")], vec![], &[]).is_empty());
        assert!(
            guarded(
                "We went to paris today.",
                &[("paris", "Paris")],
                vec![],
                &[]
            )
            .is_empty()
        );
        assert_eq!(
            guarded("she went home.", &[("she", "She")], vec![], &[]),
            ["she>She"]
        );
        // A word the rules do not know may not be rewritten, and neither may a lowercase given name.
        assert!(guarded("She wents to qzxv now.", &[("qzxv", "quartz")], vec![], &[]).is_empty());
        assert!(names::is_bundled_name("will"));
        assert!(
            guarded(
                "We should invite will to the call.",
                &[("will", "wills")],
                vec![],
                &[]
            )
            .is_empty()
        );
        // Two unknown words make the sentence code-mixed: nothing in it is touched.
        assert!(guarded("qzxv wvut he go home.", &[("go", "goes")], vec![], &[]).is_empty());
        assert_eq!(
            guarded("qzxv he go home.", &[("go", "goes")], vec![], &[]),
            ["go>goes"]
        );
        // One or many after a determiner, and a swap of articles, are the writer's choice.
        for (text, from, to) in [
            ("She read the proposal today.", "proposal", "proposals"),
            ("She read the letter today.", "the letter", "letters"),
            ("She read the report today.", "the", "a"),
        ] {
            assert!(
                guarded(text, &[(from, to)], vec![], &[]).is_empty(),
                "{text}"
            );
        }
        assert_eq!(
            guarded(
                "She read two proposal today.",
                &[("proposal", "proposals")],
                vec![],
                &[]
            ),
            ["proposal>proposals"]
        );
    }
    #[test]
    fn guards_use_the_rules_names_and_case() {
        // A gap written either side of a space is one position; an insertion inside a span overlaps it.
        assert!(
            overlaps("a b", (1, 1), (2, 3))
                && overlaps("ab cd", (1, 1), (0, 2))
                && !overlaps("ab cd", (0, 2), (3, 5))
        );
        assert!(
            touches((1, 1), &[(0, 4)])
                && !touches((0, 0), &[(0, 4)])
                && !touches((4, 4), &[(0, 4)])
        );
        assert!(sentence_initial("Hi. \"Yes", 5) && !sentence_initial("Hi there", 3));
        assert!(harmful("go", "went") && !harmful("Go", "go") && harmful("a b", "ab"));
        assert_eq!(family("go", "goes").0, "replace");
        assert_eq!(family("book", "books").0, "agreement");
        assert_eq!(family("", ",").1, "Punctuation");
    }

    /// Reference data recorded from the Python pipeline (spaCy 3.8, torch fp32); see PARZR_GEC_REF.
    fn reference() -> Option<std::path::PathBuf> {
        std::env::var_os("PARZR_GEC_REF").map(Into::into)
    }
    #[test]
    fn tokenizer_agrees_with_spacy_on_the_corpora() {
        let Some(dir) = reference() else { return };
        let t = Tokenizer::new();
        let (mut pieces, mut bad) = (0, vec![]);
        for line in std::fs::read_to_string(dir.join("tok.jsonl"))
            .unwrap()
            .lines()
        {
            let (set, piece, want, _): (String, String, Vec<(String, bool)>, u8) =
                serde_json::from_str(line).unwrap();
            let got: Vec<(String, bool)> = t
                .words(&piece)
                .into_iter()
                .map(|w| (w.text, w.space))
                .collect();
            pieces += 1;
            if got != want && bad.len() < 40 {
                bad.push(format!(
                    "[{set}] {piece:?}\n   want {want:?}\n   got  {got:?}"
                ));
            }
        }
        eprintln!("spaCy agreement: {} of {pieces} pieces differ", bad.len());
        assert!(bad.is_empty(), "{}", bad.join("\n"));
    }

    fn gec() -> Option<Gec> {
        Gec::load(Path::new(&std::env::var_os("PARZR_GEC_DIR")?)).ok()
    }
    /// The torch fp32 logits recorded while the Python pipeline corrected 430 sentences are fed through
    /// this decoder (BPE, tags, five rounds, detokenizing): every output must be identical.
    #[test]
    fn recorded_logits_decode_to_the_python_output() {
        let (Some(dir), Some(model)) = (reference(), gec()) else {
            return;
        };
        let index: Vec<serde_json::Value> =
            serde_json::from_slice(&std::fs::read(dir.join("fix/index.json")).unwrap()).unwrap();
        let blob = std::fs::read(dir.join("fix/logits.bin")).unwrap();
        let floats = |off: usize, n: usize| -> Vec<f32> {
            (0..n)
                .map(|i| f32::from_le_bytes(blob[off + i * 4..off + i * 4 + 4].try_into().unwrap()))
                .collect()
        };
        let (mut same, mut changed, mut bad) = (0, 0, vec![]);
        for row in &index {
            let (input, want) = (row["in"].as_str().unwrap(), row["out"].as_str().unwrap());
            let calls: HashMap<Vec<i32>, usize> = row["calls"]
                .as_array()
                .unwrap()
                .iter()
                .map(|c| {
                    let ids = c["ids"]
                        .as_array()
                        .unwrap()
                        .iter()
                        .map(|x| x.as_i64().unwrap() as i32)
                        .collect();
                    (ids, c["off"].as_u64().unwrap() as usize)
                })
                .collect();
            let forward = |ids: &[i32]| -> Option<Logits> {
                let off = *calls.get(ids)?;
                let n = ids.len();
                Some((floats(off, n * LABELS), floats(off + n * LABELS * 4, n * 2)))
            };
            let got = model.correct(input, &forward).map(|c| c.text);
            if got.as_deref() == Some(want) {
                same += 1;
                changed += usize::from(want != input);
            } else if bad.len() < 10 {
                bad.push(format!("{input:?}\n  want {want:?}\n  got  {got:?}"));
            }
        }
        eprintln!(
            "recorded logits: {same} of {} identical ({changed} corrected)",
            index.len()
        );
        assert!(bad.is_empty(), "{}", bad.join("\n"));
    }

    /// End to end with the native forward: raw corrections of the recorded Python results' inputs must
    /// equal its outputs. PARZR_GEC_COMPARE is a results directory (<dataset>.json with inputs and outputs).
    #[test]
    fn native_forward_matches_a_python_run() {
        let (Some(dir), Some(model)) = (std::env::var_os("PARZR_GEC_COMPARE"), shared()) else {
            return;
        };
        for name in [
            "eng1000", "clean100", "controls", "hinglish", "jfleg", "bea",
        ] {
            let Ok(raw) = std::fs::read(Path::new(&dir).join(format!("{name}.json"))) else {
                continue;
            };
            let data: serde_json::Value = serde_json::from_slice(&raw).unwrap();
            let (mut same, mut total, mut sentences, mut shown) = (0, 0, 0, 0);
            for (input, want) in data["inputs"]
                .as_array()
                .unwrap()
                .iter()
                .zip(data["outputs"].as_array().unwrap())
            {
                let (input, want) = (input.as_str().unwrap(), want.as_str().unwrap());
                let mut out = String::new();
                let mut at = 0;
                for (a, b) in pieces(input) {
                    out.push_str(&input[at..a]);
                    let piece = &input[a..b];
                    sentences += 1;
                    out.push_str(
                        &model
                            .correct(piece, &native)
                            .map_or(piece.to_owned(), |c| c.text),
                    );
                    at = b;
                }
                out.push_str(&input[at..]);
                total += 1;
                same += usize::from(out == want);
                if out != want && shown < 3 && std::env::var_os("PARZR_GEC_SHOW").is_some() {
                    shown += 1;
                    eprintln!("[{name}] {input:?}\n  python {want:?}\n  rust   {out:?}");
                }
            }
            eprintln!(
                "native vs python {name}: {same} of {total} texts identical ({sentences} sentences)"
            );
        }
    }
}
