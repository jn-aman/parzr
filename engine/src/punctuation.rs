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
            // "e:mail", "C:drive": a colon after a single letter is part of the word.
            if *kind == "after"
                && mark.as_str() == ":"
                && !req.text[..whole.start()]
                    .chars()
                    .next_back()
                    .is_some_and(char::is_alphanumeric)
            {
                continue;
            }
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
    dates_and_adverbs(req, edits);
    crate::marks::check(req, edits);
    crate::clauses::check(req, edits);
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
        if i > 0
            && tokens[i - 1].is_word
            && ["and", "or", "yet"].contains(&token.normalized.as_str())
        {
            crate::clauses::coordinated(req, &tokens, i, edits);
            continue;
        }
        if i == 0
            || !["but", "so"].contains(&token.normalized.as_str())
            || !tokens[i - 1].is_word
            || crate::marks::inside_open_quote(&req.text, token.start_byte)
        {
            continue;
        }
        // "left early so that we could park": a purpose clause takes no comma. ("so that is why"
        // has "that" for its subject: a verb follows it.)
        if token.normalized == "so"
            && tokens.get(i + 1).is_some_and(|t| t.normalized == "that")
            && tokens.get(i + 2).is_some_and(|t| {
                t.is_word
                    && (!finite(t) || crate::clauses::subject_contraction(&t.normalized))
                    && !AUX.contains(&t.normalized.as_str())
                    && !t.normalized.ends_with("n't")
            })
        {
            continue;
        }
        if token.normalized == "so"
            && !tokens.get(i + 1).is_some_and(|t| {
                [
                    "i", "we", "you", "he", "she", "they", "it", "the", "our", "my", "this", "that",
                ]
                .contains(&t.normalized.as_str())
                    || crate::clauses::subject_contraction(&t.normalized)
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
                || tokens.get(i + 1).is_none_or(|t| {
                    !t.is_word || ["for", "one", "to"].contains(&t.normalized.as_str())
                }))
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
        // "Although it was cold but he came", "Because it rained so we left": the opening word
        // already links the clauses and the doubled conjunction is dropped, so no comma goes
        // before it.
        if start == 0 || tokens[start - 1].sentence != token.sentence {
            let first = tokens[start].normalized.as_str();
            let second = tokens.get(start + 1).map_or("", |t| t.normalized.as_str());
            if token.normalized == "but"
                && (["although", "though"].contains(&first)
                    || first == "even" && ["though", "if"].contains(&second))
                || token.normalized == "so" && ["because", "since"].contains(&first)
            {
                continue;
            }
        }
        // "not just a threat to our environment but to our values": a correlative, not two clauses.
        if token.normalized == "but"
            && tokens[start..i]
                .iter()
                .any(|t| ["just", "only", "merely", "simply"].contains(&t.normalized.as_str()))
            && tokens[start..i].iter().any(|t| t.normalized == "not")
        {
            continue;
        }
        // The second clause ends at its first comma ("is new but evolving fast, and I would…").
        let end = (i + 1..tokens.len())
            .find(|&n| {
                tokens[n].sentence != token.sentence
                    || ["but", "so"].contains(&tokens[n].normalized.as_str())
                    || tokens[n].surface == ","
            })
            .unwrap_or(tokens.len());
        // A contracted subject ("so I'm") or a clause the plain check misses ("I'd love to")
        // counts only after a long first clause: short pairs read fine without the comma.
        let plain = clause(&tokens[start..i])
            && clause(&tokens[i + 1..end])
            && !crate::clauses::subject_contraction(&tokens[subject_at].normalized);
        let long = tokens[start..i].iter().filter(|t| t.is_word).count() >= 6;
        if (plain
            || long
                && crate::clauses::clause_at(&tokens, start, i).is_some()
                && crate::clauses::clause_at(&tokens, subject_at, end).is_some())
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

const MONTH_NAMES: [&str; 12] = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
];
/// Adverbs that link a clause to the one before; after a semicolon they take a comma ("; however,
/// the plan").
const LINKING: [&str; 8] = [
    "however",
    "therefore",
    "moreover",
    "furthermore",
    "consequently",
    "nevertheless",
    "nonetheless",
    "otherwise",
];
const AUX: [&str; 20] = [
    "am", "is", "are", "was", "were", "has", "have", "had", "do", "does", "did", "can", "could",
    "will", "would", "should", "may", "might", "must", "shall",
];
/// Commas that are not a matter of style: inside an American date ("October 20, 1861"), around
/// "however" between a subject or auxiliary and its verb ("The police, however, have said", "He did, however, make"), and after a linking
/// adverb that follows a semicolon.
fn dates_and_adverbs(req: &Request, edits: &mut Vec<Edit>) {
    let text = &req.text;
    let tokens = tokenizer::tokenize(text, &req.tokens);
    let gap = |a: &Token<'_>, b: &Token<'_>| &text[a.end_byte..b.start_byte];
    let spaced = |a: &Token<'_>, b: &Token<'_>| {
        let g = gap(a, b);
        !g.is_empty() && g.chars().all(|c| c == ' ')
    };
    let comma = |edits: &mut Vec<Edit>, t: &Token<'_>, id: &str, reason: &str| {
        if let Some(edit) = make_edit(
            text,
            t.end_utf16,
            t.end_utf16,
            ",".into(),
            "Punctuation",
            id,
            reason,
            0.9,
        ) {
            edits.push(edit);
        }
    };
    for i in 0..tokens.len() {
        let t = &tokens[i];
        // "October 20 1861" is "October 20, 1861" in American English; British dates put the day
        // first ("20 October 1861") and take no comma.
        if req.dialect != "british"
            && MONTH_NAMES.contains(&t.surface)
            && let (Some(day), Some(year)) = (tokens.get(i + 1), tokens.get(i + 2))
            && spaced(t, day)
            && spaced(day, year)
            && day
                .surface
                .trim_end_matches(['s', 't', 'n', 'd', 'r', 'h'])
                .parse::<u32>()
                .is_ok_and(|d| (1..=31).contains(&d))
            && day.surface.len() <= 4
            && year.surface.len() == 4
            && year
                .surface
                .parse::<u32>()
                .is_ok_and(|y| (1000..=2099).contains(&y))
            && text[year.end_byte..].chars().next().is_none_or(|c| {
                c.is_whitespace() || ",;)!?\u{2013}\u{2014}\"'".contains(c)
                    || c == '.' && !text[year.end_byte + 1..].starts_with(|d: char| d.is_ascii_digit())
            })
            // "March 3 1500 troops": a count, not a year.
            && !tokens.get(i + 3).is_some_and(|n| {
                n.is_word
                    && spaced(year, n)
                    && n.surface.starts_with(char::is_lowercase)
                    && n.normalized.ends_with('s')
                    && crate::spelling::flags(&n.normalized) & 2 != 0
            })
        {
            comma(
                edits,
                day,
                "punctuation.date_comma",
                "Separate the day from the year with a comma.",
            );
        }
        if !LINKING.contains(&t.surface) || i == 0 {
            continue;
        }
        let prev = &tokens[i - 1];
        let Some(next) = tokens.get(i + 1).filter(|n| n.is_word && spaced(t, n)) else {
            continue;
        };
        if prev.surface == ";" {
            let end = (i + 1..tokens.len())
                .find(|&k| tokens[k].sentence != t.sentence || tokens[k].paragraph != t.paragraph)
                .unwrap_or(tokens.len());
            if crate::clauses::clause_at(&tokens, i + 1, end).is_some() {
                comma(
                    edits,
                    t,
                    "punctuation.introductory_comma",
                    "Put a comma after the linking adverb.",
                );
            }
            continue;
        }
        if t.surface != "however" || !prev.is_word || !spaced(prev, t) {
            continue;
        }
        // "He did however make", "was however built": right after an auxiliary "however" is an
        // aside. After a noun it is one only when the verb follows ("The police however have").
        let p = prev.normalized.as_str();
        let n = next.normalized.as_str();
        let after_aux = AUX.contains(&p);
        let verb_next = (AUX.contains(&n) || finite(next))
            && ![
                "and", "or", "but", "that", "which", "who", "if", "so", "because", "when",
            ]
            .contains(&p)
            && !crate::clauses::PREPOSITIONS.contains(&p)
            && (!finite(prev) || crate::clauses::noun_or_verb(prev))
            && ![
                "the", "a", "an", "this", "these", "those", "my", "your", "our", "their", "his",
                "its", "her", "some", "any", "no", "every", "each", "than", "as", "then", "not",
            ]
            .contains(&p);
        if after_aux || verb_next {
            comma(
                edits,
                prev,
                "punctuation.parenthetical_comma",
                "Set off \"however\" with commas.",
            );
            comma(
                edits,
                t,
                "punctuation.parenthetical_comma",
                "Set off \"however\" with commas.",
            );
        }
    }
}

/// A verb right after "but" means the clause shares its subject with the first ("He came but
/// left early"), so there are no two independent clauses to separate.
fn shares_subject(t: &Token<'_>) -> bool {
    !crate::clauses::subject_contraction(&t.normalized)
        && (finite(t)
            || morphology::verb(&t.normalized).is_some_and(|v| v.base == t.normalized)
                && crate::spelling::flags(&t.normalized) & 2 == 0)
}
pub fn finite(t: &Token<'_>) -> bool {
    [
        "am", "is", "are", "was", "were", "has", "have", "had", "can", "could", "may", "might",
        "must", "shall", "should", "will", "would", "do", "does", "did", "cannot", "don't",
        "doesn't", "didn't", "you're", "we're", "they're", "he's", "she's", "it's", "i'm", "i've",
        "we've", "they've",
    ]
    .contains(&t.normalized.as_str())
        || morphology::verb(&t.normalized).is_some_and(|v| {
            // The past of a verb that is also a plain word ("a bit hard", "a straight bet", "a shot")
            // does not make a clause, for the verbs added to the table later, unless the app's
            // tagger read it as the verb ("it cost us a day", "we split the bill").
            t.normalized == v.third
                || t.normalized == v.past
                    && !(morphology::extra(&v.base)
                        && crate::spelling::flags(&t.normalized) & (2 | 8) != 0
                        && t.pos != "Verb")
        })
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
                "since", "cuz", "cause", "coz", "cos", "bc", "called", "named", "titled", "said",
                "says", "asked", "asks", "me", "us", "him", "her", "them", "you", "think",
                "thought", "know", "knew", "believe", "believed", "am", "is", "are", "was", "were",
                "be", "been", "being", "has", "have", "had", "do", "does", "did", "can", "could",
                "will", "would", "shall", "should", "may", "might", "must",
            ]
            .contains(&previous.normalized.as_str())
        {
            continue;
        }
        let gap = &req.text[previous.end_byte..t.start_byte];
        if gap.is_empty() || !gap.chars().all(|c| c == ' ' || c == '\t') {
            continue;
        }
        // "Cell Phones and Pagers Over the next few weeks Enron will": a title-case heading runs
        // into its first sentence; that is layout, not a run-on.
        let opening: Vec<&Token<'_>> = tokens[start..i]
            .iter()
            .filter(|x| x.is_word)
            .take(4)
            .collect();
        let paragraph_start = start == 0 || tokens[start - 1].paragraph != tokens[start].paragraph;
        if paragraph_start
            && opening
                .iter()
                .filter(|x| {
                    x.surface.starts_with(char::is_uppercase)
                        && crate::spelling::ordinary(&x.normalized)
                })
                .count()
                >= 3
        {
            continue;
        }
        // "the teams within ENA I received Tuesday": "I" and a verb with no object of its own
        // describe the noun before them.
        if t.surface == "I"
            && tokens.get(i + 1).is_some_and(finite)
            && tokens.get(i + 2).is_none_or(|x| {
                !x.is_word
                    || [
                        "from",
                        "on",
                        "in",
                        "at",
                        "for",
                        "with",
                        "to",
                        "by",
                        "yesterday",
                        "today",
                        "last",
                        "this",
                        "earlier",
                        "monday",
                        "tuesday",
                        "wednesday",
                        "thursday",
                        "friday",
                        "saturday",
                        "sunday",
                    ]
                    .contains(&x.normalized.as_str())
            })
        {
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
        // "a list of RSVP's I have received so far": a relative clause without "that", whose
        // verb has no object of its own.
        let contact_clause = {
            let mut k = i + 1;
            if tokens.get(k).is_some_and(|x| {
                ["have", "has", "had", "'ve", "’ve"].contains(&x.normalized.as_str())
            }) {
                k += 1;
            }
            tokens.get(k).is_some_and(|v| {
                [
                    "received",
                    "sent",
                    "got",
                    "made",
                    "wrote",
                    "written",
                    "bought",
                    "found",
                    "mentioned",
                    "attached",
                    "requested",
                    "asked",
                    "seen",
                    "saw",
                    "collected",
                    "prepared",
                    "reviewed",
                    "used",
                    "booked",
                    "ordered",
                ]
                .contains(&v.normalized.as_str())
            }) && tokens.get(k + 1).is_none_or(|a| {
                !a.is_word
                    || [
                        "so", "already", "yet", "recently", "from", "for", "in", "at", "on",
                        "last", "this", "today", "earlier", "before", "since", "by", "to", "with",
                    ]
                    .contains(&a.normalized.as_str())
            })
        };
        if contact_clause {
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
