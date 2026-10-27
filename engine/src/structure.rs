//! Local clause constraints. No paragraph rewrites or factual paraphrasing.
use crate::{
    Edit, Request, make_edit, match_case, morphology, spelling,
    tokenizer::{self, Token},
};

/// "Will Smith was great.", "May Lee has left.": a capitalized "Will" or "May" before another
/// capitalized word, in a sentence that asks nothing, is a first name, not an inverted auxiliary.
fn full_name_statement(tokens: &[Token<'_>], aux: usize) -> bool {
    let (first, next) = (&tokens[aux], tokens.get(aux + 1));
    ["will", "may"].contains(&first.normalized.as_str())
        && first.surface.starts_with(char::is_uppercase)
        && next.is_some_and(|n| {
            n.is_word && n.surface.starts_with(char::is_uppercase) && n.normalized != "i"
        })
        && tokens
            .iter()
            .rfind(|t| t.paragraph == first.paragraph && t.sentence == first.sentence)
            .is_some_and(|last| last.surface != "?")
}
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
/// Counting words that stand before a noun.
const NUMBER_WORDS: [&str; 20] = [
    "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
    "dozen", "hundred", "thousand", "million", "both", "several", "many", "few", "other",
];
/// Verbs that open a command with a bare verb after them ("Come sit down", "Go get it").
const IMPERATIVE_FRAMES: [&str; 9] = [
    "come", "go", "run", "hurry", "help", "wait", "stay", "please", "let",
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
/// Group nouns that British English pairs with a plural verb when it means the members.
pub(crate) const COLLECTIVE: [&str; 30] = [
    "team",
    "staff",
    "family",
    "government",
    "committee",
    "band",
    "audience",
    "jury",
    "crew",
    "company",
    "board",
    "council",
    "class",
    "club",
    "group",
    "public",
    "management",
    "panel",
    "army",
    "party",
    "union",
    "firm",
    "department",
    "couple",
    "orchestra",
    "choir",
    "cast",
    "squad",
    "faculty",
    "community",
];
/// Pairs joined by "and" that name one thing and take a singular verb.
const ONE_THING: [(&str, &str); 6] = [
    ("fish", "chips"),
    ("bread", "butter"),
    ("salt", "pepper"),
    ("macaroni", "cheese"),
    ("mac", "cheese"),
    ("rock", "roll"),
];
/// "He and I", "Sarah and I", "My sister and I" opening a clause before the verb at `i`: two
/// subjects, unlike "the theatre and I was" where "and" joins two clauses.
fn pair_with_i(tokens: &[Token<'_>], i: usize) -> bool {
    if i < 3 || tokens[i - 1].normalized != "i" || tokens[i - 2].normalized != "and" {
        return false;
    }
    let opens = |k: usize| {
        k == 0
            || tokens[k - 1].sentence != tokens[k].sentence
            || tokens[k - 1].paragraph != tokens[k].paragraph
            || [",", ";", ":"].contains(&tokens[k - 1].surface)
            || [
                "but", "so", "because", "when", "if", "that", "since", "although", "while",
            ]
            .contains(&tokens[k - 1].normalized.as_str())
    };
    let x = &tokens[i - 3];
    let person = ["he", "she", "they", "we", "you"].contains(&x.normalized.as_str())
        || x.proper_name
        || x.surface.starts_with(char::is_uppercase) && !spelling::ordinary(&x.normalized);
    person && opens(i - 3)
        || i >= 4
            && x.is_word
            && ["my", "our", "his", "her", "their", "your", "the"]
                .contains(&tokens[i - 4].normalized.as_str())
            && opens(i - 4)
}
/// Plural nouns that take no "-s": the Latin and Greek plurals ("phenomena", "criteria", "bacteria")
/// and the Germanic ones the tagger may call singular. "Data" and "media" are left out on purpose:
/// they pass for one mass as often as for many items.
pub(crate) const IRREGULAR_PLURALS: &[&str] = &[
    "phenomena",
    "criteria",
    "bacteria",
    "alumni",
    "alumnae",
    "stimuli",
    "nuclei",
    "fungi",
    "cacti",
    "radii",
    "syllabi",
    "curricula",
    "memoranda",
    "addenda",
    "errata",
    "strata",
    "millennia",
    "genera",
    "corpora",
    "vertebrae",
    "larvae",
    "hypotheses",
    "analyses",
    "diagnoses",
    "theses",
    "crises",
    "oases",
    "parentheses",
    "appendices",
    "matrices",
    "vertices",
    "indices",
    "mice",
    "geese",
    "oxen",
    "lice",
    "tableaux",
    "whereabouts",
    "belongings",
    "outskirts",
    "congratulations",
];
pub(crate) fn plural(subject: &Token<'_>) -> Option<bool> {
    let word = subject.normalized.as_str();
    // "Physics was my worst class", "Statistics are…": a field ending in -ics may take either.
    if [
        "physics",
        "mathematics",
        "economics",
        "politics",
        "ethics",
        "statistics",
        "athletics",
        "gymnastics",
        "linguistics",
        "electronics",
        "genetics",
        "logistics",
        "aerobics",
        "acoustics",
        "robotics",
        "analytics",
        "mechanics",
        "phonetics",
        "thermodynamics",
        "aeronautics",
    ]
    .contains(&word)
    {
        return None;
    }
    if [
        "i", "you", "we", "they", "people", "children", "men", "women", "police",
    ]
    .contains(&word)
    {
        return Some(true);
    }
    // Latin and Greek plurals have no "-s" for the dictionary or the suffix test to see.
    if IRREGULAR_PLURALS.contains(&word) {
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
        // "None were", "none was": either number.
        "none",
        "fish",
        "sheep",
        "deer",
        "aircraft",
        "personnel",
        "staff",
        // American English treats "data" and "media" as one mass as often as many items.
        "data",
        "media",
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
/// The number of the real subject when the word before the verb at `i` belongs to a relative clause
/// that sits between the subject and its verb: "students that are" (the plural noun before "that"
/// gives the number, not "that"), and "people I know and admire are" (a bare relative clause whose
/// own verbs end right before the verb). None when no such clause is there.
fn relative_subject(tokens: &[Token<'_>], i: usize) -> Option<bool> {
    let p = tokens.get(i.checked_sub(1)?)?;
    let noun = |k: usize| -> Option<bool> {
        let n = tokens.get(k)?;
        (n.is_word
            && n.sentence == p.sentence
            && !SUBJECT_PRONOUNS.contains(&n.normalized.as_str())
            && !function_word(&n.normalized))
        .then(|| plural(n))
        .flatten()
    };
    if ["that", "which"].contains(&p.normalized.as_str()) {
        // Only a plural antecedent is clear: "that" after one is the relative pronoun. "Yes that
        // works" has no antecedent, and a short "-s" word ("yes") is not a plural.
        let antecedent = i.checked_sub(2)?;
        let a = &tokens[antecedent];
        let regular = a.normalized.len() >= 5 && a.normalized.ends_with('s');
        return noun(antecedent).filter(|plural| *plural).filter(|_| {
            regular
                || IRREGULAR_PLURALS.contains(&a.normalized.as_str())
                || ["people", "children", "men", "women", "police"].contains(&a.normalized.as_str())
        });
    }
    // "people I know and admire": walk back over the verbs joined by "and" to the subject pronoun.
    let mut j = i - 1;
    loop {
        let x = &tokens[j];
        if !x.is_word || morphology::verb(&x.normalized).is_none() {
            return None;
        }
        if j >= 2 && tokens[j - 1].normalized == "and" && tokens[j - 2].is_word {
            j -= 2;
            continue;
        }
        break;
    }
    if j < 2 || !SUBJECT_PRONOUNS.contains(&tokens[j - 1].normalized.as_str()) {
        return None;
    }
    noun(j - 2)
}
/// Pronouns that can open a relative clause with no relative word ("the people we know").
const SUBJECT_PRONOUNS: [&str; 7] = ["i", "you", "we", "they", "he", "she", "it"];
/// The head of the noun phrase that starts at `start`, after the inverted auxiliary `aux`: the last
/// of up to four nouns and adjectives in a row ("your future plans", "the office hours"). The run
/// stops at a word that can only be the rest of the clause: after "do" a bare verb ("Do the kids
/// play"), after "is" or "are" a participle or an -ing form ("Where are the keys left"), after "have"
/// a participle. The first word when no longer phrase is there.
fn noun_phrase_head(tokens: &[Token<'_>], start: usize, aux: &str) -> usize {
    let Some(first) = tokens.get(start) else {
        return start;
    };
    let predicate = |t: &Token<'_>| {
        morphology::verb(&t.normalized).is_some_and(|v| {
            let w = t.normalized.as_str();
            match aux {
                "do" | "does" => w == v.base && v.third != w,
                "has" | "have" => w == v.participle && w != v.base,
                _ => (w == v.participle || w == v.gerund || w == v.past) && w != v.base,
            }
        })
    };
    // A first word that is only the rest of the clause ("what are considered safe") has no phrase.
    if predicate(first) && !["do", "does"].contains(&aux) {
        return start;
    }
    let mut end = start;
    while let Some(t) = tokens.get(end) {
        let nominal = t.is_word
            && t.sentence == first.sentence
            && !function_word(&t.normalized)
            && ![
                "that", "which", "who", "whom", "whose", "of", "in", "on", "at", "for", "to",
                "with", "from", "by", "into", "about", "is", "are", "was", "were", "do", "does",
                "did", "has", "have", "had", "be", "will", "can", "should", "would", "must", "not",
                "no", "it", "they", "we", "you", "i", "he", "she", "this", "these", "those",
            ]
            .contains(&t.normalized.as_str())
            && (spelling::flags(&t.normalized) & (2 | 8) != 0
                || plural(t).is_some()
                || looks_plural(&t.normalized))
            // The first word is the phrase's own start, whatever it could also be. A name's capital
            // marks it a noun ("Sharon Stone"); after "do" the clause has one bare verb and the
            // run decides below which it is.
            && (end == start
                || ["do", "does"].contains(&aux)
                || t.surface.starts_with(char::is_uppercase)
                || !predicate(t));
        if !nominal || end >= start + 4 {
            break;
        }
        end += 1;
    }
    // After "do" the last bare verb in the run is the predicate ("do the kids play", "does the sales
    // report look"): the phrase ends before it.
    if ["do", "does"].contains(&aux)
        && let Some(cut) = (start + 1..end).rfind(|k| {
            predicate(&tokens[*k]) && !tokens[*k].surface.starts_with(char::is_uppercase)
        })
    {
        end = cut;
    }
    // A trailing adjective is the complement ("Why is the staff members late"), not the head.
    while end > start + 1
        && spelling::flags(&tokens[end - 1].normalized) & 2 == 0
        && !looks_plural(&tokens[end - 1].normalized)
    {
        end -= 1;
    }
    end.saturating_sub(1).max(start)
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
        "perhaps",
        "maybe",
        "please",
    ]
    .contains(&w)
}
/// A regular plural of a known noun that the dictionary does not flag as plural ("teenagers",
/// "photographs", "lives").
pub(crate) fn looks_plural(word: &str) -> bool {
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
        .enumerate()
        .filter(|(i, t)| t.is_word && spelling::roman_hindi(&tokens, *i))
        .map(|(_, t)| t.sentence)
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
                // "He is considered to be an expert", "a plan suggested to be safe": a passive or
                // reduced passive, where "to be" is the right complement. A subject pronoun before
                // the verb ("she considered to be") makes it active.
                let before = prev
                    .checked_sub(2)
                    .map_or("", |k| tokens[k].normalized.as_str());
                let passive = [
                    "is", "are", "was", "were", "am", "be", "been", "being", "get", "gets", "got",
                ]
                .contains(&before)
                    || w == "be"
                        && ["considered", "suggested"].contains(&governor)
                        && !["i", "we", "you", "they", "he", "she"].contains(&before);
                if passive {
                    continue;
                }
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
        // "strength of will is important", "his own will remains": a noun, not a modal.
        let noun_modal = auxiliary_base
            && prev > 0
            && [
                "of", "the", "a", "an", "my", "his", "her", "their", "our", "your", "its", "this",
                "that", "free", "strong", "good", "own",
            ]
            .contains(&tokens[prev - 1].normalized.as_str());
        // "Should hackers be denied access?", "as must courses in the minor": the modal comes
        // first, so a plural noun after it is the subject.
        let inverted_modal = auxiliary_base
            && w == v.third
            && (spelling::flags(w) | spelling::flags(&v.base)) & 2 != 0
            && (prev == 0
                // "..., should hackers be denied": a verb right after the noun makes it the subject.
                || tokens.get(i + 1).is_some_and(|n| {
                    ["be", "been", "have", "get", "become"].contains(&n.normalized.as_str())
                })
                || tokens[prev - 1].sentence != t.sentence
                || [
                    "as", "than", "so", "nor", "neither", "and", "but", "or", "when", "if",
                ]
                .contains(&tokens[prev - 1].normalized.as_str())
                || crate::starts_sentence(&req.text, tokens[prev].start_byte, req));
        // "do sports", "need to do is", "can do lots of": do is the main verb with an object or a
        // complement, so what follows is not a verb to de-inflect. After a form of "be" ("I was do
        // tired") it is a slip for "so", and "tired" stays an adjective.
        let main_do = ["do", "does", "did"].contains(&previous)
            && (prev > 0
                && ([
                    "to", "can", "could", "may", "might", "must", "shall", "should", "will",
                    "would",
                ]
                .contains(&tokens[prev - 1].normalized.as_str())
                    || spelling::COPULAS.contains(&tokens[prev - 1].normalized.as_str()))
                || ["is", "are", "was", "were", "am"].contains(&w)
                // "does not works" is still an auxiliary; only "do sports" has the noun at once.
                || prev + 1 == i
                    && w == v.third
                    && (spelling::flags(w) & 2 != 0 || looks_plural(w)));
        if auxiliary_base
            && !name_subject
            && !noun_modal
            && !inverted_modal
            && !nominal_what
            && !wh_inversion
            && !main_do
            && !morphology::also_base(w)
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
            // "had like a mohawk": "like" is a preposition here, not a bare verb.
            if next != "to"
                && w != "like"
                && (w != "saw" || ["the", "a", "an", "this", "that", "it", "them"].contains(&next))
                && (w == v.past
                    || [
                        "the", "a", "an", "this", "that", "these", "those", "it", "them", "us",
                        "already", "on", "for",
                    ]
                    .contains(&next)
                        // "have time for", "have work on": a noun object, not a bare verb.
                        && !(spelling::flags(w) & 2 != 0 && ["on", "for"].contains(&next)))
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
            // "All we need to do is build a wall": a pseudo-cleft takes the bare verb.
            && !tokens[..prev].iter().any(|x| {
                x.sentence == t.sentence
                    && ["do", "does", "did", "done"].contains(&x.normalized.as_str())
            })
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
                "did", "does", "do", "can", "could", "will", "would", "should", "must", "didn't",
                "doesn't", "don't", "can't", "couldn't", "won't", "wouldn't", "shouldn't",
            ]
            .contains(&tokens[prev - 1].normalized.as_str())
            // "How you do it matters": after its own subject "do" is the main verb, not inverted.
            && !(prev >= 2
                && tokens[prev - 2].sentence == t.sentence
                && ["i", "you", "we", "they", "he", "she"]
                    .contains(&tokens[prev - 2].normalized.as_str()))
            // "I talked to Will he said yes": a capitalized "Will" inside a sentence is a name.
            && (!tokens[prev - 1].surface.starts_with(char::is_uppercase)
                || crate::starts_sentence(&req.text, tokens[prev - 1].start_byte, req))
            && !full_name_statement(&tokens, prev - 1)
        {
            // "Did you saw it?" is "see": only the homographs a writer rarely means as a base
            // ("did she lay the carpet", "did it wound him") stay.
            let keeps = morphology::also_base(w) && !["saw", "found"].contains(&w);
            if w != v.base && !keeps {
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
                    // The plural of "is" is "are": "be" is only the infinitive.
                    if v.base == "be" { "are" } else { &v.base },
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
                && [
                    "the", "a", "an", "my", "our", "your", "their", "his", "her", "all", "both",
                    "some", "any", "these", "those", "many", "several", "few", "most", "other",
                    "more", "half",
                ]
                .contains(&tokens[subject].normalized.as_str())
            {
                subject += 1;
            }
            // The verb agrees with the head of the noun phrase after it ("your future plans", "the
            // office hours"), which is its last noun, not its first word.
            let subject = noun_phrase_head(&tokens, subject, w);
            if let Some(s) = tokens.get(subject)
                // "What are HID lights?": an acronym before its noun is a modifier, not the subject.
                && !(s.surface.len() > 1
                    && s.surface.chars().all(char::is_uppercase)
                    && tokens.get(subject + 1).is_some_and(|x| x.is_word))
                && let Some(pl) = plural(s)
                && !tokens
                    .get(subject + 1)
                    .is_some_and(|x| ["and", "or", ","].contains(&x.normalized.as_str()))
                // British English lets a group noun take a plural verb ("Where are the team?").
                && !(req.dialect == "british" && !pl && COLLECTIVE.contains(&s.normalized.as_str()))
            {
                let replacement = match (w, pl) {
                    // "Where was I?": "I" takes "was" and "am", never "were" or "are".
                    ("was", _) if s.normalized == "i" => None,
                    ("is" | "are", _) if s.normalized == "i" => Some("am"),
                    ("were", _) if s.normalized == "i" => Some("was"),
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
        // "Each students has": the determiner, not the noun's ending, gives the number.
        if i >= 2
            && ["each", "every"].contains(&tokens[i - 2].normalized.as_str())
            && plural(p) == Some(true)
        {
            continue;
        }
        // "values such as these, that were believed": after a comma the antecedent is not the word
        // before; and "the only thing that matters is": a verb after "that" is not the subject.
        if ["that", "which"].contains(&p.normalized.as_str())
            && i >= 2
            && tokens[i - 2].surface == ","
        {
            continue;
        }
        if i >= 3
            && ["that", "which", "who"].contains(&tokens[i - 2].normalized.as_str())
            && morphology::verb(&p.normalized).is_some_and(|x| p.normalized == x.third)
        {
            continue;
        }
        let Some(mut is_plural) = relative_subject(&tokens, i).or_else(|| plural(p)) else {
            continue;
        };
        // "These news are good", "These entry were": a singular-looking noun after a plural
        // demonstrative is a mismatch the demonstrative rule owns; the verb is no evidence.
        if !is_plural && i >= 2 && ["these", "those"].contains(&tokens[i - 2].normalized.as_str()) {
            continue;
        }
        // British English lets a group noun take a plural verb ("The team are working on it").
        if req.dialect == "british" && !is_plural && COLLECTIVE.contains(&p.normalized.as_str()) {
            continue;
        }
        // "Fish and chips is on the menu": one dish, not two subjects.
        if i >= 3
            && tokens[i - 2].normalized == "and"
            && ONE_THING.contains(&(tokens[i - 3].normalized.as_str(), p.normalized.as_str()))
        {
            continue;
        }
        // "Today: emails, code review, gym.", "call mom, finish report": a noun pair that makes up
        // a whole list item is a noun phrase, not a subject and its verb.
        let item_start = i < 2
            || [",", ":", ";", "-", "•", "*"].contains(&tokens[i - 2].surface)
            || tokens[i - 2].paragraph != p.paragraph;
        let item_end = tokens.get(i + 1).is_none_or(|n| {
            [",", ";", ".", ")"].contains(&n.surface) || n.paragraph != t.paragraph
        });
        if item_start
            && item_end
            && !pronoun_subject
            && !determiner_subject
            && spelling::flags(&t.normalized) & 2 != 0
        {
            continue;
        }
        // "Enron Net Works invites", "Acme Industries invites": a capitalized name inside the
        // sentence is one company or team, whatever its last word's number.
        let name_subject = p.normalized != "i"
            && (p.proper_name
                || p.surface.starts_with(char::is_uppercase)
                    && !crate::starts_sentence(&req.text, p.start_byte, req));
        // "A and B are": a conjoined subject at the start of its clause. Another verb or a pronoun
        // before the "and" means it joins clauses ("I sing a song and the world is perfect").
        if let Some(and) = tokens[..i - 1]
            .iter()
            .rposition(|x| x.sentence == t.sentence && x.normalized == "and")
            && i - 1 - and <= 3
            && and > 0
            && tokens[and + 1..i - 1].iter().all(|x| x.is_word)
            // "enthusiasm, and dedication were": a comma before "and" ends a list; the item is the
            // word before it. A plain adjective is no item ("years old and my name is").
            // In a comma list the last item follows "and" at once or after one determiner.
            && (tokens[and - 1].surface != ","
                || i - 1 == and + 1
                || ["the", "a", "an", "my", "our", "your", "his", "her", "their", "this", "that"]
                    .contains(&tokens[and + 1].normalized.as_str()))
            && let left = if tokens[and - 1].surface == "," && and > 1 {
                and - 2
            } else {
                and - 1
            }
            && plural(&tokens[left]).is_some()
            && !spelling::adjective(&tokens[left])
            // A list that opens its sentence: a verb earlier in it ("X is at Y, Z, and his work is")
            // makes the "and" join two clauses.
            && (left == and - 1
                || !tokens[..left]
                    .iter()
                    .any(|x| {
                        x.sentence == t.sentence
                            && [
                                "is", "are", "was", "were", "has", "have", "had", "do", "does",
                                "did", "can", "could", "will", "would", "should", "may", "might",
                                "must",
                            ]
                            .contains(&x.normalized.as_str())
                    }))
            && !tokens[..left]
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
                        // "I'm 22 years old and my name is": a contracted verb is a clause before it.
                        || x.normalized.ends_with("'m")
                        || x.normalized.ends_with("'re")
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
                "except", "like", "than", "such", "as", "after", "before", "see", "sees", "saw",
                "watch", "watched", "hear", "heard", "make", "makes", "made", "let", "lets",
                "help", "helps", "helped", "feel", "felt", "notice", "noticed", "have", "had",
            ]
            .contains(&x.normalized.as_str())
                || morphology::verb(&x.normalized).is_some_and(|v| x.normalized == v.gerund)
        }) {
            continue;
        }
        // "He and I was": a pair closed by "I" is a plural subject the copula check can read.
        if before
            .last()
            .is_some_and(|x| ["and", "or"].contains(&x.normalized.as_str()))
            && i >= 3
            && plural(&tokens[i - 3]).is_some()
            && !(v.base == "be" && pair_with_i(&tokens, i))
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
                [
                    "punctuation.missing_sentence_boundary",
                    "punctuation.comma_splice",
                    "punctuation.run_on",
                ]
                .contains(&e.rule_id.as_str())
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
        // Nor one before ", yet" or ", but": "last month, yet nothing has happened".
        // Nor one before a second clause with its own subject: "I bought it last week and the
        // screen has a dead pixel".
        let frame = [
            ", yet ",
            ", but ",
            " and the ",
            " and my ",
            " and our ",
            " and your ",
            " and it ",
            " and this ",
            " and his ",
            " and her ",
            " and their ",
            " but the ",
            " but my ",
            " but it ",
        ]
        .iter()
        .filter_map(|c| frame.rfind(c).map(|at| at + c.len()))
        .max()
        .map_or(frame, |at| &frame[at..]);
        // A reported or relative clause ("told me that he loves me", "the letter in which you say")
        // has its own time: the time word before it belongs to the clause outside.
        let frame = [" that ", " which ", " whom ", " who ", " whose "]
            .iter()
            .filter_map(|c| frame.rfind(c).map(|at| at + c.len()))
            .max()
            .map_or(frame, |at| &frame[at..]);
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
        // "has happened" is a perfect, not a present: the perfect rules decide its tense.
        let perfect = v.base == "have"
            && tokens.get(i + 1).is_some_and(|n| {
                morphology::verb(&n.normalized)
                    .is_some_and(|m| m.participle == n.normalized && m.base != "have")
            });
        if past && v.base != "be" && !perfect && (w == v.base || w == v.third) && v.past != w {
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
            // "He and I are": "I" closing a pair is one of two subjects, never "I am"; "He and I
            // was" takes "were".
            let paired_i = pair_with_i(&tokens, i);
            let head = if paired_i {
                "pair"
            } else {
                p.normalized.as_str()
            };
            // "These are", "Those were": the demonstrative is plural, though "plural" does not mark
            // it (that would make "These prints show" read "prints" as a verb to de-inflect).
            let is_plural = is_plural || paired_i || ["these", "those"].contains(&head);
            let replacement = match (w, is_plural, head) {
                // "Me and him are": the pronoun rules fix the subject first.
                _ if named || ["me", "him", "us", "them"].contains(&head) => None,
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
        } else if w == v.third
            && is_plural
            && !name_subject
            // "These four studies": a number before a plural noun is its determiner, not a subject.
            && !(NUMBER_WORDS.contains(&p.normalized.as_str())
                && (spelling::flags(w) & 2 != 0 || looks_plural(w)))
            && !["read", "put", "cut", "let"].contains(&w)
        {
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
                                // "Our team lead, along with two engineers, is": a noun before an aside.
                                || n.surface == ","
                                // "RSS feed readers have": a noun inside a longer noun phrase.
                                || (spelling::flags(&n.normalized) & 2 != 0
                                    || spelling::flags(n.normalized.trim_end_matches('s')) & 2
                                        != 0)
                                    && tokens.get(i + 2).is_some_and(|m| {
                                        [
                                            "is", "are", "was", "were", "has", "have", "will",
                                            "can", "should", "must",
                                        ]
                                        .contains(&m.normalized.as_str())
                                    })
                                || ["about", "on", "of", "for", "in", "at", "by", "from"]
                                    .contains(&n.normalized.as_str())
                        }));
            // "Anyone need anything else?": chat drops the "Does" of a question.
            let dropped_do = [
                "anyone",
                "anybody",
                "someone",
                "somebody",
                "everyone",
                "everybody",
            ]
            .contains(&p.normalized.as_str())
                && tokens
                    .iter()
                    .take(i - 1)
                    .all(|x| x.sentence != t.sentence || !x.is_word)
                && tokens[i..]
                    .iter()
                    .take_while(|x| x.sentence == t.sentence)
                    .any(|x| x.surface == "?");
            let narrative = !clause_prefix.contains("if ")
                && tokens
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
            // "Come sit down", "Keep it like this": an imperative has no third-person subject, so
            // the word before is a verb of command, and "like" after its object is a preposition.
            let imperative = (i == 1 || tokens[i - 2].sentence != t.sentence)
                && IMPERATIVE_FRAMES.contains(&p.normalized.as_str())
                || w == "like"
                    && i >= 2
                    && (["it", "this", "that", "them", "him", "her", "me", "us"]
                        .contains(&p.normalized.as_str())
                        && morphology::verb(&tokens[i - 2].normalized).is_some()
                        && tokens[i - 2].sentence == t.sentence
                        // "nothing like eating", "something like this": "like" is a preposition.
                        || [
                            "nothing", "something", "anything", "everything", "somewhere",
                            "anywhere",
                        ]
                        .contains(&p.normalized.as_str()));
            if !subjunctive && !compound && !narrative && !dropped_do && !imperative {
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
