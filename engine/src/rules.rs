//! Compiled rule packs. Fixed phrases share one Aho-Corasick automaton; contextual patterns compile
//! lazily, only once a required-literal prefilter (a second automaton) finds one of their literals.
use crate::Mode;
use aho_corasick::AhoCorasick;
use regex::Regex;
use serde::Deserialize;
use std::{
    collections::HashMap,
    sync::{Arc, Mutex, OnceLock},
};
mod literals;
#[derive(Debug, Deserialize)]
pub struct Rule {
    pub id: String,
    pub pattern: String,
    pub replacement: String,
    #[serde(default)]
    pub modes: Vec<Mode>,
    #[serde(default = "grammar")]
    pub category: String,
    #[serde(default = "confidence")]
    pub confidence: f32,
    #[serde(alias = "reason")]
    pub explanation: String,
    pub provenance: String,
    #[cfg(test)]
    pub positive: String,
    #[cfg(test)]
    pub negative: String,
    /// The rules/packs file this rule came from (set by build.rs), none for the three base files.
    #[cfg(test)]
    #[serde(default)]
    pub pack: Option<String>,
}
fn grammar() -> String {
    "Tone".into()
}
fn confidence() -> f32 {
    0.90
}
pub struct CompiledRule {
    pub rule: Rule,
    index: usize,
}
/// How many compiled rule patterns stay in memory. A compiled pattern costs about 70 KB (its NFA
/// and one-pass DFA, mostly Unicode word classes); keeping all ~470 that a long, varied session
/// reaches cost about 20 MB, too much for a keyboard extension. Past this many, the pattern used
/// least recently is dropped and compiled again when next needed, with the same matches.
/// On the Mac the packs run to thousands of patterns and a long passage touches hundreds at once, so
/// the cache keeps 768 (about 54 MB at worst); a keyboard extension keeps the small cache.
#[cfg(target_os = "macos")]
pub const COMPILED_PATTERNS_KEPT: usize = 768;
#[cfg(not(target_os = "macos"))]
pub const COMPILED_PATTERNS_KEPT: usize = 48;
struct Compiled {
    regexes: Vec<Option<Arc<Regex>>>,
    used: Vec<u64>,
    live: usize,
    tick: u64,
}
fn compiled() -> &'static Mutex<Compiled> {
    static COMPILED: OnceLock<Mutex<Compiled>> = OnceLock::new();
    COMPILED.get_or_init(|| {
        let n = pack().rules.len();
        Mutex::new(Compiled {
            regexes: vec![None; n],
            used: vec![0; n],
            live: 0,
            tick: 0,
        })
    })
}
impl CompiledRule {
    pub fn regex(&self) -> Arc<Regex> {
        {
            let mut cache = compiled().lock().unwrap_or_else(|e| e.into_inner());
            cache.tick += 1;
            let tick = cache.tick;
            if let Some(regex) = cache.regexes[self.index].clone() {
                cache.used[self.index] = tick;
                return regex;
            }
        }
        let regex =
            Arc::new(crate::regex(&self.rule.pattern).expect("valid embedded contextual pattern"));
        let mut cache = compiled().lock().unwrap_or_else(|e| e.into_inner());
        if cache.regexes[self.index].is_none() {
            if cache.live == COMPILED_PATTERNS_KEPT {
                let oldest = (0..cache.regexes.len())
                    .filter(|&i| cache.regexes[i].is_some())
                    .min_by_key(|&i| cache.used[i])
                    .expect("a compiled pattern");
                cache.regexes[oldest] = None;
                cache.live -= 1;
            }
            cache.regexes[self.index] = Some(regex.clone());
            cache.live += 1;
        }
        cache.tick += 1;
        let tick = cache.tick;
        cache.used[self.index] = tick;
        regex
    }
}
pub fn contextual() -> &'static [CompiledRule] {
    &pack().rules
}
struct Pack {
    rules: Vec<CompiledRule>,
    filter: AhoCorasick,
    /// The rules each filter literal belongs to.
    owner: Vec<Vec<usize>>,
    /// Rules with no safe required literal: always candidates.
    always: Vec<usize>,
}
fn pack() -> &'static Pack {
    static PACK: OnceLock<Pack> = OnceLock::new();
    PACK.get_or_init(|| {
        let mut grammar: Vec<Rule> = serde_json::from_str(include_str!("../rules/grammar.json"))
            .expect("valid embedded rule pack");
        grammar.extend(
            serde_json::from_str::<Vec<Rule>>(include_str!("../rules/tone.json"))
                .expect("valid embedded rule pack"),
        );
        // Real-word confusions and word-choice usage ("their is", "could care less").
        grammar.extend(
            serde_json::from_str::<Vec<Rule>>(include_str!("../rules/usage.json"))
                .expect("valid embedded rule pack"),
        );
        // One file per category under rules/packs/, joined by build.rs (rules/packs/README.md)
        // into the tables file, which the app ships once (`tables`); the tests read the full
        // array with each rule's positive and negative.
        #[cfg(test)]
        let packs: &str = include_str!(concat!(env!("OUT_DIR"), "/rule-packs.json"));
        #[cfg(not(test))]
        let packs: &str =
            std::str::from_utf8(crate::tables::get().rule_packs).expect("rule packs are UTF-8");
        grammar
            .extend(serde_json::from_str::<Vec<Rule>>(packs).expect("valid embedded rule packs"));
        // Computed by build.rs from the same patterns; a rule it does not know (never, unless the
        // build is stale) is computed here.
        let precomputed: std::collections::HashMap<String, Option<Vec<String>>> =
            serde_json::from_slice(crate::tables::get().rule_literals)
                .expect("valid rule literals");
        let (mut words, mut owner, mut always) = (vec![], vec![], vec![]);
        let mut index: std::collections::HashMap<String, usize> = std::collections::HashMap::new();
        for (i, rule) in grammar.iter().enumerate() {
            assert!(!rule.provenance.is_empty(), "rule provenance");
            let set = match precomputed.get(&rule.id) {
                Some(set) => set.clone(),
                None => literals::required(&rule.pattern),
            };
            match set {
                Some(set) => {
                    for word in set {
                        // One automaton pattern per distinct literal; the packs share many.
                        let key = word.to_ascii_lowercase();
                        let slot = *index.entry(key).or_insert_with(|| {
                            words.push(word);
                            owner.push(Vec::new());
                            words.len() - 1
                        });
                        let owners: &mut Vec<usize> = &mut owner[slot];
                        if owners.last() != Some(&i) {
                            owners.push(i);
                        }
                    }
                }
                None => always.push(i),
            }
        }
        let filter = AhoCorasick::builder()
            .ascii_case_insensitive(true)
            .build(&words)
            .expect("required literals");
        let rules = grammar
            .into_iter()
            .enumerate()
            .map(|(index, rule)| CompiledRule { rule, index })
            .collect();
        Pack {
            rules,
            filter,
            owner,
            always,
        }
    })
}
/// Which contextual rules can match `text`: those whose required literal occurs in it. A rule
/// reported false has no match, so its regex is never compiled or run. (The engine runs
/// `windows`; this is the tests' oracle for the prefilter.)
#[cfg(test)]
pub fn candidates(text: &str) -> Vec<bool> {
    let pack = pack();
    // Unicode case folding lets "K" and "s" match U+212A and U+017F, which the filter cannot see.
    if text.contains(['\u{212A}', '\u{17F}']) {
        return vec![true; pack.rules.len()];
    }
    let mut hit = vec![false; pack.rules.len()];
    for &i in &pack.always {
        hit[i] = true;
    }
    for m in pack.filter.find_overlapping_iter(text) {
        for &i in &pack.owner[m.pattern().as_usize()] {
            hit[i] = true;
        }
    }
    hit
}
/// Where each contextual rule needs to run: for a candidate, the byte windows of `text` that hold
/// its required literal, each widened to the sentence before and the sentence after (joined when
/// they overlap) and starting at the separator before that first sentence, so `^` with `(?m)`
/// and the `[.!?]\s+` alternations see what they would see in the whole text. A long passage then
/// costs each rule only its own neighbourhood instead of the whole text. None: not a candidate.
/// A rule with no required literal, and every rule when the text holds a character the ASCII
/// filter cannot fold, gets the whole text.
pub fn windows(text: &str) -> Vec<Option<Vec<(usize, usize)>>> {
    let pack = pack();
    let n = pack.rules.len();
    let whole = || Some(vec![(0, text.len())]);
    if text.contains(['\u{212A}', '\u{17F}']) {
        return vec![whole(); n];
    }
    let mut out: Vec<Option<Vec<(usize, usize)>>> = vec![None; n];
    for &i in &pack.always {
        out[i] = whole();
    }
    // Sentence starts, and for each the byte where its separator (the space after the mark, or
    // the line break) begins; the first sentence starts at 0 with no separator.
    let bytes = text.as_bytes();
    let (mut starts, mut seps) = (vec![0usize], vec![0usize]);
    let mut i = 0;
    while i < bytes.len() {
        let b = bytes[i];
        if b == b'\n' {
            let mut j = i + 1;
            while j < bytes.len() && (bytes[j] == b' ' || bytes[j] == b'\t' || bytes[j] == b'\n') {
                j += 1;
            }
            if j < bytes.len() && j > *starts.last().unwrap() {
                seps.push(i);
                starts.push(j);
            }
            i = j.max(i + 1);
            continue;
        }
        if matches!(b, b'.' | b'!' | b'?') {
            let mut j = i + 1;
            while j < bytes.len() && matches!(bytes[j], b'.' | b'!' | b'?' | b')' | b'"' | b'\'') {
                j += 1;
            }
            if j < bytes.len() && bytes[j].is_ascii_whitespace() {
                let mark_end = j;
                while j < bytes.len() && bytes[j].is_ascii_whitespace() {
                    j += 1;
                }
                if j < bytes.len() && j > *starts.last().unwrap() {
                    seps.push(mark_end);
                    starts.push(j);
                }
                i = j.max(i + 1);
                continue;
            }
        }
        i += 1;
    }
    let sentence_of = |pos: usize| starts.partition_point(|&s| s <= pos).saturating_sub(1);
    let end_of = |k: usize| starts.get(k + 1).copied().unwrap_or(text.len());
    for m in pack.filter.find_overlapping_iter(text) {
        let k = sentence_of(m.start());
        let from = seps[k.saturating_sub(1)];
        let to = end_of((k + 1).min(starts.len() - 1));
        for &rule in &pack.owner[m.pattern().as_usize()] {
            let list = out[rule].get_or_insert_with(Vec::new);
            match list.last_mut() {
                Some(last) if from <= last.1 => last.1 = last.1.max(to),
                _ => list.push((from, to)),
            }
        }
    }
    out
}
/// The reviewed list of common misspellings: (misspelling, correction) pairs.
pub fn misspellings() -> impl Iterator<Item = (&'static str, &'static str)> {
    pairs(include_str!("../rules/misspellings.txt"))
}
/// Misspellings mined from real corrections (scripts/build-typo-lexicon.py): (misspelling,
/// correction) pairs that are no word or name and are corrected one way nearly every time.
pub fn mined_misspellings() -> impl Iterator<Item = (&'static str, &'static str)> {
    pairs(include_str!("../rules/typos.txt"))
}
/// The mined correction of one lowercase word ("febuary" is "February"), by table lookup: the
/// list is too long for the phrase matcher to build quickly.
pub fn mined_typo(lower: &str) -> Option<&'static str> {
    static TABLE: OnceLock<HashMap<&'static str, &'static str>> = OnceLock::new();
    TABLE
        .get_or_init(|| mined_misspellings().collect())
        .get(lower)
        .copied()
}
fn pairs(list: &'static str) -> impl Iterator<Item = (&'static str, &'static str)> {
    list.lines()
        .filter(|line| !line.starts_with('#'))
        .filter_map(|line| line.split_once(' '))
}
#[derive(Deserialize)]
pub struct PhraseRule {
    pub id: String,
    pub source: String,
    pub replacement: String,
    pub category: String,
    pub confidence: f32,
    #[serde(alias = "reason")]
    pub explanation: String,
    pub provenance: String,
}
pub struct PhrasePack {
    pub matcher: AhoCorasick,
    pub rules: Vec<PhraseRule>,
}
pub fn phrases() -> &'static PhrasePack {
    static PACK: OnceLock<PhrasePack> = OnceLock::new();
    PACK.get_or_init(|| {
        let mut rules: Vec<PhraseRule> =
            serde_json::from_str(include_str!("../rules/phrases.json"))
                .expect("valid embedded rule pack");
        rules.extend(misspellings().map(|(source, replacement)| PhraseRule {
            id: "spelling.common_misspelling".into(),
            source: source.into(),
            replacement: replacement.into(),
            category: "Spelling".into(),
            confidence: 0.97,
            explanation: "This is a common misspelling.".into(),
            provenance: "Parzr common misspellings list (rules/misspellings.txt)".into(),
        }));
        assert!(
            rules.iter().all(|rule| !rule.provenance.is_empty()),
            "rule provenance"
        );
        let matcher = AhoCorasick::builder()
            .ascii_case_insensitive(true)
            .build(rules.iter().map(|r| r.source.as_str()))
            .expect("reviewed phrase patterns");
        PhrasePack { matcher, rules }
    })
}
#[cfg(test)]
mod tests {
    use super::*;
    /// The text after the checker's own fixes, applied until nothing changes (rules only).
    fn fix(text: &str) -> String {
        let mut req = crate::Request {
            text: text.into(),
            ..crate::Request::default()
        };
        for _ in 0..6 {
            let pass = crate::rewrite_once(&req, false).unwrap();
            if pass.edits.is_empty() {
                break;
            }
            req.text = pass.text;
        }
        req.text
    }
    #[test]
    fn usage_confusions_are_fixed_and_correct_text_never_changes() {
        let data: serde_json::Value =
            serde_json::from_str(include_str!("../tests/usage.json")).unwrap();
        let pairs = data["positives"].as_array().unwrap();
        let (mut fixed, mut wrong) = (0, vec![]);
        for p in pairs {
            let (input, expected) = (p[0].as_str().unwrap(), p[1].as_str().unwrap());
            match fix(input) {
                out if out == expected => fixed += 1,
                out if out == input => {}
                out => wrong.push(format!("{input} => {out}")),
            }
        }
        let touched: Vec<_> = data["negatives"]
            .as_array()
            .unwrap()
            .iter()
            .map(|n| n.as_str().unwrap())
            .filter(|n| fix(n) != *n)
            .collect();
        eprintln!("usage confusions fixed: {fixed}/{}", pairs.len());
        assert!(touched.is_empty(), "changed correct text: {touched:?}");
        assert!(wrong.is_empty(), "wrong rewrites: {wrong:?}");
        assert!(
            fixed * 10 >= pairs.len() * 9,
            "only {fixed} confusions fixed"
        );
    }
    /// The wording rules of one tone mode, applied once.
    fn tone(text: &str, mode: crate::Mode) -> String {
        let req = crate::Request {
            text: text.into(),
            mode,
            ..crate::Request::default()
        };
        crate::rewrite_once(&req, true).unwrap().text
    }
    #[test]
    fn a_person_after_the_verb_moves_behind_what_is_explained() {
        for (input, expected) in [
            (
                "Please suggest me a laptop for the trip.",
                "Please suggest a laptop to me for the trip.",
            ),
            ("Can you explain me this?", "Can you explain this to me?"),
            (
                "Could you explain me the process in detail?",
                "Could you explain the process to me in detail?",
            ),
            (
                "She explained them the whole plan, and we agreed.",
                "She explained the whole plan to them, and we agreed.",
            ),
            (
                "Please explain me how the export works.",
                "Please explain to me how the export works.",
            ),
            (
                "He described me the problem.",
                "He described the problem to me.",
            ),
            (
                "She mentioned them the price yesterday.",
                "She mentioned the price to them yesterday.",
            ),
        ] {
            assert_eq!(fix(input), expected, "{input}");
        }
        for text in [
            "Please suggest a laptop to me.",
            "Can you explain this to me?",
            "Could you explain the process to us in detail?",
            "Mention me in the post.",
            "Describe me in three words.",
            "He suggested me for the role.",
        ] {
            assert_eq!(fix(text), text);
        }
    }
    #[test]
    fn a_large_number_of_keeps_its_of_before_a_determiner() {
        use crate::Mode::{Concise, Direct};
        for (input, expected) in [
            (
                "A large number of users reported the bug.",
                "Many users reported the bug.",
            ),
            (
                "A large number of the users reported the bug.",
                "Many of the users reported the bug.",
            ),
            (
                "We heard from a great number of our customers.",
                "We heard from many of our customers.",
            ),
            (
                "We need a sufficient number of the volunteers.",
                "We need enough of the volunteers.",
            ),
            (
                "We need a sufficient amount of time.",
                "We need enough time.",
            ),
        ] {
            assert_eq!(tone(input, Concise), expected, "{input}");
        }
        assert_eq!(
            tone("A large number of them replied.", Direct),
            "Many of them replied."
        );
        for text in [
            "The large number of users surprised us.",
            "Many of the users reported the bug.",
        ] {
            assert_eq!(tone(text, Concise), text);
        }
    }
    #[test]
    fn concise_keeps_a_question_a_question_and_direct_turns_it_into_an_instruction() {
        use crate::Mode::{Concise, Direct};
        for (input, concise, direct) in [
            (
                "Could you please send the files again?",
                "Could you send the files again?",
                "Send the files again.",
            ),
            (
                "Would you let me know if the room is free?",
                "Would you let me know if the room is free?",
                "Let me know if the room is free.",
            ),
            (
                "Can you look at the pull request?",
                "Can you look at the pull request?",
                "Look at the pull request.",
            ),
        ] {
            assert_eq!(tone(input, Concise), concise, "{input}");
            assert_eq!(tone(input, Direct), direct, "{input}");
        }
        // A statement that wraps a request is still said as an instruction.
        assert_eq!(
            tone("I was wondering if you could send me the file.", Concise),
            "Please send me the file."
        );
        // Not a request for an action of "you".
        assert_eq!(
            tone("Can you make it Friday?", Concise),
            "Can you make it Friday?"
        );
    }
    #[test]
    fn every_rule_has_provenance_and_fixtures() {
        let grammar: Vec<Rule> =
            serde_json::from_str(include_str!("../rules/grammar.json")).unwrap();
        let tone: Vec<Rule> = serde_json::from_str(include_str!("../rules/tone.json")).unwrap();
        let usage: Vec<Rule> = serde_json::from_str(include_str!("../rules/usage.json")).unwrap();
        let packs: Vec<Rule> =
            serde_json::from_str(include_str!(concat!(env!("OUT_DIR"), "/rule-packs.json")))
                .unwrap();
        assert_eq!(
            grammar.len() + tone.len() + usage.len() + packs.len(),
            contextual().len()
        );
        // The tables file carries the same pack rules, in order, without the test-only fields.
        let shipped: Vec<serde_json::Value> =
            serde_json::from_slice(crate::tables::get().rule_packs).unwrap();
        assert_eq!(shipped.len(), packs.len());
        for (shipped, full) in shipped.iter().zip(&packs) {
            assert_eq!(shipped["id"].as_str(), Some(full.id.as_str()));
            assert_eq!(shipped["pattern"].as_str(), Some(full.pattern.as_str()));
            assert!(shipped.get("positive").is_none() && shipped.get("negative").is_none());
        }
        let mut ids = std::collections::HashSet::new();
        for c in contextual() {
            assert!(
                ids.insert(c.rule.id.as_str()),
                "duplicate rule id {}",
                c.rule.id
            );
        }
        // A pack rule without a required literal would run on every check: packs must carry one.
        for rule in &packs {
            assert!(
                literals::required(&rule.pattern).is_some(),
                "{} ({}): no required literal for the prefilter",
                rule.id,
                rule.pack.as_deref().unwrap_or("?")
            );
        }
        for c in contextual() {
            assert!(!c.rule.provenance.is_empty());
            assert!(
                c.regex().is_match(&c.rule.positive),
                "{} positive",
                c.rule.id
            );
            assert!(
                !c.regex().is_match(&c.rule.negative),
                "{} negative",
                c.rule.id
            );
        }
        for p in &phrases().rules {
            assert!(!p.provenance.is_empty());
            assert!(!p.source.is_empty());
            assert_ne!(p.source, p.replacement);
        }
    }
    #[test]
    fn mined_misspellings_respell_words_but_not_names() {
        for (input, expected) in [
            (
                "It was in Febuary that we left.",
                "It was in February that we left.",
            ),
            (
                "He moved to Britian last year.",
                "He moved to Britain last year.",
            ),
            ("Seperate the files please.", "Separate the files please."),
            ("The competion was fierce.", "The competition was fierce."),
            ("See you on Wenesday.", "See you on Wednesday."),
            (
                "Look up a non-existant invoice.",
                "Look up a non-existent invoice.",
            ),
        ] {
            assert_eq!(fix(input), expected);
        }
        // A capitalized word inside a sentence whose correction is an ordinary word may be a
        // name ("Siller" is no "Miller", "Princip" no "Principle").
        for text in ["We met Mr Siller today.", "The shot was fired by Princip."] {
            assert_eq!(fix(text), text);
        }
        assert_eq!(mined_typo("febuary"), Some("February"));
        assert_eq!(mined_typo("february"), None);
    }
    #[test]
    fn listed_misspellings_are_never_words_or_names() {
        let mut seen = std::collections::HashSet::new();
        for (wrong, right) in misspellings().chain(mined_misspellings()) {
            // Not a word or name in any English variant, listed once, and corrected to words.
            assert!(!crate::spelling::known(wrong), "{wrong} is a word");
            assert!(!crate::names::is_bundled_name(wrong), "{wrong} is a name");
            assert!(seen.insert(wrong), "{wrong} listed twice");
            assert!(
                right
                    .split(' ')
                    .all(|w| w.contains('\'') || crate::spelling::known(w)),
                "{right}"
            );
            assert!(wrong.bytes().all(|b| b.is_ascii_lowercase()), "{wrong}");
        }
        assert!(seen.len() > 300);
    }
    /// Development probe: `PARZR_PROBE_FILE=path cargo test --release profile_rule_matching -- --ignored --nocapture`
    /// prints how many rules are candidates for the text, the window coverage, and the slowest rules.
    #[test]
    #[ignore = "needs PARZR_PROBE_FILE"]
    fn profile_rule_matching() {
        let text = std::fs::read_to_string(std::env::var("PARZR_PROBE_FILE").unwrap()).unwrap();
        let t_init = std::time::Instant::now();
        let _ = windows(&text);
        println!(
            "pack init (parse + literals + filter): {:?}",
            t_init.elapsed()
        );
        let t_lits = std::time::Instant::now();
        let n: usize = contextual()
            .iter()
            .filter(|c| literals::required(&c.rule.pattern).is_some())
            .count();
        println!(
            "literal extraction alone for {n} rules: {:?}",
            t_lits.elapsed()
        );
        let t0 = std::time::Instant::now();
        let windows = windows(&text);
        let t_windows = t0.elapsed();
        let hits = pack().filter.find_overlapping_iter(&text).count();
        println!("prefilter literal hits: {hits}");
        let mut rows: Vec<(u128, usize, usize, String)> = vec![];
        let mut candidates = 0;
        for (c, w) in contextual().iter().zip(&windows) {
            let Some(w) = w else { continue };
            candidates += 1;
            let covered: usize = w.iter().map(|(a, b)| b - a).sum();
            let regex = c.regex();
            let t = std::time::Instant::now();
            let mut n = 0;
            for &(a, b) in w {
                // The DFA answers "no match" fast; captures (the slow engines) only run on a hit.
                if regex.is_match(&text[a..b]) {
                    n += regex.captures_iter(&text[a..b]).count();
                }
            }
            rows.push((t.elapsed().as_micros(), covered, n, c.rule.id.clone()));
        }
        rows.sort_by_key(|row| std::cmp::Reverse(row.0));
        let total: u128 = rows.iter().map(|r| r.0).sum();
        println!(
            "text {} bytes; {} rules, {candidates} candidates; windows {:?}; matching total {} ms",
            text.len(),
            contextual().len(),
            t_windows,
            total / 1000
        );
        for (us, covered, n, id) in rows.iter().take(25) {
            let lits = contextual()
                .iter()
                .find(|c| c.rule.id == *id)
                .and_then(|c| literals::required(&c.rule.pattern))
                .map(|l| {
                    let mut l = l;
                    l.sort_by_key(|x| x.len());
                    format!("{} literals, shortest {:?}", l.len(), &l[..l.len().min(4)])
                })
                .unwrap_or_default();
            println!("{us:8} us  covered {covered:6}  matches {n:3}  {id}  [{lits}]");
        }
        let by_prefix: std::collections::BTreeMap<&str, (u128, usize)> =
            rows.iter().fold(Default::default(), |mut m, r| {
                let e = m.entry(r.3.split('.').next().unwrap()).or_insert((0, 0));
                e.0 += r.0;
                e.1 += 1;
                m
            });
        for (p, (us, n)) in by_prefix {
            println!("prefix {p:10} {n:5} candidates {:6} ms", us / 1000);
        }
    }
    #[test]
    fn the_prefilter_never_hides_a_match() {
        for (i, c) in contextual().iter().enumerate() {
            let positive = &c.rule.positive;
            for text in [
                positive.clone(),
                positive.to_uppercase(),
                format!("Ok. {positive}"),
            ] {
                assert!(
                    candidates(&text)[i] || !c.regex().is_match(&text),
                    "{}",
                    c.rule.id
                );
            }
            assert!(candidates(positive)[i], "{} positive", c.rule.id);
        }
        // PARZR_PREFILTER_CORPUS: a file of texts, one JSON string or {"text": ...} per line.
        let Ok(path) = std::env::var("PARZR_PREFILTER_CORPUS") else {
            return;
        };
        let (mut texts, mut matches) = (0, 0);
        for line in std::fs::read_to_string(path).unwrap().lines() {
            let v: serde_json::Value = serde_json::from_str(line).unwrap();
            let text = v.as_str().or(v["text"].as_str()).unwrap();
            let hit = candidates(text);
            texts += 1;
            for (i, c) in contextual().iter().enumerate() {
                let found = c.regex().is_match(text);
                matches += usize::from(found);
                assert!(!found || hit[i], "{} missed in {text:?}", c.rule.id);
            }
        }
        eprintln!("prefilter checked {texts} texts, {matches} rule matches, none missed");
    }
    #[test]
    fn only_k_and_s_have_non_ascii_case_variants() {
        let all: String = (0x80..=0x10FFFF_u32).filter_map(char::from_u32).collect();
        for c in 'a'..='z' {
            let re = Regex::new(&format!("(?i){c}")).unwrap();
            let odd: Vec<char> = re
                .find_iter(&all)
                .filter_map(|m| m.as_str().chars().next())
                .collect();
            let expected: &[char] = match c {
                'k' => &['\u{212A}'],
                's' => &['\u{17F}'],
                _ => &[],
            };
            assert_eq!(odd, expected, "{c}");
        }
    }
}
