//! Real-word keyboard slips ("this os bad", "I come form India"): a known word that is one
//! adjacent-key substitution or one adjacent transposition from another known word, where the
//! word pairs on both sides strongly prefer the other word. Spelling cannot see these; only
//! context can, so the evidence is the bundled word-pair counts and the bar is high.
use crate::tokenizer::Token;
use crate::{context, morphology, spelling};

/// QWERTY rows with their horizontal offsets in key widths.
const ROWS: [(&str, f32); 3] = [("qwertyuiop", 0.0), ("asdfghjkl", 0.25), ("zxcvbnm", 0.75)];
fn key(c: char) -> Option<(usize, f32)> {
    ROWS.iter()
        .enumerate()
        .find_map(|(row, (keys, shift))| keys.find(c).map(|i| (row, i as f32 + shift)))
}
pub(crate) fn adjacent(a: char, b: char) -> bool {
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
/// Words that open a clause after "but" and never after the particle "out" or the noun "bit":
/// a subject, a sentence adverb or a short verdict ("working, out fine", "Bit honestly I don't mind").
const CLAUSE_OPENERS: &str = "\
    i we they he she i'm i'll i've i'd we're we'll we've they're they'll he's she's it's \
    that's there's it'll you're you'll honestly still maybe also then not totally really \
    actually definitely probably anyway otherwise instead sadly luckily unfortunately \
    hopefully thankfully overall apparently obviously clearly surely somehow seriously yeah \
    fine worth nothing nobody everyone everything only never no";
/// Finite verbs that show a determiner phrase after the slip is a clause's subject ("out the
/// demo was rough"), not the object of "out" ("out the door").
const FINITE: &[&str] = &[
    "is", "was", "are", "were", "has", "had", "will", "would", "can", "could", "went", "got",
    "seems", "seemed", "looks", "looked", "didn't", "doesn't", "isn't", "wasn't", "can't", "won't",
    "felt", "feels", "did", "does", "should", "might", "must",
];
/// "but" typed as "out", "bit" or "nut" where a clause opens: after a comma or semicolon, or at a
/// sentence start. Lists of particles ("in, out, up") and "out of", "out there", "out the door"
/// keep their word; the comma is context here, not a reason to give up.
fn clause_but(tokens: &[Token<'_>], index: usize) -> Option<&'static str> {
    let token = &tokens[index];
    let word = token.normalized.as_str();
    if !["out", "bit", "nut"].contains(&word) || token.proper_name {
        return None;
    }
    let capital = token.surface.starts_with(char::is_uppercase);
    if token.surface[1..].chars().any(char::is_uppercase) {
        return None;
    }
    let same = |t: &Token<'_>| t.sentence == token.sentence && t.paragraph == token.paragraph;
    let start = match index.checked_sub(1).map(|i| (i, &tokens[i])) {
        None => true,
        Some((_, prev)) if !same(prev) => true,
        Some((i, prev)) if [",", ";"].contains(&prev.surface) => {
            // "in, out, up" and "inside out, out of" are lists of particles, not clauses.
            let before = i.checked_sub(1).map(|j| tokens[j].normalized.as_str());
            !before.is_some_and(|b| {
                [
                    "in", "out", "up", "down", "inside", "over", "on", "off", "back", "and", "or",
                ]
                .contains(&b)
                    || b.starts_with(|c: char| c.is_ascii_digit())
            })
        }
        _ => false,
    };
    // Mid-sentence "but" after a comma is lowercase; a capital "Out" there is a title or a name.
    if !start || (capital && index > 0 && same(&tokens[index - 1])) {
        return None;
    }
    let next = tokens.get(index + 1).filter(|t| t.is_word && same(t))?;
    // "out it goes" and "out you go" are idioms; "bit it" and "nut you" are not.
    let opener = CLAUSE_OPENERS
        .split_whitespace()
        .any(|w| w == next.normalized)
        || word != "out" && ["it", "you"].contains(&next.normalized.as_str());
    let subject_phrase = [
        "the", "my", "your", "our", "their", "his", "her", "this", "that", "these", "those",
    ]
    .contains(&next.normalized.as_str())
        && tokens.get(index + 2).is_some_and(|noun| {
            noun.is_word
                && ![
                    "door", "doors", "window", "windows", "back", "front", "gate", "way", "side",
                    "car", "room", "house", "building", "office", "kitchen", "garage", "station",
                ]
                .contains(&noun.normalized.as_str())
        })
        && tokens[index + 3..]
            .iter()
            .take(4)
            .take_while(|t| same(t) && ![",", ";", ":"].contains(&t.surface))
            .any(|t| FINITE.contains(&t.normalized.as_str()));
    (opener || subject_phrase).then_some(if capital { "But" } else { "but" })
}
/// Subject pronouns: what follows one is a verb or an auxiliary, so a known word that never
/// follows one ("I cam do", "we fan push") is a slip of a word that very often does.
const SUBJECTS: &[&str] = &["i", "we", "they", "he", "she", "you"];
/// Function words a slip after a subject pronoun is never taken for: "you ad me" is not "you and me".
const NOT_AFTER_SUBJECT: &[&str] = &[
    "and", "or", "the", "a", "an", "of", "to", "in", "on", "at", "by", "for", "but", "as", "so",
    "if", "is", "it",
];
/// After a subject pronoun, a word whose pairs on both sides are unattested in the corpus, while
/// one keyboard-slip or one-letter-drop candidate is common on both sides.
fn after_subject(tokens: &[Token<'_>], index: usize) -> Option<String> {
    let token = &tokens[index];
    let word = token.normalized.as_str();
    let left = neighbour(tokens, index.checked_sub(1)?, index)?;
    let right = neighbour(tokens, index + 1, index)?;
    // A word attested after "to", a modal or "not" is a verb ("we hop that fence"), which may
    // follow a subject even when the corpus pair is too rare to be listed.
    if !SUBJECTS.contains(&left)
        || context::count(left, word) > 0
        || context::count(word, right) > 0
        || spelling::frequency(word) == 0
        || ["to", "will", "can", "not", "would", "could"]
            .iter()
            .any(|v| context::count(v, word) > 0)
    {
        return None;
    }
    let mut cands = slips(word);
    let chars: Vec<char> = word.chars().collect();
    for i in 0..=chars.len() {
        for c in 'a'..='z' {
            let mut t = chars.clone();
            t.insert(i, c);
            let t: String = t.into_iter().collect();
            if spelling::ordinary(&t) && !variant(word, &t) {
                cands.push(t);
            }
        }
    }
    cands.sort();
    cands.dedup();
    let mut best: Vec<(f64, String)> = cands
        .into_iter()
        .filter(|c| {
            spelling::frequency(c) >= 500
                && spelling::frequency(c) >= spelling::frequency(word) + 100
                && !NOT_AFTER_SUBJECT.contains(&c.as_str())
        })
        .filter_map(|c| {
            let (a, b) = (context::count(left, &c), context::count(&c, right));
            // Both pairs already count the candidate's own frequency; take it out once, so "I cam
            // by" weighs "came" against "can" by context rather than by how common "can" is.
            let prior = f64::from(spelling::frequency(&c)) / 100.0;
            (a >= 2 * FLOOR && b >= FLOOR)
                .then(|| ((a as f64).log10() + (b as f64).log10() - prior, c))
        })
        .collect();
    best.sort_by(|a, b| b.0.total_cmp(&a.0));
    let (score, cand) = best.first()?.clone();
    best.get(1)
        .is_none_or(|s| score - s.0 >= 0.5)
        .then_some(cand)
}
/// Words that name a part or a quantity and take "of", never a condition after them: "a lot of",
/// "most of", "one of", "the rest of".
const PARTITIVES: &[&str] = &[
    "lot", "lots", "bit", "bunch", "couple", "kind", "sort", "type", "number", "piece", "pair",
    "set", "part", "rest", "most", "many", "few", "some", "none", "half", "both", "plenty", "ton",
    "tons", "list", "group", "variety", "series", "range", "one",
];
/// Words of quantity that also stand before a real condition ("eats a lot if food is free"): a
/// clause with a verb after "if" keeps it there, unlike after "most" or "one".
const LOOSE_PARTITIVES: &[&str] = &[
    "lot", "lots", "bit", "bunch", "couple", "plenty", "ton", "tons",
];
/// Words that open a subject: after "if" they start a clause ("if the shop asks", "if they ask").
const SUBJECT_OPENERS: &[&str] = &[
    "i",
    "you",
    "he",
    "she",
    "it",
    "we",
    "they",
    "there",
    "the",
    "a",
    "an",
    "my",
    "your",
    "his",
    "her",
    "our",
    "their",
    "this",
    "that",
    "these",
    "those",
    "some",
    "any",
    "no",
    "every",
    "each",
    "someone",
    "anyone",
    "everyone",
    "nobody",
    "somebody",
    "anybody",
    "everybody",
];
/// Whether the words after `tokens[index]` read as a clause with a finite verb (a subject, then a
/// verb within a few words, before any punctuation): what a conjunction like "if" introduces.
fn clause_follows(tokens: &[Token<'_>], index: usize) -> bool {
    let token = &tokens[index];
    let mut words = tokens[index + 1..]
        .iter()
        .take_while(|t| t.sentence == token.sentence && t.is_word);
    let Some(subject) = words.next() else {
        return false;
    };
    (SUBJECT_OPENERS.contains(&subject.normalized.as_str())
        || spelling::flags(&subject.normalized) & 2 != 0)
        && words.take(5).any(|t| {
            FINITE.contains(&t.normalized.as_str())
                || morphology::verb(&t.normalized)
                    .is_some_and(|v| v.third == t.normalized || v.past == t.normalized)
        })
}
/// "a lot if apples", "plenty if room", "lots if friends": "if" right after a word of quantity
/// and before a bare noun phrase that ends the clause is "of". The clause after a real "if"
/// ("if apples are cheap", "if necessary") carries a verb or an adjective, so only a noun that
/// is followed by the end of the sentence, a mark or a preposition counts.
fn quantity_if(tokens: &[Token<'_>], index: usize) -> bool {
    let token = &tokens[index];
    let same = |t: &Token<'_>| t.sentence == token.sentence && t.paragraph == token.paragraph;
    let Some(before) = index.checked_sub(1).map(|i| &tokens[i]) else {
        return false;
    };
    if token.surface != "if"
        || !same(before)
        || ![
            "lot", "lots", "plenty", "bunch", "couple", "number", "pair", "rest",
        ]
        .contains(&before.normalized.as_str())
    {
        return false;
    }
    let mut at = index + 1;
    if tokens.get(at).is_some_and(|t| {
        same(t)
            && ["the", "a", "an", "my", "your", "our", "their", "his", "her"]
                .contains(&t.normalized.as_str())
    }) {
        at += 1;
    }
    let Some(_noun) = tokens.get(at).filter(|t| {
        same(t)
            && t.is_word
            && t.surface.starts_with(char::is_lowercase)
            && spelling::ordinary(&t.normalized)
            && spelling::flags(&t.normalized) & 2 != 0
            && !SUBJECT_OPENERS.contains(&t.normalized.as_str())
            // "if necessary", "if possible", "if needed": the tails of a real condition.
            && !["necessary", "possible", "needed", "required", "desired", "wanted", "applicable",
                "available", "appropriate", "relevant", "anything", "everything", "so", "not", "ever"]
            .contains(&t.normalized.as_str())
            && !["ible", "able", "ary", "ed"].iter().any(|e| t.normalized.ends_with(e))
    }) else {
        return false;
    };
    tokens.get(at + 1).is_none_or(|t| {
        !same(t)
            || !t.is_word
            || ["in", "on", "at", "for", "to", "from", "with", "of", "by"]
                .contains(&t.normalized.as_str())
    })
}
/// A word the sentence builds a construction around, so that it is right where it stands and a
/// keyboard slip is not the reading: "neither ... nor" (and "nor" opening a sentence) and an
/// "if" that opens a condition ("Keep a copy if the shop asks"), never one after a quantity
/// ("a lot if apples").
fn licensed(tokens: &[Token<'_>], index: usize) -> bool {
    let token = &tokens[index];
    let same = |t: &Token<'_>| t.sentence == token.sentence && t.paragraph == token.paragraph;
    match token.normalized.as_str() {
        "nor" => {
            index == 0
                || !same(&tokens[index - 1])
                || tokens[..index]
                    .iter()
                    .rev()
                    .take_while(|t| same(t))
                    .any(|t| {
                        [
                            "neither", "not", "no", "never", "nobody", "nothing", "none",
                            "nowhere", "hardly", "barely", "cannot", "without",
                        ]
                        .contains(&t.normalized.as_str())
                            || t.normalized.ends_with("n't")
                    })
        }
        "if" => {
            let partitive = index
                .checked_sub(1)
                .map(|i| &tokens[i])
                .is_some_and(|p| same(p) && PARTITIVES.contains(&p.normalized.as_str()));
            let loose = index
                .checked_sub(1)
                .map(|i| &tokens[i])
                .is_some_and(|p| LOOSE_PARTITIVES.contains(&p.normalized.as_str()));
            (!partitive || loose) && clause_follows(tokens, index)
        }
        _ => false,
    }
}
/// The slip's replacement, when the pair counts on both sides back one candidate overwhelmingly.
/// Bars tuned on the authored set (engine/tests/real_word.json) and BEA dev; see the commit log.
pub fn fix(tokens: &[Token<'_>], index: usize) -> Option<String> {
    if let Some(but) = clause_but(tokens, index) {
        return Some(but.into());
    }
    if quantity_if(tokens, index) {
        return Some("of".into());
    }
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
        || licensed(tokens, index)
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
    let chosen = best.first().and_then(|(total, weakest, cand)| {
        let bar = if fw > 0 {
            *weakest >= 0.8 && *total >= 3.0
        } else {
            *weakest >= 0.8 && *total >= 2.0 || *weakest >= 0.3 && *total >= 3.0
        };
        (bar && best.get(1).is_none_or(|s| total - s.0 >= 0.8)).then(|| cand.clone())
    });
    chosen.or_else(|| after_subject(tokens, index))
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
    fn a_construction_the_sentence_builds_keeps_its_word() {
        // "neither ... nor" and a sentence-opening "nor" are right as typed.
        for text in [
            "Neither the manager nor the staff knew the answer.",
            "He neither called nor wrote back.",
            "She could not sing nor dance.",
            "Nor did the plan work.",
            "There is no tea nor coffee left.",
        ] {
            assert_eq!(fix(text), text, "{text}");
        }
        // An "if" that opens a condition is right where the words after it are a clause.
        for text in [
            "Keep a copy if the shop asks for it.",
            "Call me if the printer jams again.",
            "We can leave early if they agree.",
            "Ask if the office is open on Sunday.",
            "Do we need friends or family members if technology can care for us?",
        ] {
            assert_eq!(fix(text), text, "{text}");
        }
        // After a quantity the same letters are a slip of "of", and are still fixed.
        assert_eq!(
            fix("We ate a lot if the cake."),
            "We ate a lot of the cake."
        );
        assert_eq!(fix("Most if them left early."), "Most of them left early.");
        // A quantity before a bare noun phrase that ends the clause is "of", too.
        assert_eq!(fix("I want a lot if apples."), "I want a lot of apples.");
        assert_eq!(fix("There is plenty if room."), "There is plenty of room.");
        assert_eq!(fix("He has lots if friends."), "He has lots of friends.");
        // A condition after a quantity keeps its "if".
        for text in [
            "I will pay a lot if necessary.",
            "She saves a lot if possible.",
            "He eats a lot if food is free.",
            "It hurts a lot if you press.",
        ] {
            assert_eq!(fix(text), text, "{text}");
        }
    }
    #[test]
    fn the_reported_miss_is_fixed() {
        assert_eq!(fix("this os do bad."), "This is so bad.");
        assert_eq!(
            fix("I love you. This is so bad. I don’t think this is working, out fine."),
            "I love you. This is so bad. I don’t think this is working, but fine."
        );
        // The comma is context, not a reason to give up; particles keep their word.
        for text in [
            "Everything is working out fine so far.",
            "The tickets sold out, fine by me.",
            "Get in, out of the rain.",
        ] {
            assert_eq!(fix(text), text);
        }
    }
}
