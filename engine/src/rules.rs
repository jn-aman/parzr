//! Compiled rule packs. Fixed phrases share one Aho-Corasick automaton; contextual patterns compile
//! lazily, only once a required-literal prefilter (a second automaton) finds one of their literals.
use crate::Mode;
use aho_corasick::AhoCorasick;
use regex::Regex;
use serde::Deserialize;
use std::sync::OnceLock;
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
}
fn grammar() -> String {
    "Tone".into()
}
fn confidence() -> f32 {
    0.90
}
pub struct CompiledRule {
    pub rule: Rule,
    regex: OnceLock<Regex>,
}
impl CompiledRule {
    pub fn regex(&self) -> &Regex {
        self.regex.get_or_init(|| {
            Regex::new(&self.rule.pattern).expect("valid embedded contextual pattern")
        })
    }
}
pub fn contextual() -> &'static [CompiledRule] {
    &pack().rules
}
struct Pack {
    rules: Vec<CompiledRule>,
    filter: AhoCorasick,
    /// Rule index of each filter literal.
    owner: Vec<usize>,
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
        let (mut words, mut owner, mut always) = (vec![], vec![], vec![]);
        for (i, rule) in grammar.iter().enumerate() {
            assert!(!rule.provenance.is_empty(), "rule provenance");
            match literals::required(&rule.pattern) {
                Some(set) => {
                    owner.extend(set.iter().map(|_| i));
                    words.extend(set);
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
            .map(|rule| CompiledRule {
                rule,
                regex: OnceLock::new(),
            })
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
/// reported false has no match, so its regex is never compiled or run.
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
        hit[pack.owner[m.pattern().as_usize()]] = true;
    }
    hit
}
/// The reviewed list of common misspellings: (misspelling, correction) pairs.
pub fn misspellings() -> impl Iterator<Item = (&'static str, &'static str)> {
    include_str!("../rules/misspellings.txt")
        .lines()
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
    #[test]
    fn every_rule_has_provenance_and_fixtures() {
        let grammar: Vec<Rule> =
            serde_json::from_str(include_str!("../rules/grammar.json")).unwrap();
        let tone: Vec<Rule> = serde_json::from_str(include_str!("../rules/tone.json")).unwrap();
        assert_eq!(grammar.len() + tone.len(), contextual().len());
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
    fn listed_misspellings_are_never_words_or_names() {
        let mut seen = std::collections::HashSet::new();
        for (wrong, right) in misspellings() {
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
