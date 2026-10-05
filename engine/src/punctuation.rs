//! Objective spacing fixes. Never collapse paragraph layout or invent sentence meaning.
use crate::{
    Edit, Request, make_edit, morphology,
    tokenizer::{self, Token},
    utf16_at,
};
use regex::Regex;
use std::sync::OnceLock;
pub fn check(req: &Request, edits: &mut Vec<Edit>) {
    static PATTERNS: OnceLock<Vec<(Regex, &str, &str, &str)>> = OnceLock::new();
    let patterns = PATTERNS.get_or_init(|| {
        vec![
            (
                Regex::new(r"[A-Za-z][ \t]+(?P<target>[,;:!?])").unwrap(),
                "punctuation.before_mark",
                "Remove whitespace before punctuation.",
                "before",
            ),
            (
                Regex::new(r"[A-Za-z](?P<target>[,;:])(?P<next>[A-Za-z])").unwrap(),
                "punctuation.after_mark",
                "Separate words with a space after punctuation.",
                "after",
            ),
        ]
    });
    for (regex, id, reason, kind) in patterns {
        for cap in regex.captures_iter(&req.text) {
            let whole = cap.get(0).unwrap();
            let mark = cap.name("target").unwrap();
            let (a, b, replacement) = if *kind == "before" {
                (whole.start() + 1, mark.start(), String::new())
            } else {
                (mark.end(), mark.end(), " ".into())
            };
            if let Some(edit) = make_edit(
                &req.text,
                utf16_at(&req.text, a),
                utf16_at(&req.text, b),
                replacement,
                "Punctuation",
                id,
                reason,
                0.98,
            ) {
                edits.push(edit);
            }
        }
    }
    sentence_boundaries(req, edits);
    clause_commas(req, edits);
}

fn clause_commas(req: &Request, edits: &mut Vec<Edit>) {
    let tokens = tokenizer::tokenize(&req.text, &req.tokens);
    for (i, token) in tokens.iter().enumerate() {
        if ["yesterday", "tomorrow"].contains(&token.normalized.as_str())
            && crate::starts_sentence(&req.text, token.start_byte, req)
            && tokens.get(i + 1).is_some_and(|t| {
                ["i", "we", "he", "she", "they", "the"].contains(&t.normalized.as_str())
                    || t.proper_name
            })
            && let Some(edit) = make_edit(
                &req.text,
                token.end_utf16,
                token.end_utf16,
                ",".into(),
                "Punctuation",
                "punctuation.introductory_time",
                "Separate this introductory time expression from its clause.",
                0.9,
            )
        {
            edits.push(edit);
        }
        if i == 0 || !["but", "so"].contains(&token.normalized.as_str()) || !tokens[i - 1].is_word {
            continue;
        }
        if token.normalized == "so"
            && !tokens.get(i + 1).is_some_and(|t| {
                [
                    "i", "we", "you", "he", "she", "they", "it", "the", "our", "my", "this", "that",
                ]
                .contains(&t.normalized.as_str())
                    || t.proper_name
            })
        {
            continue;
        }
        // "nothing but", "all but", "is but" (only) and "but also" are not joining clauses, and a
        // second clause needs a subject of its own ("He came but left early" shares one).
        if token.normalized == "but"
            && ([
                "nothing",
                "all",
                "anything",
                "everything",
                "none",
                "no",
                "not",
                "cannot",
            ]
            .contains(&tokens[i - 1].normalized.as_str())
                || ["be", "is", "are", "was", "were", "been", "being"]
                    .contains(&tokens[i - 1].normalized.as_str())
                || tokens
                    .get(i + 1)
                    .is_none_or(|t| !t.is_word || ["for", "one"].contains(&t.normalized.as_str())))
        {
            continue;
        }
        // "but also have": the adverb does not stand in for a subject.
        let subject_at = if tokens
            .get(i + 1)
            .is_some_and(|t| ["also", "then"].contains(&t.normalized.as_str()))
        {
            i + 2
        } else {
            i + 1
        };
        if tokens.get(subject_at).is_none_or(shares_subject)
            || [
                "and", "or", "but", "yet", "nor", "not", "even", "just", "do", "does", "did",
                "doing", "done", "if", "that", "as", "than",
            ]
            .contains(&tokens[i - 1].normalized.as_str())
        {
            continue;
        }
        let start = tokens[..i]
            .iter()
            .rposition(|t| {
                t.sentence != token.sentence || ["but", "so"].contains(&t.normalized.as_str())
            })
            .map(|n| n + 1)
            .unwrap_or(0);
        let end = (i + 1..tokens.len())
            .find(|&n| {
                tokens[n].sentence != token.sentence
                    || ["but", "so"].contains(&tokens[n].normalized.as_str())
            })
            .unwrap_or(tokens.len());
        if clause(&tokens[start..i])
            && clause(&tokens[i + 1..end])
            && let Some(edit) = make_edit(
                &req.text,
                tokens[i - 1].end_utf16,
                tokens[i - 1].end_utf16,
                ",".into(),
                "Punctuation",
                "punctuation.coordinated_clauses",
                "Separate these independent clauses before the coordinating conjunction.",
                0.9,
            )
        {
            edits.push(edit);
        }
    }
}

/// A verb right after "but" means the clause shares its subject with the first ("He came but
/// left early"), so there are no two independent clauses to separate.
fn shares_subject(t: &Token<'_>) -> bool {
    finite(t)
        || morphology::verb(&t.normalized).is_some_and(|v| v.base == t.normalized)
            && crate::spelling::flags(&t.normalized) & 2 == 0
}
pub fn finite(t: &Token<'_>) -> bool {
    [
        "am", "is", "are", "was", "were", "has", "have", "had", "can", "could", "may", "might",
        "must", "shall", "should", "will", "would", "do", "does", "did", "cannot", "don't",
        "doesn't", "didn't", "you're", "we're", "they're", "he's", "she's", "it's", "i'm", "i've",
        "we've", "they've",
    ]
    .contains(&t.normalized.as_str())
        || morphology::verb(&t.normalized)
            .is_some_and(|v| t.normalized == v.third || t.normalized == v.past)
}
fn clause(tokens: &[Token<'_>]) -> bool {
    let words: Vec<_> = tokens.iter().filter(|t| t.is_word).collect();
    words.len() >= 3
        && words.iter().enumerate().skip(1).take(10).any(|(i, t)| {
            finite(t)
                || (morphology::verb(&t.normalized)
                    .is_some_and(|v| v.base == t.normalized && morphology::predicate(&v.base))
                    && ["we", "you", "they", "people", "colleagues", "friends"]
                        .contains(&words[i - 1].normalized.as_str()))
        })
}
/// Words that open a subordinate clause or a question, so a clause beginning with one is not a
/// finished sentence.
const SUBORDINATORS: [&str; 25] = [
    "when", "while", "if", "as", "because", "although", "though", "since", "after", "before",
    "once", "until", "unless", "whenever", "where", "wherever", "whether", "which", "who", "whom",
    "whose", "what", "why", "how", "that",
];
/// Capitalized words that open a sentence and are never names, with "I".
const SENTENCE_OPENERS: [&str; 33] = [
    "The",
    "This",
    "That",
    "These",
    "Those",
    "A",
    "An",
    "I",
    "We",
    "He",
    "She",
    "They",
    "It",
    "Its",
    "My",
    "Our",
    "Her",
    "Their",
    "Each",
    "Why",
    "Where",
    "When",
    "How",
    "What",
    "If",
    "Never",
    "Rarely",
    "Not",
    "Tomorrow",
    "Yesterday",
    "Then",
    "Last",
    "By",
];
const AUXILIARIES: &[&str] = &[
    "am",
    "is",
    "are",
    "was",
    "were",
    "has",
    "have",
    "had",
    "can",
    "could",
    "may",
    "might",
    "must",
    "shall",
    "should",
    "will",
    "would",
    "did",
    "cannot",
    "can't",
    "couldn't",
    "won't",
    "wouldn't",
    "shouldn't",
    "don't",
    "doesn't",
    "didn't",
    "isn't",
    "wasn't",
    "haven't",
    "hasn't",
];
/// Beside the subordinators, first words that make a clause a modifier, not an independent one.
const OPENERS: [&str; 26] = [
    "in", "on", "at", "by", "for", "with", "from", "to", "of", "into", "during", "over", "under",
    "through", "between", "that", "upon", "around", "behind", "beside", "across", "along", "above",
    "below", "without", "within",
];
fn sentence_boundaries(req: &Request, edits: &mut Vec<Edit>) {
    let tokens = tokenizer::tokenize(&req.text, &req.tokens);
    let mut start = 0;
    for i in 0..tokens.len() {
        let t = &tokens[i];
        if [".", "!", "?", ";"].contains(&t.surface) {
            start = i + 1;
            continue;
        }
        if i == 0 || tokens[i - 1].paragraph != t.paragraph {
            start = i;
            continue;
        }
        if i <= start || !t.is_word || !t.surface.chars().next().is_some_and(char::is_uppercase) {
            continue;
        }
        let named_start = t.proper_name
            || crate::spelling::name_only(&t.normalized) && tokens.get(i + 1).is_some_and(finite)
            || t.surface.ends_with("'s")
            || t.surface.ends_with("’s")
            || (!crate::spelling::known(&t.normalized) && tokens.get(i + 1).is_some_and(finite));
        if !named_start && !SENTENCE_OPENERS.contains(&t.surface) {
            continue;
        }
        let previous = &tokens[i - 1];
        // A name right after a preposition, determiner or transitive verb is its object
        // ("I talked to Aman and he said it is fine"), not the start of a new sentence.
        if [
            "to", "with", "for", "from", "of", "at", "in", "on", "by", "about", "into", "onto",
            "like", "than", "as", "per", "via", "near", "after", "before", "between", "among",
            "through", "over", "under", "upon", "around", "toward", "towards", "against",
            "without", "within", "the", "a", "an", "my", "your", "his", "our", "their", "its",
            "dear", "hey", "hi", "hello", "thanks", "thank", "cc", "ask", "tell", "invite", "call",
            "ping", "email", "meet", "see", "told", "asked", "met", "called", "emailed", "invited",
            "thanked", "pinged", "texted", "text", "message", "messaged", "contact",
        ]
        .contains(&previous.normalized.as_str())
            || (t.proper_name
                && morphology::verb(&previous.normalized).is_some_and(|v| {
                    morphology::predicate(&v.base)
                        && crate::spelling::flags(&previous.normalized) & 2 == 0
                }))
        {
            continue;
        }
        // A name after another capitalized word ("Aman Jain") is one name, not a new sentence.
        if named_start
            && previous.is_word
            && previous.surface.chars().count() > 1
            && previous
                .surface
                .chars()
                .next()
                .is_some_and(char::is_uppercase)
        {
            continue;
        }
        if t.surface == "I"
            && tokens[start..i].iter().rev().take(7).any(|x| {
                morphology::verb(&x.normalized).is_some_and(|v| {
                    ["tell", "think", "know", "believe", "say", "ask", "hear"]
                        .contains(&v.base.as_str())
                })
            })
        {
            continue;
        }
        if !previous.is_word
            || [
                "and", "or", "but", "so", "that", "because", "if", "when", "while", "although",
                "since", "called", "named", "titled", "said", "says", "asked", "asks", "me", "us",
                "him", "her", "them", "you", "think", "thought", "know", "knew", "believe",
                "believed", "am", "is", "are", "was", "were", "be", "been", "being", "has", "have",
                "had", "do", "does", "did", "can", "could", "will", "would", "shall", "should",
                "may", "might", "must",
            ]
            .contains(&previous.normalized.as_str())
        {
            continue;
        }
        let gap = &req.text[previous.end_byte..t.start_byte];
        if gap.is_empty() || !gap.chars().all(|c| c == ' ' || c == '\t') {
            continue;
        }
        let right_end = (i + 1..tokens.len())
            .find(|&j| {
                tokens[j].paragraph != t.paragraph
                    || [".", "!", "?", ";"].contains(&tokens[j].surface)
            })
            .unwrap_or(tokens.len());
        if !clause(&tokens[start..i]) || !clause(&tokens[i..right_end]) {
            continue;
        }
        // Only a run-on whose first clause is plainly independent: it opens with its subject (no
        // subordinator, question word or preposition), no subordinate clause is still open at its
        // end, and both sides are long. Published prose joins clauses far more often than it runs
        // them together, so anything less certain stays untouched.
        let words = |range: &[Token<'_>]| range.iter().filter(|x| x.is_word).count();
        let first = tokens
            .get(start)
            .map(|t| t.normalized.as_str())
            .unwrap_or("");
        // The run of words right before the name, since the last comma or dash, must itself be
        // long: a short one is an adverbial or conjunction phrase ("and then I", "at least I").
        let run = tokens[start..i]
            .iter()
            .rev()
            .take_while(|x| x.is_word)
            .count();
        // A short pair is accepted only when the first clause plainly ends: on an adjective or an
        // adverb ("The plan is clear We should"), not a noun that a reduced relative clause could
        // modify ("the palaces I had explored").
        let word = previous.normalized.as_str();
        let predicate_adjective = crate::spelling::flags(word) & 8 != 0
            && i >= 2
            && ["is", "are", "was", "were", "be", "been"]
                .contains(&tokens[i - 2].normalized.as_str());
        // "Why is the door locked When will it open": an inverted question is a finished clause.
        let question = ["why", "where", "when", "how", "what", "who"].contains(&first)
            && tokens.get(start + 1).is_some_and(|x| {
                AUXILIARIES.contains(&x.normalized.as_str())
                    || ["do", "does"].contains(&x.normalized.as_str())
            });
        let plain_end = question
            || predicate_adjective
            || word.ends_with("ly")
            || [
                "yesterday",
                "today",
                "tomorrow",
                "now",
                "here",
                "there",
                "away",
                "home",
            ]
            .contains(&word);
        let (left, right) = if plain_end { (3, 3) } else { (6, 5) };
        // A capitalized word that is never a name, mid-sentence ("The", "We", "If"), is the
        // writer's own sentence start, so two clauses around it are enough. "I" and names are
        // always capitalized and need the stricter evidence.
        let capitalized_opener = t.surface != "I" && SENTENCE_OPENERS.contains(&t.surface);
        let wh = capitalized_opener
            && [
                "why", "where", "when", "how", "what", "who", "whose", "which",
            ]
            .contains(&first);
        // The segment since the last comma or dash is itself a clause, not a conjunct, a
        // subordinate clause or a prepositional phrase ("and if McCarthy is condemned I").
        let run_first = tokens[i - run.min(i)..i]
            .first()
            .map_or("", |x| x.normalized.as_str());
        // A subordinate clause needs a main verb before it ("Some time before he introduced
        // himself I'd"): the first finite word comes ahead of the first subordinator.
        let main_verb_first = tokens[start..i]
            .iter()
            .position(|x| SUBORDINATORS.contains(&x.normalized.as_str()))
            .is_none_or(|k| tokens[start..start + k].iter().any(finite));
        // "The Wizard of Oz", "We Make Contact": a capitalized title, not a sentence start.
        let title = ["The", "A", "An", "We"].contains(&t.surface)
            && tokens.get(i + 1).is_some_and(|x| {
                x.surface.starts_with(char::is_uppercase) && !SENTENCE_OPENERS.contains(&x.surface)
            });
        if capitalized_opener && title {
            continue;
        }
        if !capitalized_opener
            && (words(&tokens[start..i]) < left
            || OPENERS.contains(&run_first)
            || SUBORDINATORS.contains(&run_first)
            || ["and", "but", "or", "so", "yet", "nor"].contains(&run_first)
            || !main_verb_first
            || run < left
            || tokens[start..i].iter().rev().take(3).any(|x| {
                ["and", "but", "or", "yet", "nor", "then"].contains(&x.normalized.as_str())
            })
            || words(&tokens[i..right_end]) < right
            || OPENERS.contains(&first)
            || !question && SUBORDINATORS.contains(&first)
            // A subordinate clause still open at the end ("the place where Priya"), as opposed to
            // one that already has its verb ("before the meeting starts Maya").
            || !question
                && tokens[start..i]
                    .iter()
                    .rposition(|x| SUBORDINATORS.contains(&x.normalized.as_str()))
                    .is_some_and(|k| {
                        // A lowercase unknown word is a damaged verb, which closes the clause.
                        !tokens[start + k + 1..i].iter().any(|x| {
                            finite(x)
                                || x.is_word
                                    && x.surface.starts_with(char::is_lowercase)
                                    && !crate::spelling::known(&x.normalized)
                        })
                    })
            // The verb follows the subject at once ("Aman will"). A plural noun also looks finite
            // ("Hollywood films"), so the verb must be unambiguous.
            || !tokens[i + 1..]
                .iter()
                .take_while(|x| x.is_word)
                .take(if t.surface.ends_with(['s', 'S']) && t.surface.contains(['\'', '\u{2019}']) { 3 } else { 1 })
                .any(|x| {
                    finite(x)
                        && x.surface.starts_with(char::is_lowercase)
                        && (crate::spelling::flags(&x.normalized) & 2 == 0
                            || AUXILIARIES.contains(&x.normalized.as_str()))
                }))
        {
            continue;
        }
        if let Some(edit) = make_edit(
            &req.text,
            previous.end_utf16,
            previous.end_utf16,
            if question || wh { "?" } else { "." }.into(),
            "Punctuation",
            "punctuation.missing_sentence_boundary",
            "Separate these complete clauses with sentence punctuation.",
            0.88,
        ) {
            edits.push(edit);
        }
        start = i;
    }
}

#[cfg(test)]
mod name_tests {
    use super::*;
    /// Boundary marks proposed for `text`, with `names` tagged the way the language tagger does.
    fn boundaries(text: &str, names: &[&str]) -> Vec<String> {
        let mut hints = vec![];
        for name in names {
            for (byte, _) in text.match_indices(name) {
                let start = text[..byte].encode_utf16().count();
                hints.push(crate::TokenHint {
                    start_utf16: start,
                    end_utf16: start + name.encode_utf16().count(),
                    pos: "Noun".into(),
                    lemma: String::new(),
                    name: true,
                    ..Default::default()
                });
            }
        }
        let req = Request {
            text: text.into(),
            tokens: hints,
            ..Request::default()
        };
        let mut edits = vec![];
        check(&req, &mut edits);
        edits
            .into_iter()
            .filter(|e| e.rule_id == "punctuation.missing_sentence_boundary")
            .map(|e| e.replacement)
            .collect()
    }
    #[test]
    fn a_name_is_never_a_sentence_start_after_an_object_marker_or_another_name() {
        for (text, names) in [
            ("I talked to Aman and he said it is fine.", &["Aman"][..]),
            ("I talked to Mark and he said it is fine.", &["Mark"]),
            (
                "I talked to Zo\u{eb} and she said it is fine.",
                &["Zo\u{eb}"],
            ),
            (
                "I met Aman Jain, and Aman's friend said aman jain was kind.",
                &["Aman", "Jain"],
            ),
            ("I met Aman Jain and he said it is fine.", &["Aman", "Jain"]),
        ] {
            assert!(boundaries(text, names).is_empty(), "{text}");
        }
    }
    #[test]
    fn a_real_run_on_still_gets_its_period() {
        assert_eq!(
            boundaries(
                "The quarterly report for the finance team is done Aman will send it to everyone tomorrow morning",
                &["Aman"]
            ),
            ["."]
        );
    }
    #[test]
    fn a_clause_that_is_not_plainly_finished_gets_no_period() {
        for (text, names) in [
            // Subordinate or modifying openers need a comma, not a period.
            (
                "When the harbour lights came on at dusk Priya walked down to the quay alone.",
                &["Priya"][..],
            ),
            (
                "Because the train from the coast was late again Priya missed her connection to Leeds.",
                &["Priya"],
            ),
            // A relative or subordinating word right before the name keeps the clause open.
            (
                "The old cottage by the river is the place where Priya spent every summer as a child.",
                &["Priya"],
            ),
            // Too short on either side to be sure.
            ("The team met Priya will send it.", &["Priya"]),
            // A conditional or time clause before the name has no main verb of its own.
            (
                "I will keep your secret, and if Mara is blamed Priya will speak up for her.",
                &["Mara", "Priya"],
            ),
            (
                "Some time before the committee met Priya had finished the whole report.",
                &["Priya"],
            ),
            // A capitalized title is not a sentence start.
            (
                "The students then watched the film The Lion King and sang along happily.",
                &[],
            ),
            // A question opener never gets a period.
            (
                "Why did the committee reject the proposal so late Priya asked her colleagues quietly.",
                &["Priya"],
            ),
        ] {
            assert!(boundaries(text, names).is_empty(), "{text}");
        }
    }
    #[test]
    fn an_i_after_a_finished_clause_is_not_split_off_mid_sentence() {
        for text in [
            "As I opened the door I seemed to hear a low whistle from the garden.",
            "The shopkeeper said that he knew the road well and I trusted his directions all day.",
            "She watched the harbour for an hour before I joined her on the quay.",
        ] {
            assert!(boundaries(text, &[]).is_empty(), "{text}");
        }
    }
}
