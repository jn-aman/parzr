//! Short-word swaps that only the whole sentence can decide: "I'll be on the office" (in), "Got your
//! note form Priya" (from), "Can you check of the lot is open" (if), "I think the already shipped
//! it" (they), "This as exactly what I wanted" (is). Word pairs cannot tell these apart without
//! false alarms; the bundled language model reads the sentence both ways and the swap is kept only
//! when the sentence with it is far more probable (left and right context, plain text, no prompt).
//!
//! Candidates are systematic, not tuned to examples: a word's neighbours among the ~2,000 most
//! frequent English words by one keyboard-adjacent key, one vowel for another, one letter added or
//! dropped or two adjacent letters swapped, plus a short list of homophones and contractions. Two
//! forms of one word ("year"/"years", "provided"/"provides") and words that fill the same slot
//! ("our"/"your", "he"/"she") are the writer's choice and are never proposed. A slip the fingers
//! rarely make (a vowel for a distant vowel, an extra letter, above all an extra first letter) and a
//! sentence's first word, which has no left context, need a larger gain.
use crate::{Edit, Request, TextRange, real_word, spelling, tokenizer};
use std::{
    collections::{HashMap, VecDeque},
    sync::{
        Mutex, OnceLock,
        atomic::{AtomicBool, Ordering},
        mpsc,
    },
    time::{Duration, Instant},
};

/// A candidate must be at least this frequent (Zipf x 100): about the 2,000 most frequent words.
const FREQUENT: u16 = 467;
/// The typed word must be at least this frequent (Zipf 3): rarer words ("fuser", "crating") are
/// terms or spelling errors, not slips of a common word. Two-letter words must be FREQUENT ("fa",
/// "ta" are abbreviations).
const TYPED_FLOOR: u16 = 300;
/// log P(sentence with the swap) - log P(sentence as typed), in nats, less the slip's cost, at or
/// above which the swap is suggested. Calibrated on the dev set, 3,445 chat and email sentences and a
/// precision probe of 2.4M words of published prose (see the commit log).
pub const THRESHOLD: f64 = 8.0;
/// The best candidate for a word must beat the next one by this much.
const MARGIN: f64 = 0.5;
/// The slip checker's masked-word gain (PLL of the candidate less that of the typed word, in nats,
/// less SLIPS_COST times the slip's cost) at or above which a swap is suggested while typing.
/// Calibrated on dev data only (`slips::tests::slips_dev`, scripts/eval-slips.py): the dev slip sets
/// (held-out dev split, typo-fuzz dev, the everyday regression set, the owner's probe slips and
/// 2,264 clean sentences) and 15,251 sentences of published technical prose. At 5.5 the dev sets
/// give precision 0.94 and 85% of the fixes the candidates can reach, with 0.44 false alarms per
/// 1,000 clean chat sentences and 3.1 per 1,000 sentences of prose; 5.0 catches one more probe slip
/// at 1.5 times the prose false alarms, 6.0 drops four.
pub const SLIPS_THRESHOLD: f64 = 5.5;
const SLIPS_COST: f64 = 0.5;
/// On an explicit check the writing model confirms the slip checker, which may then go lower: a
/// swap it accepts at this threshold stands when the full-sentence gain, less the slip's cost,
/// reaches CONFIRM (the writing model's own threshold still finds swaps alone).
const SLIPS_CONFIRMED_THRESHOLD: f64 = 5.0;
pub const CONFIRM: f64 = 2.0;
/// Extra gain needed for a slip the fingers rarely make: a vowel for a distant vowel ("as" for "is"),
/// an extra letter ("toe" for "to"), an extra first letter ("bits" for "its"); and for a sentence's
/// first word, which the model sees without left context.
const VOWEL_COST: f64 = 2.0;
const EXTRA_COST: f64 = 2.0;
const EXTRA_FIRST_COST: f64 = 3.0;
const START_COST: f64 = 2.0;
/// Non-English function words that are frequent in the corpus through names ("de", "la").
const FOREIGN: &[&str] = &[
    "de", "la", "le", "el", "da", "du", "di", "des", "del", "der", "den", "von",
];
/// A candidate whose first token is this much less likely than the typed one from the left context
/// alone is not worth a full-sentence pass.
pub const SCREEN: f64 = -4.0;
/// The longest a typing check waits for the model. Scoring runs in one background job; a sentence it
/// has not finished by then is ready, from the cache, on a later check.
const TYPING_BUDGET_MS: u32 = 80;
/// The background job's own model budget (one original and one variant decode take ~60-110 ms).
const TYPING_JOB_MS: u32 = 600;
const EXPLICIT_BUDGET_MS: u32 = 4000;
/// Sentences longer than this are not scored (the window is one sentence).
const MAX_PIECE_BYTES: usize = 400;
/// At most this much of the sentence before is scored with a sentence, as context.
const CONTEXT_BYTES: usize = 240;
const CACHE_ENTRIES: usize = 1024;

/// Homophones and contractions that are not one keyboard slip apart.
const HOMOPHONES: &[&[&str]] = &[
    &["to", "too", "two"],
    &["there", "their", "they're"],
    &["your", "you're"],
    &["its", "it's"],
    &["were", "we're", "where", "wear"],
    &["whose", "who's"],
    &["lets", "let's"],
    &["know", "no"],
    &["new", "knew"],
    &["here", "hear"],
    &["by", "buy", "bye"],
    &["right", "write"],
    &["one", "won"],
    &["for", "four"],
    &["our", "hour", "are"],
    &["weather", "whether"],
    &["than", "then"],
    &["whole", "hole"],
    &["week", "weak"],
    &["piece", "peace"],
    &["meet", "meat"],
    &["through", "threw"],
    &["passed", "past"],
    &["accept", "except"],
    &["affect", "effect"],
    &["lose", "loose"],
    &["quite", "quiet"],
    &["who", "how"],
    &["way", "weigh"],
    &["eight", "ate"],
    &["would", "wood"],
    &["sea", "see"],
    &["son", "sun"],
    &["wait", "weight"],
    &["allowed", "aloud"],
    &["break", "brake"],
    &["breaks", "brakes"],
    &["advice", "advise"],
    &["breath", "breathe"],
    &["loss", "lost"],
    &["bare", "bear"],
    &["board", "bored"],
    &["fair", "fare"],
    &["plain", "plane"],
    &["forth", "fourth"],
    &["waist", "waste"],
    &["principal", "principle"],
    &["complement", "compliment"],
    &["council", "counsel"],
    &["weary", "wary"],
    &["personal", "personnel"],
    &["conscience", "conscious"],
    &["choose", "chose"],
    &["later", "latter"],
    &["higher", "hire"],
    &["affects", "effects"],
    &["thorough", "through"],
    &["though", "thought"],
];
const VOWELS: &str = "aeiou";

/// One keyboard-adjacent or vowel-for-vowel substitution, one adjacent transposition, or one letter
/// added or dropped.
fn related(a: &str, b: &str) -> bool {
    let (x, y): (Vec<char>, Vec<char>) = (a.chars().collect(), b.chars().collect());
    if x.len() == y.len() {
        let diff: Vec<usize> = (0..x.len()).filter(|&i| x[i] != y[i]).collect();
        return match diff[..] {
            [i] => {
                real_word::adjacent(x[i], y[i]) || VOWELS.contains(x[i]) && VOWELS.contains(y[i])
            }
            [i, j] => j == i + 1 && x[i] == y[j] && x[j] == y[i],
            _ => false,
        };
    }
    let (short, long) = if x.len() < y.len() {
        (&x, &y)
    } else {
        (&y, &x)
    };
    long.len() == short.len() + 1
        && (0..long.len()).any(|i| long[..i] == short[..i] && long[i + 1..] == short[i..])
}
/// "year"/"years", "use"/"used", "provided"/"provides": one word in two forms, the writer's choice.
/// Every reading of a suffix counts: "codes" is "cod" + "es" or "code" + "s", "removed" is "remov" +
/// "ed" or "remove" + "d", "making" is "mak" + "ing" or "make" less its "e"; "thrown" is "throw" + "n".
fn inflection(a: &str, b: &str) -> bool {
    fn stems(w: &str) -> Vec<String> {
        let mut out = vec![w.to_owned()];
        for s in ["ing", "es", "ed", "s", "d"] {
            if let Some(r) = w.strip_suffix(s).filter(|r| r.len() >= 3) {
                out.push(r.to_owned());
                if s == "ing" {
                    out.push(format!("{r}e"));
                }
            }
        }
        if w.ends_with("wn") && w.len() >= 5 {
            out.push(w[..w.len() - 1].to_owned());
        }
        out
    }
    a.len() >= 3 && b.len() >= 3 && {
        let x = stems(a);
        stems(b).iter().any(|s| x.contains(s))
    }
}
fn homophones(a: &str, b: &str) -> bool {
    HOMOPHONES
        .iter()
        .any(|set| set.contains(&a) && set.contains(&b))
}
/// How much more gain a swap from `word` to `cand` needs than an easy slip (see the costs above).
fn slip_cost(word: &str, cand: &str) -> f64 {
    if homophones(word, cand) {
        return 0.0;
    }
    let (x, y): (Vec<char>, Vec<char>) = (word.chars().collect(), cand.chars().collect());
    if x.len() == y.len() {
        let diff: Vec<usize> = (0..x.len()).filter(|&i| x[i] != y[i]).collect();
        return match diff[..] {
            [i] if !real_word::adjacent(x[i], y[i]) => VOWEL_COST,
            _ => 0.0,
        };
    }
    if x.len() < y.len() {
        0.0
    } else if x[1..] == y[..] {
        EXTRA_FIRST_COST
    } else {
        EXTRA_COST
    }
}
/// Words that stand in for each other in the same slot: "our"/"your", "he"/"she", "this"/"these" all
/// read as written, and which one is meant is the writer's knowledge, not the sentence's.
const SAME_SLOT: &[&[&str]] = &[
    &["my", "your", "our", "his", "her", "their", "its"],
    &["i", "you", "he", "she", "we", "they", "it"],
    &["me", "you", "him", "her", "us", "them", "it"],
    &["this", "that", "these", "those"],
];
fn same_slot(a: &str, b: &str) -> bool {
    SAME_SLOT
        .iter()
        .any(|set| set.contains(&a) && set.contains(&b))
}
/// Every string one edit from `word` (letters a to z).
fn edits(word: &str) -> Vec<String> {
    let chars: Vec<char> = word.chars().collect();
    let mut out = vec![];
    for i in 0..=chars.len() {
        if i < chars.len() {
            out.push(chars[..i].iter().chain(&chars[i + 1..]).collect());
        }
        if i + 1 < chars.len() {
            let mut t = chars.clone();
            t.swap(i, i + 1);
            out.push(t.into_iter().collect());
        }
        for c in 'a'..='z' {
            if i < chars.len() {
                let mut t = chars.clone();
                t[i] = c;
                out.push(t.into_iter().collect());
            }
            let mut t = chars.clone();
            t.insert(i, c);
            out.push(t.into_iter().collect());
        }
    }
    out
}
/// The words `word` (lowercase, straight apostrophe) may have been meant as.
pub fn candidates(word: &str) -> Vec<String> {
    let mut out: Vec<String> = vec![];
    let typed = spelling::frequency(word);
    // "nit: rename this", "pls", "np": chat and code-review shorthand is meant as typed.
    if word.len() >= 2
        && !crate::names::is_shorthand(word)
        && word.bytes().all(|b| b.is_ascii_lowercase())
        && spelling::ordinary(word)
        && typed >= TYPED_FLOOR
        && (word.len() > 2 || typed >= FREQUENT)
    {
        out.extend(edits(word).into_iter().filter(|c| {
            c != word
                && spelling::frequency(c) >= FREQUENT
                && c.len() >= 2
                && spelling::ordinary(c)
                && related(word, c)
        }));
    }
    for set in HOMOPHONES {
        if set.contains(&word) {
            out.extend(set.iter().filter(|w| **w != word).map(|w| (*w).to_owned()));
        }
    }
    out.retain(|c| !inflection(word, c) && !same_slot(word, c) && !FOREIGN.contains(&c.as_str()));
    out.sort();
    out.dedup();
    out
}

/// One proposed swap inside a sentence: byte offsets in the sentence, the replacement as typed and the
/// extra gain it needs (`slip_cost`, plus the sentence-start cost).
#[derive(Clone, Debug, PartialEq)]
pub struct Swap {
    pub start: usize,
    pub end: usize,
    pub candidate: String,
    pub cost: f64,
}
/// How the scorer may use the model: typing never loads or waits for it.
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Use {
    Typing { budget_ms: u32 },
    Explicit { budget_ms: u32 },
}
/// Why a sentence was not scored.
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Unscored {
    /// No runtime, a cold or busy model, or a failure: try again on the next check.
    Unavailable,
    /// The budget ran out before every swap was scored.
    OutOfTime,
}
/// The full-sentence gain of each swap (None: not scored, as when its left context screened it out).
/// A typing check scores only the most promising swaps in one variant decode; `complete` says whether
/// every swap that passed the screen was scored.
pub struct Scored {
    pub gains: Vec<Option<f64>>,
    pub complete: bool,
}
/// A plain function, so a typing check can hand it to the background job.
pub type Scorer = fn(&str, &[Swap], Use) -> Result<Scored, Unscored>;

/// The swaps a sentence's words could take. `skip` holds sentence-relative byte ranges that must stay.
pub fn sentence_swaps(sentence: &str, skip: &[(usize, usize)]) -> Vec<Swap> {
    let tokens = tokenizer::tokenize(sentence, &[]);
    let mut out = vec![];
    for (i, t) in tokens.iter().enumerate() {
        if !t.is_word
            || skip
                .iter()
                .any(|&(a, b)| t.start_byte < b && t.end_byte > a)
        {
            continue;
        }
        let surface = t.surface;
        // Code, paths, handles, hyphenated or glued words and abbreviations keep their word.
        let before = sentence[..t.start_byte].chars().next_back();
        let after = sentence[t.end_byte..].chars().next();
        let free_before = before.is_none_or(|c| c.is_whitespace() || c == '(');
        let free_after = match after {
            None => true,
            Some('.') => sentence[t.end_byte + 1..]
                .chars()
                .next()
                .is_none_or(char::is_whitespace),
            Some(c) => c.is_whitespace() || ",;:!?)".contains(c),
        };
        if !free_before || !free_after {
            continue;
        }
        let lower = surface.to_lowercase().replace('’', "'");
        if surface == "I" || lower.len() < 2 || !lower.is_ascii() {
            continue;
        }
        let capital = surface.chars().any(char::is_uppercase);
        // Only a sentence's first word may be capitalized; elsewhere a capital is a name.
        if capital && (i > 0 || surface.chars().skip(1).any(char::is_uppercase)) {
            continue;
        }
        let curly = surface.contains('’');
        for c in candidates(&lower) {
            let cost = slip_cost(&lower, &c) + if capital { START_COST } else { 0.0 };
            let mut c = if capital { upper_first(&c) } else { c };
            if curly {
                c = c.replace('\'', "’");
            }
            out.push(Swap {
                start: t.start_byte,
                end: t.end_byte,
                candidate: c,
                cost,
            });
        }
    }
    out
}
fn upper_first(s: &str) -> String {
    let mut c = s.chars();
    c.next()
        .map(|f| f.to_uppercase().chain(c).collect())
        .unwrap_or_default()
}
/// How a scorer's gains become a verdict: the gain (less `cost` times the slip's cost) a swap needs,
/// and how far it must beat the word's next candidate.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Decision {
    pub threshold: f64,
    pub cost: f64,
    pub margin: f64,
}
/// The writing model's full-sentence gains.
pub const MODEL: Decision = Decision {
    threshold: THRESHOLD,
    cost: 1.0,
    margin: MARGIN,
};
/// The slip checker's masked-word gains (`slips`), calibrated on the dev sets (see `slips_dev`).
pub const SLIPS: Decision = Decision {
    threshold: SLIPS_THRESHOLD,
    cost: SLIPS_COST,
    margin: MARGIN,
};
/// The same, when the writing model will confirm the swap (explicit checks).
const SLIPS_CONFIRMED: Decision = Decision {
    threshold: SLIPS_CONFIRMED_THRESHOLD,
    ..SLIPS
};
/// The accepted swap of one sentence from the scores: per word the best candidate (gain less its
/// cost), clear of the next and over the threshold; then the single strongest word of the sentence.
#[cfg(test)]
pub fn choose(swaps: &[Swap], gains: &[Option<f64>]) -> Option<(Swap, f64)> {
    choose_with(swaps, gains, MODEL)
}
pub fn choose_with(swaps: &[Swap], gains: &[Option<f64>], d: Decision) -> Option<(Swap, f64)> {
    let mut words: HashMap<(usize, usize), Vec<(f64, &Swap)>> = HashMap::new();
    for (s, g) in swaps.iter().zip(gains) {
        if let Some(g) = g {
            words
                .entry((s.start, s.end))
                .or_default()
                .push((*g - d.cost * s.cost, s));
        }
    }
    let mut best: Option<(Swap, f64)> = None;
    for mut v in words.into_values() {
        v.sort_by(|a, b| b.0.total_cmp(&a.0));
        let (gain, swap) = v[0];
        let next = v.get(1).map_or(0.0, |s| s.0.max(0.0));
        if gain >= d.threshold
            && gain - next >= d.margin
            && best.as_ref().is_none_or(|b| gain > b.1)
        {
            best = Some((swap.clone(), gain));
        }
    }
    best
}

/// The swap a sentence's scores accept, its gain, and which checker found it (the edit's rule).
#[derive(Clone, Debug, PartialEq)]
struct Found {
    swap: Swap,
    gain: f64,
    rule: &'static str,
}
const MODEL_RULE: &str = "context.sentence_swap";
const SLIPS_RULE: &str = "context.slip_swap";
/// A sentence's verdict, and whether every swap that passed the screen was scored (a typing verdict
/// may not be; an explicit check then scores the sentence again).
type Verdict = (Option<Found>, bool);
#[derive(Default)]
struct Cache {
    map: HashMap<String, Verdict>,
    order: VecDeque<String>,
}
static CACHE: Mutex<Option<Cache>> = Mutex::new(None);
fn cached(key: &str) -> Option<Verdict> {
    CACHE.lock().ok()?.as_ref()?.map.get(key).cloned()
}
fn remember(key: &str, verdict: Option<Found>, complete: bool) {
    if let Ok(mut guard) = CACHE.lock() {
        let cache = guard.get_or_insert_with(Cache::default);
        if cache
            .map
            .insert(key.to_owned(), (verdict, complete))
            .is_none()
        {
            cache.order.push_back(key.to_owned());
            if cache.order.len() > CACHE_ENTRIES
                && let Some(old) = cache.order.pop_front()
            {
                cache.map.remove(&old);
            }
        }
    }
}

/// The scorers a check may use: the slip checker (`slips`, a small masked language model on the
/// Neural Engine, cheap enough for every typing check) and the writing model (full-sentence
/// gains). Typing uses the slip checker when it is downloaded, else the writing model; an explicit
/// check uses both, the writing model confirming the slip checker.
#[derive(Clone, Copy)]
pub struct Scorers {
    pub slips: Option<Scorer>,
    pub model: Option<Scorer>,
}
impl Scorers {
    fn model_for(&self, deep: bool) -> Option<Scorer> {
        self.model.filter(|_| deep || self.slips.is_none())
    }
    /// Verdicts of different scorers never stand in for each other in the cache.
    fn key(&self, deep: bool, window: &str) -> String {
        let tag = match (self.slips.is_some(), self.model_for(deep).is_some()) {
            (true, true) => "sm",
            (true, false) => "s",
            _ => "m",
        };
        format!("{tag}\u{0}{window}")
    }
}
/// The rules' (and grammar model's) plan plus the swaps the language models find, which never touch
/// an edit of theirs, a protected range, a name or a user dictionary word.
pub fn combine(req: &Request, protected: &[TextRange], plan: Vec<Edit>) -> Vec<Edit> {
    let scorers = scorers_for(
        req,
        crate::slips::available(),
        // Before the model pack is downloaded there is nothing to wait for: no pending follow-ups.
        crate::model::model_available(),
    );
    if scorers.slips.is_none() && scorers.model.is_none() {
        return plan;
    }
    combine_using(req, protected, plan, scorers)
}
/// The scorers a request may use: the slip checker only when it is installed and the request has not
/// switched it off (`Request::slips`); the writing model whenever it is installed.
fn scorers_for(req: &Request, slips_installed: bool, model_installed: bool) -> Scorers {
    Scorers {
        slips: (req.slips && slips_installed).then_some(crate::slips::scores as Scorer),
        model: model_installed.then_some(native as Scorer),
    }
}
fn found(swaps: &[Swap], gains: &[Option<f64>], d: Decision, rule: &'static str) -> Option<Found> {
    choose_with(swaps, gains, d).map(|(swap, gain)| Found { swap, gain, rule })
}
/// One sentence's verdict from the scorers (see `Scorers`).
fn decide(window: &str, swaps: &[Swap], how: Use, scorers: Scorers) -> Result<Verdict, Unscored> {
    let deep = matches!(how, Use::Explicit { .. });
    let fits = |s: Scored| {
        if s.gains.len() == swaps.len() {
            Ok(s)
        } else {
            Err(Unscored::Unavailable)
        }
    };
    let slips = scorers.slips.map(|f| f(window, swaps, how).and_then(fits));
    let model = scorers
        .model_for(deep)
        .map(|f| f(window, swaps, how).and_then(fits));
    match (slips, model) {
        (Some(s), None) => {
            let s = s?;
            Ok((found(swaps, &s.gains, SLIPS, SLIPS_RULE), s.complete))
        }
        (None, Some(m)) => {
            let m = m?;
            Ok((found(swaps, &m.gains, MODEL, MODEL_RULE), m.complete))
        }
        (Some(s), Some(m)) => match (s, m) {
            (Ok(s), Ok(m)) => {
                if let Some(f) = found(swaps, &m.gains, MODEL, MODEL_RULE) {
                    return Ok((Some(f), m.complete));
                }
                // The slip checker's swap, if the whole sentence reads better with it too.
                let confirmed = found(swaps, &s.gains, SLIPS_CONFIRMED, SLIPS_RULE).filter(|f| {
                    swaps
                        .iter()
                        .zip(&m.gains)
                        .any(|(w, g)| *w == f.swap && g.is_some_and(|g| g - f.swap.cost >= CONFIRM))
                });
                Ok((confirmed, s.complete && m.complete))
            }
            // The writing model is cold, busy or failed: the slip checker alone, and an explicit
            // check scores the sentence again.
            (Ok(s), Err(_)) => Ok((found(swaps, &s.gains, SLIPS, SLIPS_RULE), false)),
            (Err(_), Ok(m)) => Ok((found(swaps, &m.gains, MODEL, MODEL_RULE), false)),
            (Err(e), Err(_)) => Err(e),
        },
        (None, None) => Err(Unscored::Unavailable),
    }
}
/// Scores a sentence and caches its verdict. Explicit checks call it directly; typing runs it in
/// the background job. A cold or busy model leaves the sentence for a later check; a typing job that
/// runs out of time marks the sentence done for typing (explicit checks score it again).
fn score_sentence(window: &str, swaps: &[Swap], how: Use, scorers: Scorers) -> Option<Verdict> {
    let deep = matches!(how, Use::Explicit { .. });
    let verdict = match decide(window, swaps, how, scorers) {
        Ok(verdict) => verdict,
        Err(Unscored::OutOfTime) if !deep => (None, false),
        Err(_) => return None,
    };
    remember(&scorers.key(deep, window), verdict.0.clone(), verdict.1);
    Some(verdict)
}
/// True while the typing job runs: at most one, so typing never queues work on the model.
static JOB: AtomicBool = AtomicBool::new(false);
thread_local! {
    /// Set when a typing check left a sentence for the model (cold, busy or slower than the budget):
    /// the app checks once more shortly, so the swap appears without another keystroke.
    static PENDING: std::cell::Cell<bool> = const { std::cell::Cell::new(false) };
}
/// Whether the last typing check on this thread left model work pending (and clears it).
pub fn take_pending() -> bool {
    PENDING.with(|p| p.replace(false))
}
/// Starts the typing job for one sentence and waits for it at most `wait`.
fn typing_job(window: &str, swaps: Vec<Swap>, scorers: Scorers, wait: Duration) -> Option<Verdict> {
    if JOB.swap(true, Ordering::AcqRel) {
        return None;
    }
    let (send, receive) = mpsc::channel();
    let window = window.to_owned();
    let spawned = std::thread::Builder::new()
        .name("parzr-sentence-swaps".into())
        .spawn(move || {
            let how = Use::Typing {
                budget_ms: TYPING_JOB_MS,
            };
            let verdict = score_sentence(&window, &swaps, how, scorers);
            JOB.store(false, Ordering::Release);
            let _ = send.send(verdict);
        });
    if spawned.is_err() {
        JOB.store(false, Ordering::Release);
        return None;
    }
    receive.recv_timeout(wait).ok().flatten()
}
fn native(sentence: &str, swaps: &[Swap], how: Use) -> Result<Scored, Unscored> {
    crate::model::swap_scores(sentence, swaps, SCREEN, how)
}
/// The writing model's swaps alone, scored by `scorer` (tests and tools).
#[cfg(test)]
pub fn combine_with(
    req: &Request,
    protected: &[TextRange],
    plan: Vec<Edit>,
    scorer: Scorer,
) -> Vec<Edit> {
    let scorers = Scorers {
        slips: None,
        model: Some(scorer),
    };
    combine_using(req, protected, plan, scorers)
}
pub fn combine_using(
    req: &Request,
    protected: &[TextRange],
    plan: Vec<Edit>,
    scorers: Scorers,
) -> Vec<Edit> {
    let text = req.text.as_str();
    let started = Instant::now();
    let total = if req.deep {
        EXPLICIT_BUDGET_MS
    } else {
        TYPING_BUDGET_MS
    };
    // Everything that must stay, as UTF-16 ranges of the request.
    let mut shielded: Vec<TextRange> = protected.to_vec();
    // Every name candidate, even a guess from context ("will", "mark" written lowercase).
    shielded.extend(crate::name_guard_ranges(req));
    shielded.extend(plan.iter().map(|e| TextRange {
        start_utf16: e.start_utf16,
        end_utf16: e.end_utf16,
    }));
    shielded.extend(quoted(text));
    let to16 = |byte: usize| text[..byte].encode_utf16().count();
    let mut added = vec![];
    let mut previous: Option<usize> = None;
    for (a, b) in crate::gec::pieces(text) {
        let piece = text[a..b].trim_end();
        if piece.len() > MAX_PIECE_BYTES || piece.is_empty() {
            previous = None;
            continue;
        }
        // The sentence before, in the same paragraph, is scored as context: "This is so bad. I hat it."
        // gives "hate" twice the gain "I hat it." alone does, where "I hit it" reads just as well.
        let from = previous
            .filter(|&p| {
                !text[p..a].contains('\n') && a + piece.len() - p <= MAX_PIECE_BYTES + CONTEXT_BYTES
            })
            .unwrap_or(a);
        previous = Some(a);
        let window = &text[from..a + piece.len()];
        let shift = a - from;
        let verdict = match cached(&scorers.key(req.deep, window)) {
            Some((hit, complete)) if complete || !req.deep => hit,
            _ => {
                let spent = started.elapsed().as_millis() as u32;
                if spent >= total {
                    continue;
                }
                let swaps: Vec<Swap> = sentence_swaps(piece, &[])
                    .into_iter()
                    .map(|mut w| {
                        w.start += shift;
                        w.end += shift;
                        w
                    })
                    .collect();
                if swaps.is_empty() {
                    remember(&scorers.key(req.deep, window), None, true);
                    continue;
                }
                let verdict = if req.deep {
                    let how = Use::Explicit {
                        budget_ms: total - spent,
                    };
                    score_sentence(window, &swaps, how, scorers)
                } else {
                    let wait = Duration::from_millis(u64::from(total - spent));
                    typing_job(window, swaps, scorers, wait)
                };
                let Some((verdict, complete)) = verdict else {
                    if !req.deep {
                        PENDING.with(|p| p.set(true));
                    }
                    continue;
                };
                if !req.deep && !complete && verdict.is_none() {
                    PENDING.with(|p| p.set(true));
                }
                verdict
            }
        };
        let Some(Found { swap, gain, rule }) = verdict else {
            continue;
        };
        let (s, e) = (to16(from + swap.start), to16(from + swap.end));
        if shielded
            .iter()
            .any(|r| s == r.start_utf16 || (s < r.end_utf16 && e > r.start_utf16))
        {
            continue;
        }
        let original = &text[from + swap.start..from + swap.end];
        // A user dictionary word, and a less common word the text uses more than once ("the fa ...
        // the fa", "the sub"), is a term the writer means.
        let lower = original.to_lowercase();
        let repeated = || {
            text.to_lowercase()
                .split(|c: char| !c.is_alphanumeric() && c != '\'' && c != '’')
                .filter(|w| *w == lower)
                .count()
                >= 2
        };
        if req
            .dictionary
            .iter()
            .any(|w| w.eq_ignore_ascii_case(original))
            || spelling::frequency(&lower) < FREQUENT && repeated()
        {
            continue;
        }
        added.push(Edit {
            start_utf16: s,
            end_utf16: e,
            original: original.to_owned(),
            replacement: swap.candidate.clone(),
            category: "Word choice".into(),
            rule_id: rule.into(),
            explanation: format!(
                "“{}” fits this sentence much better than “{original}”.",
                swap.candidate
            ),
            confidence: if rule == SLIPS_RULE {
                (0.5 + gain / 25.0).min(0.95)
            } else {
                (0.5 + gain / 40.0).min(0.95)
            } as f32,
            group_id: None,
        });
    }
    if added.is_empty() {
        return plan;
    }
    let mut all = plan.clone();
    all.extend(added);
    all.sort_by_key(|e| (e.start_utf16, e.end_utf16));
    if crate::apply_edits(text, &all).is_ok() {
        all
    } else {
        plan
    }
}
/// UTF-16 ranges inside quotation marks: quoted words are someone else's, never respelled.
fn quoted(text: &str) -> Vec<TextRange> {
    static RE: OnceLock<regex::Regex> = OnceLock::new();
    let re = RE.get_or_init(|| {
        regex::Regex::new(r#""[^"\n]{1,200}"|“[^”\n]{1,200}”|(?:^|[\s(])'[^'\n]{1,200}'(?:$|[\s).,!?;:])|‘[^’\n]{1,200}’(?:$|[\s).,!?;:])"#)
            .expect("constant quote regex")
    });
    re.find_iter(text)
        .map(|m| TextRange {
            start_utf16: text[..m.start()].encode_utf16().count(),
            end_utf16: text[..m.end()].encode_utf16().count(),
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    fn has(word: &str, cand: &str) -> bool {
        candidates(word).iter().any(|c| c == cand)
    }
    #[test]
    fn candidates_are_frequent_neighbours_and_homophones() {
        for (w, c) in [
            ("on", "in"),
            ("form", "from"),
            ("of", "if"),
            ("the", "they"),
            ("as", "is"),
            ("it", "at"),
            ("nit", "not"),
            ("wit", "with"),
            ("ear", "year"),
            ("there", "their"),
            ("its", "it's"),
        ] {
            assert!(has(w, c), "{w} -> {c}: {:?}", candidates(w));
        }
        // Inflections and rare words are never proposed; neither is a non-word or a single letter.
        assert!(!has("year", "years"));
        assert!(!has("use", "used"));
        for (w, c) in [
            ("removed", "remove"),
            ("codes", "code"),
            ("sometime", "sometimes"),
            ("creates", "create"),
            ("measure", "measures"),
            ("thrown", "throw"),
        ] {
            assert!(!has(w, c) && !has(c, w), "{w} / {c} are one word");
        }
        assert!(!has("in", "i"));
        assert!(candidates("zzzq").is_empty());
    }
    fn swapped(sentence: &str) -> Vec<String> {
        sentence_swaps(sentence, &[])
            .into_iter()
            .map(|s| format!("{}>{}", &sentence[s.start..s.end], s.candidate))
            .collect()
    }
    #[test]
    fn code_names_and_glued_words_are_never_candidates() {
        assert!(swapped("Got your note form Priya.").contains(&"form>from".to_owned()));
        // Case follows the typed word at a sentence start; a capital elsewhere is a name.
        assert!(swapped("Of course.").iter().any(|s| s.starts_with("Of>")));
        assert!(
            swapped("I met On at noon")
                .iter()
                .all(|s| !s.starts_with("On>"))
        );
        for code in [
            "run os.path.join now",
            "see on-call",
            "ping @on now",
            "x_on_y",
            "on/off",
        ] {
            assert!(
                swapped(code)
                    .iter()
                    .all(|s| !s.starts_with("on>") && !s.starts_with("os>")),
                "{code}: {:?}",
                swapped(code)
            );
        }
    }
    #[test]
    fn one_clear_winner_per_sentence() {
        let s = |start, end, c: &str| Swap {
            start,
            end,
            candidate: c.into(),
            cost: 0.0,
        };
        let swaps = [s(0, 2, "in"), s(0, 2, "an"), s(5, 8, "they")];
        assert_eq!(
            choose(&swaps, &[Some(8.0), Some(-3.0), Some(THRESHOLD + 3.0)]).map(|c| c.0.candidate),
            Some("they".into())
        );
        // Two candidates that fit about as well: the sentence does not say which was meant.
        assert!(choose(&swaps[..2], &[Some(8.0), Some(7.9)]).is_none());
        assert!(choose(&swaps[..1], &[Some(THRESHOLD - 0.1)]).is_none());
        assert!(choose(&swaps[..1], &[None]).is_none());
    }
    fn fake(sentence: &str, swaps: &[Swap], _: Use) -> Result<Scored, Unscored> {
        let good = [("on", "in"), ("form", "from")];
        let gains = swaps
            .iter()
            .map(|s| {
                let pair = (&sentence[s.start..s.end], s.candidate.as_str());
                Some(if good.contains(&pair) { 12.0 } else { -5.0 })
            })
            .collect();
        Ok(Scored {
            gains,
            complete: true,
        })
    }
    fn run(text: &str, dictionary: &[&str], protected: &[TextRange]) -> Vec<(String, String)> {
        let req = Request {
            text: text.into(),
            dictionary: dictionary.iter().map(|w| (*w).to_owned()).collect(),
            deep: true,
            ..Request::default()
        };
        combine_with(&req, protected, vec![], fake)
            .into_iter()
            .map(|e| (e.original, e.replacement))
            .collect()
    }
    #[test]
    fn guards_hold_whatever_the_model_says() {
        let text = "I'll be on the office until 6.";
        assert_eq!(run(text, &[], &[]), [("on".to_owned(), "in".to_owned())]);
        // Quoted text, a protected range and a dictionary word stay as typed.
        assert!(run("He said \"I'll be on the office\" to me.", &[], &[]).is_empty());
        let range = TextRange {
            start_utf16: 8,
            end_utf16: 10,
        };
        assert!(run(text, &[], &[range]).is_empty());
        assert!(run(text, &["on"], &[]).is_empty());
        // No model (cold, busy or out of time): nothing changes.
        let req = Request {
            text: "We'll be on the train.".into(),
            deep: true,
            ..Request::default()
        };
        fn cold(_: &str, _: &[Swap], _: Use) -> Result<Scored, Unscored> {
            Err(Unscored::Unavailable)
        }
        assert!(combine_with(&req, &[], vec![], cold).is_empty());
    }
    /// The slip checker's gains: "hat" to "hate" and "then" to "than" fit far better; "form" to
    /// "from" only a little (under the typing threshold, over the confirmed one).
    fn slips_fake(sentence: &str, swaps: &[Swap], _: Use) -> Result<Scored, Unscored> {
        let good = [("hat", "hate"), ("then", "than")];
        let gains = swaps
            .iter()
            .map(|s| {
                let pair = (&sentence[s.start..s.end], s.candidate.as_str());
                Some(if good.contains(&pair) {
                    SLIPS_THRESHOLD + 4.0
                } else if pair == ("form", "from") {
                    SLIPS_CONFIRMED_THRESHOLD + 0.2
                } else {
                    -6.0
                })
            })
            .collect();
        Ok(Scored {
            gains,
            complete: true,
        })
    }
    /// The writing model agrees about "hate" (above CONFIRM, below its own threshold) and not "than".
    fn model_fake(sentence: &str, swaps: &[Swap], _: Use) -> Result<Scored, Unscored> {
        let gains = swaps
            .iter()
            .map(|s| {
                Some(match (&sentence[s.start..s.end], s.candidate.as_str()) {
                    ("hat", "hate") | ("form", "from") => CONFIRM + 1.0,
                    ("then", "than") => -1.0,
                    ("on", "in") => THRESHOLD + 2.0,
                    _ => -8.0,
                })
            })
            .collect();
        Ok(Scored {
            gains,
            complete: true,
        })
    }
    fn cold(_: &str, _: &[Swap], _: Use) -> Result<Scored, Unscored> {
        Err(Unscored::Unavailable)
    }
    fn verdict(text: &str, how: Use, scorers: Scorers) -> Option<(String, &'static str, bool)> {
        let swaps = sentence_swaps(text, &[]);
        let (found, complete) = decide(text, &swaps, how, scorers).ok()?;
        found.map(|f| (f.swap.candidate, f.rule, complete))
    }
    #[test]
    fn a_request_with_the_slip_check_off_never_asks_the_slip_checker() {
        let on = Request::default();
        assert!(on.slips, "on unless the request says otherwise");
        assert!(scorers_for(&on, true, false).slips.is_some());
        assert!(
            scorers_for(&on, false, false).slips.is_none(),
            "not installed: nothing to ask"
        );
        let off = Request {
            slips: false,
            ..Request::default()
        };
        let scorers = scorers_for(&off, true, true);
        assert!(scorers.slips.is_none(), "switched off: never asked");
        assert!(scorers.model.is_some(), "the writing model is not affected");
        assert!(scorers_for(&off, true, false).slips.is_none());
    }
    #[test]
    fn typing_uses_the_slip_checker_and_explicit_checks_let_the_writing_model_confirm_it() {
        let both = Scorers {
            slips: Some(slips_fake),
            model: Some(model_fake),
        };
        let typing = Use::Typing { budget_ms: 80 };
        let explicit = Use::Explicit { budget_ms: 4000 };
        // While typing the slip checker decides alone (the writing model is never asked).
        let slips_only = Scorers {
            slips: Some(slips_fake),
            model: Some(cold),
        };
        assert_eq!(
            verdict("This is so bad. I hat it.", typing, slips_only),
            Some(("hate".into(), SLIPS_RULE, true))
        );
        assert_eq!(
            verdict("It is better then before.", typing, both),
            Some(("than".into(), SLIPS_RULE, true))
        );
        // On an explicit check the writing model confirms "hate" and overrules "than".
        assert_eq!(
            verdict("This is so bad. I hat it.", explicit, both),
            Some(("hate".into(), SLIPS_RULE, true))
        );
        assert_eq!(verdict("It is better then before.", explicit, both), None);
        // A borderline slip waits for the writing model's confirmation.
        assert_eq!(verdict("Got your note form Priya.", typing, both), None);
        assert_eq!(
            verdict("Got your note form Priya.", explicit, both),
            Some(("from".into(), SLIPS_RULE, true))
        );
        // The writing model still finds what the slip checker does not.
        assert_eq!(
            verdict("I'll be on the office.", explicit, both),
            Some(("in".into(), MODEL_RULE, true))
        );
        // A cold writing model leaves the slip checker's verdict, scored again on the next explicit check.
        assert_eq!(
            verdict("It is better then before.", explicit, slips_only),
            Some(("than".into(), SLIPS_RULE, false))
        );
        // Without the slip checker, typing and explicit checks use the writing model as before.
        let model_only = Scorers {
            slips: None,
            model: Some(model_fake),
        };
        assert_eq!(
            verdict("This is so bad. I hat it.", typing, model_only),
            None
        );
        assert_eq!(
            verdict("I'll be on the office.", typing, model_only),
            Some(("in".into(), MODEL_RULE, true))
        );
        // Verdicts of different scorers never stand in for each other.
        assert_ne!(both.key(false, "x"), both.key(true, "x"));
        assert_eq!(model_only.key(false, "x"), model_only.key(true, "x"));
    }
    #[test]
    fn slip_swaps_keep_every_guard() {
        let run = |text: &str, dictionary: &[&str], names: &[&str], protected: &[TextRange]| {
            let req = Request {
                text: text.into(),
                dictionary: dictionary.iter().map(|w| (*w).to_owned()).collect(),
                names: names.iter().map(|w| (*w).to_owned()).collect(),
                deep: true,
                ..Request::default()
            };
            let scorers = Scorers {
                slips: Some(slips_fake),
                model: None,
            };
            combine_using(&req, protected, vec![], scorers)
                .into_iter()
                .map(|e| (e.original, e.replacement, e.rule_id))
                .collect::<Vec<_>>()
        };
        assert_eq!(
            run("It is better then before.", &[], &[], &[]),
            [("then".into(), "than".into(), SLIPS_RULE.into())]
        );
        // Quoted text, a protected range (code, a link), a dictionary word and a name stay as typed.
        assert!(
            run(
                "He wrote \"it is better then before\" today.",
                &[],
                &[],
                &[]
            )
            .is_empty()
        );
        let range = TextRange {
            start_utf16: 13,
            end_utf16: 17,
        };
        assert!(run("It is better then before.", &[], &[], &[range]).is_empty());
        assert!(run("It is better then before.", &["then"], &[], &[]).is_empty());
        assert!(run("I hat it, said Hat.", &[], &["hat"], &[]).is_empty());
        // Code and paths never offer the word at all.
        assert!(run("run better.then(before) now", &[], &[], &[]).is_empty());
        assert!(run("see ~/then/before.txt", &[], &[], &[]).is_empty());
    }
    #[test]
    fn context_swap_does_not_share_start_with_insertion() {
        fn knew(_: &str, swaps: &[Swap], _: Use) -> Result<Scored, Unscored> {
            Ok(Scored {
                gains: swaps
                    .iter()
                    .map(|swap| (swap.candidate == "knew").then_some(12.0))
                    .collect(),
                complete: true,
            })
        }
        let req = Request {
            text: "That's not fair. He new about it the whole time.".into(),
            deep: true,
            ..Request::default()
        };
        let expected = "That's not fair. He knew about it the whole time.";
        let context_only = combine_with(&req, &[], vec![], knew);
        assert_eq!(context_only.len(), 1);
        assert_eq!(context_only[0].start_utf16, 20);
        assert_eq!(context_only[0].end_utf16, 23);
        assert_eq!(context_only[0].original, "new");
        assert_eq!(context_only[0].replacement, "knew");
        assert_eq!(
            crate::apply_edits(&req.text, &context_only).unwrap().0,
            expected
        );

        let insertion = Edit {
            start_utf16: 20,
            end_utf16: 20,
            original: String::new(),
            replacement: "k".into(),
            category: "Grammar".into(),
            rule_id: "model.grammar".into(),
            explanation: "Insert the missing letter.".into(),
            confidence: 1.0,
            group_id: None,
        };
        let edits = combine_with(&req, &[], vec![insertion], knew);
        assert_eq!(edits.len(), 1, "same-start edits: {edits:?}");
        assert_eq!(edits[0].rule_id, "model.grammar");
        assert_eq!(crate::apply_edits(&req.text, &edits).unwrap().0, expected);
    }
    #[test]
    fn actual_plan_collision_keeps_ungrammatical_model_insertion() {
        let req = Request {
            text: "That's not fair. He new about it the whole time.".into(),
            deep: true,
            ..Request::default()
        };
        let insertion = Edit {
            start_utf16: 20,
            end_utf16: 20,
            original: String::new(),
            replacement: "was ".into(),
            category: "Grammar".into(),
            rule_id: "local-model".into(),
            explanation: "Add “was”.".into(),
            confidence: 1.0,
            group_id: None,
        };
        let edits = combine_with(&req, &[], vec![insertion], |_, swaps, _| {
            Ok(Scored {
                gains: swaps
                    .iter()
                    .map(|swap| (swap.candidate == "knew").then_some(12.0))
                    .collect(),
                complete: true,
            })
        });
        assert_eq!(edits.len(), 1, "same-start edits: {edits:?}");
        assert_eq!(edits[0].rule_id, "local-model");
        assert_eq!(edits[0].replacement, "was ");
        let (text, _) = crate::apply_edits(&req.text, &edits).unwrap();
        assert_eq!(text, "That's not fair. He was new about it the whole time.");
        assert_ne!(text, "That's not fair. He knew about it the whole time.");
    }
    #[test]
    fn typing_never_waits_past_its_budget_and_the_answer_comes_from_the_cache() {
        // The scorer takes far longer than the typing budget (80 ms), so a check that waited for it would take
        // over SLOW; one that kept to its budget returns long before, however busy the machine running the tests.
        const SLOW: Duration = Duration::from_millis(1500);
        fn slow(sentence: &str, swaps: &[Swap], how: Use) -> Result<Scored, Unscored> {
            std::thread::sleep(SLOW);
            fake(sentence, swaps, how)
        }
        let req = Request {
            text: "We'll be on the platform at noon.".into(),
            gec: true,
            ..Request::default()
        };
        // Load the word lists first: their one-time start-up is not the typing budget under test.
        let warm = Request {
            text: "Load the lists once.".into(),
            ..req.clone()
        };
        combine_with(&warm, &[], vec![], fake);
        let started = Instant::now();
        assert!(combine_with(&req, &[], vec![], slow).is_empty());
        assert!(
            started.elapsed() < SLOW / 2,
            "typing waited {:?} for the scorer",
            started.elapsed()
        );
        // The job finishes in the background; a later check reads its verdict.
        let deadline = Instant::now() + Duration::from_secs(10);
        let mut edits = vec![];
        while edits.is_empty() && Instant::now() < deadline {
            std::thread::sleep(Duration::from_millis(50));
            edits = combine_with(&req, &[], vec![], slow);
        }
        assert_eq!(edits.len(), 1);
        assert_eq!(edits[0].replacement, "in");
    }
    /// The typing route end to end without models: the slip check runs in the background job (the
    /// writing model, though present, is never asked while typing), a check it outlasts reports
    /// pending, a follow-up reads the verdict from the cache, and an explicit check of the same
    /// text scores it again with the writing model confirming.
    #[test]
    fn typing_scores_slips_in_the_background_and_a_follow_up_reads_the_verdict() {
        static MODEL_ASKED: AtomicBool = AtomicBool::new(false);
        static SLIPS_RUNS: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);
        // Far over the typing budget (80 ms): a check that waited for the job would take over SLOW.
        const SLOW: Duration = Duration::from_millis(1500);
        fn slow_slips(sentence: &str, swaps: &[Swap], how: Use) -> Result<Scored, Unscored> {
            SLIPS_RUNS.fetch_add(1, Ordering::SeqCst);
            std::thread::sleep(SLOW);
            slips_fake(sentence, swaps, how)
        }
        fn watched_model(sentence: &str, swaps: &[Swap], how: Use) -> Result<Scored, Unscored> {
            MODEL_ASKED.store(true, Ordering::SeqCst);
            model_fake(sentence, swaps, how)
        }
        let scorers = Scorers {
            slips: Some(slow_slips),
            model: Some(watched_model),
        };
        let typing = |text: &str| Request {
            text: text.into(),
            gec: true,
            ..Request::default()
        };
        // Load the word lists first: their one-time start-up is not the budget under test.
        combine_using(&typing("Warm the lists up."), &[], vec![], scorers);
        take_pending();
        let req = typing("Honestly, I really hat waiting.");
        let started = Instant::now();
        let first = combine_using(&req, &[], vec![], scorers);
        assert!(first.is_empty());
        assert!(
            started.elapsed() < SLOW / 2,
            "typing waits for its budget only, not the {:?} job (took {:?})",
            SLOW,
            started.elapsed()
        );
        assert!(take_pending(), "the app is told to look again");
        // Follow-ups (the app's come 900 ms apart) find the verdict once the job is done.
        let deadline = Instant::now() + Duration::from_secs(10);
        let mut edits = vec![];
        while edits.is_empty() && Instant::now() < deadline {
            std::thread::sleep(Duration::from_millis(100));
            take_pending();
            edits = combine_using(&req, &[], vec![], scorers);
        }
        assert_eq!(edits.len(), 1, "a follow-up reads the slip check's verdict");
        assert_eq!(
            (edits[0].replacement.as_str(), edits[0].rule_id.as_str()),
            ("hate", SLIPS_RULE)
        );
        assert!(!take_pending());
        assert!(
            !MODEL_ASKED.load(Ordering::SeqCst),
            "typing never asks the writing model"
        );
        // Once cached, typing checks of the same text do not run the scorer again.
        let runs = SLIPS_RUNS.load(Ordering::SeqCst);
        assert_eq!(combine_using(&req, &[], vec![], scorers).len(), 1);
        assert_eq!(SLIPS_RUNS.load(Ordering::SeqCst), runs);
        // An explicit check does not take the typing verdict: the writing model confirms it.
        let explicit = Request {
            deep: true,
            ..req.clone()
        };
        let confirmed = combine_using(&explicit, &[], vec![], scorers);
        assert!(MODEL_ASKED.load(Ordering::SeqCst));
        assert_eq!(confirmed.len(), 1);
        assert_eq!(confirmed[0].replacement, "hate");
        // A failed or unavailable slip check is never cached as "nothing here".
        fn broken(_: &str, _: &[Swap], _: Use) -> Result<Scored, Unscored> {
            Err(Unscored::Unavailable)
        }
        let unavailable = Scorers {
            slips: Some(broken),
            model: None,
        };
        let text = typing("So I hat it again.");
        let deadline = Instant::now() + Duration::from_secs(2);
        while Instant::now() < deadline {
            assert!(combine_using(&text, &[], vec![], unavailable).is_empty());
            std::thread::sleep(Duration::from_millis(50));
        }
        assert!(cached(&unavailable.key(false, "So I hat it again.")).is_none());
        assert_eq!(combine_using(&text, &[], vec![], scorers).len(), 0);
        let deadline = Instant::now() + Duration::from_secs(5);
        let mut later = vec![];
        while later.is_empty() && Instant::now() < deadline {
            std::thread::sleep(Duration::from_millis(100));
            later = combine_using(&text, &[], vec![], scorers);
        }
        assert_eq!(
            later.len(),
            1,
            "the slip check scores it once it is available"
        );
    }
    /// Latency harness: PARZR_LATENCY=in.jsonl:out.jsonl:typing|explicit times `combine` (the time this
    /// checker adds to a check) on each line's text, back to back, as the app would call it.
    #[test]
    #[ignore = "needs the model runtime and PARZR_LATENCY"]
    fn latency() {
        use std::io::Write;
        let spec = std::env::var("PARZR_LATENCY").expect("PARZR_LATENCY=in:out:mode");
        let mut parts = spec.split(':');
        let (input, output, mode) = (
            parts.next().unwrap(),
            parts.next().unwrap(),
            parts.next().unwrap(),
        );
        // PARZR_LATENCY_GAP_MS: a pause before each check, as between bursts of typing.
        let gap = std::env::var("PARZR_LATENCY_GAP_MS")
            .ok()
            .and_then(|g| g.parse().ok())
            .unwrap_or(0);
        // PARZR_LATENCY_WARMUP_MS: a pause after the first check, so the model is resident (warm numbers).
        let warmup = std::env::var("PARZR_LATENCY_WARMUP_MS")
            .ok()
            .and_then(|g| g.parse().ok())
            .unwrap_or(0);
        let mut out = std::fs::File::create(output).unwrap();
        for (i, line) in std::fs::read_to_string(input).unwrap().lines().enumerate() {
            std::thread::sleep(std::time::Duration::from_millis(if i == 1 {
                warmup
            } else {
                gap
            }));
            let item: serde_json::Value = serde_json::from_str(line).unwrap();
            let text = item["text"].as_str().or(item["input"].as_str()).unwrap();
            let req = Request {
                text: text.into(),
                gec: true,
                deep: mode == "explicit",
                ..Request::default()
            };
            let started = Instant::now();
            let edits = combine(&req, &[], vec![]);
            let ms = started.elapsed().as_secs_f64() * 1000.0;
            let fixes: Vec<_> = edits
                .iter()
                .map(|e| serde_json::json!([e.start_utf16, e.end_utf16, e.replacement]))
                .collect();
            let record = serde_json::json!({"id": item["id"], "ms": ms, "edits": edits.len(), "fixes": fixes});
            writeln!(out, "{record}").unwrap();
        }
    }
    /// Calibration harness: PARZR_CALIBRATE=in.jsonl:out.jsonl (lines with "id" and "text" or "input")
    /// writes every scored swap of every sentence with its full-sentence gain, for threshold curves.
    #[test]
    #[ignore = "needs the model runtime and PARZR_CALIBRATE"]
    fn calibrate() {
        use std::io::Write;
        let spec = std::env::var("PARZR_CALIBRATE").expect("PARZR_CALIBRATE=in:out");
        let (input, output) = spec.split_once(':').expect("in:out");
        let mut out = std::fs::File::create(output).unwrap();
        for line in std::fs::read_to_string(input).unwrap().lines() {
            let item: serde_json::Value = serde_json::from_str(line).unwrap();
            let text = item["text"].as_str().or(item["input"].as_str()).unwrap();
            let mut rows = vec![];
            for (a, b) in crate::gec::pieces(text) {
                let piece = text[a..b].trim_end();
                let swaps = sentence_swaps(piece, &[]);
                if swaps.is_empty() || piece.len() > MAX_PIECE_BYTES {
                    continue;
                }
                let started = Instant::now();
                let how = Use::Explicit { budget_ms: 20_000 };
                let gains = crate::model::swap_scores(piece, &swaps, SCREEN, how);
                let ms = started.elapsed().as_secs_f64() * 1000.0;
                let scored: Vec<_> = swaps
                    .iter()
                    .zip(gains.map_or_else(|_| vec![None; swaps.len()], |s| s.gains))
                    .filter_map(|(s, g)| {
                        Some(serde_json::json!([
                            a + s.start,
                            a + s.end,
                            &piece[s.start..s.end],
                            s.candidate,
                            g?
                        ]))
                    })
                    .collect();
                rows.push(serde_json::json!({"piece": [a, b], "n": swaps.len(), "ms": ms, "swaps": scored}));
            }
            let record = serde_json::json!({"id": item["id"], "rows": rows});
            writeln!(out, "{record}").unwrap();
        }
    }
}
