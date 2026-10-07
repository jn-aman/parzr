//! Verb-group and word-order repairs inside one clause: a perfect tense with a finished past time,
//! regularized irregular pasts, inverted questions and their auxiliaries, embedded questions,
//! frequency adverbs and a dropped "be" or "have". Each repair reads only the words around it.
use crate::{
    Edit, Request, make_edit, morphology, spelling,
    structure::plural,
    tokenizer::{self, Token},
};

pub(crate) const SUBJECTS: [&str; 7] = ["i", "you", "he", "she", "it", "we", "they"];
pub(crate) const WH: [&str; 6] = ["where", "what", "when", "why", "how", "who"];
/// Words after a wh-word that belong to it ("how old", "what time").
const WH_MODIFIERS: [&str; 9] = [
    "old", "long", "much", "many", "far", "often", "time", "big", "kind",
];
pub(crate) const DETERMINERS: [&str; 11] = [
    "the", "my", "your", "his", "her", "our", "their", "this", "that", "these", "those",
];
const FREQUENCY: [&str; 9] = [
    "always",
    "never",
    "often",
    "usually",
    "sometimes",
    "rarely",
    "seldom",
    "generally",
    "normally",
];
/// Words that end a clause for the purpose of finding its time words.
const CLAUSE_BREAKS: [&str; 20] = [
    ",", ";", ":", ".", "!", "?", "and", "but", "because", "so", "while", "when", "although",
    "though", "if", "after", "before", "until", "since", "whereas",
];

pub(crate) struct Sentence<'t, 'a> {
    pub tokens: &'t [Token<'a>],
    pub question: bool,
}
pub(crate) fn sentences<'t, 'a>(tokens: &'t [Token<'a>]) -> Vec<Sentence<'t, 'a>> {
    let mut out = vec![];
    let mut from = 0;
    for i in 0..=tokens.len() {
        if i == tokens.len() || tokens[i].sentence != tokens[from].sentence {
            if i > from {
                let s = &tokens[from..i];
                out.push(Sentence {
                    tokens: s,
                    question: s.last().is_some_and(|t| t.surface == "?"),
                });
            }
            from = i;
        }
    }
    out
}
pub(crate) fn word<'t>(s: &'t [Token<'_>], i: usize) -> &'t str {
    s.get(i)
        .filter(|t| t.is_word)
        .map_or("", |t| t.normalized.as_str())
}
pub(crate) fn clause_start(s: &[Token<'_>], i: usize) -> bool {
    i == 0
        || [
            ",", ";", ":", "and", "but", "so", "because", "when", "if", "that", "while", "since",
            "though", "although", "then",
        ]
        .contains(&s[i - 1].normalized.as_str())
}
/// The surface of a subject pronoun as it should read ("i" is "I").
fn pronoun(t: &Token<'_>) -> String {
    if t.normalized == "i" {
        "I".into()
    } else {
        t.surface.to_owned()
    }
}
fn lower_first(s: &str) -> String {
    if s == "I" || s.starts_with("I'") || s.starts_with("I’") {
        return s.to_owned();
    }
    let mut c = s.chars();
    c.next()
        .map_or(String::new(), |f| f.to_lowercase().chain(c).collect())
}
pub(crate) fn push(
    req: &Request,
    edits: &mut Vec<Edit>,
    (start, end): (usize, usize),
    replacement: String,
    id: &str,
    reason: &str,
    confidence: f32,
) {
    if let Some(e) = make_edit(
        &req.text,
        start,
        end,
        replacement,
        "Grammar",
        id,
        reason,
        confidence,
    ) {
        edits.push(e);
    }
}
pub(crate) fn span(s: &[Token<'_>], a: usize, b: usize) -> (usize, usize) {
    (s[a].start_utf16, s[b].end_utf16)
}
/// A finished past time inside the clause that runs through `from..=to`: "yesterday", "ago",
/// "last week", "in 2019".
fn past_time(s: &[Token<'_>], from: usize, to: usize) -> bool {
    let mut a = from;
    while a > 0 && !CLAUSE_BREAKS.contains(&s[a - 1].normalized.as_str()) {
        a -= 1;
    }
    let mut b = to;
    while b + 1 < s.len() && !CLAUSE_BREAKS.contains(&s[b + 1].normalized.as_str()) {
        b += 1;
    }
    let clause = &s[a..=b];
    let has = |w: &str| clause.iter().any(|t| t.normalized == w);
    // An ongoing or open period keeps the perfect ("since May", "ever", "never", "already").
    if [
        "since", "ever", "never", "already", "yet", "just", "recently", "for",
    ]
    .iter()
    .any(|w| has(w))
    {
        return false;
    }
    clause.iter().enumerate().any(|(k, t)| {
        let next = clause.get(k + 1).map_or("", |n| n.normalized.as_str());
        t.normalized == "yesterday"
            || t.normalized == "ago"
            || t.normalized == "last"
                && [
                    "night",
                    "week",
                    "weekend",
                    "month",
                    "year",
                    "summer",
                    "winter",
                    "spring",
                    "fall",
                    "autumn",
                    "semester",
                    "quarter",
                    "monday",
                    "tuesday",
                    "wednesday",
                    "thursday",
                    "friday",
                    "saturday",
                    "sunday",
                ]
                .contains(&next)
            || t.normalized == "in"
                && next.len() == 4
                && (next.starts_with("19") || next.starts_with("20"))
                && next.chars().all(|c| c.is_ascii_digit())
    })
}
/// "She has went there yesterday", "I have been in Paris in 2019": a finished past time takes the
/// simple past, whatever form the writer gave the perfect.
fn perfect_with_past_time(req: &Request, s: &[Token<'_>], edits: &mut Vec<Edit>) {
    for i in 0..s.len().saturating_sub(1) {
        let t = &s[i];
        let n = t.normalized.as_str();
        let contracted = n.ends_with("'ve");
        if !(contracted || (i > 0 && ["have", "has"].contains(&n))) {
            continue;
        }
        let j = i + 1;
        let w = word(s, j);
        let Some(v) = morphology::verb(w) else {
            continue;
        };
        if w != v.participle && !(w == v.past && v.past != v.participle) {
            continue;
        }
        if !past_time(s, i, j) {
            continue;
        }
        let subject = if contracted {
            n.trim_end_matches("'ve").to_owned()
        } else {
            s[i - 1].normalized.clone()
        };
        if !contracted && !SUBJECTS.contains(&subject.as_str()) && plural(&s[i - 1]).is_none() {
            continue;
        }
        let past = if v.base == "be" {
            let many = match subject.as_str() {
                "i" | "he" | "she" | "it" => false,
                "you" | "we" | "they" => true,
                _ => match plural(&s[i - 1]) {
                    Some(p) => p,
                    None => continue,
                },
            };
            if many { "were" } else { "was" }.to_owned()
        } else {
            v.past.clone()
        };
        let replacement = if contracted {
            let cut = t.surface.len() - "'ve".len() - usize::from(t.surface.contains('’')) * 2;
            format!("{} {past}", &t.surface[..cut])
        } else {
            past
        };
        push(
            req,
            edits,
            span(s, i, j),
            replacement,
            "grammar.perfect_past_time",
            "A finished past time takes the simple past.",
            0.98,
        );
    }
}
/// "She's went", "I've ate": after a contracted "has" or "have" the verb is a past participle.
fn contracted_perfect(req: &Request, s: &[Token<'_>], edits: &mut Vec<Edit>) {
    for i in 0..s.len().saturating_sub(1) {
        let n = s[i].normalized.as_str();
        let has = n.ends_with("'s") && SUBJECTS.contains(&n.trim_end_matches("'s"));
        if !(n.ends_with("'ve") || has) {
            continue;
        }
        let w = word(s, i + 1);
        let Some(v) = morphology::verb(w) else {
            continue;
        };
        // "He's broke" is an adjective; "it's done" and "she's left" read as participles already.
        if w != v.past || v.past == v.participle || w == "broke" || !spelling::known(&v.participle)
        {
            continue;
        }
        push(
            req,
            edits,
            span(s, i + 1, i + 1),
            v.participle.clone(),
            "grammar.contracted_perfect",
            "Use a past participle after has or have.",
            0.96,
        );
    }
}
/// "buyed", "catched", "brung": an irregular verb given the regular "-ed" ending.
fn regularized_past(req: &Request, s: &[Token<'_>], edits: &mut Vec<Edit>) {
    for i in 0..s.len() {
        let t = &s[i];
        let w = t.normalized.as_str();
        if !t.is_word || spelling::known(w) || t.proper_name {
            continue;
        }
        let v = if ["brung", "brang"].contains(&w) {
            morphology::irregular_base("bring")
        } else {
            let Some(stem) = w.strip_suffix("ed") else {
                continue;
            };
            let doubled = stem.len() > 2
                && stem.as_bytes()[stem.len() - 1] == stem.as_bytes()[stem.len() - 2];
            [
                Some(stem.to_owned()),
                w.strip_suffix('d').map(str::to_owned),
                doubled.then(|| stem[..stem.len() - 1].to_owned()),
            ]
            .into_iter()
            .flatten()
            .find_map(|base| morphology::irregular_base(&base))
        };
        let Some(v) = v else { continue };
        let previous = if i > 0 { word(s, i - 1) } else { "" };
        let perfect = [
            "have", "has", "had", "having", "be", "been", "being", "am", "is", "are", "was", "were",
        ]
        .contains(&previous)
            || previous.ends_with("'ve");
        let form = if perfect { &v.participle } else { &v.past };
        push(
            req,
            edits,
            span(s, i, i),
            crate::match_case(form, t.surface),
            "grammar.regularized_past",
            "This verb has an irregular past form.",
            0.97,
        );
    }
}
/// "Did the package arrived?", "Didn't you got my text?": after an inverted do or modal and its
/// subject the verb takes its base form.
fn inverted_base(req: &Request, s: &[Token<'_>], edits: &mut Vec<Edit>, question: bool) {
    if !question {
        return;
    }
    const AUX: [&str; 16] = [
        "did",
        "does",
        "do",
        "didn't",
        "doesn't",
        "don't",
        "can",
        "could",
        "will",
        "would",
        "should",
        "can't",
        "won't",
        "couldn't",
        "wouldn't",
        "shouldn't",
    ];
    for i in 0..s.len() {
        if !AUX.contains(&s[i].normalized.as_str()) || !(i == 0 || WH.contains(&word(s, i - 1))) {
            continue;
        }
        // The subject: a pronoun, or a determiner and one noun.
        let verb_at = if SUBJECTS.contains(&word(s, i + 1)) {
            i + 2
        } else if DETERMINERS.contains(&word(s, i + 1)) && spelling::flags(word(s, i + 2)) & 2 != 0
        {
            i + 3
        } else {
            continue;
        };
        let w = word(s, verb_at);
        let Some(v) = morphology::verb(w) else {
            continue;
        };
        if w == v.base
            || ![&v.third, &v.past, &v.participle].contains(&&w.to_owned())
            || spelling::flags(&v.base) & 4 == 0
        {
            continue;
        }
        push(
            req,
            edits,
            span(s, verb_at, verb_at),
            v.base.clone(),
            "grammar.inverted_auxiliary_base",
            "Use the base verb form after the inverted auxiliary and subject.",
            0.95,
        );
    }
}
/// "Where you are?", "How old your son is?": a direct question puts its auxiliary before the subject.
fn question_order(req: &Request, s: &[Token<'_>], edits: &mut Vec<Edit>, question: bool) {
    const AUX: [&str; 12] = [
        "am", "is", "are", "was", "were", "will", "can", "could", "should", "would", "have", "has",
    ];
    if !question || !WH.contains(&word(s, 0)) {
        return;
    }
    let k = if WH_MODIFIERS.contains(&word(s, 1)) {
        2
    } else {
        1
    };
    // "Why you didn't tell me?": a do or a negated auxiliary moves too when a base verb follows
    // ("Why you do that?" keeps "do" as the main verb).
    let next = word(s, k + 2);
    let do_aux = [
        "do",
        "does",
        "did",
        "didn't",
        "don't",
        "doesn't",
        "can't",
        "won't",
        "couldn't",
        "wouldn't",
        "shouldn't",
        "isn't",
        "aren't",
        "wasn't",
        "weren't",
    ]
    .contains(&word(s, k + 1))
        && (morphology::verb(next)
            .is_some_and(|v| v.base == next && spelling::flags(next) & 4 != 0)
            || word(s, k + 1).ends_with("n't") && next.ends_with("ing"));
    if SUBJECTS.contains(&word(s, k)) && (AUX.contains(&word(s, k + 1)) || do_aux) {
        let replacement = format!("{} {}", s[k + 1].surface, pronoun(&s[k]));
        push(
            req,
            edits,
            span(s, k, k + 1),
            replacement,
            "grammar.question_order",
            "In a direct question the auxiliary comes before the subject.",
            0.95,
        );
        return;
    }
    // "What time the meeting is?": a determiner, one or two nouns, then a final "is" or "are".
    if s.len() < k + 4 {
        return;
    }
    let last = s.len() - 2;
    if DETERMINERS.contains(&word(s, k))
        && ["is", "are", "was", "were"].contains(&word(s, last))
        && (k + 2..=k + 3).contains(&last)
        && s[k + 1..last]
            .iter()
            .all(|t| t.is_word && spelling::flags(&t.normalized) & 2 != 0)
    {
        let np: Vec<&str> = s[k..last].iter().map(|t| t.surface).collect();
        push(
            req,
            edits,
            span(s, k, last),
            format!("{} {}", s[last].surface, np.join(" ")),
            "grammar.question_order",
            "In a direct question the auxiliary comes before the subject.",
            0.95,
        );
    }
}
/// "Do you know where is the bathroom?": a question inside a sentence keeps statement order.
fn embedded_order(req: &Request, s: &[Token<'_>], edits: &mut Vec<Edit>) {
    const ASKING: [&str; 21] = [
        "know",
        "tell",
        "remind",
        "ask",
        "asked",
        "asking",
        "wonder",
        "wondering",
        "wondered",
        "sure",
        "idea",
        "explain",
        "understand",
        "remember",
        "forgot",
        "forget",
        "guess",
        "check",
        "see",
        "find",
        "out",
    ];
    const AUX: [&str; 11] = [
        "is", "are", "was", "were", "will", "can", "could", "should", "would", "has", "have",
    ];
    for w in 1..s.len() {
        if !WH.contains(&word(s, w)) {
            continue;
        }
        let mut before = w - 1;
        if ["me", "him", "her", "us", "them", "you"].contains(&word(s, before)) && before > 0 {
            before -= 1;
        }
        if !ASKING.contains(&word(s, before)) {
            continue;
        }
        let a = if WH_MODIFIERS.contains(&word(s, w + 1)) {
            w + 2
        } else {
            w + 1
        };
        let aux = word(s, a);
        if !AUX.contains(&aux) {
            continue;
        }
        let be = ["is", "are", "was", "were"].contains(&aux);
        let end_at = |k: usize| {
            s.get(k)
                .is_none_or(|t| [".", "?", "!", ","].contains(&t.surface))
        };
        // The subject: a pronoun, or a determiner with one or two more words.
        let base_verb = |w: &str| morphology::verb(w).is_some_and(|v| v.base == w);
        let np_end = if SUBJECTS.contains(&word(s, a + 1)) {
            Some(a + 1)
        } else if DETERMINERS.contains(&word(s, a + 1)) {
            (a + 2..=a + 3).filter(|&e| e < s.len()).find(|&e| {
                s[a + 2..=e].iter().all(|t| t.is_word)
                    && if be {
                        end_at(e + 1)
                    } else {
                        base_verb(word(s, e + 1))
                    }
            })
        } else {
            None
        };
        let Some(np_end) = np_end else { continue };
        let np: Vec<String> = s[a + 1..=np_end]
            .iter()
            .map(|t| {
                if t.normalized == "i" {
                    "I".into()
                } else {
                    t.surface.to_owned()
                }
            })
            .collect();
        push(
            req,
            edits,
            span(s, a, np_end),
            format!("{} {}", np.join(" "), s[a].surface),
            "grammar.embedded_question_order",
            "A question inside a sentence keeps the subject before the verb.",
            0.94,
        );
    }
}
/// "I go always to the gym", "I have finished already the report", "I can't still believe it":
/// the adverb goes before the verb.
fn adverb_position(req: &Request, s: &[Token<'_>], edits: &mut Vec<Edit>) {
    for i in 0..s.len().saturating_sub(3) {
        if !SUBJECTS.contains(&word(s, i)) || word(s, i) == "it" || !clause_start(s, i) {
            continue;
        }
        let (v, a) = (i + 1, i + 2);
        let verb = word(s, v);
        let adverb = word(s, a);
        let follows = s.get(a + 1).is_some_and(|t| t.is_word);
        let swap = |edits: &mut Vec<Edit>, x: usize, y: usize| {
            push(
                req,
                edits,
                span(s, x, y),
                format!("{} {}", lower_first(s[y].surface), s[x].surface),
                "grammar.adverb_position",
                "This adverb goes before the verb.",
                0.93,
            );
        };
        if FREQUENCY.contains(&adverb) && follows {
            let Some(m) = morphology::verb(verb) else {
                continue;
            };
            if ["be", "have", "do"].contains(&m.base.as_str())
                || ![&m.base, &m.third, &m.past].contains(&&verb.to_owned())
                || spelling::flags(verb) & 4 == 0
            {
                continue;
            }
            swap(edits, v, a);
        } else if ["have", "has"].contains(&verb)
            && word(s, a + 1) == "already"
            && morphology::verb(adverb).is_some_and(|m| m.participle == adverb)
            && s.get(a + 2).is_some_and(|t| t.is_word)
        {
            swap(edits, a, a + 1);
        } else if [
            "can't", "don't", "doesn't", "didn't", "won't", "couldn't", "isn't", "aren't",
        ]
        .contains(&verb)
            && adverb == "still"
        {
            swap(edits, v, a);
        }
    }
}
/// "She working from home", "He been sick", "What you doing?": the auxiliary is missing.
fn missing_auxiliary(req: &Request, s: &[Token<'_>], edits: &mut Vec<Edit>, question: bool) {
    let be = |p: &str| match p {
        "i" => "am",
        "he" | "she" | "it" => "is",
        _ => "are",
    };
    let gerund = |w: &str| {
        w.ends_with("ing")
            && spelling::flags(w) & 4 != 0
            && morphology::verb(w).is_some_and(|v| v.gerund == w)
    };
    for i in 0..s.len().saturating_sub(1) {
        let p = word(s, i);
        if !SUBJECTS.contains(&p) {
            continue;
        }
        let next = word(s, i + 1);
        let insert = |edits: &mut Vec<Edit>, at: &Token<'_>, aux: &str| {
            push(
                req,
                edits,
                (at.end_utf16, at.end_utf16),
                format!(" {aux}"),
                "grammar.missing_auxiliary",
                "A helping verb looks missing here.",
                0.93,
            );
        };
        // A question word, then the subject: "What you doing?", "What you think?".
        // "When you get a chance, ..." is a clause, not a question: no comma, and "when" opens none.
        if question
            && i == 1
            && WH.contains(&word(s, 0))
            && word(s, 0) != "when"
            && !s.iter().any(|t| t.surface == ",")
        {
            if gerund(next) && next != "being" {
                insert(edits, &s[0], be(p));
            } else if ["i", "you", "we", "they"].contains(&p)
                && morphology::verb(next).is_some_and(|v| {
                    v.base == next && !["be", "have", "do"].contains(&v.base.as_str())
                })
                && spelling::flags(next) & 4 != 0
                && morphology::predicate(next)
            {
                insert(edits, &s[0], "do");
            }
            continue;
        }
        if !clause_start(s, i) {
            continue;
        }
        if next == "been" {
            insert(
                edits,
                &s[i],
                if ["he", "she", "it"].contains(&p) {
                    "has"
                } else {
                    "have"
                },
            );
        } else if p != "it"
            && p != "you"
            && gerund(next)
            // "He meeting got moved": a verb after the "-ing" word makes it a noun.
            && !s.get(i + 2).is_some_and(crate::punctuation::finite)
        {
            insert(edits, &s[i], be(p));
        }
    }
}
/// A subject right before `i` at the start of its clause: a pronoun ("we are"), or a determiner
/// and a noun ("my flight gets").
fn subject_before(s: &[Token<'_>], i: usize) -> bool {
    i > 0
        && (SUBJECTS.contains(&word(s, i - 1)) && clause_start(s, i - 1)
            || i > 1
                && DETERMINERS.contains(&word(s, i - 2))
                && clause_start(s, i - 2)
                && plural(&s[i - 1]).is_some())
}
fn base_verb(w: &str) -> bool {
    spelling::flags(w) & 4 != 0 && morphology::verb(w).is_some_and(|v| v.base == w)
}
/// The words of a verb group the writer meant: a passive participle, a past with a finished time,
/// a perfect with "since", and helping words added or dropped by a slip.
fn verb_groups(req: &Request, s: &[Token<'_>], edits: &mut Vec<Edit>) {
    let n = s.len();
    for i in 0..n {
        let w = word(s, i);
        let next = word(s, i + 1);
        let fix = |edits: &mut Vec<Edit>, a: usize, b: usize, r: String, id: &str, why: &str| {
            push(req, edits, span(s, a, b), r, id, why, 0.94)
        };
        // "My phone was froze": a passive takes the past participle.
        if ["is", "are", "was", "were", "be", "been", "being", "am"].contains(&w)
            && let Some(v) = morphology::verb(next)
            && next == v.past
            && v.past != v.participle
            && !["broke", "lay", "saw"].contains(&next)
            // A verb with no object has no passive ("is rose" is a name, "was went" a slip of tense).
            && !["rise", "fall", "go", "come", "become", "lie", "sit", "stand", "swim", "fly", "sleep", "arise"].contains(&v.base.as_str())
            && !s[i + 1].proper_name
            // "are saw blades": a noun after it makes the word a noun modifier.
            && !s.get(i + 2).is_some_and(|t| {
                let f = spelling::flags(&t.normalized);
                t.is_word
                    && f & 2 != 0
                    && f & 4 == 0
                    && !["by", "in", "on", "at", "for", "to", "with", "from", "all", "of", "during", "until", "after", "before", "again", "yesterday", "today"].contains(&t.normalized.as_str())
            })
            && spelling::known(&v.participle)
        {
            fix(
                edits,
                i + 1,
                i + 1,
                v.participle.clone(),
                "grammar.passive_participle",
                "Use a past participle in this passive verb phrase.",
            );
            continue;
        }
        // "We are at the beach yesterday", "My flight gets cancelled yesterday": a finished past time
        // later in the clause puts its verb in the past.
        if subject_before(s, i) {
            let past = match w {
                "am" | "is" => Some("was".to_owned()),
                "are" => Some("were".to_owned()),
                _ => morphology::verb(w)
                    .filter(|v| {
                        (w == v.third
                            || w == v.base && v.base != v.past && spelling::known(&v.past))
                            && !w.contains('\'')
                            && !["be", "have", "do"].contains(&v.base.as_str())
                            && spelling::flags(w) & 4 != 0
                    })
                    .map(|v| v.past),
            };
            // The time word must come after the verb, with no other verb between them.
            let marker_after = (i + 1..n)
                .take_while(|&k| {
                    !CLAUSE_BREAKS.contains(&s[k].normalized.as_str())
                        && !(crate::punctuation::finite(&s[k])
                            && !(k == i + 1
                                && morphology::verb(word(s, k))
                                    .is_some_and(|v| v.participle == word(s, k))))
                })
                .any(|k| {
                    let t = word(s, k);
                    t == "yesterday"
                        || t == "ago"
                        || t == "last"
                            && [
                                "night",
                                "week",
                                "weekend",
                                "month",
                                "year",
                                "summer",
                                "winter",
                                "monday",
                                "tuesday",
                                "wednesday",
                                "thursday",
                                "friday",
                                "saturday",
                                "sunday",
                            ]
                            .contains(&word(s, k + 1))
                });
            if let Some(past) = past
                && marker_after
                && past_time(s, i, i)
                && !(w == "is" && word(s, i - 1) == "i")
            {
                let past = if past == "was" && word(s, i - 1) == "you" {
                    "were".to_owned()
                } else {
                    past
                };
                fix(
                    edits,
                    i,
                    i,
                    past,
                    "grammar.explicit_past_time",
                    "Use the past verb form with this explicit past-time context.",
                );
                continue;
            }
        }
        // "She works here since March": "since" a point in time takes the perfect.
        if i > 0 && clause_start(s, i - 1) && SUBJECTS.contains(&word(s, i - 1)) {
            let since_point = (i + 1..n)
                .take_while(|&k| {
                    !CLAUSE_BREAKS[..20]
                        .iter()
                        .filter(|b| **b != "since")
                        .any(|b| *b == s[k].normalized)
                })
                .find(|&k| word(s, k) == "since")
                .is_some_and(|k| {
                    let t = word(s, k + 1);
                    [
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
                        "last",
                        "yesterday",
                        "then",
                        "morning",
                        "noon",
                    ]
                    .contains(&t)
                        || t.len() == 4 && t.chars().all(|c| c.is_ascii_digit())
                });
            let have = if ["he", "she", "it"].contains(&word(s, i - 1)) {
                "has"
            } else {
                "have"
            };
            if since_point {
                if ["am", "is", "are"].contains(&w) {
                    let g = word(s, i + 1);
                    let r = if g.ends_with("ing")
                        && morphology::verb(g).is_some_and(|v| v.gerund == g)
                    {
                        Some(format!("{have} been"))
                    } else {
                        None
                    };
                    if let Some(r) = r {
                        fix(
                            edits,
                            i,
                            i,
                            r,
                            "grammar.since_perfect",
                            "A state lasting since a point in time takes the perfect.",
                        );
                        continue;
                    }
                } else if let Some(v) = morphology::verb(w)
                    && (w == v.third || w == v.base)
                    && !["be", "have", "do"].contains(&v.base.as_str())
                    && spelling::flags(w) & 4 != 0
                    && spelling::known(&v.participle)
                {
                    fix(
                        edits,
                        i,
                        i,
                        format!("{have} {}", v.participle),
                        "grammar.since_perfect",
                        "A state lasting since a point in time takes the perfect.",
                    );
                    continue;
                }
            }
        }
        // "I'll be call you", "happy to be announce": a stray "be" before a base verb.
        if w == "be"
            && i > 0
            && ([
                "will", "would", "can", "could", "should", "must", "to", "might", "may",
            ]
            .contains(&word(s, i - 1))
                || ["'ll", "'d"].iter().any(|c| word(s, i - 1).ends_with(c)))
            && base_verb(next)
            && spelling::flags(next) & 8 == 0
            && morphology::verb(next).is_some_and(|v| v.participle != next)
            // An object after the verb rules out a passive ("will be sent tomorrow").
            && ["it", "them", "you", "me", "him", "her", "us", "the", "a", "an", "my", "your", "our", "that", "this"]
                .contains(&word(s, i + 2))
        {
            push(
                req,
                edits,
                (s[i - 1].end_utf16, s[i + 1].end_utf16),
                format!(" {}", s[i + 1].surface),
                "grammar.extra_be",
                "This “be” does not belong before the verb.",
                0.96,
            );
            continue;
        }
        // "Let's to grab coffee".
        if w == "let's" && next == "to" && base_verb(word(s, i + 2)) {
            push(
                req,
                edits,
                (s[i].end_utf16, s[i + 1].end_utf16),
                String::new(),
                "grammar.extra_to",
                "“Let's” takes the verb without “to”.",
                0.95,
            );
            continue;
        }
        // "I ought call", "I can able to".
        if w == "ought" && base_verb(next) {
            push(
                req,
                edits,
                (s[i].end_utf16, s[i].end_utf16),
                " to".into(),
                "grammar.missing_to",
                "“Ought” takes “to” before its verb.",
                0.95,
            );
            continue;
        }
        if ["can", "could"].contains(&w) && next == "able" && word(s, i + 2) == "to" {
            push(
                req,
                edits,
                (s[i].end_utf16, s[i + 2].end_utf16),
                String::new(),
                "grammar.can_able",
                "“Can” already means “be able to”.",
                0.95,
            );
            continue;
        }
        // "We use to go": the past habit is "used to".
        if w == "use"
            && i > 0
            && SUBJECTS.contains(&word(s, i - 1))
            && clause_start(s, i - 1)
            && next == "to"
            && base_verb(word(s, i + 2))
        {
            fix(
                edits,
                i,
                i,
                "used".into(),
                "grammar.used_to",
                "A past habit is “used to”.",
            );
            continue;
        }
        // "If I would have known": the "if" clause takes the past perfect.
        if w == "if"
            && SUBJECTS.contains(&word(s, i + 1))
            && word(s, i + 2) == "would"
            && word(s, i + 3) == "have"
            && morphology::verb(word(s, i + 4)).is_some_and(|v| v.participle == word(s, i + 4))
        {
            fix(
                edits,
                i + 2,
                i + 3,
                "had".into(),
                "grammar.conditional_past_perfect",
                "An “if” clause about the past takes “had”.",
            );
            continue;
        }
        // "He not answering": the "be" before "not" is missing.
        if SUBJECTS.contains(&w)
            && clause_start(s, i)
            && next == "not"
            && word(s, i + 2).ends_with("ing")
            && morphology::verb(word(s, i + 2)).is_some_and(|v| v.gerund == word(s, i + 2))
        {
            let r = match w {
                "i" => "I'm not",
                "he" | "she" | "it" => "isn't",
                _ => "aren't",
            };
            // "I not" becomes "I'm not"; otherwise "not" becomes "isn't" or "aren't".
            let a = if w == "i" { i } else { i + 1 };
            fix(
                edits,
                a,
                i + 1,
                r.to_owned(),
                "grammar.missing_auxiliary",
                "A helping verb looks missing here.",
            );
            continue;
        }
        // "We are wanting", "This box is containing": a state verb is not used in the progressive.
        if ["am", "is", "are"].contains(&w)
            && i > 0
            && (SUBJECTS.contains(&word(s, i - 1)) || plural(&s[i - 1]).is_some())
        {
            const STATES: [&str; 11] = [
                "want", "contain", "need", "know", "believe", "own", "belong", "prefer", "seem",
                "consist", "deserve",
            ];
            if let Some(v) = morphology::verb(next)
                .filter(|v| v.gerund == next && STATES.contains(&v.base.as_str()))
            {
                let form = if w == "is" {
                    v.third.clone()
                } else {
                    v.base.clone()
                };
                fix(
                    edits,
                    i,
                    i + 1,
                    form,
                    "grammar.state_progressive",
                    "This verb names a state and is not used with “-ing” here.",
                );
                continue;
            }
        }
    }
    // "Because I was sick, so I stayed home": one linking word is enough.
    if ["because", "since", "although", "though", "as"].contains(&word(s, 0))
        && let Some(c) = s.iter().position(|t| t.surface == ",")
        && ["so", "but"].contains(&word(s, c + 1))
        && (word(s, c + 1) == "so") == (word(s, 0) != "although" && word(s, 0) != "though")
        && s.get(c + 2).is_some_and(|t| t.is_word)
    {
        push(
            req,
            edits,
            (s[c].end_utf16, s[c + 1].end_utf16),
            String::new(),
            "grammar.double_conjunction",
            "The clause already has its linking word.",
            0.94,
        );
    }
}
/// "There a problem", "This the best", "Who going", "What time the meeting?": a missing "is".
fn missing_copula(req: &Request, s: &[Token<'_>], edits: &mut Vec<Edit>, question: bool) {
    let first = word(s, 0);
    let second = word(s, 1);
    let insert = |edits: &mut Vec<Edit>, at: usize, what: &str| {
        push(
            req,
            edits,
            (s[at].end_utf16, s[at].end_utf16),
            what.to_owned(),
            "grammar.missing_copula",
            "A form of “be” looks missing here.",
            0.93,
        );
    };
    if first == "there" && ["a", "an", "no"].contains(&second) {
        insert(edits, 0, "'s");
    } else if ["this", "that"].contains(&first)
        && ["the", "a", "an", "my", "our", "your"].contains(&second)
        && s.len() > 3
        || first == "who"
            && second.ends_with("ing")
            && morphology::verb(second).is_some_and(|v| v.gerund == second)
    {
        insert(edits, 0, " is");
    } else if question && WH.contains(&first) {
        // "What time the meeting?": the wh-phrase, a determiner and nouns, then the question mark.
        let k = if WH_MODIFIERS.contains(&second) { 2 } else { 1 };
        let last = s.len() - 1;
        if k > 0
            && last > k + 1
            && DETERMINERS.contains(&word(s, k))
            && s[k + 1..last].iter().all(|t| {
                t.is_word
                    && spelling::flags(&t.normalized) & 2 != 0
                    && !crate::punctuation::finite(t)
            })
            && last - k <= 3
        {
            let many = plural(&s[last - 1]) == Some(true);
            insert(edits, k - 1, if many { " are" } else { " is" });
        }
    }
}
/// "It's hard say": an adjective of judgment takes "to" before its verb.
fn missing_to(req: &Request, s: &[Token<'_>], edits: &mut Vec<Edit>) {
    for i in 1..s.len().saturating_sub(1) {
        if ["it's", "it", "that's", "is", "was"].contains(&word(s, i - 1))
            && [
                "hard",
                "easy",
                "difficult",
                "impossible",
                "nice",
                "good",
                "great",
                "important",
                "tough",
            ]
            .contains(&word(s, i))
            && [
                "say",
                "tell",
                "believe",
                "imagine",
                "know",
                "find",
                "see",
                "understand",
                "explain",
                "describe",
                "predict",
                "decide",
                "read",
                "hear",
                "remember",
                "get",
            ]
            .contains(&word(s, i + 1))
        {
            push(
                req,
                edits,
                (s[i].end_utf16, s[i].end_utf16),
                " to".into(),
                "grammar.missing_to",
                "Put “to” before the verb here.",
                0.93,
            );
        }
    }
}
pub fn check(req: &Request, edits: &mut Vec<Edit>) {
    let tokens = tokenizer::tokenize(&req.text, &req.tokens);
    // A sentence end the punctuation rules add ("We left yesterday Jules has arrived") splits the
    // sentence here too, so a time word does not reach across it.
    let breaks: Vec<usize> = edits
        .iter()
        .filter(|e| e.rule_id == "punctuation.missing_sentence_boundary")
        .map(|e| e.start_utf16)
        .collect();
    let mut parts = vec![];
    for sentence in sentences(&tokens) {
        let s = sentence.tokens;
        let mut from = 0;
        for k in 1..s.len() {
            if breaks
                .iter()
                .any(|&b| s[k - 1].end_utf16 <= b && b <= s[k].start_utf16)
            {
                parts.push((&s[from..k], false));
                from = k;
            }
        }
        parts.push((&s[from..], sentence.question));
    }
    for (s, question) in parts {
        let sentence = Sentence {
            tokens: s,
            question,
        };
        perfect_with_past_time(req, s, edits);
        contracted_perfect(req, s, edits);
        regularized_past(req, s, edits);
        inverted_base(req, s, edits, sentence.question);
        question_order(req, s, edits, sentence.question);
        embedded_order(req, s, edits);
        adverb_position(req, s, edits);
        missing_auxiliary(req, s, edits, sentence.question);
        verb_groups(req, s, edits);
        missing_copula(req, s, edits, sentence.question);
        missing_to(req, s, edits);
        crate::determiners::check(req, s, edits, sentence.question);
    }
}
