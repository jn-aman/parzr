//! Determiners and the number they carry: "a" or "an" by sound, one noun after "a", "this" and
//! "these", "much" and "many", "there is" and "there are", and a helping verb that agrees with a
//! determiner phrase or pronoun subject.
use crate::{
    Edit, Request,
    clause_repairs::{SUBJECTS, clause_start, push, span, word},
    morphology, spelling,
    structure::plural,
    tokenizer::Token,
};

/// Whether "an" (rather than "a") goes before this word, from its spelling; None when unclear.
pub fn an_fits(word: &str) -> Option<bool> {
    let w: String = word
        .chars()
        .take_while(|c| c.is_alphanumeric() || *c == '-')
        .collect();
    let first = w.chars().next()?;
    if !first.is_alphabetic() {
        return None;
    }
    let letters: Vec<char> = w.chars().take_while(|c| c.is_alphabetic()).collect();
    // An abbreviation or a letter said by its name ("an MBA", "a URL", "an A").
    if letters.iter().all(|c| c.is_uppercase()) && (letters.len() >= 2 || w.len() == 1) {
        return Some("AEFHILMNORSX".contains(first));
    }
    let l = w.to_lowercase();
    let starts = |list: &[&str]| list.iter().any(|p| l.starts_with(p));
    match first.to_ascii_lowercase() {
        'a' | 'i' => Some(true),
        'e' => Some(!starts(&["eu", "ewe"])),
        'o' => Some(!starts(&["one", "once"])),
        'u' => Some(
            l.len() > 1
                && !starts(&[
                    "uni", "use", "usu", "uti", "ura", "ure", "uri", "uro", "ubiq", "uku", "unan",
                    "uk", "ute",
                ]),
        ),
        // American English says "an herb".
        'h' => Some(starts(&[
            "hour", "honest", "honor", "honour", "heir", "herb",
        ])),
        'x' | 'y' => None,
        _ => Some(false),
    }
}
/// "a engineer", "an huge": the article's form follows the sound of the next word. Only an ordinary
/// word that can follow an article counts, never a letter or code ("the letter a is").
fn article_sound(req: &Request, s: &[Token<'_>], edits: &mut Vec<Edit>) {
    for i in 0..s.len().saturating_sub(1) {
        let t = &s[i];
        let lower = t.surface.chars().all(char::is_lowercase);
        if !["a", "an"].contains(&t.normalized.as_str()) || !(lower || i == 0) {
            continue;
        }
        let next = &s[i + 1];
        let w = next.normalized.as_str();
        // Glued to a hyphen, digit or quote ("a-b", "a 'x'"), or a single letter: leave it.
        if !next.is_word
            || req.text[t.end_byte..next.start_byte] != *" "
            || w.chars().count() < 2
                && !(next.surface.len() == 1
                    && next.surface != "I"
                    && next.surface.chars().all(char::is_uppercase))
            || spelling::flags(w) & (2 | 8) == 0 && !next.surface.chars().all(|c| c.is_uppercase())
            // Function words never follow an article: "an then" is a slip for "and then", not "a then".
            || [
                "and", "or", "is", "of", "in", "then", "than", "the", "that", "to", "at", "on", "as",
                "it", "its", "if", "so", "but", "by", "for", "from", "with",
            ]
            .contains(&w)
            // "I an going": after a subject pronoun "an" is a slip for "am", not an article.
            || i > 0 && SUBJECTS.contains(&word(s, i - 1))
            // "a A$1.5 billion": the letter belongs to a currency or code.
            || req.text[next.end_byte..].starts_with(|c: char| c.is_alphanumeric() || "$€£¥#/_-".contains(c))
        {
            continue;
        }
        let Some(an) = an_fits(next.surface) else {
            continue;
        };
        if an == (t.normalized == "an") {
            continue;
        }
        let form = if an { "an" } else { "a" };
        push(
            req,
            edits,
            span(s, i, i),
            crate::match_case(form, t.surface),
            "grammar.article_sound",
            if an {
                "Use “an” before a vowel sound."
            } else {
                "Use “a” before a consonant sound."
            },
            0.96,
        );
    }
}
/// The singular of a regular plural noun the lexicon knows ("experts" to "expert").
fn singular(w: &str) -> Option<String> {
    let noun = |x: &str| spelling::flags(x) & 2 != 0 && spelling::ordinary(x);
    if let Some(stem) = w.strip_suffix("ies") {
        let y = format!("{stem}y");
        return noun(&y).then_some(y);
    }
    if let Some(stem) = w.strip_suffix("es")
        && ["s", "sh", "ch", "x", "z"]
            .iter()
            .any(|e| stem.ends_with(e))
        && noun(stem)
    {
        return Some(stem.to_owned());
    }
    let stem = w.strip_suffix('s')?;
    (!stem.ends_with('s') && noun(stem)).then(|| stem.to_owned())
}
/// "an experts in": one article, one noun. A plural that names one thing ("a savings account",
/// "a means") or that modifies a following noun ("a sports car") is left alone.
fn article_number(req: &Request, s: &[Token<'_>], edits: &mut Vec<Edit>) {
    for i in 0..s.len().saturating_sub(2) {
        if !["a", "an"].contains(&s[i].normalized.as_str()) || !s[i + 1].is_word {
            continue;
        }
        // "Q&A Facts", "R&A teams": an "A" glued to the mark before it is no article.
        if i > 0 && s[i - 1].end_byte == s[i].start_byte {
            continue;
        }
        let w = s[i + 1].normalized.as_str();
        let after = &s[i + 2];
        if s[i + 1].proper_name
            || w.len() < 4
            || [
                "news",
                "series",
                "species",
                "means",
                "sales",
                "savings",
                "arms",
                "goods",
                "odds",
                "glasses",
                "jeans",
                "pants",
                "scissors",
                "clothes",
                "headquarters",
                "physics",
                "politics",
                "economics",
                "athletics",
                "thanks",
                "sports",
                "series",
                "lots",
            ]
            .contains(&w)
            || after.is_word
                && spelling::flags(&after.normalized) & (2 | 8) != 0
                && ![
                    "in", "on", "at", "of", "for", "to", "with", "from", "by", "about", "and",
                    "or", "but", "who", "that", "which", "is", "are", "was", "were", "will", "can",
                ]
                .contains(&after.normalized.as_str())
            || after.normalized == "'s"
        {
            continue;
        }
        let Some(one) = singular(w) else { continue };
        // The article must still fit the singular's sound ("an experts" to "an expert").
        if an_fits(&one).is_some_and(|an| an != (s[i].normalized == "an")) {
            continue;
        }
        push(
            req,
            edits,
            span(s, i + 1, i + 1),
            one,
            "grammar.article_number",
            "“A” or “an” goes with one thing: use the singular noun.",
            0.93,
        );
    }
}
/// "The age don't matter", "they interests me": a noun or pronoun subject and its verb disagree.
fn subject_agreement(req: &Request, s: &[Token<'_>], edits: &mut Vec<Edit>) {
    const DET: [&str; 10] = [
        "the", "this", "that", "my", "your", "his", "her", "our", "their", "each",
    ];
    for i in 0..s.len().saturating_sub(2) {
        // A determiner, its noun and a negated do at the start of the clause.
        if DET.contains(&word(s, i)) && clause_start(s, i) {
            // "Tom and the dog don't agree", "Tom or the dog doesn't": a conjunction that joins two
            // noun phrases makes a compound subject ("and": plural, "or": the nearer noun), so the
            // last noun does not decide the helping verb.
            if i > 0
                && ["and", "or"].contains(&word(s, i - 1))
                && !s[..i - 1]
                    .iter()
                    .any(|t| t.sentence == s[i].sentence && crate::punctuation::finite(t))
            {
                continue;
            }
            let aux = word(s, i + 2);
            let fix = match (plural(&s[i + 1]), aux) {
                (Some(false), "don't")
                    if word(s, i) != "the" || spelling::flags(word(s, i + 1)) & 2 != 0 =>
                {
                    "doesn't"
                }
                (Some(true), "doesn't") => "don't",
                _ => continue,
            };
            push(
                req,
                edits,
                span(s, i + 2, i + 2),
                crate::match_case(fix, s[i + 2].surface),
                "grammar.subject_do_agreement",
                "Match the helping verb to its subject.",
                0.95,
            );
            continue;
        }
        // A plural pronoun with a verb in the "-s" form.
        let p = word(s, i);
        if !["i", "you", "we", "they"].contains(&p) || !clause_start(s, i) {
            continue;
        }
        let w = word(s, i + 1);
        let Some(v) = morphology::verb(w) else {
            continue;
        };
        let next = &s[i + 2];
        if w != v.third
            || v.third == v.base
            || ["be", "have", "do"].contains(&v.base.as_str())
            || spelling::flags(&v.base) & 4 == 0
            || crate::punctuation::finite(next)
            || morphology::verb(&next.normalized).is_some_and(|n| n.base == next.normalized)
        {
            continue;
        }
        push(
            req,
            edits,
            span(s, i + 1, i + 1),
            v.base.clone(),
            "grammar.subject_base",
            "Use the base present-tense verb with this plural subject.",
            0.94,
        );
    }
}
/// A noun that is plural in form and never a verb ("stories", "puppies"; not "issues" or "costs",
/// which also follow the pronoun "this" as verbs).
fn plural_noun(t: &Token<'_>) -> bool {
    let w = t.normalized.as_str();
    t.is_word
        && !t.proper_name
        && plural(t) == Some(true)
        && w.ends_with('s')
        && spelling::flags(w) & 4 == 0
        && singular_known(w)
}
fn singular_known(w: &str) -> bool {
    singular(w).is_some()
}
/// One noun that has no plural reading ("guy", "furniture", "weather").
fn singular_noun(t: &Token<'_>) -> bool {
    let w = t.normalized.as_str();
    t.is_word
        && !t.proper_name
        && plural(t) == Some(false)
        && spelling::flags(w) & 2 != 0
        && !w.ends_with('s')
        && !crate::punctuation::finite(t)
        && !["kind", "sort", "type", "one", "lot", "day", "time", "way"].contains(&w)
}
/// A regular plural noun, whether or not the same spelling is also a verb ("files", "cooks").
fn plural_form(t: &Token<'_>) -> bool {
    let w = t.normalized.as_str();
    t.is_word
        && !t.proper_name
        && plural(t) == Some(true)
        && w.ends_with('s')
        && singular_known(w)
        // "does" is a verb before it is the plural of "doe".
        && !morphology::verb(w).is_some_and(|v| ["be", "have", "do", "go"].contains(&v.base.as_str()))
}
/// The words from `start` that can make one noun phrase, as indexes: up to four nouns and
/// adjectives with a plain space between them, stopping at anything else (a verb form, a function
/// word, a mark, a hyphen).
fn nominal_run(req: &Request, s: &[Token<'_>], start: usize) -> Vec<usize> {
    let mut run: Vec<usize> = vec![];
    for k in start..start + 6 {
        let Some(t) = s.get(k) else { break };
        let w = t.normalized.as_str();
        if !t.is_word
            || SUBJECTS.contains(&w)
            || spelling::flags(w) & (2 | 8) == 0 && !crate::structure::looks_plural(w)
            || [
                "is", "are", "was", "were", "and", "or", "of", "to", "that", "who", "which", "the",
                "a", "an", "not", "do", "does", "did", "has", "have", "had", "in", "on", "at",
                "for", "with", "from", "by", "into", "onto", "over", "under", "about", "as",
                "than", "if", "but", "so", "when", "while", "will", "can", "could", "would",
                "should", "may", "might", "must",
            ]
            .contains(&w)
            // A past form or an -ing form is the verb or a modifier that runs the phrase on
            // ("those left", "those dealing", "these differing"), never the counted noun.
            || participle_form(t)
            || morphology::verb(w).is_some_and(|v| v.gerund == w)
            || run
                .last()
                .is_some_and(|p| req.text[s[*p].end_byte..t.start_byte] != *" ")
        {
            break;
        }
        run.push(k);
        // The head of a plural compound is its first plural word ("library subject guides",
        // "these children receive"), whether it ends in "-s" or not.
        if plural(t) == Some(true) {
            break;
        }
        // The head of a plural compound is its first plural word ("library subject guides").
        if w.len() >= 4
            && w.ends_with('s')
            && !w.ends_with("ss")
            && !w.ends_with("us")
            && !w.ends_with("is")
        {
            break;
        }
    }
    // A run that hit its limit with more words to come is a long compound or a clause: unclear.
    if run.len() == 6 {
        run.clear();
    }
    // A hyphen glued to the end of the last word makes it part of a longer word ("non-slip").
    if run
        .last()
        .is_some_and(|k| req.text[s[*k].end_byte..].starts_with(['-', '(', '\'', '’']))
    {
        run.clear();
    }
    run
}
/// Whether a noun phrase ends before `next`: the end of the text, a mark, a conjunction, a verb or
/// an adverb of time: anything but another noun that would run the phrase on.
fn ends_clause(next: Option<&Token<'_>>) -> bool {
    next.is_none_or(|a| {
        !a.is_word
            || [
                "and",
                "or",
                "but",
                "so",
                "who",
                "today",
                "tomorrow",
                "tonight",
                "yesterday",
                "again",
                "now",
                "first",
                "please",
            ]
            .contains(&a.normalized.as_str())
            || spelling::flags(&a.normalized) & 2 == 0
            || spelling::flags(&a.normalized) & 4 != 0 && spelling::flags(&a.normalized) & 2 != 0
    })
}
/// Adjectives common enough to stand before a noun that the word may not be a head.
const COMMON_ADJECTIVES: [&str; 30] = [
    "new",
    "old",
    "big",
    "small",
    "good",
    "bad",
    "other",
    "same",
    "few",
    "last",
    "next",
    "first",
    "free",
    "full",
    "high",
    "low",
    "great",
    "little",
    "long",
    "short",
    "young",
    "main",
    "own",
    "real",
    "whole",
    "different",
    "popular",
    "public",
    "private",
    "special",
];
/// Verbs and adjectives whose clause complement opens with "that" ("insist that", "clear that").
const COMPLEMENT_WORDS: &[&str] = &[
    "reveal",
    "insist",
    "recommend",
    "argue",
    "admit",
    "ensure",
    "show",
    "indicate",
    "suggest",
    "note",
    "claim",
    "state",
    "find",
    "tell",
    "assume",
    "conclude",
    "demonstrate",
    "prove",
    "report",
    "announce",
    "explain",
    "notice",
    "realize",
    "remember",
    "discover",
    "learn",
    "agree",
    "decide",
    "imply",
    "confirm",
    "doubt",
    "deny",
    "expect",
    "predict",
    "require",
    "demand",
    "order",
    "propose",
    "request",
    "clear",
    "true",
    "possible",
    "likely",
    "certain",
    "sure",
    "obvious",
    "evident",
    "important",
    "so",
    "now",
    "given",
    "provided",
    "shown",
    "known",
    "determine",
    "hypothesize",
    "hypothesise",
    "observe",
    "establish",
    "see",
    "hear",
];
/// A word that is the "-s" form of a verb ("rings", "leads"): after "this" in subject position it is
/// the verb.
fn verb_third(t: &Token<'_>) -> bool {
    morphology::verb(&t.normalized).is_some_and(|v| {
        v.third == t.normalized
            && v.base != t.normalized
            // A word that is a verb first ("requires", "leads"), not a countable noun ("pages"):
            // the lexicon's noun flag is too loose to tell them apart.
            && [
                "require", "lead", "ring", "mean", "help", "work", "need", "cost", "hold",
                "result", "turn", "feel", "look", "stand", "seem", "make", "take", "give", "keep",
                "show", "bring", "set", "put", "include", "involve", "contain", "provide", "allow",
                "cause", "create", "produce", "support", "suggest", "indicate", "reflect",
                "represent", "reveal", "explain", "describe", "depend", "rely", "appear",
                "become", "remain", "matter", "change", "prove", "imply", "affect", "add", "apply",
                "fit", "get", "go", "come", "sound", "taste", "smell", "happen", "occur", "exist",
                "remind", "prevent", "enable", "encourage", "reduce", "increase", "improve",
                "hurt", "cut", "sum", "relate", "tend", "belong", "differ", "mention",
            ]
            .contains(&v.base.as_str())
    })
}
/// A word that is a verb's past or participle form and not its base ("left", "given", "chosen").
fn participle_form(t: &Token<'_>) -> bool {
    morphology::verb(&t.normalized).is_some_and(|v| {
        t.normalized != v.base && (t.normalized == v.past || t.normalized == v.participle)
    })
}
/// Words before "this" or "that" that make it a determiner: a preposition, or a verb taking an
/// object ("print this pages"). Verbs of saying and thinking take a clause ("I think this works").
fn object_position(s: &[Token<'_>], i: usize) -> bool {
    if i == 0 {
        return false;
    }
    let p = word(s, i - 1);
    if [
        "of", "at", "for", "on", "in", "with", "from", "to", "about", "into", "by", "all", "are",
        "were",
    ]
    .contains(&p)
    {
        return true;
    }
    morphology::verb(p).is_some_and(|v| {
        spelling::flags(p) & 4 != 0
            && ![
                "be", "have", "do", "think", "know", "say", "believe", "hope", "guess", "feel",
                "bet", "mean", "suppose", "find", "tell", "show", "realize", "wish", "make", "let",
            ]
            .contains(&v.base.as_str())
    })
}
/// "this pages", "these furniture": a demonstrative takes the number of its noun.
fn demonstratives(req: &Request, s: &[Token<'_>], edits: &mut Vec<Edit>) {
    for i in 0..s.len().saturating_sub(1) {
        let d = word(s, i);
        // "check that that directories": the doubled word is the slip, not the number.
        if i > 0 && word(s, i - 1) == d {
            continue;
        }
        // One adjective may come first ("this cute puppies").
        let n = if spelling::flags(word(s, i + 1)) & 8 != 0
            && spelling::flags(word(s, i + 2)) & 2 != 0
        {
            i + 2
        } else {
            i + 1
        };
        let noun = &s[n];
        // "These Q&A Facts", "this API": a title-case or acronym noun names something; its
        // number is the name's.
        if s[i + 1..=n]
            .iter()
            .any(|t| t.surface.chars().any(char::is_uppercase))
        {
            continue;
        }
        // "this weeks pool", "this years budget": a time word before another noun lost its
        // possessive apostrophe.
        if [
            "weeks", "months", "years", "days", "quarters", "seasons", "mornings", "nights",
        ]
        .contains(&noun.normalized.as_str())
            && s.get(n + 1)
                .is_some_and(|a| a.is_word && spelling::flags(&a.normalized) & 2 != 0)
            && ["this", "that"].contains(&d)
        {
            continue;
        }
        // A noun that goes on into a compound ("this sports car") is a modifier.
        let ends = s.get(n + 1).is_none_or(|a| {
            let f = spelling::flags(&a.normalized);
            !a.is_word
                || f & 2 == 0
                || f & 4 != 0
                || [
                    "today",
                    "tomorrow",
                    "tonight",
                    "yesterday",
                    "again",
                    "now",
                    "first",
                ]
                .contains(&a.normalized.as_str())
        });
        let object = object_position(s, i);
        // As a subject "this" or "that" may take an "-s" verb ("this costs", "that works"), so
        // there the noun must have no verb reading.
        // After "see" or "hear" a clause can follow too ("I see this works"): a noun that is also a
        // common verb stays.
        let perceived = i > 0
            && morphology::verb(word(s, i - 1))
                .is_some_and(|v| ["see", "hear"].contains(&v.base.as_str()))
            && singular(&noun.normalized).is_some_and(|one| morphology::predicate(&one));
        let plural_here = if object || i == 0 && ["are", "were"].contains(&word(s, n + 1)) {
            plural_form(noun) && !perceived
        } else {
            plural_noun(noun)
        };
        let prep = i > 0
            && [
                "of", "at", "for", "on", "in", "with", "from", "to", "about", "into", "by", "all",
                "are", "were",
            ]
            .contains(&word(s, i - 1));
        // "revealed that participants", "clear that genes", "are that radiologists": "that" opens a
        // clause here, not a noun phrase.
        let complement = d == "that"
            && i > 0
            && (["are", "were", "is", "was"].contains(&word(s, i - 1))
                && s.get(n + 1).is_some_and(crate::punctuation::finite)
                || COMPLEMENT_WORDS.contains(&word(s, i - 1))
                || morphology::verb(word(s, i - 1))
                    .is_some_and(|v| COMPLEMENT_WORDS.contains(&v.base.as_str())));
        if complement {
            continue;
        }
        // "skills that employers want", "the fun that other kids can't": after a noun "that" opens a
        // relative clause. "I pondered this many times": "this" is an adverb before "many".
        if d == "that"
            && i > 0
            && (crate::structure::looks_plural(word(s, i - 1))
                || plural_form(&s[i - 1])
                || spelling::flags(word(s, i - 1)) & 2 != 0
                    && spelling::flags(word(s, i - 1)) & 4 == 0)
        {
            continue;
        }
        if ["this", "that"].contains(&d)
            && [
                "many", "much", "few", "long", "far", "little", "early", "late", "well",
            ]
            .contains(&word(s, i + 1))
        {
            continue;
        }
        let that_ok = prep
            || object && plural_noun(noun)
            || i == 0 && (plural_noun(noun) || ["are", "were"].contains(&word(s, n + 1)));
        // "that returns a 429": a verb reading with its own object.
        let verb_object = spelling::flags(&noun.normalized) & 4 != 0
            && [
                "a", "an", "the", "my", "your", "it", "them", "me", "us", "him", "this", "that",
            ]
            .contains(&word(s, n + 1));
        if verb_object && !prep {
            continue;
        }
        // "similar to those that you put together": a pronoun before a relative clause.
        if ["that", "who", "which", "whom", "whose", "where", "when"]
            .contains(&noun.normalized.as_str())
        {
            continue;
        }
        // "see that final agreements are forwarded": a "that" with a clause after it is the
        // conjunction.
        if d == "that"
            && i > 0
            && !prep
            && [
                "are", "were", "have", "is", "was", "will", "can", "could", "should", "would",
                "must", "may", "might", "do", "don't", "get", "go",
            ]
            .contains(&word(s, n + 1))
        {
            continue;
        }
        // "those left behind", "those outside the movement", "those dealing with", "these non-slip
        // mats", "these car keys", "these library subject guides": the noun phrase after a plural
        // demonstrative runs to its last noun, and only a singular last noun that is no verb form
        // and ends the phrase makes "these" wrong.
        let singular_head = {
            let run = nominal_run(req, s, i + 1);
            let head = run.last().map(|k| &s[*k]);
            let after = run.last().and_then(|k| s.get(k + 1));
            !run.is_empty()
                && head.is_some_and(|h| {
                    singular_noun(h)
                        // "these new and dangerous threats": a word that can be an adjective is no
                        // head while another word may follow; the noun is further on.
                        && !spelling::adjective(h)
                        && !COMMON_ADJECTIVES.contains(&h.normalized.as_str())
                        // "those outside the movement", "those in your family": a place word or
                        // preposition is no noun to count.
                        && ![
                            "outside", "inside", "above", "below", "near", "close", "such",
                            "around", "behind", "beyond", "among", "along", "across", "between",
                            "within", "through", "over", "under", "up", "down", "out", "off",
                            "in", "on", "at", "else", "only", "alike",
                        ]
                        .contains(&h.normalized.as_str())
                        && ends_clause(after)
                        // A word that is also a verb ("These mean", "those guy like it") is the
                        // noun only when the phrase ends or a helping verb follows.
                        && (spelling::flags(&h.normalized) & 4 == 0
                            || after.is_none_or(|a| {
                                !a.is_word
                                    || [
                                        "is", "was", "are", "were", "will", "can", "could",
                                        "would", "should", "has", "had", "does", "did",
                                    ]
                                    .contains(&a.normalized.as_str())
                            }))
                })
                && run.iter().all(|k| {
                    let t = &s[*k];
                    t.normalized.chars().all(char::is_alphabetic)
                })
                && !SUBJECTS.contains(&word(s, i + 1))
        };
        // "He found those book": a plural demonstrative before a countable singular noun is almost
        // always a dropped plural ending, so the noun changes. Only a singular verb after the phrase
        // ("Those guy is late") or a noun with no plural ("those furniture") points at the
        // demonstrative instead.
        if singular_head
            && ["these", "those"].contains(&d)
            && let Some(&head_k) = nominal_run(req, s, i + 1).last()
            && !s[head_k + 1..].iter().take(4).any(|t| {
                [
                    "is", "was", "has", "does", "isn't", "wasn't", "hasn't", "doesn't",
                ]
                .contains(&t.normalized.as_str())
            })
            && let Some(plural) = crate::forms::countable_plural(&s[head_k].normalized)
        {
            push(
                req,
                edits,
                span(s, head_k, head_k),
                crate::match_case(&plural, s[head_k].surface),
                "grammar.demonstrative_number",
                "“These” and “those” go with a plural noun.",
                0.9,
            );
            continue;
        }
        let fix = match d {
            // "any of this requires work", "this leads to": a verb in "-s" after "this" with more
            // clause to come is the verb, not a plural noun.
            "this" if plural_here && ends && !verb_third(noun) => "these",
            // "that" also opens a clause ("I know that kids love it"): only as a determiner.
            "that" if plural_here && ends && that_ok => "those",
            "these" if singular_head => "this",
            "those" if singular_head && word(s, n + 1) != "who" => "that",
            _ => continue,
        };
        push(
            req,
            edits,
            span(s, i, i),
            crate::match_case(fix, s[i].surface),
            "grammar.demonstrative_number",
            "Match “this” or “these” to the number of the noun.",
            0.95,
        );
    }
}
/// Adverbs that go with "few" and "little" and cannot take the comparative "fewer".
const INTENSIFIERS: [&str; 6] = ["very", "so", "too", "quite", "really", "extremely"];
/// "less complaints", "too much cooks", "an another": the quantifier follows the noun's number.
fn quantifiers(req: &Request, s: &[Token<'_>], edits: &mut Vec<Edit>) {
    for i in 0..s.len().saturating_sub(1) {
        let q = word(s, i);
        let next = &s[i + 1];
        if q == "an" && next.normalized == "another" {
            push(
                req,
                edits,
                (s[i].start_utf16, next.start_utf16),
                String::new(),
                "grammar.another_article",
                "“Another” already includes the article.",
                0.97,
            );
            continue;
        }
        let fix = match q {
            // "very less people" is "very few people" ("so few", "too few"), never "very fewer".
            "less" if plural_form(next) && i > 0 && INTENSIFIERS.contains(&word(s, i - 1)) => "few",
            "less" if plural_form(next) => "fewer",
            "much" if plural_form(next) && !["thanks"].contains(&next.normalized.as_str()) => {
                "many"
            }
            _ => continue,
        };
        // "much more", "less than": only a quantifier straight before its noun.
        push(
            req,
            edits,
            span(s, i, i),
            crate::match_case(fix, s[i].surface),
            "grammar.quantifier_number",
            "Use “fewer” and “many” with countable plural nouns.",
            0.95,
        );
    }
}
/// Nouns of quantity and grouping that follow "a" and take the number of what follows "of" ("a
/// number of reasons are", "a lot of water is"), so "there is" or "there are" can be right.
const PARTITIVES: [&str; 40] = [
    "lot",
    "few",
    "couple",
    "number",
    "bunch",
    "variety",
    "total",
    "lots",
    "pair",
    "dozen",
    "ton",
    "handful",
    "range",
    "host",
    "majority",
    "minority",
    "series",
    "set",
    "group",
    "mix",
    "mixture",
    "plethora",
    "myriad",
    "array",
    "selection",
    "collection",
    "multitude",
    "wealth",
    "load",
    "heap",
    "stack",
    "pile",
    "batch",
    "percentage",
    "proportion",
    "fraction",
    "slew",
    "raft",
    "barrage",
    "flood",
];
/// "There's three emails", "Is there any snacks", "There are a problem": the verb of "there is"
/// agrees with the noun after it.
fn there_be(req: &Request, s: &[Token<'_>], edits: &mut Vec<Edit>) {
    const NUMBERS: [&str; 15] = [
        "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "many", "several",
        "few", "both", "dozens", "hundreds",
    ];
    // Whether the noun phrase starting at `k` is plural (Some(true)), one thing (Some(false)) or unclear.
    let number = |mut k: usize| -> Option<bool> {
        while [
            "still", "also", "just", "only", "really", "so", "now", "too",
        ]
        .contains(&word(s, k))
        {
            k += 1;
        }
        let w = word(s, k);
        if NUMBERS.contains(&w)
            || w.chars().all(|c| c.is_ascii_digit()) && !w.is_empty() && w != "1"
        {
            return Some(true);
        }
        if [
            "some", "any", "the", "these", "those", "no", "my", "your", "our", "their",
        ]
        .contains(&w)
        {
            let mut n = k + 1;
            if s.get(n).is_some_and(|t| spelling::adjective(t)) {
                n += 1;
            }
            return s.get(n).filter(|t| plural_form(t)).map(|_| true);
        }
        if ["a", "an", "one"].contains(&w) {
            // "a large number of", "a wide range of", "a great many": the adjectives before a
            // quantity noun do not make it one thing.
            let mut head = k + 1;
            while head < k + 3
                && !PARTITIVES.contains(&word(s, head))
                && word(s, head) != "many"
                && s.get(head).is_some_and(|t| {
                    spelling::adjective(t)
                        || [
                            "good", "fair", "great", "large", "small", "big", "wide", "decent",
                            "huge", "vast", "healthy", "whole", "fine", "tidy", "sizeable",
                            "quite",
                        ]
                        .contains(&t.normalized.as_str())
                })
            {
                head += 1;
            }
            let h = word(s, head);
            if PARTITIVES.contains(&h) || head > k + 1 && h == "many" {
                return None;
            }
            return Some(false);
        }
        None
    };
    for i in 0..s.len().saturating_sub(1) {
        let w = word(s, i);
        // "there's" / "here's", or "there is" / "there was" / "here is".
        let (be_at, after, many) = match w {
            "there's" | "here's" => (i, i + 1, false),
            "there" | "here" if ["is", "are", "was", "were"].contains(&word(s, i + 1)) => {
                (i + 1, i + 2, ["are", "were"].contains(&word(s, i + 1)))
            }
            // "Is there any snacks left?"
            "is" | "are" | "was" | "were" if word(s, i + 1) == "there" && i == 0 => {
                (i, i + 2, ["are", "were"].contains(&w))
            }
            _ => continue,
        };
        let Some(plural_np) = number(after) else {
            continue;
        };
        if plural_np == many {
            continue;
        }
        let be = word(s, be_at);
        let past = ["was", "were"].contains(&be);
        let fixed_be = match (plural_np, past) {
            (true, false) => "are",
            (true, true) => "were",
            (false, false) => "is",
            (false, true) => "was",
        };
        let replacement = if be.ends_with("'s") {
            let stem = &s[be_at].surface
                [..s[be_at].surface.len() - 2 - usize::from(s[be_at].surface.ends_with("’s")) * 2];
            format!("{stem} {fixed_be}")
        } else {
            crate::match_case(fixed_be, s[be_at].surface)
        };
        push(
            req,
            edits,
            span(s, be_at, be_at),
            replacement,
            "grammar.there_agreement",
            "After “there”, the verb agrees with the noun that follows.",
            0.95,
        );
    }
}
/// "Does they have", "Has they confirmed", "Was you there": a question's opening auxiliary agrees
/// with the pronoun after it.
fn opening_auxiliary(req: &Request, s: &[Token<'_>], edits: &mut Vec<Edit>, question: bool) {
    if !question || s.len() < 3 {
        return;
    }
    let (aux, subject) = (word(s, 0), word(s, 1));
    if !SUBJECTS.contains(&subject) {
        return;
    }
    let one = ["he", "she", "it"].contains(&subject);
    let fix = match (aux, subject) {
        ("does", _) if !one => "do",
        ("do", _) if one => "does",
        ("has", _) if !one => "have",
        ("have", _) if one => "has",
        ("was", "you" | "we" | "they") => "were",
        ("were", "i" | "he" | "she" | "it") => "was",
        ("is", "you" | "we" | "they") => "are",
        ("is", "i") | ("are", "i") => "am",
        ("are", _) if one => "is",
        ("doesn't", _) if !one => "don't",
        ("don't", _) if one => "doesn't",
        _ => return,
    };
    push(
        req,
        edits,
        span(s, 0, 0),
        crate::match_case(fix, s[0].surface),
        "grammar.inverted_subject_agreement",
        "Match the inverted auxiliary to its subject.",
        0.95,
    );
}
pub fn check(req: &Request, s: &[Token<'_>], edits: &mut Vec<Edit>, question: bool) {
    article_sound(req, s, edits);
    article_number(req, s, edits);
    subject_agreement(req, s, edits);
    demonstratives(req, s, edits);
    quantifiers(req, s, edits);
    there_be(req, s, edits);
    opening_auxiliary(req, s, edits, question);
}
