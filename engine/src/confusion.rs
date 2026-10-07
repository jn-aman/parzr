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
fn inflection(a: &str, b: &str) -> bool {
    fn stem(w: &str) -> &str {
        ["ing", "es", "ed", "s", "d"]
            .iter()
            .find_map(|s| w.strip_suffix(s).filter(|r| r.len() >= 3))
            .unwrap_or(w)
    }
    a.len() >= 3 && b.len() >= 3 && stem(a) == stem(b)
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
    if word.len() >= 2
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
/// The accepted swap of one sentence from the scores: per word the best candidate (gain less its
/// cost), clear of the next and over the threshold; then the single strongest word of the sentence.
pub fn choose(swaps: &[Swap], gains: &[Option<f64>]) -> Option<(Swap, f64)> {
    let mut words: HashMap<(usize, usize), Vec<(f64, &Swap)>> = HashMap::new();
    for (s, g) in swaps.iter().zip(gains) {
        if let Some(g) = g {
            words
                .entry((s.start, s.end))
                .or_default()
                .push((*g - s.cost, s));
        }
    }
    let mut best: Option<(Swap, f64)> = None;
    for mut v in words.into_values() {
        v.sort_by(|a, b| b.0.total_cmp(&a.0));
        let (gain, swap) = v[0];
        let next = v.get(1).map_or(0.0, |s| s.0.max(0.0));
        if gain >= THRESHOLD && gain - next >= MARGIN && best.as_ref().is_none_or(|b| gain > b.1) {
            best = Some((swap.clone(), gain));
        }
    }
    best
}

/// A sentence's verdict, and whether every swap that passed the screen was scored (a typing verdict
/// may not be; an explicit check then scores the sentence again).
type Verdict = (Option<(Swap, f64)>, bool);
#[derive(Default)]
struct Cache {
    map: HashMap<String, Verdict>,
    order: VecDeque<String>,
}
static CACHE: Mutex<Option<Cache>> = Mutex::new(None);
fn cached(sentence: &str) -> Option<Verdict> {
    CACHE.lock().ok()?.as_ref()?.map.get(sentence).cloned()
}
fn remember(sentence: &str, verdict: Option<(Swap, f64)>, complete: bool) {
    if let Ok(mut guard) = CACHE.lock() {
        let cache = guard.get_or_insert_with(Cache::default);
        if cache
            .map
            .insert(sentence.to_owned(), (verdict, complete))
            .is_none()
        {
            cache.order.push_back(sentence.to_owned());
            if cache.order.len() > CACHE_ENTRIES
                && let Some(old) = cache.order.pop_front()
            {
                cache.map.remove(&old);
            }
        }
    }
}

/// The rules' (and grammar model's) plan plus the language model's swaps, which never touch an edit
/// of theirs, a protected range, a name or a user dictionary word.
pub fn combine(req: &Request, protected: &[TextRange], plan: Vec<Edit>) -> Vec<Edit> {
    combine_with(req, protected, plan, native)
}
/// Scores a sentence and caches its verdict. Explicit checks call it directly; typing runs it in
/// the background job. A cold or busy model leaves the sentence for a later check; a typing job that
/// runs out of time marks the sentence done for typing (explicit checks score it again).
fn score_sentence(piece: &str, swaps: &[Swap], how: Use, scorer: Scorer) -> Option<Verdict> {
    let verdict = match scorer(piece, swaps, how) {
        Ok(scored) if scored.gains.len() == swaps.len() => {
            (choose(swaps, &scored.gains), scored.complete)
        }
        Err(Unscored::OutOfTime) if matches!(how, Use::Typing { .. }) => (None, false),
        _ => return None,
    };
    remember(piece, verdict.0.clone(), verdict.1);
    Some(verdict)
}
/// True while the typing job runs: at most one, so typing never queues work on the model.
static JOB: AtomicBool = AtomicBool::new(false);
/// Starts the typing job for one sentence and waits for it at most `wait`.
fn typing_job(piece: &str, swaps: Vec<Swap>, scorer: Scorer, wait: Duration) -> Option<Verdict> {
    if JOB.swap(true, Ordering::AcqRel) {
        return None;
    }
    let (send, receive) = mpsc::channel();
    let piece = piece.to_owned();
    let spawned = std::thread::Builder::new()
        .name("parzr-sentence-swaps".into())
        .spawn(move || {
            let how = Use::Typing {
                budget_ms: TYPING_JOB_MS,
            };
            let verdict = score_sentence(&piece, &swaps, how, scorer);
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
pub fn combine_with(
    req: &Request,
    protected: &[TextRange],
    plan: Vec<Edit>,
    scorer: Scorer,
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
    for (a, b) in crate::gec::pieces(text) {
        let piece = text[a..b].trim_end();
        if piece.len() > MAX_PIECE_BYTES || piece.is_empty() {
            continue;
        }
        let verdict = match cached(piece) {
            Some((hit, complete)) if complete || !req.deep => hit,
            _ => {
                let spent = started.elapsed().as_millis() as u32;
                if spent >= total {
                    continue;
                }
                let swaps = sentence_swaps(piece, &[]);
                if swaps.is_empty() {
                    remember(piece, None, true);
                    continue;
                }
                let verdict = if req.deep {
                    let how = Use::Explicit {
                        budget_ms: total - spent,
                    };
                    score_sentence(piece, &swaps, how, scorer)
                } else {
                    let wait = Duration::from_millis(u64::from(total - spent));
                    typing_job(piece, swaps, scorer, wait)
                };
                let Some((verdict, _)) = verdict else {
                    continue;
                };
                verdict
            }
        };
        let Some((swap, gain)) = verdict else {
            continue;
        };
        let (s, e) = (to16(a + swap.start), to16(a + swap.end));
        if shielded
            .iter()
            .any(|r| s < r.end_utf16 && e > r.start_utf16)
        {
            continue;
        }
        let original = &text[a + swap.start..a + swap.end];
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
            rule_id: "context.sentence_swap".into(),
            explanation: format!(
                "“{}” fits this sentence much better than “{original}”.",
                swap.candidate
            ),
            confidence: (0.5 + gain / 40.0).min(0.95) as f32,
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
    #[test]
    fn typing_never_waits_past_its_budget_and_the_answer_comes_from_the_cache() {
        fn slow(sentence: &str, swaps: &[Swap], how: Use) -> Result<Scored, Unscored> {
            std::thread::sleep(Duration::from_millis(300));
            fake(sentence, swaps, how)
        }
        let req = Request {
            text: "We'll be on the platform at noon.".into(),
            gec: true,
            ..Request::default()
        };
        let started = Instant::now();
        assert!(combine_with(&req, &[], vec![], slow).is_empty());
        assert!(started.elapsed() < Duration::from_millis(250));
        // The job finishes in the background; a later check reads its verdict.
        let deadline = Instant::now() + Duration::from_secs(5);
        let mut edits = vec![];
        while edits.is_empty() && Instant::now() < deadline {
            std::thread::sleep(Duration::from_millis(50));
            edits = combine_with(&req, &[], vec![], slow);
        }
        assert_eq!(edits.len(), 1);
        assert_eq!(edits[0].replacement, "in");
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
