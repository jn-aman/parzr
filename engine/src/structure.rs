//! Local clause constraints. No paragraph rewrites or factual paraphrasing.
use crate::{
    Edit, Request, make_edit, match_case, morphology, spelling,
    tokenizer::{self, Token},
};

/// Words after which a clause (and so a subject) can begin.
const CLAUSE_OPENERS: [&str; 41] = [
    "and",
    "but",
    "so",
    "that",
    "because",
    "if",
    "when",
    "while",
    "then",
    "or",
    "although",
    "since",
    "though",
    "whether",
    "unless",
    "until",
    "after",
    "before",
    "once",
    "yesterday",
    "today",
    "tomorrow",
    "now",
    "finally",
    "also",
    "however",
    "usually",
    "often",
    "sometimes",
    "always",
    "never",
    "still",
    "even",
    "first",
    "here",
    "again",
    "soon",
    "think",
    "say",
    "know",
    "believe",
];
/// Sentence openers that front a place or time phrase and so invert the clause.
const FRONTED: [&str; 24] = [
    "round", "inside", "outside", "in", "on", "at", "under", "over", "behind", "beside", "near",
    "among", "between", "across", "around", "along", "above", "below", "beyond", "within",
    "through", "toward", "towards", "from",
];
fn emit(
    req: &Request,
    t: &Token<'_>,
    replacement: &str,
    id: &str,
    reason: &str,
    edits: &mut Vec<Edit>,
) {
    if let Some(edit) = make_edit(
        &req.text,
        t.start_utf16,
        t.end_utf16,
        match_case(replacement, t.surface),
        "Grammar",
        id,
        reason,
        0.94,
    ) {
        edits.push(edit);
    }
}
fn plural(subject: &Token<'_>) -> Option<bool> {
    let word = subject.normalized.as_str();
    if [
        "i", "you", "we", "they", "people", "children", "men", "women", "police",
    ]
    .contains(&word)
    {
        return Some(true);
    }
    if [
        "he",
        "she",
        "it",
        "this",
        "that",
        "someone",
        "anyone",
        "everyone",
        "nobody",
        "somebody",
        "each",
        "everything",
        "nothing",
    ]
    .contains(&word)
    {
        return Some(false);
    }
    // Relative and expletive words take their number from elsewhere; these nouns do not mark it.
    if [
        "who",
        "which",
        "whom",
        "whose",
        "there",
        "here",
        "fish",
        "sheep",
        "deer",
        "aircraft",
        "personnel",
        "staff",
    ]
    .contains(&word)
    {
        return None;
    }
    if [
        "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
        "dozen", "hundred", "thousand", "million", "both", "several", "many", "few",
    ]
    .contains(&word)
    {
        return Some(true);
    }
    if subject.proper_name
        || subject.pos == "Noun" && spelling::known(word)
        || spelling::flags(word) & 2 != 0
    {
        return Some(
            (spelling::flags(word) & 16 != 0
                || !subject.proper_name && !spelling::name_only(word) && looks_plural(word))
                && !["news", "series", "species", "means"].contains(&word),
        );
    }
    // A capitalized unknown name can be a simple subject; edits target its verb. One ending in
    // "s" may be a plural the dictionary lacks, so its number is unknown.
    if subject
        .surface
        .chars()
        .next()
        .is_some_and(char::is_uppercase)
        && !spelling::known(word)
        && !word.ends_with('s')
    {
        return Some(false);
    }
    None
}
/// A subject that can sit between an inverted auxiliary and its verb ("did she called"): a
/// pronoun or a name, never a common word that might itself be the verb ("play games").
fn inverted_subject(t: &Token<'_>) -> bool {
    t.proper_name
        || [
            "i", "you", "he", "she", "it", "we", "they", "someone", "anyone", "everyone", "nobody",
            "somebody", "people",
        ]
        .contains(&t.normalized.as_str())
        || t.surface.chars().next().is_some_and(char::is_uppercase)
            && t.is_word
            && !spelling::known(&t.normalized)
}
/// Conjunctions, adverbs and place words that never head a subject phrase.
fn function_word(w: &str) -> bool {
    [
        "and",
        "or",
        "but",
        "so",
        "yet",
        "because",
        "if",
        "when",
        "while",
        "although",
        "though",
        "since",
        "then",
        "also",
        "even",
        "still",
        "now",
        "just",
        "only",
        "again",
        "too",
        "very",
        "really",
        "always",
        "often",
        "usually",
        "sometimes",
        "here",
        "there",
        "everywhere",
        "nowhere",
        "somewhere",
        "anywhere",
        "where",
        "how",
        "why",
        "what",
        "than",
        "as",
    ]
    .contains(&w)
}
/// A regular plural of a known noun that the dictionary does not flag as plural ("teenagers",
/// "photographs", "lives").
fn looks_plural(word: &str) -> bool {
    if word.len() < 5
        || !word.ends_with('s')
        || word.ends_with("ss")
        || word.ends_with("us")
        || word.ends_with("is")
    {
        return false;
    }
    let noun = |stem: &str| spelling::flags(stem) & 2 != 0;
    let stem = &word[..word.len() - 1];
    noun(stem)
        || word.strip_suffix("es").is_some_and(noun)
        || word
            .strip_suffix("ies")
            .is_some_and(|s| noun(&format!("{s}y")))
        || word
            .strip_suffix("ves")
            .is_some_and(|s| noun(&format!("{s}fe")) || noun(&format!("{s}f")))
}
pub fn check(req: &Request, edits: &mut Vec<Edit>) {
    let tokens = tokenizer::tokenize(&req.text, &req.tokens);
    // Move the auxiliary around a name using two linked edits. The name's
    // original scalar anchors and rich-text attributes remain untouched.
    for (i, window) in tokens.windows(4).enumerate() {
        if window[0].normalized != "not"
            || window[1].normalized != "only"
            || !window[2].is_word
            || ![
                "did", "does", "do", "has", "have", "had", "can", "could", "will", "would",
            ]
            .contains(&window[3].normalized.as_str())
            || !crate::starts_sentence(&req.text, window[0].start_byte, req)
        {
            continue;
        }
        if i + 4 >= tokens.len() || !tokens[i + 4].is_word {
            continue;
        }
        let group = format!("grammar.not_only:{}", window[1].end_utf16);
        let mut pair = Vec::new();
        for (a, b, replacement) in [
            (
                window[1].end_utf16,
                window[1].end_utf16,
                format!(" {}", window[3].normalized),
            ),
            (window[2].end_utf16, window[3].end_utf16, String::new()),
        ] {
            if let Some(mut edit) = make_edit(
                &req.text,
                a,
                b,
                replacement,
                "Grammar",
                "grammar.inversion_not_only",
                "Move the auxiliary before the subject after fronted not only.",
                0.98,
            ) {
                edit.group_id = Some(group.clone());
                pair.push(edit);
            }
        }
        if pair.len() == 2 {
            edits.extend(pair);
        }
    }
    // Hinglish verbs ("Thoda wait karo") are not English agreement errors.
    let hinglish: Vec<usize> = tokens
        .iter()
        .filter(|t| t.is_word && spelling::hinglish(&t.normalized))
        .map(|t| t.sentence)
        .collect();
    for (i, t) in tokens.iter().enumerate().filter(|(_, t)| t.is_word) {
        let w = t.normalized.as_str();
        if hinglish.contains(&t.sentence) {
            continue;
        }
        if [
            "and", "or", "but", "may", "might", "must", "can", "could", "will", "would", "should",
            "shall", "not", "never", "if", "then", "of", "in", "on", "at", "by", "for", "from",
            "with", "a", "an", "the", "this", "that", "these", "those", "each", "every", "some",
            "any",
        ]
        .contains(&w)
            || w.ends_with("n't")
        {
            continue;
        }
        let Some(v) = morphology::verb(w).or_else(|| morphology::from_base(&t.lemma)) else {
            continue;
        };
        if i == 0 {
            continue;
        }
        let p = &tokens[i - 1];
        if p.sentence != t.sentence || p.paragraph != t.paragraph {
            continue;
        }
        let mut prev = i - 1;
        while prev > 0
            && [
                "not", "never", "already", "just", "also", "still", "always", "often", "usually",
            ]
            .contains(&tokens[prev].normalized.as_str())
        {
            prev -= 1;
        }
        let previous = tokens[prev].normalized.as_str();
        // A capitalized word inside a sentence ("Hey Hope!", "invite Rose") is a name, not a
        // verb to inflect. Only the lowercase-the-participle repair below may touch it.
        if t.surface.chars().next().is_some_and(char::is_uppercase)
            && !crate::starts_sentence(&req.text, t.start_byte, req)
            && !(["be", "been", "being", "has", "have", "had"].contains(&previous)
                && w == v.participle)
        {
            continue;
        }
        if previous == "to" && prev > 0 && w == v.base && morphology::predicate(&v.base) {
            let governor = tokens[prev - 1].normalized.as_str();
            if [
                "enjoy",
                "enjoys",
                "enjoyed",
                "avoid",
                "avoids",
                "avoided",
                "suggest",
                "suggests",
                "suggested",
                "consider",
                "considers",
                "considered",
                "finish",
                "finishes",
                "finished",
            ]
            .contains(&governor)
            {
                if let Some(edit) = make_edit(
                    &req.text,
                    tokens[prev].start_utf16,
                    t.end_utf16,
                    v.gerund.clone(),
                    "Grammar",
                    "grammar.gerund_complement",
                    "This governing verb takes a gerund complement.",
                    0.95,
                ) {
                    edits.push(edit);
                }
                continue;
            }
            if ["forward", "committed", "accustomed", "opposed", "used"].contains(&governor)
                && governor != "used"
            {
                emit(
                    req,
                    t,
                    &v.gerund,
                    "grammar.prepositional_gerund",
                    "Use a gerund after this prepositional to.",
                    edits,
                );
                continue;
            }
        }
        if ["be", "been", "being", "has", "have", "had"].contains(&previous)
            && w == v.participle
            && t.surface != w
            && t.surface.chars().skip(1).all(char::is_lowercase)
            && !t.proper_name
            && !crate::starts_sentence(&req.text, t.start_byte, req)
            && let Some(edit) = make_edit(
                &req.text,
                t.start_utf16,
                t.end_utf16,
                w.to_owned(),
                "Capitalization",
                "capitalization.auxiliary_participle",
                "Use lowercase for this participle inside the sentence.",
                0.96,
            )
        {
            edits.push(edit);
        }
        let auxiliary_base = [
            "can",
            "could",
            "may",
            "might",
            "must",
            "shall",
            "should",
            "will",
            "would",
            "do",
            "does",
            "did",
            "don't",
            "doesn't",
            "didn't",
            "cannot",
            "can't",
            "couldn't",
            "won't",
            "wouldn't",
            "shouldn't",
            "mustn't",
        ]
        .contains(&previous);
        // "why couldn't boys read": after a question word the auxiliary is inverted, so a noun
        // after it is the subject, not a verb.
        let wh_inversion = prev > 0
            && ["why", "how", "what", "where", "when", "who"]
                .contains(&tokens[prev - 1].normalized.as_str());
        let nominal_what = tokens
            .iter()
            .take(i)
            .find(|x| x.sentence == t.sentence)
            .is_some_and(|x| ["what", "whatever"].contains(&x.normalized.as_str()))
            && ["does", "do"].contains(&previous);
        // "Will said hi" / "I think Will said": a capitalized or sentence-initial modal word
        // directly before a verb is a subject name, not a modal.
        let name_subject = auxiliary_base
            && (tokens[prev].surface.starts_with(char::is_uppercase)
                || crate::starts_sentence(&req.text, tokens[prev].start_byte, req));
        // "do sports", "need to do is", "can do lots of": do is the main verb with an object or a
        // complement, so what follows is not a verb to de-inflect.
        let main_do = ["do", "does", "did"].contains(&previous)
            && (prev > 0
                && [
                    "to", "can", "could", "may", "might", "must", "shall", "should", "will",
                    "would",
                ]
                .contains(&tokens[prev - 1].normalized.as_str())
                || ["is", "are", "was", "were", "am"].contains(&w)
                || w == v.third && (spelling::flags(w) & 2 != 0 || looks_plural(w)));
        if auxiliary_base
            && !name_subject
            && !nominal_what
            && !wh_inversion
            && !main_do
            && w != "saw"
            && w != v.base
            && [v.third.as_str(), &v.past, &v.participle].contains(&w)
        {
            emit(
                req,
                t,
                &v.base,
                "grammar.auxiliary_base",
                "Use the base verb form after a modal or do auxiliary.",
                edits,
            );
            continue;
        }
        if ["has", "have", "had", "hasn't", "haven't", "hadn't"].contains(&previous)
            && w != v.participle
            && w != v.gerund
            && (w == v.past || w == v.base)
            && (spelling::known(&v.participle))
        {
            // Have + bare noun/infinitive can be valid: 'have work to do'.
            let next = tokens
                .get(i + 1)
                .map(|t| t.normalized.as_str())
                .unwrap_or("");
            if next != "to"
                && (w != "saw" || ["the", "a", "an", "this", "that", "it", "them"].contains(&next))
                && (w == v.past
                    || [
                        "the", "a", "an", "this", "that", "these", "those", "it", "them", "us",
                        "already", "on", "for",
                    ]
                    .contains(&next))
            {
                emit(
                    req,
                    t,
                    &v.participle,
                    "grammar.perfect_participle",
                    "Use a past participle in this perfect-tense verb phrase.",
                    edits,
                );
                continue;
            }
        }
        if ["am", "is", "are", "was", "were", "be", "been", "being"].contains(&previous)
            && w == v.base
            // "is do bad" is a damaged "is so bad", not a passive.
            && !(w == "do" && tokens.get(i + 1).is_some_and(spelling::adjective))
            && (spelling::flags(w) & 8 == 0
                || [
                    "deliver", "prepare", "repair", "invite", "attach", "assign", "publish",
                    "approve",
                ]
                .contains(&w))
            && [
                "suppose", "deliver", "approve", "check", "complete", "prepare", "finish",
                "repair", "publish", "invite", "attach", "assign", "require", "expect", "allow",
                "design", "build", "send", "write", "make", "take", "give", "do", "see", "choose",
            ]
            .contains(&v.base.as_str())
        {
            emit(
                req,
                t,
                &v.participle,
                "grammar.passive_participle",
                "Use a past participle in this passive verb phrase.",
                edits,
            );
            continue;
        }
        if ["was", "were"].contains(&previous) && w == "knowing" {
            if let Some(edit) = make_edit(
                &req.text,
                tokens[prev].start_utf16,
                t.end_utf16,
                "knew".into(),
                "Grammar",
                "grammar.stative_know",
                "Use the simple past for the state of knowing here.",
                0.92,
            ) {
                edits.push(edit);
            }
            continue;
        }
        if [
            "am", "is", "are", "was", "were", "be", "been", "being", "has", "have", "had",
            "hasn't", "haven't", "hadn't",
        ]
        .contains(&previous)
        {
            continue;
        }
        // Inversion: 'did she called' / 'does Maya works'.
        if prev > 0
            && inverted_subject(&tokens[prev])
            && [
                "did", "does", "do", "can", "could", "will", "would", "should", "must",
            ]
            .contains(&tokens[prev - 1].normalized.as_str())
            // "I talked to Will he said yes": a capitalized "Will" inside a sentence is a name.
            && (!tokens[prev - 1].surface.starts_with(char::is_uppercase)
                || crate::starts_sentence(&req.text, tokens[prev - 1].start_byte, req))
        {
            if w != v.base {
                emit(
                    req,
                    t,
                    &v.base,
                    "grammar.inverted_auxiliary_base",
                    "Use the base verb form after the inverted auxiliary and subject.",
                    edits,
                );
            }
            continue;
        }
        if !p.is_word {
            continue;
        }
        if previous == "who"
            && prev > 0
            && let Some(pl) = plural(&tokens[prev - 1])
            && morphology::predicate(&v.base)
        {
            if pl && w == v.third {
                emit(
                    req,
                    t,
                    &v.base,
                    "grammar.relative_plural",
                    "Match the relative-clause verb to its plural antecedent.",
                    edits,
                );
            } else if !pl && w == v.base && v.base != v.past {
                emit(
                    req,
                    t,
                    &v.third,
                    "grammar.relative_singular",
                    "Match the relative-clause verb to its singular antecedent.",
                    edits,
                );
            }
            continue;
        }
        if ["is", "are", "was", "were", "do", "does", "has", "have"].contains(&w)
            && (["why", "where", "when", "how", "what"].contains(&p.normalized.as_str()) || i == 0)
        {
            let mut subject = i + 1;
            while subject < tokens.len()
                && ["the", "a", "an", "my", "our", "your", "their", "his", "her"]
                    .contains(&tokens[subject].normalized.as_str())
            {
                subject += 1;
            }
            if let Some(s) = tokens.get(subject)
                && let Some(pl) = plural(s)
                && !tokens
                    .get(subject + 1)
                    .is_some_and(|x| ["and", "or"].contains(&x.normalized.as_str()))
            {
                let replacement = match (w, pl) {
                    ("are", false) => Some("is"),
                    ("is", true) => Some("are"),
                    ("were", false) => Some("was"),
                    ("was", true) => Some("were"),
                    ("do", false) => Some("does"),
                    ("does", true) => Some("do"),
                    ("have", false) => Some("has"),
                    ("has", true) => Some("have"),
                    _ => None,
                };
                if let Some(r) = replacement {
                    emit(
                        req,
                        t,
                        r,
                        "grammar.inverted_subject_agreement",
                        "Match the inverted auxiliary to its subject.",
                        edits,
                    );
                }
            }
            continue;
        }
        if !morphology::predicate(&v.base) {
            continue;
        }

        if [
            "am", "is", "are", "was", "were", "be", "been", "being", "has", "have", "had", "to",
            "not", "never",
        ]
        .contains(&previous)
        {
            continue;
        }
        // A determiner and noun open a subject only where a clause can start; after a verb or a
        // preposition they are an object or an adjunct ("as a kitchen help").
        let determiner_subject = i >= 2
            && [
                "the", "a", "an", "this", "that", "these", "those", "my", "your", "our", "their",
                "his", "her", "its", "every", "each", "some", "many", "several",
            ]
            .contains(&tokens[i - 2].normalized.as_str())
            && (i == 2
                || tokens[i - 3].sentence != t.sentence
                || !tokens[i - 3].is_word
                || CLAUSE_OPENERS.contains(&tokens[i - 3].normalized.as_str()));
        let subject_start = i == 1
            || tokens[i - 2].sentence != t.sentence
            || [
                ",", ";", "and", "but", "so", "that", "because", "if", "then",
            ]
            .contains(&tokens[i - 2].normalized.as_str());
        let pronoun_subject = [
            "i",
            "you",
            "we",
            "they",
            "he",
            "she",
            "it",
            "this",
            "that",
            "someone",
            "anyone",
            "everyone",
            "nobody",
            "somebody",
            "everything",
            "nothing",
        ]
        .contains(&p.normalized.as_str());
        if pronoun_subject
            && tokens[..i - 1].iter().rev().take(4).any(|x| {
                [
                    "letter", "letters", "word", "words", "symbol", "symbols", "name", "names",
                    "pronoun", "pronouns",
                ]
                .contains(&x.normalized.as_str())
            })
        {
            continue;
        }
        // "I think that provide the seat": here "that" is the complementizer, not a subject.
        if p.normalized == "that"
            && i >= 2
            && tokens[i - 2].is_word
            && morphology::verb(&tokens[i - 2].normalized).is_some_and(|v| {
                [
                    "think", "say", "know", "believe", "hope", "feel", "suggest", "mean", "show",
                    "find", "claim", "argue", "agree", "ensure", "realize", "see", "hear",
                ]
                .contains(&v.base.as_str())
            })
        {
            continue;
        }
        if ["this", "that", "each", "every"].contains(&p.normalized.as_str())
            && w == v.base
            && spelling::flags(w) & 2 != 0
        {
            continue;
        }
        if i >= 2
            && ["letter", "word", "pronoun", "symbol", "name", "term"]
                .contains(&tokens[i - 2].normalized.as_str())
        {
            continue;
        }
        if !pronoun_subject
            && !p.proper_name
            && spelling::flags(&p.normalized) & 8 != 0
            && ![
                "weather", "water", "work", "light", "season", "paper", "glass", "iron", "wood",
                "plastic", "stone", "orange", "silver", "gold", "time",
            ]
            .contains(&p.normalized.as_str())
        {
            continue;
        }
        // After a modal or do-auxiliary the word is not a clause subject ("an will join" is a
        // split name plus "will join"); agreement edits here fight the modal rules.
        if auxiliary_base {
            continue;
        }
        if !(determiner_subject
            || subject_start
            || pronoun_subject
            || p.proper_name
            || (p.surface.chars().next().is_some_and(char::is_uppercase)
                && !spelling::known(&p.normalized)))
        {
            continue;
        }
        // A possessive or contraction ("Let's see", "my morning's work") and a conjunction or
        // adverb are no subject.
        if p.normalized.ends_with("'s") || function_word(&p.normalized) {
            continue;
        }
        // A fronted place phrase inverts the clause ("Round this corner were three doors"): the
        // verb agrees with a noun phrase that comes after it.
        if let Some(first) = tokens.iter().find(|x| x.sentence == t.sentence)
            && FRONTED.contains(&first.normalized.as_str())
            && tokens[..i]
                .iter()
                .filter(|x| x.sentence == t.sentence)
                .all(|x| x.surface != ",")
        {
            continue;
        }
        // "actions that day were": the plural before "that" is the head of the subject.
        if i >= 3 && tokens[i - 2].normalized == "that" && plural(&tokens[i - 3]) == Some(true) {
            continue;
        }
        let Some(mut is_plural) = plural(p) else {
            continue;
        };
        // "A and B are": a conjoined subject at the start of its clause. Another verb or a pronoun
        // before the "and" means it joins clauses ("I sing a song and the world is perfect").
        if let Some(and) = tokens[..i - 1]
            .iter()
            .rposition(|x| x.sentence == t.sentence && x.normalized == "and")
            && i - 1 - and <= 3
            && and > 0
            && tokens[and + 1..i - 1].iter().all(|x| x.is_word)
            && plural(&tokens[and - 1]).is_some()
            && !tokens[..and - 1]
                .iter()
                .rev()
                .take_while(|x| {
                    x.sentence == t.sentence
                        && ![",", ";", ":", "that", "because", "if", "but"]
                            .contains(&x.normalized.as_str())
                })
                .any(|x| {
                    morphology::verb(&x.normalized).is_some()
                        || [
                            "i", "you", "he", "she", "it", "we", "they", "is", "are", "was",
                            "were", "has", "have", "had",
                        ]
                        .contains(&x.normalized.as_str())
                })
        {
            is_plural = true;
        }
        // Restrict immediate-subject analysis to clause heads; avoid objects,
        // subjunctives, coordinated subjects, and noun complements.
        let before = &tokens[..i - 1];
        // A damaged verb or joined word before this noun phrase must be repaired
        // first. Otherwise its object can be mistaken for a new clause subject.
        if before.len() >= 2
            && ["the", "a", "an", "this", "that", "my", "our", "their"]
                .contains(&before[before.len() - 1].normalized.as_str())
        {
            let preceding = &before[before.len() - 2];
            if preceding.is_word
                && !preceding.proper_name
                && !spelling::known(&preceding.normalized)
            {
                continue;
            }
        }

        // A determiner and noun after a preposition belong to its object phrase.
        // For example, "work on the station repair" does not make repair a verb.
        if before.len() >= 2
            && ["the", "a", "an", "this", "that", "my", "our", "their"]
                .contains(&before[before.len() - 1].normalized.as_str())
            && ([
                "on", "in", "at", "for", "from", "of", "to", "by", "with", "without", "during",
                "after", "before",
            ]
            .contains(&before[before.len() - 2].normalized.as_str())
                || morphology::verb(&before[before.len() - 2].normalized)
                    .is_some_and(|v| morphology::predicate(&v.base)))
        {
            continue;
        }
        let previous_clause: Vec<_> = before
            .iter()
            .rev()
            .take_while(|x| {
                x.sentence == t.sentence
                    && ![
                        ",", ";", "and", "but", "so", "that", "who", "because", "if", "then",
                    ]
                    .contains(&x.normalized.as_str())
            })
            .take(7)
            .collect();
        // A preposition before the noun means p may only end a modifier of the real head ("the
        // roads near the station get", "the platform off the coast were"); a gerund or a
        // perception or causative verb means p is an object or part of a gerund subject ("reading
        // these chapters is", "saw him walk", "makes Martha attend").
        if previous_clause.iter().any(|x| {
            [
                "to", "of", "about", "from", "with", "between", "whether", "in", "on", "at", "by",
                "for", "near", "off", "among", "around", "behind", "beside", "under", "over",
                "inside", "outside", "across", "through", "during", "within", "toward", "towards",
                "into", "onto", "upon", "along", "against", "above", "below", "beyond", "without",
                "except", "like", "than", "such", "after", "before", "see", "sees", "saw", "watch",
                "watched", "hear", "heard", "make", "makes", "made", "let", "lets", "help",
                "helps", "helped", "feel", "felt", "notice", "noticed", "have", "had",
            ]
            .contains(&x.normalized.as_str())
                || morphology::verb(&x.normalized).is_some_and(|v| x.normalized == v.gerund)
        }) {
            continue;
        }
        if before
            .last()
            .is_some_and(|x| ["and", "or"].contains(&x.normalized.as_str()))
            && i >= 3
            && plural(&tokens[i - 3]).is_some()
        {
            continue;
        }
        if previous_clause.iter().any(|x| {
            [
                "can", "could", "may", "might", "must", "shall", "should", "will", "would",
            ]
            .contains(&x.normalized.as_str())
                || morphology::verb(&x.normalized).is_some_and(|v| {
                    x.normalized == v.third
                        || x.normalized == v.past
                        || x.normalized == v.participle
                })
        }) {
            continue;
        }
        let prefix = &req.text[..t.start_byte];
        let mut sentence_start = tokens
            .iter()
            .take(i)
            .rfind(|x| x.sentence != t.sentence)
            .map(|x| x.end_byte)
            .unwrap_or(0);
        if let Some(boundary) = edits
            .iter()
            .filter(|e| {
                e.rule_id == "punctuation.missing_sentence_boundary"
                    && e.start_utf16 <= t.start_utf16
            })
            .map(|e| e.start_utf16)
            .max()
            && let Some(byte) = crate::byte_at(&req.text, boundary)
        {
            sentence_start = sentence_start.max(byte);
        }
        let clause_prefix = req.text[sentence_start..t.start_byte].to_lowercase();
        let sentence_tail = req.text[t.end_byte..]
            .split(['.', '!', '?'])
            .next()
            .unwrap_or("")
            .to_lowercase();
        let anchored_past = prefix.to_lowercase().contains("yesterday")
            && sentence_tail.contains("after ")
            && sentence_tail.contains(" was ")
            && !["every ", "usually", "always", "tomorrow", "next "]
                .iter()
                .any(|marker| clause_prefix.contains(marker) || sentence_tail.contains(marker));
        // The time word governs its own clause: not one before a semicolon, and not a clause
        // already written in the present ("... yesterday ...; it is only now that it has been").
        let frame = clause_prefix.rsplit([';', ':']).next().unwrap_or("");
        let markers = ["yesterday", "last week", "last month", "last night"];
        let present_frame = markers
            .iter()
            .filter_map(|m| frame.rfind(m).map(|at| at + m.len()))
            .max()
            .is_some_and(|end| {
                [
                    " is ", " are ", " am ", " has ", " have ", " does ", " do ", " now ",
                ]
                .iter()
                .any(|m| frame[end..].contains(m))
            });
        let past = !present_frame
            && (anchored_past
                || markers.iter().any(|m| frame.contains(m))
                || (clause_prefix.trim_start().starts_with("then ")
                    && prefix.to_lowercase().contains("yesterday")));
        if past && v.base != "be" && (w == v.base || w == v.third) && v.past != w {
            emit(
                req,
                t,
                &v.past,
                "grammar.explicit_past_time",
                "Use the past verb form with this explicit past-time context.",
                edits,
            );
            continue;
        }
        if v.base == "be" {
            // A name can be a collective ("Wigan were paired") or a multi-word name whose head
            // the tagger missed; "were" can be subjunctive after a conditional or wish frame.
            let named = p.normalized != "i"
                && (p.proper_name
                    || p.surface.chars().next().is_some_and(char::is_uppercase)
                        && (spelling::name_only(&p.normalized)
                            || !spelling::known(&p.normalized)
                            || !crate::starts_sentence(&req.text, p.start_byte, req)));
            let subjunctive = [
                "if ", "though", "wish", "suppose", "unless", "lest", "whether", "as it ", "till ",
                "until ", "were it", "even so",
            ]
            .iter()
            .any(|m| clause_prefix.contains(m));
            let replacement = match (w, is_plural, p.normalized.as_str()) {
                _ if named => None,
                ("are", _, "i") => Some("am"),
                ("was", true, "i") => None,
                ("was", true, _) => Some("were"),
                ("were", false, _) if !subjunctive => Some("was"),
                ("is", true, "i") => Some("am"),
                ("is", true, _) => Some("are"),
                ("are", false, _) => Some("is"),
                _ => None,
            };
            if let Some(r) = replacement {
                emit(
                    req,
                    t,
                    r,
                    "grammar.subject_copula",
                    "Match the copula to its subject.",
                    edits,
                );
            }
        } else if w == v.third && is_plural && !["read", "put", "cut", "let"].contains(&w) {
            emit(
                req,
                t,
                &v.base,
                "grammar.subject_base",
                "Use the base present-tense verb with this plural subject.",
                edits,
            );
        } else if w == v.base
            && !is_plural
            && v.base != v.past
            && !["be", "have", "do"].contains(&v.base.as_str())
        {
            let subjunctive = prefix.to_lowercase().contains("suggest that")
                || prefix.to_lowercase().contains("important that")
                || prefix.to_lowercase().contains("recommend that")
                || prefix.to_lowercase().contains("insist that")
                || prefix.to_lowercase().contains("demand that");
            // A noun-capable verb after a noun is usually a compound ("kitchen help", "NASA study
            // shows"), "like" and "save" are prepositions after one, and a narrative in the past
            // that drops "-ed" ("Tom open the door") is not missing an "-s".
            let compound = !pronoun_subject
                && (!p.proper_name && ["like", "save", "except"].contains(&w)
                    || spelling::flags(w) & 2 != 0
                        && tokens.get(i + 1).is_some_and(|n| {
                            crate::punctuation::finite(n)
                                || ["about", "on", "of", "for", "in", "at", "by", "from"]
                                    .contains(&n.normalized.as_str())
                        }));
            let narrative = tokens
                .iter()
                .enumerate()
                .filter(|(_, x)| {
                    x.paragraph == t.paragraph
                        && x.sentence + 1 >= t.sentence
                        && x.sentence <= t.sentence
                })
                .any(|(k, x)| {
                    // "be obliged" and "has asked" are participles, not a past-tense narrative.
                    k > 0
                        && ![
                            "be", "been", "being", "am", "is", "are", "has", "have", "having",
                        ]
                        .contains(&tokens[k - 1].normalized.as_str())
                        && morphology::verb(&x.normalized)
                            .is_some_and(|v| x.normalized == v.past && v.past != v.base)
                });
            if !subjunctive && !compound && !narrative {
                emit(
                    req,
                    t,
                    &v.third,
                    "grammar.subject_third",
                    "Use the third-person singular present-tense verb with this subject.",
                    edits,
                );
            }
        }
    }
}
