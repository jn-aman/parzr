//! Compiled rule packs. Fixed phrases share one Aho–Corasick automaton; contextual patterns compile once.
use crate::Mode;
use aho_corasick::AhoCorasick;
use regex::Regex;
use serde::Deserialize;
use std::sync::OnceLock;
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
    pub regex: Regex,
}
pub fn contextual() -> &'static [CompiledRule] {
    static RULES: OnceLock<Vec<CompiledRule>> = OnceLock::new();
    RULES.get_or_init(|| {
        let mut grammar: Vec<Rule> = serde_json::from_str(include_str!("../rules/grammar.json"))
            .expect("valid embedded rule pack");
        grammar.extend(
            serde_json::from_str::<Vec<Rule>>(include_str!("../rules/tone.json"))
                .expect("valid embedded rule pack"),
        );
        grammar
            .into_iter()
            .map(|rule| {
                assert!(!rule.provenance.is_empty(), "rule provenance");
                let regex = Regex::new(&rule.pattern).expect("valid embedded contextual pattern");
                CompiledRule { rule, regex }
            })
            .collect()
    })
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
    #[test]
    fn every_rule_has_provenance_and_fixtures() {
        let grammar: Vec<Rule> =
            serde_json::from_str(include_str!("../rules/grammar.json")).unwrap();
        let tone: Vec<Rule> = serde_json::from_str(include_str!("../rules/tone.json")).unwrap();
        assert_eq!(grammar.len() + tone.len(), contextual().len());
        for c in contextual() {
            assert!(!c.rule.provenance.is_empty());
            assert!(c.regex.is_match(&c.rule.positive), "{} positive", c.rule.id);
            assert!(
                !c.regex.is_match(&c.rule.negative),
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
}
