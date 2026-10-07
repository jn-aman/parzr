//! Clause boundaries: comma splices, run-on sentences, fragments cut off by a period, commas after
//! introductory words and clauses, commas that split a subject from its verb, and question marks.
//! A clause is a subject followed by its finite verb; every rule needs one on each side and backs
//! off from lists, appositives, tag questions, dialogue and anything a writer may have meant.
use crate::{
    Edit, Request, make_edit, morphology,
    punctuation::finite,
    spelling,
    tokenizer::{self, Token},
};

pub(crate) const SUBORDINATORS: [&str; 15] = [
    "if", "when", "once", "since", "because", "although", "though", "while", "unless", "before",
    "after", "until", "whenever", "as", "whereas",
];
pub(crate) const PREPOSITIONS: [&str; 18] = [
    "in",
    "on",
    "at",
    "by",
    "for",
    "with",
    "from",
    "during",
    "after",
    "before",
    "over",
    "under",
    "through",
    "without",
    "within",
    "throughout",
    "around",
    "upon",
];
/// Words that are a subject on their own.
const SUBJECTS: [&str; 18] = [
    "i",
    "you",
    "we",
    "they",
    "he",
    "she",
    "it",
    "this",
    "that",
    "there",
    "nobody",
    "everyone",
    "everybody",
    "someone",
    "somebody",
    "nothing",
    "everything",
    "something",
];
/// A subject and its verb in one word.
const CONTRACTED: [&str; 33] = [
    "i'm",
    "i'll",
    "i've",
    "i'd",
    "you're",
    "you'll",
    "you've",
    "you'd",
    "we're",
    "we'll",
    "we've",
    "we'd",
    "they're",
    "they'll",
    "they've",
    "they'd",
    "he's",
    "he'll",
    "he'd",
    "she's",
    "she'll",
    "she'd",
    "it's",
    "it'll",
    "it'd",
    "that's",
    "that'll",
    "there's",
    "there'll",
    "here's",
    "nobody's",
    "everyone's",
    "what's",
];
const DETERMINERS: [&str; 26] = [
    "the", "a", "an", "my", "our", "your", "their", "his", "her", "its", "this", "that", "these",
    "those", "all", "most", "some", "many", "every", "each", "no", "both", "several", "any",
    "more", "few",
];
const NEGATED: [&str; 17] = [
    "can't",
    "couldn't",
    "won't",
    "wouldn't",
    "shouldn't",
    "isn't",
    "aren't",
    "wasn't",
    "weren't",
    "hasn't",
    "haven't",
    "hadn't",
    "doesn't",
    "don't",
    "didn't",
    "mustn't",
    "cannot",
];
const AUXILIARIES: [&str; 20] = [
    "am", "is", "are", "was", "were", "has", "have", "had", "do", "does", "did", "can", "could",
    "may", "might", "must", "shall", "should", "will", "would",
];
/// Adverbs that sit between a subject and its verb ("we never open", "it also improves").
const MID_ADVERBS: [&str; 18] = [
    "just",
    "never",
    "also",
    "still",
    "already",
    "always",
    "really",
    "only",
    "even",
    "probably",
    "usually",
    "often",
    "finally",
    "actually",
    "definitely",
    "recently",
    "sometimes",
    "not",
];
/// Words that end a noun phrase before any verb could: the subject did not continue.
const PHRASE_BREAKS: [&str; 14] = [
    "and", "or", "but", "that", "which", "who", "whom", "whose", "if", "when", "because", "so",
    "than", "as",
];

/// "I'm", "we'll", "it's": a subject and its verb in one word.
pub(crate) fn subject_contraction(word: &str) -> bool {
    CONTRACTED.contains(&word.replace('’', "'").as_str())
}
/// Words inside a clause that make an "and" or "or" after them join parts of a smaller unit
/// ("if you call and nobody answers", "the plan that we chose and they approved").
const EMBEDDED: [&str; 15] = [
    "if", "when", "that", "which", "who", "because", "whether", "while", "although", "though",
    "since", "unless", "until", "both", "either",
];
/// "…older devices and it also improves…": a comma before a conjunction that joins two complete
/// clauses, each with its own subject. Lists, shared subjects and short pairs stay as typed.
pub(crate) fn coordinated(req: &Request, tokens: &[Token<'_>], i: usize, edits: &mut Vec<Edit>) {
    let conj = &tokens[i];
    let s = tokens[..i]
        .iter()
        .rposition(|t| t.sentence != conj.sentence || t.paragraph != conj.paragraph)
        .map_or(0, |n| n + 1);
    let e = (i..tokens.len())
        .find(|&n| tokens[n].sentence != conj.sentence || tokens[n].paragraph != conj.paragraph)
        .unwrap_or(tokens.len());
    let Some(end) = last_word(tokens, s, e) else {
        return;
    };
    if quoted(tokens, s, e)
        || tokens[s..end].iter().any(|t| t.surface == ",")
        // Short pairs ("We bought a couch and it's comfy") read fine without the comma.
        || conj.normalized != "yet" && (words(tokens, s, i) < 6 || words(tokens, i + 1, end) < 4)
        || words(tokens, s, i) < 4
        || words(tokens, i + 1, end) < 3
        || (s..i).any(|k| {
            EMBEDDED.contains(&word(tokens, k)) || takes_clause(tokens, k) && word(tokens, k + 1) != "to"
        })
        || ["and", "or", "but", "nor", "between"].contains(&word(tokens, i - 1))
    {
        return;
    }
    let right = clause_at(tokens, i + 1, end).is_some_and(|v| {
        // The second clause has a subject of its own, not a verb after an object ("and sent it").
        let w = word(tokens, i + 1);
        v > i + 1 || CONTRACTED.contains(&w)
    });
    let left = clause_at(tokens, s, i).is_some()
        || conj.normalized == "or" && word(tokens, s) == "please" && base_verb(&tokens[s + 1]);
    if left && right {
        put(
            req,
            edits,
            tokens[i - 1].end_utf16,
            tokens[i - 1].end_utf16,
            ",",
            "punctuation.coordinated_clauses",
            "Separate these independent clauses before the coordinating conjunction.",
            0.88,
        );
    }
}
/// The finite verb at `k`. "am" glued to a number is a time ("2am"), not a verb.
pub(crate) fn finite_at(tokens: &[Token<'_>], k: usize) -> bool {
    let t = &tokens[k];
    if !t.is_word
        || ["am", "pm"].contains(&t.normalized.as_str())
            && k > 0
            && tokens[k - 1].end_byte == t.start_byte
    {
        return false;
    }
    NEGATED.contains(&t.normalized.as_str())
        || finite(t)
        // "She quit", "it hit": verbs whose past is their base, right after a subject.
        || SAME_PAST.contains(&t.normalized.as_str())
            && k > 0
            && SUBJECTS[..7].contains(&tokens[k - 1].normalized.as_str())
}
const SAME_PAST: [&str; 12] = [
    "quit", "set", "hit", "shut", "hurt", "cost", "split", "upset", "spread", "fit", "bet", "burst",
];
/// A noun that also reads as a verb form ("results", "reports", "update").
pub(crate) fn noun_or_verb(t: &Token<'_>) -> bool {
    spelling::flags(&t.normalized) & 2 != 0
        && t.pos != "Verb"
        && !AUXILIARIES.contains(&t.normalized.as_str())
        && !NEGATED.contains(&t.normalized.as_str())
}
fn base_verb(t: &Token<'_>) -> bool {
    t.is_word
        && morphology::verb(&t.normalized).is_some_and(|v| v.base == t.normalized)
        && (t.pos == "Verb"
            || t.pos.is_empty()
                && (morphology::predicate(&t.normalized)
                    || spelling::flags(&t.normalized) & 2 == 0))
}
fn word<'a>(tokens: &'a [Token<'_>], k: usize) -> &'a str {
    tokens.get(k).map_or("", |t| t.normalized.as_str())
}
/// The index of the verb when a clause begins at `j` (before `end`): a subject followed by its
/// finite verb ("the old cluster will", "results will", "we never open", "I'll").
pub(crate) fn clause_at(tokens: &[Token<'_>], j: usize, end: usize) -> Option<usize> {
    let t = tokens.get(j).filter(|_| j < end)?;
    if !t.is_word {
        return None;
    }
    let w = t.normalized.as_str();
    if CONTRACTED.contains(&w) {
        return (j + 1 < end).then_some(j);
    }
    let verb_after = |mut k: usize, plural: bool| -> Option<usize> {
        while k < end && MID_ADVERBS.contains(&word(tokens, k)) {
            k += 1;
        }
        (k < end
            && (finite_at(tokens, k)
                && !(k + 1 < end && finite_at(tokens, k + 1) && noun_or_verb(&tokens[k]))
                || plural && base_verb(&tokens[k])))
        .then_some(k)
    };
    if SUBJECTS.contains(&w) {
        return verb_after(j + 1, ["i", "you", "we", "they"].contains(&w));
    }
    let determined = DETERMINERS.contains(&w);
    let capitalized = t.surface.starts_with(char::is_uppercase);
    // "results will", "Tickets are": a plural noun that also reads as a verb is the subject
    // when a verb follows.
    let noun_subject = noun_or_verb(t) && j + 1 < end && finite_at(tokens, j + 1);
    let bare = !determined
        && (spelling::flags(w) & (2 | 8 | 16) != 0 || capitalized)
        && (!finite_at(tokens, j) || noun_subject)
        && !AUXILIARIES.contains(&w)
        && !SUBORDINATORS.contains(&w)
        && !PREPOSITIONS.contains(&w)
        && !PHRASE_BREAKS.contains(&w)
        && !MID_ADVERBS.contains(&w)
        && ![
            "please", "let", "let's", "thanks", "thank", "maybe", "so", "then", "now",
        ]
        .contains(&w);
    if !determined && !bare {
        return None;
    }
    let limit = if determined { 7 } else { 3 };
    for k in j + 1..(j + limit).min(end) {
        let x = &tokens[k];
        if !x.is_word && !x.surface.chars().all(|c| c.is_ascii_digit()) {
            return None;
        }
        let xw = x.normalized.as_str();
        if PHRASE_BREAKS.contains(&xw) || SUBJECTS.contains(&xw) || CONTRACTED.contains(&xw) {
            return None;
        }
        // The head noun of "most users" or "the reports" is not the verb, nor is a noun right
        // after a determiner, preposition or adjective ("the sports tournament").
        let before = word(tokens, k - 1);
        if determined && k == j + 1 {
            if DETERMINERS.contains(&xw) || PREPOSITIONS.contains(&xw) || AUXILIARIES.contains(&xw)
            {
                return None;
            }
            continue;
        }
        if MID_ADVERBS.contains(&xw)
            || DETERMINERS.contains(&before)
            || PREPOSITIONS.contains(&before)
            || spelling::flags(before) & (4 | 8) == 8 && spelling::flags(xw) & 2 != 0
        {
            continue;
        }
        // The noun before any adverbs decides whether a plain verb form agrees ("users never open").
        let noun = (j..k)
            .rev()
            .map(|n| word(tokens, n))
            .find(|x| !MID_ADVERBS.contains(x))
            .unwrap_or("");
        let plural =
            spelling::flags(noun) & 16 != 0 || noun.ends_with('s') && !noun.ends_with("ss");
        if let Some(v) = verb_after(k, plural) {
            return Some(v);
        }
    }
    None
}
/// "can you", "is the slot", "did Maya": an auxiliary before its subject opens a question.
pub(crate) fn inverted_question(tokens: &[Token<'_>], j: usize, end: usize) -> bool {
    let (a, b) = (word(tokens, j), word(tokens, j + 1));
    if j + 2 >= end || !(AUXILIARIES.contains(&a) || NEGATED.contains(&a)) {
        return false;
    }
    let pronoun = ["you", "i", "we", "they", "he", "she", "it", "there"].contains(&b);
    match a {
        "do" | "does" | "did" | "don't" | "doesn't" | "didn't" => {
            pronoun && !(a == "do" && b == "it")
                || DETERMINERS.contains(&b) && !["this", "that"].contains(&b)
        }
        "have" | "has" | "had" => pronoun,
        "am" => b == "i",
        _ => {
            pronoun
                || DETERMINERS.contains(&b) && b != "a"
                || tokens[j + 1].surface.starts_with(char::is_uppercase)
        }
    }
}
/// "What time does the game start", "Where are you", "Who's coming".
fn wh_question(tokens: &[Token<'_>], j: usize, end: usize) -> bool {
    let w = word(tokens, j);
    if ["what's", "where's", "who's", "how's", "when's", "why's"].contains(&w) {
        return true;
    }
    ["what", "when", "where", "why", "how", "who", "which"].contains(&w)
        && (j + 1..(j + 4).min(end)).any(|k| inverted_question(tokens, k, end))
}
/// "please send", "let me know", "let's go", "don't wait", "feel free": a command opens a clause.
fn imperative_at(tokens: &[Token<'_>], j: usize, end: usize) -> bool {
    let (a, b) = (word(tokens, j), word(tokens, j + 1));
    j + 1 < end
        && (a == "please" && base_verb(&tokens[j + 1])
            || a == "let's"
            || a == "let" && ["me", "us"].contains(&b)
            || a == "feel" && b == "free"
            || a == "don't" && base_verb(&tokens[j + 1]))
}
/// "Thanks for sending it over": a sentence of its own, though it has no subject.
fn thanks_for(tokens: &[Token<'_>], s: usize, end: usize) -> bool {
    match word(tokens, s) {
        "thanks" => word(tokens, s + 1) == "for" && s + 3 < end,
        "thank" => word(tokens, s + 1) == "you" && word(tokens, s + 2) == "for" && s + 4 < end,
        _ => false,
    }
}
/// Sentences as token ranges (end exclusive, final mark included).
fn sentences(tokens: &[Token<'_>]) -> Vec<(usize, usize)> {
    let mut out = vec![];
    let mut start = 0;
    for k in 1..=tokens.len() {
        if k == tokens.len()
            || tokens[k].sentence != tokens[start].sentence
            || tokens[k].paragraph != tokens[start].paragraph
        {
            out.push((start, k));
            start = k;
        }
    }
    out
}
fn words(tokens: &[Token<'_>], a: usize, b: usize) -> usize {
    tokens[a..b].iter().filter(|t| t.is_word).count()
}
/// One past the last word or number of the sentence.
fn last_word(tokens: &[Token<'_>], s: usize, e: usize) -> Option<usize> {
    (s..e)
        .rev()
        .find(|&k| tokens[k].is_word || tokens[k].surface.chars().all(|c| c.is_ascii_digit()))
        .map(|k| k + 1)
}
fn spaced(text: &str, a: &Token<'_>, b: &Token<'_>) -> bool {
    a.end_byte < b.start_byte && text[a.end_byte..b.start_byte].chars().all(|c| c == ' ')
}
fn quoted(tokens: &[Token<'_>], s: usize, e: usize) -> bool {
    tokens[s..e]
        .iter()
        .any(|t| ["\"", "“", "”", "—", "–", "(", ")", ";", ":"].contains(&t.surface))
}

#[expect(
    clippy::too_many_arguments,
    reason = "Mirrors make_edit; every call site names its rule."
)]
fn put(
    req: &Request,
    edits: &mut Vec<Edit>,
    start: usize,
    end: usize,
    replacement: &str,
    id: &str,
    reason: &str,
    confidence: f32,
) {
    if let Some(edit) = make_edit(
        &req.text,
        start,
        end,
        replacement.into(),
        "Punctuation",
        id,
        reason,
        confidence,
    ) {
        edits.push(edit);
    }
}
/// The first letter of `t` in upper case, when the token now starts a sentence.
fn capitalize(req: &Request, edits: &mut Vec<Edit>, t: &Token<'_>, id: &str) {
    let Some(first) = t.surface.chars().next().filter(|c| c.is_lowercase()) else {
        return;
    };
    put(
        req,
        edits,
        t.start_utf16,
        t.start_utf16 + first.len_utf16(),
        &first.to_uppercase().to_string(),
        id,
        "Start the new sentence with a capital letter.",
        0.88,
    );
}

pub fn check(req: &Request, edits: &mut Vec<Edit>) {
    let tokens = tokenizer::tokenize(&req.text, &req.tokens);
    if tokens.is_empty() {
        return;
    }
    let ranges = sentences(&tokens);
    for &(s, e) in &ranges {
        comma_splice(req, &tokens, s, e, edits);
        run_on(req, &tokens, s, e, edits);
        introductory_comma(req, &tokens, s, e, edits);
        extra_comma(req, &tokens, s, e, edits);
        question_mark(req, &tokens, s, e, edits);
    }
    for pair in ranges.windows(2) {
        fragment(req, &tokens, pair[0], pair[1], edits);
    }
}

/// Adverbs that link two sentences after a comma ("…, however, we…").
const CONJUNCTIVE: [&str; 10] = [
    "however",
    "therefore",
    "consequently",
    "otherwise",
    "moreover",
    "furthermore",
    "nevertheless",
    "meanwhile",
    "instead",
    "hence",
];
/// Sentence adverbs that may open the second clause of a splice ("…, luckily Sam had one").
const SENTENCE_ADVERBS: [&str; 10] = [
    "luckily",
    "unfortunately",
    "fortunately",
    "hopefully",
    "honestly",
    "sadly",
    "thankfully",
    "apparently",
    "obviously",
    "maybe",
];
const SPEECH: [&str; 14] = [
    "said",
    "says",
    "asked",
    "asks",
    "replied",
    "added",
    "explained",
    "whispered",
    "told",
    "wrote",
    "shouted",
    "answered",
    "admitted",
    "noted",
];
/// A clause that can stand alone and ends complete: it opens with its subject and does not stop
/// on a verb, preposition or determiner ("The problem is, we…" is one sentence).
fn independent(tokens: &[Token<'_>], s: usize, c: usize) -> bool {
    if words(tokens, s, c) < 3 {
        return false;
    }
    let last = &tokens[c - 1];
    let lw = last.normalized.as_str();
    // "May" mid-sentence is the month.
    let month = last.surface == "May";
    if !month && (AUXILIARIES.contains(&lw) || NEGATED.contains(&lw))
        || takes_clause(tokens, c - 1)
        || [
            "of", "to", "for", "with", "from", "at", "by", "during", "upon", "without",
        ]
        .contains(&lw)
        || DETERMINERS.contains(&lw)
        || PHRASE_BREAKS.contains(&lw)
    {
        return false;
    }
    clause_at(tokens, s, c).is_some()
        || thanks_for(tokens, s, c)
        || word(tokens, s) == "please" && base_verb(&tokens[s + 1])
}
/// "The invoice is attached, let me know…": two sentences joined by a bare comma.
fn comma_splice(req: &Request, tokens: &[Token<'_>], s: usize, e: usize, edits: &mut Vec<Edit>) {
    let Some(end) = last_word(tokens, s, e) else {
        return;
    };
    if quoted(tokens, s, e) {
        return;
    }
    let commas: Vec<usize> = (s..end).filter(|&k| tokens[k].surface == ",").collect();
    let question = tokens[end..e].iter().any(|t| t.surface == "?");
    let (c, r) = match commas.as_slice() {
        [c] => (*c, *c + 1),
        [c, d] if *d == c + 2 && CONJUNCTIVE.contains(&word(tokens, c + 1)) => (*c, *d + 1),
        [c, d]
            if *d == c + 4
                && (c + 1..*d).map(|k| word(tokens, k)).collect::<Vec<_>>()
                    == ["as", "a", "result"] =>
        {
            (*c, *d + 1)
        }
        _ => return,
    };
    let linked = r != c + 1;
    if !independent(tokens, s, c) || words(tokens, c + 1, end) < 3 {
        return;
    }
    let r = if !linked && SENTENCE_ADVERBS.contains(&word(tokens, r)) {
        r + 1
    } else {
        r
    };
    let speech = |v: usize| SPEECH.contains(&word(tokens, v)) && end - r <= 5;
    if !(clause_at(tokens, r, end).is_some_and(|v| !speech(v))
        // ", please check it" is a common, accepted request after a statement.
        || imperative_at(tokens, r, end) && word(tokens, r) != "please"
        || question && inverted_question(tokens, r, end))
    {
        return;
    }
    let comma = &tokens[c];
    put(
        req,
        edits,
        comma.start_utf16,
        comma.end_utf16,
        ".",
        "punctuation.comma_splice",
        "These are two complete sentences; a comma alone cannot join them.",
        0.86,
    );
    capitalize(req, edits, &tokens[c + 1], "punctuation.comma_splice");
}

/// Words that keep a sentence from being split where a second subject appears: subordinate and
/// relative clauses, comparisons, and verbs or adjectives that take a clause without "that"
/// ("I think it works", "I'm sorry I missed it", "so tired I fell asleep").
const NO_SPLIT: &[&str] = &[
    "that",
    "which",
    "who",
    "whom",
    "whose",
    "when",
    "where",
    "why",
    "how",
    "what",
    "if",
    "whether",
    "because",
    "since",
    "as",
    "than",
    "so",
    "such",
    "though",
    "although",
    "while",
    "until",
    "unless",
    "before",
    "after",
    "once",
    "and",
    "or",
    "but",
    "think",
    "thought",
    "know",
    "knew",
    "known",
    "say",
    "said",
    "says",
    "tell",
    "told",
    "hope",
    "hoped",
    "guess",
    "feel",
    "felt",
    "believe",
    "mean",
    "meant",
    "wish",
    "realize",
    "realized",
    "notice",
    "noticed",
    "hear",
    "heard",
    "sure",
    "glad",
    "sorry",
    "afraid",
    "happy",
    "sad",
    "surprised",
    "worried",
    "proud",
    "aware",
    "certain",
    "convinced",
    "excited",
    "lucky",
    "thankful",
    "grateful",
    "see",
    "saw",
    "seen",
    "show",
    "showed",
    "figure",
    "figured",
    "bet",
    "promise",
    "promised",
    "remember",
    "forgot",
    "forget",
    "find",
    "found",
    "decide",
    "decided",
    "learned",
    "understand",
    "understood",
    "mind",
    "wonder",
    "asked",
    "ask",
    "suppose",
    "assume",
    "doubt",
    "expect",
    "expected",
    "imagine",
    "reckon",
    "swear",
    "swore",
    "sworn",
    "shown",
    "like",
    "want",
    "make",
    "made",
    "upset",
    "disappointed",
    "relieved",
    "shocked",
    "amazed",
    "pleased",
    "thrilled",
    "positive",
    "confident",
    "hopeful",
];
/// Verbs that take a clause without "that" in any of their forms ("I could've sworn it was").
const CLAUSE_VERBS: &[&str] = &[
    "think",
    "know",
    "say",
    "tell",
    "hope",
    "guess",
    "feel",
    "believe",
    "mean",
    "wish",
    "realize",
    "notice",
    "hear",
    "see",
    "show",
    "figure",
    "bet",
    "promise",
    "remember",
    "forget",
    "find",
    "decide",
    "learn",
    "understand",
    "mind",
    "wonder",
    "ask",
    "suppose",
    "assume",
    "doubt",
    "expect",
    "imagine",
    "reckon",
    "swear",
    "pretend",
    "claim",
    "admit",
    "mention",
    "explain",
    "agree",
    "worry",
    "prove",
    "insist",
    "suggest",
    "warn",
    "confirm",
    "discover",
    "sense",
    "fear",
    "predict",
    "guarantee",
    "ensure",
    "argue",
    "complain",
    "announce",
    "deny",
    "recall",
    "regret",
    "acknowledge",
    "conclude",
    "dream",
];
/// A word after which a second subject may begin an embedded clause, not a new sentence. A verb
/// used as a noun ("the report") does not count.
fn takes_clause(tokens: &[Token<'_>], k: usize) -> bool {
    let t = &tokens[k];
    let before = word(tokens, k.wrapping_sub(1));
    NO_SPLIT.contains(&t.normalized.as_str())
        || morphology::verb(&t.normalized).is_some_and(|v| CLAUSE_VERBS.contains(&v.base.as_str()))
            && t.pos != "Noun"
            && !DETERMINERS.contains(&before)
            && spelling::flags(before) & (4 | 8) != 8
}
/// Where the verbs and adjectives of `NO_SPLIT` begin, after its linking words.
const COMPLEMENT_TAKERS: usize = 29;
const TIME_ENDS: [&str; 21] = [
    "today",
    "tonight",
    "tomorrow",
    "yesterday",
    "now",
    "later",
    "again",
    "already",
    "soon",
    "anymore",
    "morning",
    "afternoon",
    "evening",
    "night",
    "midnight",
    "noon",
    "weekend",
    "week",
    "month",
    "year",
    "here",
];
const MONTHS: [&str; 19] = [
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
];
/// The clause before `i` plainly ends: on a time word or -ly adverb, a predicate adjective or
/// participle ("is broken", "has shipped"), a month or weekday after a preposition, or a number.
fn plain_end(tokens: &[Token<'_>], s: usize, i: usize, pronoun: bool) -> bool {
    let prev = &tokens[i - 1];
    let w = prev.normalized.as_str();
    let before = word(tokens, i.wrapping_sub(2));
    if MID_ADVERBS.contains(&w) || PREPOSITIONS.contains(&w) || DETERMINERS.contains(&w) {
        return false;
    }
    // A participle after "has" ends its clause only when a pronoun opens the next one ("has
    // shipped it should"); "has written the review" goes on to its object.
    let perfect = ["has", "have", "had"].contains(&before) || before.ends_with("'ve");
    if perfect && !pronoun {
        return false;
    }
    let copula = |x: &str| {
        [
            "is", "are", "was", "were", "be", "been", "am", "has", "have", "had", "very", "really",
            "too", "super", "pretty", "not",
        ]
        .contains(&x)
            || ["'s", "'m", "'re", "'ve"].iter().any(|c| x.ends_with(c))
    };
    TIME_ENDS.contains(&w) && (w != "here" || i - s >= 3)
        || w.ends_with("ly") && spelling::flags(w) & 2 == 0 && w.len() > 4
        || MONTHS.contains(&w) && PREPOSITIONS.contains(&before)
        || prev.surface.chars().all(|c| c.is_ascii_digit()) && PREPOSITIONS.contains(&before)
        || i >= s + 2
            && copula(before)
            && (spelling::flags(w) & 8 != 0
                || w.ends_with("ing")
                || morphology::verb(w).is_some_and(|v| v.participle == w))
        || [
            "failed", "started", "finished", "shipped", "crashed", "arrived", "left", "died",
        ]
        .contains(&w)
            && words(tokens, s, i) <= 4
        || NEGATED.contains(&before) && base_verb(prev) && words(tokens, s, i) <= 4
}
/// "I sent the report this morning it should be in your inbox": two clauses with nothing between.
fn run_on(req: &Request, tokens: &[Token<'_>], s: usize, e: usize, edits: &mut Vec<Edit>) {
    let Some(end) = last_word(tokens, s, e) else {
        return;
    };
    if quoted(tokens, s, e) || tokens[s..end].iter().any(|t| t.surface == ",") {
        return;
    }
    let question = tokens[end..e].iter().any(|t| t.surface == "?");
    let thanks = thanks_for(tokens, s, end);
    for i in s + 2..end.saturating_sub(1) {
        let (prev, t) = (&tokens[i - 1], &tokens[i]);
        if !t.is_word || !spaced(&req.text, prev, t) || takes_clause(tokens, i - 1) {
            continue;
        }
        if (s..i).any(|k| takes_clause(tokens, k)) {
            break;
        }
        let w = t.normalized.as_str();
        let pronoun = SUBJECTS[..7].contains(&w) || CONTRACTED[..29].contains(&w);
        let clause = clause_at(tokens, i, end);
        let left = clause_at(tokens, s, i).is_some_and(|v| v < i);
        let left_words = words(tokens, s, i);
        let strong = question && inverted_question(tokens, i, end)
            || imperative_at(tokens, i, end)
            || w == "maybe" && clause_at(tokens, i + 1, end).is_some();
        let ok = if strong {
            (left && left_words >= 2) && words(tokens, i, end) >= 3
        } else if pronoun && clause.is_some() {
            // "It's late I'm going to bed": two words are enough before a contracted subject.
            let short =
                left_words == 2 && CONTRACTED.contains(&w) && CONTRACTED.contains(&word(tokens, s));
            (left && (left_words >= 3 || short) && plain_end(tokens, s, i, true)
                || thanks
                    && (CONTRACTED.contains(&w)
                        || clause.is_some_and(|v| AUXILIARIES.contains(&word(tokens, v)))))
                && words(tokens, i, end) >= 3
        } else if DETERMINERS.contains(&w)
            && let Some(v) = clause
        {
            left && left_words >= 3
                && (plain_end(tokens, s, i, false)
                    || ["is", "are", "was", "were", "will", "must", "should", "can"]
                        .contains(&word(tokens, v))
                        && !finite_at(tokens, i - 1)
                        && spelling::flags(word(tokens, i - 1)) & 2 != 0)
                && words(tokens, i, end) >= 3
        } else {
            false
        };
        if !ok {
            continue;
        }
        put(
            req,
            edits,
            prev.end_utf16,
            prev.end_utf16,
            ".",
            "punctuation.run_on",
            "Separate these complete sentences with a period.",
            0.86,
        );
        capitalize(req, edits, t, "punctuation.run_on");
        return;
    }
}

/// Openers of a subordinate clause or phrase that cannot stand as a sentence of its own, with
/// what joins them back to the sentence before.
const FRAGMENT_OPENERS: [(&str, &str); 16] = [
    ("so", " "),
    ("because", " "),
    ("since", " "),
    ("which", ", "),
    ("after", " "),
    ("when", " "),
    ("if", " "),
    ("before", " "),
    ("while", " "),
    ("once", " "),
    ("until", " "),
    ("unless", " "),
    ("except", " "),
    ("including", ", "),
    ("with", " "),
    ("due", " "),
];
/// "I left early. Because I was tired.": a subordinate clause cut off by a period.
fn fragment(
    req: &Request,
    tokens: &[Token<'_>],
    (ps, pe): (usize, usize),
    (s, e): (usize, usize),
    edits: &mut Vec<Edit>,
) {
    let opener = &tokens[s];
    let Some((_, join)) = FRAGMENT_OPENERS
        .iter()
        .find(|(w, _)| *w == opener.normalized)
    else {
        return;
    };
    let Some(end) = last_word(tokens, s, e) else {
        return;
    };
    let Some(prev_end) = last_word(tokens, ps, pe) else {
        return;
    };
    let stop = &tokens[pe - 1];
    if opener.paragraph != stop.paragraph
        || stop.surface != "."
        || prev_end != pe - 1
        || !opener.surface.starts_with(char::is_uppercase)
        || tokens[s..end].iter().any(|t| t.surface == ",")
        || quoted(tokens, s, e)
        || tokens[end..e].iter().any(|t| t.surface == "?")
        || words(tokens, s, end) < 2
        || !independent(tokens, ps, prev_end)
        || inverted_question(tokens, s + 1, end)
        || opener.normalized == "due" && word(tokens, s + 1) != "to"
        || opener.normalized == "except" && word(tokens, s + 1) != "for"
        || opener.normalized == "so" && word(tokens, s + 1) != "that"
    {
        return;
    }
    // One subordinate clause at most: a second subject and verb make it a full sentence.
    let clauses = (s + 1..end)
        .filter(|&k| SUBJECTS.contains(&word(tokens, k)) || CONTRACTED.contains(&word(tokens, k)))
        .filter(|&k| clause_at(tokens, k, end).is_some())
        .count();
    if clauses > 1 {
        return;
    }
    let first = opener.surface.chars().next().unwrap_or(' ');
    let lowered = format!("{join}{}", first.to_lowercase().collect::<String>());
    put(
        req,
        edits,
        stop.start_utf16,
        opener.start_utf16 + first.len_utf16(),
        &lowered,
        "punctuation.fragment",
        "This part cannot stand as a sentence; join it to the sentence before.",
        0.86,
    );
}

/// Sentence-opening words that a comma separates from the clause they introduce.
const INTRO_WORDS: [&str; 22] = [
    "yes",
    "no",
    "well",
    "hopefully",
    "unfortunately",
    "fortunately",
    "luckily",
    "honestly",
    "apparently",
    "obviously",
    "sadly",
    "thankfully",
    "ideally",
    "personally",
    "frankly",
    "however",
    "meanwhile",
    "otherwise",
    "therefore",
    "additionally",
    "consequently",
    "nevertheless",
];
const GREETINGS: [&str; 4] = ["hi", "hey", "hello", "dear"];
/// Words that begin a message right after a greeting and a name ("Hi Sarah I hope…").
const AFTER_GREETING: [&str; 22] = [
    "i", "we", "hope", "thanks", "thank", "just", "quick", "how", "can", "could", "i'm", "i've",
    "i'll", "it", "this", "sorry", "please", "happy", "good", "welcome", "hope", "are",
];
/// Verbs whose object would otherwise be read as the subject of the main clause.
const OBJECT_TAKERS: [&str; 6] = ["have", "has", "had", "get", "got", "need"];
fn introductory_comma(
    req: &Request,
    tokens: &[Token<'_>],
    s: usize,
    e: usize,
    edits: &mut Vec<Edit>,
) {
    let Some(end) = last_word(tokens, s, e) else {
        return;
    };
    let first = &tokens[s];
    if !crate::starts_sentence(&req.text, first.start_byte, req) || quoted(tokens, s, e) {
        return;
    }
    let comma_after = |edits: &mut Vec<Edit>, k: usize, id: &str, reason: &str| {
        let t = &tokens[k];
        put(req, edits, t.end_utf16, t.end_utf16, ",", id, reason, 0.88);
    };
    let fw = first.normalized.as_str();
    let next = tokens.get(s + 1);
    // "Yes that works", "Hopefully the new process will".
    if INTRO_WORDS.contains(&fw)
        && next.is_some_and(|n| spaced(&req.text, first, n))
        && clause_at(tokens, s + 1, end).is_some()
        && !(fw == "no"
            && ["one", "doubt", "way", "problem", "worries"].contains(&word(tokens, s + 1)))
    {
        comma_after(
            edits,
            s,
            "punctuation.introductory_comma",
            "Put a comma after an introductory word.",
        );
        return;
    }
    // "Hi Sarah I hope": a comma closes the greeting.
    if GREETINGS.contains(&fw) {
        let mut k = s + 1;
        while k < end
            && k <= s + 2
            && tokens[k].surface.starts_with(char::is_uppercase)
            && !AFTER_GREETING.contains(&word(tokens, k))
        {
            k += 1;
        }
        if k > s + 1
            && k < end
            && spaced(&req.text, &tokens[k - 1], &tokens[k])
            && AFTER_GREETING.contains(&word(tokens, k))
        {
            comma_after(
                edits,
                k - 1,
                "punctuation.greeting_comma",
                "Put a comma after the greeting.",
            );
        }
        return;
    }
    // "Once the contract is signed we can start": a comma closes the introductory clause.
    if !SUBORDINATORS.contains(&fw) || fw == "as" || fw == "whereas" {
        return;
    }
    if tokens[s..end].iter().any(|t| t.surface == ",")
        || AUXILIARIES.contains(&word(tokens, s + 1))
        || NEGATED.contains(&word(tokens, s + 1))
    {
        return;
    }
    let question = tokens[end..e].iter().any(|t| t.surface == "?");
    let prepositional = ["since", "after", "before", "until"].contains(&fw);
    for j in s + 2..end.saturating_sub(2) {
        if !spaced(&req.text, &tokens[j - 1], &tokens[j]) {
            continue;
        }
        let part = s + 1..j;
        if part.clone().any(|k| {
            let w = word(tokens, k);
            ["that", "which", "who"].contains(&w) || NO_SPLIT[COMPLEMENT_TAKERS..].contains(&w)
        }) {
            return;
        }
        let has_verb = part.clone().any(|k| {
            finite_at(tokens, k)
                || base_verb(&tokens[k])
                    && ["i", "you", "we", "they"].contains(&word(tokens, k - 1))
        });
        if !(has_verb || prepositional && words(tokens, s + 1, j) >= 3) {
            continue;
        }
        let prev = &tokens[j - 1];
        if PREPOSITIONS.contains(&word(tokens, j - 1))
            || DETERMINERS.contains(&word(tokens, j - 1))
            || AUXILIARIES.contains(&word(tokens, j - 1))
            || !prev.is_word && !prev.surface.chars().all(|c| c.is_ascii_digit())
        {
            continue;
        }
        let verb_before = prev.pos == "Verb" || prev.pos.is_empty() && finite_at(tokens, j - 1);
        let main = if question && inverted_question(tokens, j, end) || imperative_at(tokens, j, end)
        {
            true
        } else if let Some(v) = clause_at(tokens, j, end) {
            let w = word(tokens, j);
            (SUBJECTS[..7].contains(&w) && w != "it"
                || CONTRACTED.contains(&w)
                || DETERMINERS.contains(&w))
                && (!verb_before
                    || (AUXILIARIES.contains(&word(tokens, v))
                        || NEGATED.contains(&word(tokens, v))
                        || CONTRACTED.contains(&word(tokens, v)))
                        && !OBJECT_TAKERS.contains(&word(tokens, j - 1)))
        } else {
            false
        };
        if main {
            comma_after(
                edits,
                j - 1,
                "punctuation.introductory_comma",
                "Put a comma after the introductory clause.",
            );
            return;
        }
    }
}

/// Commas that split what belongs together: a subject from its verb ("The users who signed up,
/// received"), two verbs sharing a subject ("I went to the store, and bought"), and set phrases.
fn extra_comma(req: &Request, tokens: &[Token<'_>], s: usize, e: usize, edits: &mut Vec<Edit>) {
    let Some(end) = last_word(tokens, s, e) else {
        return;
    };
    // "On Friday May 5": a comma after the weekday of a date.
    for k in s..end.saturating_sub(2) {
        if MONTHS[12..].contains(&word(tokens, k))
            && MONTHS[..12].contains(&word(tokens, k + 1))
            && tokens[k + 1].surface.starts_with(char::is_uppercase)
            && tokens[k + 2].surface.chars().all(|c| c.is_ascii_digit())
            && spaced(&req.text, &tokens[k], &tokens[k + 1])
        {
            put(
                req,
                edits,
                tokens[k].end_utf16,
                tokens[k].end_utf16,
                ",",
                "punctuation.date_comma",
                "Separate the weekday from the date with a comma.",
                0.9,
            );
        }
        // "such as, Jira" and "Thank you, so much".
        let pair = (word(tokens, k), word(tokens, k + 1));
        if tokens[k + 2].surface == ","
            && (pair == ("such", "as")
                || pair == ("thank", "you")
                    && word(tokens, k + 3) == "so"
                    && word(tokens, k + 4) == "much")
        {
            let comma = &tokens[k + 2];
            put(
                req,
                edits,
                comma.start_utf16,
                comma.end_utf16,
                "",
                "punctuation.extra_comma",
                "No comma here.",
                0.9,
            );
        }
    }
    if quoted(tokens, s, e) {
        return;
    }
    let commas: Vec<usize> = (s..end).filter(|&k| tokens[k].surface == ",").collect();
    let [c] = commas.as_slice() else {
        return;
    };
    let c = *c;
    if words(tokens, s, c) < 3 || words(tokens, c + 1, end) < 2 {
        return;
    }
    let delete = |edits: &mut Vec<Edit>, reason: &str| {
        let comma = &tokens[c];
        put(
            req,
            edits,
            comma.start_utf16,
            comma.end_utf16,
            "",
            "punctuation.extra_comma",
            reason,
            0.86,
        );
    };
    let verb_at = |k: usize| {
        k < end
            && finite_at(tokens, k)
            && !SUBJECTS.contains(&word(tokens, k))
            && !CONTRACTED.contains(&word(tokens, k))
            && !(noun_or_verb(&tokens[k])
                && (k + 1 >= end || finite_at(tokens, k + 1) || tokens[k].pos == "Noun"))
    };
    let fw = word(tokens, s);
    let opens_with_subject =
        SUBJECTS[..7].contains(&fw) || CONTRACTED.contains(&fw) || DETERMINERS.contains(&fw);
    // "He grabbed his coat, and ran out": the second verb shares the subject.
    if ["and", "but"].contains(&word(tokens, c + 1)) && opens_with_subject {
        let Some(v) = clause_at(tokens, s, c) else {
            return;
        };
        let modal = ["will", "would", "can", "could", "should", "must", "might"]
            .contains(&word(tokens, v))
            || word(tokens, v).ends_with("'ll");
        let one_clause = (v + 1..c).all(|k| !finite_at(tokens, k) || noun_or_verb(&tokens[k]));
        let r = c + 2;
        if one_clause
            && (verb_at(r)
                || modal
                    && morphology::verb(word(tokens, r)).is_some_and(|v| v.base == word(tokens, r))
                    && !(r + 1 < end && finite_at(tokens, r + 1)))
            // "and does it work?": an auxiliary before a subject opens a question.
            && !(AUXILIARIES.contains(&word(tokens, r))
                && r + 1 < end
                && SUBJECTS.contains(&word(tokens, r + 1)))
        {
            delete(
                edits,
                "Two verbs that share a subject take no comma between them.",
            );
        }
        return;
    }
    // "The users who signed up last week, received": no comma between a subject and its verb.
    if (DETERMINERS.contains(&fw) && fw != "this" && fw != "that"
        || [
            "everyone",
            "everybody",
            "anyone",
            "anybody",
            "someone",
            "somebody",
        ]
        .contains(&fw))
        && verb_at(c + 1)
    {
        let relative = (s..c).find(|&k| ["who", "that", "which"].contains(&word(tokens, k)));
        let main_verb = (s + 1..c).any(|k| {
            finite_at(tokens, k) && !noun_or_verb(&tokens[k]) && relative.is_none_or(|r| k < r)
        });
        if !main_verb {
            delete(edits, "No comma between the subject and its verb.");
        }
    }
}

/// Verbs and adjectives that embed a question as a statement ("I wonder if…", "not sure what…").
const EMBEDDING: [&str; 16] = [
    "wonder",
    "wondering",
    "know",
    "sure",
    "asked",
    "ask",
    "curious",
    "choose",
    "decide",
    "understand",
    "unsure",
    "check",
    "see",
    "tell",
    "idea",
    "remember",
];
const QUESTION_WORDS: [&str; 9] = [
    "if", "whether", "what", "why", "how", "when", "where", "which", "who",
];
/// A question without its question mark ("Did you get my text"), or a statement with one
/// ("I wonder if they'll fix it?").
fn question_mark(req: &Request, tokens: &[Token<'_>], s: usize, e: usize, edits: &mut Vec<Edit>) {
    let Some(end) = last_word(tokens, s, e) else {
        return;
    };
    let first = &tokens[s];
    if !crate::starts_sentence(&req.text, first.start_byte, req) || quoted(tokens, s, e) {
        return;
    }
    let marks: String = tokens[end..e].iter().map(|t| t.surface).collect();
    if end == tokens.len()
        && marks.is_empty()
        && req.sentence_end
        && words(tokens, s, end) >= 3
        && (inverted_question(tokens, s, end) || wh_question(tokens, s, end))
        && !tokens[s..end].iter().any(|t| t.surface == ",")
        && ![
            "the", "a", "an", "to", "of", "and", "or", "but", "with", "for", "in", "on", "at",
            "my", "your", "our", "their", "his", "her", "its", "is", "are", "if", "that",
        ]
        .contains(&word(tokens, end - 1))
    {
        let last = &tokens[end - 1];
        put(
            req,
            edits,
            last.end_utf16,
            last.end_utf16,
            "?",
            "punctuation.question_mark",
            "End a question with a question mark.",
            0.88,
        );
        return;
    }
    if marks != "?" || tokens[s..end].iter().any(|t| t.surface == ",") {
        return;
    }
    let fw = first.normalized.as_str();
    let declarative = (["i", "we", "she", "he", "they"].contains(&fw)
        || CONTRACTED[..4].contains(&fw)
        || ["we're", "we'd", "she's", "he's"].contains(&fw)
        || fw == "let" && word(tokens, s + 1) == "me")
        || DETERMINERS.contains(&fw) && clause_at(tokens, s, end).is_some()
        || first.surface.starts_with(char::is_uppercase)
            && spelling::flags(fw) & 16 != 0
            && clause_at(tokens, s, end).is_some();
    let embedded = (s + 1..end.saturating_sub(2)).any(|k| {
        EMBEDDING.contains(&word(tokens, k))
            && QUESTION_WORDS.contains(&word(tokens, k + 1))
            && !inverted_question(tokens, k + 2, end)
            && !(AUXILIARIES.contains(&word(tokens, k + 2)) && k + 3 >= end)
    });
    if declarative && embedded {
        let mark = &tokens[end];
        put(
            req,
            edits,
            mark.start_utf16,
            mark.end_utf16,
            ".",
            "punctuation.indirect_question",
            "This is a statement about a question; end it with a period.",
            0.86,
        );
    }
}

#[cfg(test)]
mod tests {
    use crate::Request;
    /// The full pipeline on the rules alone (no tagger hints), as in the tests of lib.rs.
    fn fix(text: &str) -> String {
        crate::pipeline::rewrite(&Request {
            text: text.into(),
            ..Request::default()
        })
        .unwrap()
        .text
    }
    #[test]
    fn two_sentences_joined_by_a_comma_are_split() {
        for (input, expected) in [
            (
                "The shipment left the warehouse this morning, it should arrive by Thursday.",
                "The shipment left the warehouse this morning. It should arrive by Thursday.",
            ),
            (
                "The vendor raised their prices, we need to find another supplier.",
                "The vendor raised their prices. We need to find another supplier.",
            ),
            (
                "The new hire starts on Monday, let me know when her laptop is ready.",
                "The new hire starts on Monday. Let me know when her laptop is ready.",
            ),
            (
                "The library was closed, however, the café next door was open.",
                "The library was closed. However, the café next door was open.",
            ),
        ] {
            assert_eq!(fix(input), expected, "{input}");
        }
    }
    #[test]
    fn commas_that_join_less_than_two_sentences_stay() {
        for text in [
            "You'll be fine, trust me.",
            "It's late, isn't it?",
            "I'm done, she said.",
            "Ok, I'm leaving now.",
            "My sister, who lives in Boston, is visiting.",
            "We bought apples, pears, and plums.",
            "If you need anything, let me know.",
            "The problem is, we don't have time.",
            "Revenue grew last quarter, mostly from new customers.",
            "Long story short, we missed the flight.",
        ] {
            assert_eq!(fix(text), text);
        }
    }
    #[test]
    fn run_ons_and_fragments_get_their_boundary() {
        for (input, expected) in [
            (
                "I'll be home late tonight don't wait for me.",
                "I'll be home late tonight. Don't wait for me.",
            ),
            (
                "My laptop is broken can you lend me yours?",
                "My laptop is broken. Can you lend me yours?",
            ),
            (
                "I stayed home. Because I was sick.",
                "I stayed home because I was sick.",
            ),
            (
                "He finally called. Which was a relief.",
                "He finally called, which was a relief.",
            ),
            (
                "We hired three people. Including a designer.",
                "We hired three people, including a designer.",
            ),
        ] {
            assert_eq!(fix(input), expected, "{input}");
        }
        for text in [
            "I think we should go.",
            "I'm sorry I missed your call.",
            "I'm sure it'll be fine.",
            "I heard they're hiring.",
            "Why? Because I said so.",
            "Thanks so much. With love.",
        ] {
            assert_eq!(fix(text), text);
        }
    }
    #[test]
    fn introductory_and_coordinating_commas() {
        for (input, expected) in [
            (
                "Hi Daniel I wanted to follow up.",
                "Hi Daniel, I wanted to follow up.",
            ),
            (
                "Yes I can make it on Friday.",
                "Yes, I can make it on Friday.",
            ),
            (
                "If the payment fails the order is cancelled.",
                "If the payment fails, the order is cancelled.",
            ),
            (
                "You can pay online with a credit card or you can pay in person at the desk.",
                "You can pay online with a credit card, or you can pay in person at the desk.",
            ),
            (
                "The intern fixed the bug, and pushed the change to staging.",
                "The intern fixed the bug and pushed the change to staging.",
            ),
            (
                "The students who finished early, were allowed to leave.",
                "The students who finished early were allowed to leave.",
            ),
        ] {
            assert_eq!(fix(input), expected, "{input}");
        }
        for text in [
            "On Monday I'll send the invoice.",
            "No one knows yet.",
            "Well done.",
            "We bought a new couch and it's so comfy.",
            "Just finished my first marathon and I can't feel my legs",
            "She finished the report and sent it to the client.",
        ] {
            assert_eq!(fix(text), text);
        }
    }
    #[test]
    fn question_marks_follow_the_shape_of_the_question() {
        for (input, expected) in [
            ("Did the package arrive yet", "Did the package arrive yet?"),
            ("Where did you park the car", "Where did you park the car?"),
            (
                "I'm not sure why the build failed?",
                "I'm not sure why the build failed.",
            ),
        ] {
            assert_eq!(fix(input), expected, "{input}");
        }
        for text in [
            "Have a great weekend",
            "Do it now",
            "See you at 7",
            "You know what I mean?",
            "Can you tell me where the station is?",
        ] {
            assert_eq!(fix(text), text);
        }
    }
}
