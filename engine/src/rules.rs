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
        // Real-word confusions and word-choice usage ("their is", "could care less").
        grammar.extend(
            serde_json::from_str::<Vec<Rule>>(include_str!("../rules/usage.json"))
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
        let rules: Vec<PhraseRule> = serde_json::from_str(include_str!("../rules/phrases.json"))
            .expect("valid embedded rule pack");
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
    #[test]
    fn every_rule_has_provenance_and_fixtures() {
        let grammar: Vec<Rule> =
            serde_json::from_str(include_str!("../rules/grammar.json")).unwrap();
        let tone: Vec<Rule> = serde_json::from_str(include_str!("../rules/tone.json")).unwrap();
        let usage: Vec<Rule> = serde_json::from_str(include_str!("../rules/usage.json")).unwrap();
        assert_eq!(grammar.len() + tone.len() + usage.len(), contextual().len());
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
