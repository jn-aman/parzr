//! Conservative required-literal extraction for the contextual rule patterns: a set of strings of
//! which every match contains at least one (compared ASCII case-insensitively). Anything the small
//! parser does not understand gives up, and a rule without a literal always runs.
use std::cmp::Reverse;

/// Longest cross product kept as one exact set; beyond it the run is cut and restarted.
const LIMIT: usize = 256;

enum Lits {
    /// The node matches exactly one of these strings (possibly empty).
    Exact(Vec<String>),
    /// Every match of the node contains one of these (non-empty) strings.
    Need(Vec<String>),
    Any,
}
use Lits::{Any, Exact, Need};

pub fn required(pattern: &str) -> Option<Vec<String>> {
    let chars: Vec<char> = pattern.chars().collect();
    let mut parser = Parser { c: &chars, i: 0 };
    let node = parser.alt()?;
    if parser.i != chars.len() {
        return None;
    }
    match node {
        Exact(set) | Need(set) if usable(&set) => Some(set),
        _ => None,
    }
}
fn usable(set: &[String]) -> bool {
    !set.is_empty() && set.iter().all(|s| !s.is_empty())
}
fn score(set: &[String]) -> (usize, Reverse<usize>) {
    let shortest = set.iter().map(|s| s.chars().count()).min().unwrap_or(0);
    (shortest, Reverse(set.len()))
}
fn keep(best: &mut Option<Vec<String>>, set: Vec<String>) {
    if usable(&set) && best.as_ref().is_none_or(|b| score(&set) > score(b)) {
        *best = Some(set);
    }
}
fn union(a: Vec<String>, b: Vec<String>) -> Vec<String> {
    let mut out = a;
    for s in b {
        if !out.contains(&s) {
            out.push(s);
        }
    }
    out
}
fn concat(parts: Vec<Lits>) -> Lits {
    let mut cur = vec![String::new()];
    let mut best = None;
    let mut exact = true;
    for part in parts {
        match part {
            Exact(set) if cur.len() * set.len() <= LIMIT => {
                cur = cur
                    .iter()
                    .flat_map(|a| set.iter().map(move |b| format!("{a}{b}")))
                    .collect();
            }
            other => {
                exact = false;
                keep(&mut best, std::mem::replace(&mut cur, vec![String::new()]));
                match other {
                    Exact(set) => cur = set,
                    Need(set) => keep(&mut best, set),
                    Any => {}
                }
            }
        }
    }
    if exact {
        return Exact(cur);
    }
    keep(&mut best, cur);
    best.map_or(Any, Need)
}
fn alternate(branches: Vec<Lits>) -> Lits {
    let mut all_exact = true;
    let mut set = vec![];
    for branch in branches {
        match branch {
            Exact(s) => set = union(set, s),
            Need(s) => {
                all_exact = false;
                set = union(set, s);
            }
            Any => return Any,
        }
    }
    if all_exact && set.len() <= LIMIT {
        Exact(set)
    } else if usable(&set) {
        Need(set)
    } else {
        Any
    }
}
fn repeated(node: Lits) -> Lits {
    match node {
        Exact(set) | Need(set) if usable(&set) => Need(set),
        _ => Any,
    }
}
fn optional(node: Lits) -> Lits {
    match node {
        Exact(set) => Exact(union(set, vec![String::new()])),
        _ => Any,
    }
}
/// ASCII, or the typographic apostrophe, which has no case: nothing else is matched byte for byte.
fn literal(c: char) -> Lits {
    if c.is_ascii() || c == '’' {
        Exact(vec![c.to_string()])
    } else {
        Any
    }
}
struct Parser<'a> {
    c: &'a [char],
    i: usize,
}
impl Parser<'_> {
    fn peek(&self) -> Option<char> {
        self.c.get(self.i).copied()
    }
    fn eat(&mut self, c: char) -> bool {
        let found = self.peek() == Some(c);
        self.i += usize::from(found);
        found
    }
    fn alt(&mut self) -> Option<Lits> {
        let mut branches = vec![self.concat()?];
        while self.eat('|') {
            branches.push(self.concat()?);
        }
        Some(if branches.len() == 1 {
            branches.remove(0)
        } else {
            alternate(branches)
        })
    }
    fn concat(&mut self) -> Option<Lits> {
        let mut parts = vec![];
        while !matches!(self.peek(), None | Some('|' | ')')) {
            parts.push(self.quantified()?);
        }
        Some(concat(parts))
    }
    fn quantified(&mut self) -> Option<Lits> {
        let atom = self.atom()?;
        let node = match self.peek() {
            Some('?') => {
                self.i += 1;
                optional(atom)
            }
            Some('*') => {
                self.i += 1;
                Any
            }
            Some('+') => {
                self.i += 1;
                repeated(atom)
            }
            Some('{') => {
                let close = self.c[self.i..].iter().position(|c| *c == '}')? + self.i;
                let body: String = self.c[self.i + 1..close].iter().collect();
                self.i = close + 1;
                let (min, max) = body.split_once(',').unwrap_or((&body, &body));
                let min: usize = min.parse().ok()?;
                if min == 0 {
                    Any
                } else if min == 1 && max == "1" {
                    atom
                } else {
                    repeated(atom)
                }
            }
            _ => return Some(atom),
        };
        self.eat('?');
        Some(node)
    }
    fn atom(&mut self) -> Option<Lits> {
        let c = self.peek()?;
        self.i += 1;
        Some(match c {
            '(' => self.group()?,
            '[' => self.class()?,
            '\\' => self.escape()?,
            '^' | '$' => Exact(vec![String::new()]),
            '.' => Any,
            '*' | '+' | '?' | '{' | '}' | ']' | ')' | '|' => return None,
            c => literal(c),
        })
    }
    fn group(&mut self) -> Option<Lits> {
        if self.eat('?') {
            if self.eat('P') {
                // A named group: skip "<name>".
                while self.peek()? != '>' {
                    self.i += 1;
                }
                self.i += 1;
            } else {
                // Flags only (i, m, s): "(?i)" is zero-width, "(?-i:" scopes the flags to a group.
                let mut flags = 0;
                while !matches!(self.peek()?, ')' | ':') {
                    if !"ims-".contains(self.peek()?) {
                        return None;
                    }
                    self.i += 1;
                    flags += 1;
                }
                if self.eat(')') {
                    return (flags > 0).then(|| Exact(vec![String::new()]));
                }
                self.i += 1;
            }
        }
        let inner = self.alt()?;
        self.eat(')').then_some(inner)
    }
    /// A small class of plain characters is a set of alternatives; anything else matches Any.
    fn class(&mut self) -> Option<Lits> {
        let mut set: Vec<String> = vec![];
        let mut plain = !self.eat('^');
        let mut first = true;
        loop {
            let c = self.peek()?;
            self.i += 1;
            match c {
                ']' if !first => break,
                '[' => return None,
                '\\' => match self.escape()? {
                    Exact(s) if s.len() == 1 && !s[0].is_empty() => set.extend(s),
                    _ => plain = false,
                },
                '-' | '&' | '~' => plain = false,
                c => match literal(c) {
                    Exact(s) => set.extend(s),
                    _ => plain = false,
                },
            }
            first = false;
        }
        Some(if plain && usable(&set) && set.len() <= 8 {
            Exact(set)
        } else {
            Any
        })
    }
    fn escape(&mut self) -> Option<Lits> {
        let c = self.peek()?;
        self.i += 1;
        Some(match c {
            'b' | 'B' | 'A' | 'z' => Exact(vec![String::new()]),
            'd' | 'D' | 'w' | 'W' | 's' | 'S' => Any,
            'p' | 'P' => {
                if self.eat('{') {
                    while self.peek()? != '}' {
                        self.i += 1;
                    }
                }
                self.i += 1;
                Any
            }
            'x' => {
                let hex: String = self.c.get(self.i..self.i + 2)?.iter().collect();
                self.i += 2;
                literal(char::from(
                    u8::from_str_radix(&hex, 16).ok().filter(u8::is_ascii)?,
                ))
            }
            'n' => literal('\n'),
            't' => literal('\t'),
            c if c.is_ascii_punctuation() => literal(c),
            _ => return None,
        })
    }
}
#[cfg(test)]
mod tests {
    use super::required;
    use regex::Regex;
    fn set(pattern: &str) -> Option<Vec<String>> {
        required(pattern).map(|mut s| {
            s.sort();
            s
        })
    }
    fn strs(items: &[&str]) -> Option<Vec<String>> {
        Some(items.iter().map(|s| s.to_string()).collect())
    }
    #[test]
    fn sequences_alternatives_and_optionals_become_literals() {
        assert_eq!(set(r"(?i)\bwanna\b"), strs(&["wanna"]));
        assert_eq!(
            set(r"(?i)\b(?P<target>an) (?:report|file)\b"),
            strs(&["an file", "an report"])
        );
        assert_eq!(
            set(r"(?im)^(can|could) you "),
            strs(&["can you ", "could you "])
        );
        assert_eq!(set(r"(?i)\bI['’]m\b"), strs(&["I'm", "I’m"]));
        assert_eq!(set(r"(?i)\bgoes? home\b"), strs(&["goe home", "goes home"]));
    }
    #[test]
    fn unknown_parts_cut_a_run_but_never_invent_one() {
        // The word before is unknown: only the literal tail is required.
        assert_eq!(set(r"(?i)\b[\p{L}']+ (?P<target>goes)\b"), strs(&[" goes"]));
        assert_eq!(set(r"(?i)\b(?:a|b)?\w+"), None);
        assert_eq!(set(r"(?i)\bfoo*"), strs(&["fo"]));
        assert_eq!(set(r"(?i)(?:ab)?"), None);
        assert_eq!(set(r"(?x)a b"), None);
        assert_eq!(set(r"é"), None);
    }
    /// Random patterns from the shapes the rule packs use, against random texts: a match must
    /// always contain one of the required literals.
    #[test]
    fn random_patterns_never_match_without_a_literal() {
        let words = ["go", "goes", "an", "is", "I", "the", "not", "it's", "a"];
        let mut seed = 0x2545_F491_4F6C_DD1D_u64;
        let mut next = |n: usize| {
            seed ^= seed << 13;
            seed ^= seed >> 7;
            seed ^= seed << 17;
            (seed >> 33) as usize % n
        };
        let mut matched = 0;
        for _ in 0..500 {
            let mut parts = vec![];
            for _ in 0..1 + next(4) {
                let word = words[next(words.len())];
                parts.push(match next(9) {
                    0 => format!("(?:{word}|{})", words[next(words.len())]),
                    1 => format!("(?:{word} )?"),
                    2 => format!("(?:{word})+"),
                    3 => r"[\p{L}']+".into(),
                    4 => r"\b".into(),
                    5 => format!("(?-i:{word})"),
                    6 => format!("{word}*"),
                    7 => "['’]".into(),
                    _ => format!("{word} "),
                });
            }
            let pattern = format!("(?i){}", parts.concat());
            let re = Regex::new(&pattern).unwrap();
            let literals = required(&pattern);
            for _ in 0..30 {
                let text: String = (0..1 + next(6))
                    .map(|_| format!("{} ", words[next(words.len())]))
                    .collect::<String>()
                    .replace("it's", if next(2) == 0 { "it's" } else { "it’s" });
                let text = if next(2) == 0 {
                    text.to_uppercase()
                } else {
                    text
                };
                if re.is_match(&text) {
                    matched += 1;
                    let lower = text.to_lowercase();
                    assert!(
                        literals
                            .as_ref()
                            .is_none_or(|l| l.iter().any(|x| lower.contains(&x.to_lowercase()))),
                        "{pattern} matched {text:?} without {literals:?}"
                    );
                }
            }
        }
        assert!(matched > 200, "{matched}");
    }
}
