//! Text side of GECToR: a port of spaCy's English word tokenizer (rules in rules/gec-tokenizer.json,
//! exported from spaCy 3.8) and the RoBERTa byte-level BPE, both pure Rust.
use regex::Regex;
use serde::Deserialize;
use std::{collections::HashMap, sync::Mutex};

/// One spaCy token of a piece: where it starts and whether a single space follows it.
#[derive(Clone, Debug, PartialEq)]
pub struct Word {
    pub text: String,
    pub start: usize,
    pub space: bool,
}

type RuleSpec = (Option<String>, String, Option<String>);
#[derive(Deserialize)]
struct Spec {
    exceptions: Vec<(String, Vec<String>)>,
    prefixes: Vec<RuleSpec>,
    suffixes: Vec<RuleSpec>,
    infixes: Vec<RuleSpec>,
}
/// A regex rule with the lookbehind and lookahead that the regex crate lacks, applied by hand.
struct Rule {
    before: Option<Regex>,
    body: Regex,
    after: Option<(bool, Regex)>,
}
impl Rule {
    fn after_ok(&self, rest: &str) -> bool {
        self.after
            .as_ref()
            .is_none_or(|(want, re)| re.is_match(rest) == *want)
    }
    fn before_ok(&self, head: &str) -> bool {
        self.before.as_ref().is_none_or(|re| re.is_match(head))
    }
}
fn re(pattern: &str) -> Regex {
    Regex::new(pattern).unwrap_or_else(|e| panic!("constant tokenizer rule {pattern:.60}: {e}"))
}
/// Consecutive rules without lookarounds fuse into one alternation (same order, same winner).
fn rules(specs: Vec<RuleSpec>, end: &str) -> Vec<Rule> {
    let mut out = vec![];
    let mut fused: Vec<String> = vec![];
    let flush = |fused: &mut Vec<String>, out: &mut Vec<Rule>| {
        if !fused.is_empty() {
            out.push(Rule {
                before: None,
                body: re(&format!("^(?:{}){end}", fused.join("|"))),
                after: None,
            });
            fused.clear();
        }
    };
    for (before, body, after) in specs {
        if before.is_none() && after.is_none() {
            fused.push(body);
            continue;
        }
        flush(&mut fused, &mut out);
        out.push(Rule {
            before: before.map(|b| re(&format!("(?:{b})\\z"))),
            body: re(&format!("^(?:{body}){end}")),
            after: after.map(|a| (a.starts_with('+'), re(&format!("^(?:{})", &a[1..])))),
        });
    }
    flush(&mut fused, &mut out);
    out
}

pub struct Tokenizer {
    exceptions: HashMap<String, Vec<String>>,
    prefixes: Vec<Rule>,
    suffixes: Vec<Rule>,
    infixes: Vec<Rule>,
    url: Regex,
    /// Token sequences of the special cases that affix rules would split, by first token.
    phrases: HashMap<String, Vec<Vec<String>>>,
}
impl Tokenizer {
    pub fn new() -> Self {
        let spec: Spec = serde_json::from_str(include_str!("../rules/gec-tokenizer.json"))
            .expect("constant tokenizer rules");
        let mut this = Self {
            exceptions: spec.exceptions.into_iter().collect(),
            prefixes: rules(spec.prefixes, ""),
            suffixes: rules(spec.suffixes, "$"),
            infixes: rules(spec.infixes, ""),
            // spaCy's URL pattern minus its private-address exclusions.
            url: re(
                r"^(?:(?:[\w+\-.]{2,})://)?(?:\S+(?::\S*)?@)?(?:(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){2}(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))|(?:(?:[A-Za-z0-9\x{a1}-\x{ffff}][A-Za-z0-9\x{a1}-\x{ffff}_-]{0,62})?[A-Za-z0-9\x{a1}-\x{ffff}]\.)+(?:\p{Ll}{2,63}))(?::\d{2,5})?(?:[/?#]\S*)?$",
            ),
            phrases: HashMap::new(),
        };
        let mut keys: Vec<&String> = this.exceptions.keys().collect();
        keys.sort();
        let mut phrases: HashMap<String, Vec<Vec<String>>> = HashMap::new();
        for key in keys {
            if this.prefix(key) > 0 || this.suffix(key) > 0 || !this.infix_matches(key).is_empty() {
                let phrase: Vec<String> = this
                    .split_span(key, false)
                    .into_iter()
                    .map(str::to_owned)
                    .collect();
                phrases.entry(phrase[0].clone()).or_default().push(phrase);
            }
        }
        this.phrases = phrases;
        this
    }
    fn prefix(&self, s: &str) -> usize {
        self.prefixes
            .iter()
            .find_map(|r| r.body.find(s).filter(|m| r.after_ok(&s[m.end()..])))
            .map_or(0, |m| m.end())
    }
    /// Length of the suffix starting at the leftmost position where some rule matches to the end.
    fn suffix(&self, s: &str) -> usize {
        for (start, _) in s.char_indices() {
            for r in &self.suffixes {
                if r.before_ok(&s[..start]) && r.body.is_match(&s[start..]) {
                    return s.len() - start;
                }
            }
        }
        0
    }
    fn infix_matches(&self, s: &str) -> Vec<(usize, usize)> {
        let (mut out, mut at) = (vec![], 0);
        while at < s.len() {
            let hit = self.infixes.iter().find_map(|r| {
                r.before_ok(&s[..at])
                    .then(|| r.body.find(&s[at..]))
                    .flatten()
                    .map(|m| at + m.end())
                    .filter(|end| *end > at && r.after_ok(&s[*end..]))
            });
            match hit {
                Some(end) => {
                    out.push((at, end));
                    at = end;
                }
                None => at += s[at..].chars().next().map_or(1, char::len_utf8),
            }
        }
        out
    }
    /// The tokens of one run of non-space characters. `specials` is spaCy's `with_special_cases`.
    fn split_span<'a>(&self, span: &'a str, specials: bool) -> Vec<&'a str> {
        let special = |s: &str| specials && !s.is_empty() && self.exceptions.contains_key(s);
        let pieces = |s: &'a str, out: &mut Vec<&'a str>| {
            let mut at = 0;
            for p in &self.exceptions[s] {
                out.push(&s[at..at + p.len()]);
                at += p.len();
            }
        };
        let mut out = vec![];
        if special(span) {
            pieces(span, &mut out);
            return out;
        }
        let (mut core, mut prefixes, mut suffixes) = (span, vec![], vec![]);
        let mut last = 0;
        while !core.is_empty() && core.len() != last {
            if special(core) {
                break;
            }
            last = core.len();
            let pre = self.prefix(core);
            let minus_pre = &core[pre..];
            if pre > 0 && special(minus_pre) {
                prefixes.push(&core[..pre]);
                core = minus_pre;
                break;
            }
            let suf = self.suffix(minus_pre);
            let minus_suf = &core[..core.len() - suf];
            if suf > 0 && special(minus_suf) {
                suffixes.push(&core[core.len() - suf..]);
                core = minus_suf;
                break;
            }
            if pre > 0 && suf > 0 && pre + suf <= core.len() {
                prefixes.push(&core[..pre]);
                suffixes.push(&core[core.len() - suf..]);
                core = &core[pre..core.len() - suf];
            } else if pre > 0 {
                prefixes.push(&core[..pre]);
                core = minus_pre;
            } else if suf > 0 {
                suffixes.push(&core[core.len() - suf..]);
                core = minus_suf;
            }
        }
        out.extend(prefixes);
        if special(core) {
            pieces(core, &mut out);
        } else if !core.is_empty() {
            if self.url.is_match(core) {
                out.push(core);
            } else {
                let mut start = 0;
                for (a, b) in self.infix_matches(core) {
                    // An infix at the very start stays attached.
                    if a == 0 {
                        continue;
                    }
                    if a != start {
                        out.push(&core[start..a]);
                    }
                    out.push(&core[a..b]);
                    start = b;
                }
                if start < core.len() {
                    out.push(&core[start..]);
                }
            }
        }
        out.extend(suffixes.into_iter().rev());
        out
    }
    /// Special cases that affix splitting would take apart (":)", "''") are found again in the token
    /// stream and put back together, as spaCy's special-case matcher does after the first pass.
    fn restore_specials(&self, text: &str, tokens: Vec<Word>) -> Vec<Word> {
        let mut spans: Vec<(usize, usize)> = vec![];
        for (i, t) in tokens.iter().enumerate() {
            for phrase in self.phrases.get(&t.text).into_iter().flatten() {
                let end = i + phrase.len();
                if end <= tokens.len()
                    && phrase
                        .iter()
                        .zip(&tokens[i..end])
                        .all(|(p, t)| *p == t.text)
                {
                    spans.push((i, end));
                }
            }
        }
        // Longest first, earliest first; a span whose first or last token is taken is dropped.
        spans.sort_by_key(|&(a, b)| (std::cmp::Reverse(b - a), a));
        let (mut seen, mut accepted) = (vec![false; tokens.len()], vec![]);
        for (a, b) in spans {
            if !seen[a] && !seen[b - 1] {
                accepted.push((a, b));
            }
            seen[a..b].iter_mut().for_each(|x| *x = true);
        }
        accepted.sort_unstable();
        let (mut out, mut i) = (vec![], 0);
        let mut next = accepted.into_iter().peekable();
        while i < tokens.len() {
            let hit = next.next_if(|&(a, _)| a == i);
            let Some((a, b)) = hit else {
                out.push(tokens[i].clone());
                i += 1;
                continue;
            };
            let last = &tokens[b - 1];
            let whole = &text[tokens[a].start..last.start + last.text.len()];
            if self.exceptions.contains_key(whole) {
                let mut at = tokens[a].start;
                for p in &self.exceptions[whole] {
                    out.push(Word {
                        text: p.clone(),
                        start: at,
                        space: false,
                    });
                    at += p.len();
                }
                if let Some(t) = out.last_mut() {
                    t.space = last.space;
                }
            } else {
                out.extend(tokens[a..b].iter().cloned());
            }
            i = b;
        }
        out
    }
    /// The non-space tokens of `text` (spaCy `tokenizer(text)` without the space tokens).
    pub fn words(&self, text: &str) -> Vec<Word> {
        let mut out = vec![];
        let mut at = 0;
        while at < text.len() {
            at += text[at..].len() - text[at..].trim_start().len();
            let rest = &text[at..];
            let len = rest.find(char::is_whitespace).unwrap_or(rest.len());
            if len == 0 {
                break;
            }
            let mut offset = at;
            for part in self.split_span(&rest[..len], true) {
                out.push(Word {
                    text: part.to_owned(),
                    start: offset,
                    space: false,
                });
                offset += part.len();
            }
            if let Some(last) = out.last_mut() {
                last.space = text[at + len..].starts_with(' ');
            }
            at += len;
        }
        self.restore_specials(text, out)
    }
}

/// RoBERTa byte-level BPE (vocab.json, merges.txt).
pub struct Bpe {
    vocab: HashMap<String, i32>,
    ranks: HashMap<(String, String), usize>,
    split: Regex,
    bytes: Vec<char>,
    cache: Mutex<HashMap<String, Vec<i32>>>,
}
impl Bpe {
    pub fn new(vocab: &str, merges: &str) -> Result<Self, String> {
        let vocab: HashMap<String, i32> = serde_json::from_str(vocab).map_err(|e| e.to_string())?;
        let ranks = merges
            .lines()
            .filter(|l| !l.starts_with("#version"))
            .filter_map(|l| l.split_once(' '))
            .enumerate()
            .map(|(i, (a, b))| ((a.to_owned(), b.to_owned()), i))
            .collect();
        // GPT-2's byte to printable character table.
        let mut table = vec!['\0'; 256];
        let printable = |b: u32| {
            (33..=126).contains(&b) || (161..=172).contains(&b) || (174..=255).contains(&b)
        };
        let mut extra = 0;
        for b in 0..256u32 {
            table[b as usize] = if printable(b) {
                char::from_u32(b).unwrap_or('?')
            } else {
                extra += 1;
                char::from_u32(255 + extra).unwrap_or('?')
            };
        }
        Ok(Self {
            vocab,
            ranks,
            split: re(r"'s|'t|'re|'ve|'m|'ll|'d| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+"),
            bytes: table,
            cache: Mutex::new(HashMap::new()),
        })
    }
    pub fn id(&self, token: &str) -> Option<i32> {
        self.vocab.get(token).copied()
    }
    fn merge(&self, chunk: &str) -> Vec<i32> {
        if let Some(hit) = self.cache.lock().ok().and_then(|c| c.get(chunk).cloned()) {
            return hit;
        }
        let mut symbols: Vec<String> = chunk
            .bytes()
            .map(|b| self.bytes[b as usize].to_string())
            .collect();
        while symbols.len() > 1 {
            let best = (0..symbols.len() - 1)
                .filter_map(|i| {
                    self.ranks
                        .get(&(symbols[i].clone(), symbols[i + 1].clone()))
                        .map(|r| (*r, i))
                })
                .min();
            let Some((_, i)) = best else { break };
            let joined = format!("{}{}", symbols[i], symbols[i + 1]);
            symbols.splice(i..i + 2, [joined]);
        }
        // Every byte symbol is in the vocabulary; an unknown merge result falls back to <unk>.
        let ids: Vec<i32> = symbols.iter().map(|s| self.id(s).unwrap_or(3)).collect();
        if let Ok(mut cache) = self.cache.lock() {
            if cache.len() > 50_000 {
                cache.clear();
            }
            cache.insert(chunk.to_owned(), ids.clone());
        }
        ids
    }
    /// Subword ids of one word, with the prefix space the GECToR tokenizer adds to every word.
    pub fn word(&self, word: &str) -> Vec<i32> {
        let spaced = format!(" {word}");
        self.split
            .find_iter(&spaced)
            .flat_map(|m| self.merge(m.as_str()))
            .collect()
    }
}
