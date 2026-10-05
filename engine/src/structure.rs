//! Local clause constraints. No paragraph rewrites or factual paraphrasing.
use crate::{
    Edit, Request, make_edit, match_case, morphology, spelling,
    tokenizer::{self, Token},
};

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
    if subject.proper_name
        || subject.pos == "Noun" && spelling::known(word)
        || spelling::flags(word) & 2 != 0
    {
        return Some(
            spelling::flags(word) & 16 != 0
                && !["news", "series", "species", "means"].contains(&word),
        );
    }
    // A capitalized unknown name can be a simple subject; edits target its verb.
    if subject
        .surface
        .chars()
        .next()
        .is_some_and(char::is_uppercase)
        && !spelling::known(word)
    {
        return Some(false);
    }
    None
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
    for (i, t) in tokens.iter().enumerate().filter(|(_, t)| t.is_word) {
        let w = t.normalized.as_str();
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
        let nominal_what = tokens
            .iter()
            .take(i)
            .find(|x| x.sentence == t.sentence)
            .is_some_and(|x| ["what", "whatever"].contains(&x.normalized.as_str()))
            && ["does", "do"].contains(&previous);
        if auxiliary_base
            && !nominal_what
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
            && plural(&tokens[prev]).is_some()
            && [
                "did", "does", "do", "can", "could", "will", "would", "should", "must",
            ]
            .contains(&tokens[prev - 1].normalized.as_str())
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
        let determiner_subject = i >= 2
            && [
                "the", "a", "an", "this", "that", "these", "those", "my", "your", "our", "their",
                "his", "her", "its", "every", "each", "some", "many", "several",
            ]
            .contains(&tokens[i - 2].normalized.as_str());
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
        if !(determiner_subject
            || subject_start
            || pronoun_subject
            || p.proper_name
            || (p.surface.chars().next().is_some_and(char::is_uppercase)
                && !spelling::known(&p.normalized)))
        {
            continue;
        }
        let Some(mut is_plural) = plural(p) else {
            continue;
        };
        if let Some(and) = tokens[..i - 1]
            .iter()
            .rposition(|x| x.sentence == t.sentence && x.normalized == "and")
            && i - 1 - and <= 3
            && and > 0
            && tokens[and + 1..i - 1].iter().all(|x| x.is_word)
            && plural(&tokens[and - 1]).is_some()
            && !tokens[..and]
                .iter()
                .filter(|x| x.sentence == t.sentence)
                .any(|x| {
                    morphology::verb(&x.normalized)
                        .is_some_and(|v| x.normalized == v.past || x.normalized == v.third)
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
        if previous_clause.iter().any(|x| {
            ["to", "of", "about", "from", "with", "between", "whether"]
                .contains(&x.normalized.as_str())
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
        let past = anchored_past
            || clause_prefix.contains("yesterday")
            || clause_prefix.contains("last week")
            || clause_prefix.contains("last month")
            || clause_prefix.contains("last night")
            || (clause_prefix.trim_start().starts_with("then ")
                && prefix.to_lowercase().contains("yesterday"));
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
            let replacement = match (w, is_plural, p.normalized.as_str()) {
                ("are", _, "i") => Some("am"),
                ("was", true, "i") => None,
                ("was", true, _) => Some("were"),
                ("were", false, _)
                    if !clause_prefix.contains("if ")
                        && !prefix.to_lowercase().contains("wish ") =>
                {
                    Some("was")
                }
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
            if !subjunctive {
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
