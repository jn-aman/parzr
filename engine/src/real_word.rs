//! Real-word keyboard slips ("this os bad", "I come form India"): a known word that is one
//! adjacent-key substitution or one adjacent transposition from another known word, where the
//! word pairs on both sides strongly prefer the other word. Spelling cannot see these; only
//! context can, so the evidence is the bundled word-pair counts and the bar is high.
use crate::tokenizer::Token;
use crate::{context, spelling};

/// QWERTY rows with their horizontal offsets in key widths.
const ROWS: [(&str, f32); 3] = [("qwertyuiop", 0.0), ("asdfghjkl", 0.25), ("zxcvbnm", 0.75)];
fn key(c: char) -> Option<(usize, f32)> {
    ROWS.iter()
        .enumerate()
        .find_map(|(row, (keys, shift))| keys.find(c).map(|i| (row, i as f32 + shift)))
}
fn adjacent(a: char, b: char) -> bool {
    match (key(a), key(b)) {
        (Some((r1, x1)), Some((r2, x2))) => {
            a != b && r1.abs_diff(r2) <= 1 && (x1 - x2).abs() <= 1.0
        }
        _ => false,
    }
}
/// "center"/"centre" and "realise"/"realize" are two valid spellings, not a slip.
fn variant(word: &str, cand: &str) -> bool {
    let swapped = |a: &str, b: &str| {
        a.strip_suffix("er")
            .is_some_and(|stem| b.strip_suffix("re") == Some(stem))
    };
    swapped(word, cand)
        || swapped(cand, word)
        || word.len() >= 5 && word.replace('z', "s") == cand.replace('z', "s")
}
/// Dictionary words one keyboard-adjacent substitution or one adjacent transposition away.
fn slips(word: &str) -> Vec<String> {
    let chars: Vec<char> = word.chars().collect();
    let mut out: Vec<String> = vec![];
    for i in 0..chars.len() {
        for c in ('a'..='z').filter(|c| adjacent(chars[i], *c)) {
            let mut t = chars.clone();
            t[i] = c;
            out.push(t.into_iter().collect());
        }
        if i + 1 < chars.len() && chars[i] != chars[i + 1] {
            let mut t = chars.clone();
            t.swap(i, i + 1);
            out.push(t.into_iter().collect());
        }
    }
    out.sort();
    out.dedup();
    out.retain(|c| spelling::ordinary(c) && !variant(word, c));
    out
}
/// Pair counts below the corpus floor are unknown, not zero.
const FLOOR: u64 = 6_400_000;
/// log10 of how much more the pair with `other` favours `cand` than `word` (0 when neither is
/// above the floor, negative when the original pair is the more common one).
fn side(pair: impl Fn(&str) -> u64, word: &str, cand: &str) -> f64 {
    (pair(cand).max(FLOOR) as f64 / pair(word).max(FLOOR) as f64).log10()
}
/// A neighbour the word pairs can speak for: an adjacent known word of the same sentence.
fn neighbour<'a>(tokens: &'a [Token<'_>], at: usize, index: usize) -> Option<&'a str> {
    let t = tokens.get(at)?;
    (t.is_word
        && t.sentence == tokens[index].sentence
        && t.paragraph == tokens[index].paragraph
        && spelling::known(&t.normalized))
    .then_some(t.normalized.as_str())
}
/// The slip's replacement, when the pair counts on both sides back one candidate overwhelmingly.
/// Bars tuned on the authored set (engine/tests/real_word.json) and BEA dev; see the commit log.
pub fn fix(tokens: &[Token<'_>], index: usize) -> Option<String> {
    let token = &tokens[index];
    let word = token.normalized.as_str();
    if token.proper_name
        || token.surface != word
        || !(2..=9).contains(&word.len())
        || !word.bytes().all(|b| b.is_ascii_lowercase())
        || !spelling::known(word)
        // Reviewed typos that `spelling::suggest` corrects with frames of its own ("ot" is "to").
        || ["ot", "fro", "ew"].contains(&word)
        || spelling::hinglish(word)
        || spelling::lowercase_name(tokens, index)
    {
        return None;
    }
    let left = neighbour(tokens, index.checked_sub(1)?, index)?;
    let right = neighbour(tokens, index + 1, index)?;
    let fw = spelling::frequency(word);
    // A word with no frequency is listed only as a name or acronym ("os", "bo"): only one that is
    // also an adjacent swap from a frequent word reads as a typo rather than a person.
    if fw == 0 && !spelling::swaps_to_common(word) {
        return None;
    }
    // (score, weakest side, candidate)
    let mut best: Vec<(f64, f64, String)> = vec![];
    for cand in slips(word) {
        // Slips happen on the most frequent words; a rarer candidate is as likely a wrong word.
        if spelling::frequency(&cand) < 570 {
            continue;
        }
        let sides = [
            side(|w| context::count(left, w), word, &cand),
            side(|w| context::count(w, right), word, &cand),
        ];
        // A side where the original pair is the more common one vetoes the candidate.
        if sides.iter().any(|v| *v < 0.0) {
            continue;
        }
        // Each side's count already favours a more common word; for a listed word take that
        // prior back out once. A word with no frequency ("os", listed only as a name) has none.
        let prior = (f64::from(spelling::frequency(&cand)) - f64::from(fw)) / 100.0;
        let total = sides.iter().sum::<f64>() - if fw > 0 { prior.clamp(-1.0, 2.5) } else { 0.0 };
        best.push((total, sides[0].min(sides[1]), cand));
    }
    best.sort_by(|a, b| b.0.total_cmp(&a.0));
    let (total, weakest, cand) = best.first()?.clone();
    let bar = if fw > 0 {
        weakest >= 0.8 && total >= 3.0
    } else {
        weakest >= 0.8 && total >= 2.0 || weakest >= 0.3 && total >= 3.0
    };
    (bar && best.get(1).is_none_or(|s| total - s.0 >= 0.8)).then_some(cand)
}

#[cfg(test)]
mod tests {
    use crate::{Request, rewrite_once};
    fn fix(text: &str) -> String {
        let mut req = Request {
            text: text.into(),
            ..Request::default()
        };
        for _ in 0..6 {
            let pass = rewrite_once(&req, false).unwrap();
            if pass.edits.is_empty() {
                break;
            }
            req.text = pass.text;
        }
        req.text
    }
    #[test]
    fn slips_are_fixed_only_on_overwhelming_context_and_correct_text_never_changes() {
        let data: serde_json::Value =
            serde_json::from_str(include_str!("../tests/real_word.json")).unwrap();
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
        eprintln!("real-word slips fixed: {fixed}/{}", pairs.len());
        // Precision is 100%: nothing correct changes and nothing is fixed wrongly.
        assert!(touched.is_empty(), "changed correct text: {touched:?}");
        assert!(wrong.is_empty(), "wrong rewrites: {wrong:?}");
        // Recall is reported, not promised; this floor catches a regression of the mechanism.
        assert!(fixed >= 20, "only {fixed} slips fixed");
    }
    #[test]
    fn the_reported_miss_is_fixed() {
        assert_eq!(fix("this os do bad."), "This is so bad.");
    }
}
