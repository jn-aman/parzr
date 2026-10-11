//! Word forms that the neighbouring words decide: "its" or "it's". Each repair reads a few words on
//! either side and fires only where the other reading is not English ("on it's own", "its blocking
//! the deploy").
use crate::{
    Edit, Request,
    clause_repairs::{push, span, word},
    morphology,
    tokenizer::Token,
};

/// Nouns that follow a possessive and are hardly ever a bare predicate ("it's name" is no clause).
const POSSESSED: &[&str] = &[
    "name",
    "names",
    "purpose",
    "members",
    "contents",
    "origin",
    "origins",
    "roots",
    "doors",
    "headquarters",
    "inception",
    "debut",
    "predecessor",
    "predecessors",
    "successor",
    "successors",
    "parent",
    "mission",
    "goals",
    "peak",
    "core",
    "height",
    "width",
    "length",
    "shape",
    "colour",
    "color",
    "population",
    "ability",
    "entirety",
    "status",
    "territory",
    "inhabitants",
    "residents",
    "citizens",
    "surface",
    "owner",
    "owners",
    "users",
    "author",
    "authors",
    "creator",
    "creators",
    "founder",
    "founders",
    "borders",
    "tail",
    "wings",
    "legs",
    "employees",
    "customers",
    "constructor",
    "subsidiaries",
    "habitat",
    "nickname",
    "sequel",
    "creation",
    "establishment",
    "premiere",
    "completion",
    "formation",
    "demise",
    "heyday",
    "infancy",
    "closure",
    "beginnings",
    "launch",
    "values",
    "properties",
    "methods",
    "dependencies",
    "arguments",
    "parameters",
    "behaviour",
    "behavior",
    "lifetime",
    "lifespan",
    "lifecycle",
    "id",
    "api",
    "interface",
    "implementation",
];
/// Adjectives that only stand before a noun ("its own", "its former"), never after "it is".
const ATTRIBUTIVE: &[&str] = &[
    "own",
    "former",
    "entire",
    "principal",
    "inaugural",
    "maiden",
    "respective",
    "eastern",
    "western",
    "northern",
    "southern",
    "founding",
    "main",
];
/// Prepositions after which "it's" cannot start a clause ("in it's place").
const PREPOSITIONS: &[&str] = &[
    "of",
    "in",
    "into",
    "onto",
    "within",
    "from",
    "by",
    "at",
    "under",
    "during",
    "throughout",
    "despite",
    "via",
    "across",
    "without",
    "upon",
    "through",
    "against",
    "among",
    "behind",
    "beyond",
    "inside",
    "with",
];
/// Verbs that take an object and never a clause, so "it's" after one is a possessive.
const OBJECT_VERBS: &[&str] = &[
    "has",
    "have",
    "had",
    "having",
    "changed",
    "changes",
    "change",
    "changing",
    "lost",
    "lose",
    "loses",
    "losing",
    "made",
    "opened",
    "opens",
    "using",
    "use",
    "uses",
    "received",
    "receives",
    "given",
    "held",
    "holds",
    "hold",
    "reached",
    "reaches",
    "gained",
    "kept",
    "keeps",
    "retained",
    "retains",
    "took",
    "takes",
    "increased",
    "expanded",
    "won",
    "celebrated",
    "celebrates",
    "maintained",
    "maintains",
    "began",
    "begins",
    "completed",
    "finished",
    "ended",
    "raised",
    "moved",
    "moves",
    "launched",
    "fulfilled",
    "fulfil",
    "fulfill",
    "served",
    "serves",
    "defined",
    "defines",
    "define",
    "updates",
    "update",
    "updated",
    "returns",
    "returned",
    "sets",
    "set",
    "stores",
    "stored",
    "renamed",
    "rename",
    "shared",
    "shares",
    "earned",
    "earns",
    "doubled",
    "reduced",
    "reduces",
    "lived",
    "spent",
    "spends",
    "established",
    "relocated",
    "closed",
    "closes",
    "extended",
    "extends",
    "improved",
    "improves",
    "lowered",
    "released",
    "releases",
    "stepped",
    "cut",
    "calls",
    "called",
];
/// Adjectives that say what something is, after "it is" ("it's possible to").
const PREDICATE_ADJECTIVES: &[&str] = &[
    "possible",
    "impossible",
    "important",
    "hard",
    "easy",
    "easier",
    "harder",
    "difficult",
    "illegal",
    "necessary",
    "unnecessary",
    "true",
    "likely",
    "unlikely",
    "better",
    "worse",
    "cool",
    "nice",
    "ready",
    "okay",
    "ok",
    "fine",
    "great",
    "bad",
    "sad",
    "funny",
    "weird",
    "strange",
    "interesting",
    "boring",
    "amazing",
    "awesome",
    "annoying",
    "useful",
    "helpful",
    "safe",
    "unsafe",
    "clear",
    "obvious",
    "simple",
    "complicated",
    "expensive",
    "cheap",
    "late",
    "cold",
    "hot",
    "dark",
    "free",
    "wrong",
    "right",
    "recommended",
    "needed",
    "required",
    "finished",
    "done",
    "gone",
    "broken",
    "over",
    "worth",
    "enough",
    "alright",
    "crazy",
    "fun",
    "beautiful",
    "perfect",
    "terrible",
    "horrible",
    "awful",
    "tough",
    "unclear",
    "unknown",
];
/// Words that can begin the object of a verb.
const OBJECT_START: &[&str] = &[
    "the",
    "a",
    "an",
    "my",
    "your",
    "our",
    "their",
    "his",
    "her",
    "me",
    "us",
    "them",
    "him",
    "you",
    "everything",
    "something",
    "anything",
    "it",
    "all",
    "some",
    "any",
    "every",
    "each",
    "no",
];
/// Words that can end a short "it's" clause after an "-ing" verb ("its working now").
const CLAUSE_TAIL: &[&str] = &[
    "now",
    "again",
    "fine",
    "well",
    "properly",
    "correctly",
    "perfectly",
    "great",
    "ok",
    "okay",
    "so",
    "too",
    "really",
    "right",
    "already",
    "still",
    "forever",
    "anymore",
];
/// A word that starts a noun phrase owned by "its": an attributive adjective, a noun that is no
/// predicate, or a common noun the tagger is sure about (an adjective needs a noun after it).
fn nominal(s: &[Token<'_>], i: usize, strict: bool) -> bool {
    let w = word(s, i);
    if w.is_empty() {
        return false;
    }
    if ATTRIBUTIVE.contains(&w) || POSSESSED.contains(&w) {
        return true;
    }
    if strict {
        return false;
    }
    let noun = |t: &Token<'_>| {
        let x = t.normalized.as_str();
        t.is_word
            && t.pos == "Noun"
            && !t.proper_name
            && !PREDICATE_ADJECTIVES.contains(&x)
            && ![
                "time",
                "fun",
                "nothing",
                "something",
                "everything",
                "anything",
                "home",
                "lunch",
                "dinner",
                "breakfast",
                "night",
                "morning",
                "afternoon",
                "evening",
                "today",
                "tomorrow",
                "yesterday",
                "christmas",
                "me",
                "you",
                "him",
                "her",
                "us",
                "them",
                "one",
                "kind",
                "sort",
                "part",
                "half",
                "all",
                "both",
                "way",
            ]
            .contains(&x)
            && !morphology::verb(x).is_some_and(|v| v.gerund == x || v.participle == x)
    };
    let after = s.get(i + 1);
    // "of it's history, ..." or "in it's place.": a noun that ends the phrase.
    if noun(&s[i])
        && after.is_none_or(|a| {
            !a.is_word || !["that", "who", "which"].contains(&a.normalized.as_str())
        })
    {
        return true;
    }
    // "of it's long history": an adjective and its noun.
    s[i].pos == "Adjective" && !PREDICATE_ADJECTIVES.contains(&w) && after.is_some_and(|a| noun(a))
}
/// "it's" where only the possessive fits: "it's own", "it's name", "in it's place", "has it's".
fn its_possessive(req: &Request, s: &[Token<'_>], edits: &mut Vec<Edit>) {
    for i in 0..s.len().saturating_sub(1) {
        if word(s, i) != "it's" {
            continue;
        }
        // "it's own-brand" or "it's name-calling": a compound may say something else.
        if req.text[s[i + 1].end_byte..].starts_with('-') {
            continue;
        }
        let before = if i > 0 { word(s, i - 1) } else { "" };
        let next = word(s, i + 1);
        // "It's name that matters" is a cleft; "Now it's colour and ..." a short clause.
        let open = s.get(i + 2).is_some_and(|t| {
            t.is_word
                && !["that", "who", "which", "and", "or", "but"].contains(&t.normalized.as_str())
        });
        let fits = next == "own"
            || open && (ATTRIBUTIVE.contains(&next) || POSSESSED.contains(&next))
            || PREPOSITIONS.contains(&before) && nominal(s, i + 1, false)
            || OBJECT_VERBS.contains(&before) && nominal(s, i + 1, false);
        if !fits {
            continue;
        }
        push(
            req,
            edits,
            span(s, i, i),
            crate::match_case("its", s[i].surface),
            "grammar.its_possessive",
            "Use “its” for something that belongs to it; “it's” means “it is”.",
            0.96,
        );
    }
}
/// "its" where only "it is" fits: "its blocking the deploy", "if its possible", "its working now".
fn its_contraction(req: &Request, s: &[Token<'_>], edits: &mut Vec<Edit>) {
    for i in 0..s.len().saturating_sub(1) {
        if word(s, i) != "its" {
            continue;
        }
        let next = word(s, i + 1);
        let after = word(s, i + 2);
        let ends = |k: usize| {
            s.get(k)
                .is_none_or(|t| [".", "!", "?", ",", ";", ":"].contains(&t.surface))
        };
        let gerund = next.ends_with("ing")
            && !["being", "having"].contains(&next)
            && morphology::verb(next).is_some_and(|v| v.gerund == next);
        // An "-ing" verb with its object: "its blocking the deploy". A time phrase after a noun in
        // "-ing" stays ("its opening the next day").
        let with_object = gerund
            && OBJECT_START.contains(&after)
            && !(after == "the"
                && [
                    "next",
                    "following",
                    "previous",
                    "same",
                    "last",
                    "first",
                    "day",
                    "week",
                    "year",
                ]
                .contains(&word(s, i + 3)));
        // A short clause at the start: "its working now", "its raining."
        let short = gerund && i == 0 && (ends(i + 2) || CLAUSE_TAIL.contains(&after));
        // "if its possible to", "because its illegal.", "its very hard to": a predicate adjective
        // and then no noun.
        let mut k = i + 1;
        if [
            "very",
            "quite",
            "really",
            "so",
            "too",
            "super",
            "extremely",
            "fairly",
            "pretty",
            "also",
            "still",
            "just",
            "not",
            "always",
            "often",
            "usually",
            "probably",
            "actually",
            "definitely",
        ]
        .contains(&word(s, k))
            && PREDICATE_ADJECTIVES.contains(&word(s, k + 1))
        {
            k += 1;
        }
        let predicate = PREDICATE_ADJECTIVES.contains(&word(s, k))
            && !(k == i + 1 && ["worth", "right"].contains(&next))
            && (ends(k + 1)
                || [
                    "to", "for", "that", "if", "when", "because", "now", "enough", "though",
                    "anyway", "too",
                ]
                .contains(&word(s, k + 1)));
        // "more trouble than its worth".
        let worth = next == "worth" && i > 0 && word(s, i - 1) == "than";
        // "its just a typo", "its still there".
        let adverb = [
            "just",
            "still",
            "already",
            "now",
            "actually",
            "basically",
            "literally",
            "definitely",
            "obviously",
            "simply",
            "totally",
            "completely",
            "almost",
        ]
        .contains(&next)
            && [
                "a", "an", "the", "not", "no", "like", "my", "your", "our", "their", "me", "him",
                "them", "us", "that", "what", "how", "because", "about", "getting", "going",
                "been", "there", "here",
            ]
            .contains(&after);
        if !(with_object || short || predicate || worth || adverb) {
            continue;
        }
        push(
            req,
            edits,
            span(s, i, i),
            crate::match_case("it's", s[i].surface),
            "grammar.its_contraction",
            "Use “it's” (it is or it has) here; “its” is possessive.",
            0.95,
        );
    }
}
pub fn check(req: &Request, s: &[Token<'_>], edits: &mut Vec<Edit>) {
    its_possessive(req, s, edits);
    its_contraction(req, s, edits);
    be_participle(req, s, edits);
    known_as(req, s, edits);
    modal_gerund(req, s, edits);
    infinitive_base(req, s, edits);
}
/// Adverbs that may stand between a helping verb and its participle ("was originally built").
const MID_ADVERBS: &[&str] = &[
    "also",
    "best",
    "well",
    "commonly",
    "widely",
    "now",
    "still",
    "not",
    "never",
    "already",
    "often",
    "usually",
    "generally",
    "originally",
    "formerly",
    "later",
    "first",
    "just",
    "currently",
    "previously",
    "rarely",
    "sometimes",
    "mostly",
    "mainly",
    "largely",
    "fully",
    "newly",
    "recently",
    "specifically",
    "primarily",
    "typically",
    "always",
    "actually",
    "successfully",
    "officially",
    "eventually",
    "finally",
    "initially",
    "subsequently",
    "only",
    "automatically",
    "properly",
    "correctly",
    "easily",
];
/// How strongly the word pairs prefer `b` after `prev` to `a` after it.
fn prefers(prev: &str, a: &str, b: &str, ratio: u64) -> bool {
    let (ca, cb) = (
        crate::context::count(prev, a),
        crate::context::count(prev, b),
    );
    cb >= 5_000_000 && cb >= ratio * ca.max(1)
}
/// "was build in 1900", "will be replaces", "is believe to be", "has been check": a form of "be"
/// before a verb that is not its participle, where the word pairs show the participle belongs.
fn be_participle(req: &Request, s: &[Token<'_>], edits: &mut Vec<Edit>) {
    const BE: [&str; 8] = ["is", "are", "was", "were", "be", "been", "being", "am"];
    for i in 0..s.len().saturating_sub(1) {
        let be = word(s, i);
        if !BE.contains(&be) {
            continue;
        }
        // "There is need for", "Is use of force ...": an existential or a question.
        if i == 0 || ["there", "here"].contains(&word(s, i - 1)) {
            continue;
        }
        // "All we need to do is build it": the pseudo-cleft takes the bare verb.
        if s[..i]
            .iter()
            .any(|t| ["do", "does", "did", "done"].contains(&t.normalized.as_str()))
        {
            continue;
        }
        let mut k = i + 1;
        if MID_ADVERBS.contains(&word(s, k)) && word(s, k) != "well" {
            k += 1;
        }
        let w = word(s, k);
        let t = &s[k];
        if w.is_empty()
            || t.proper_name
            || t.surface.starts_with(char::is_uppercase)
            || req.text[t.end_byte..].starts_with('-')
        {
            continue;
        }
        let Some(v) = morphology::verb(w) else {
            continue;
        };
        let form = if w == v.base {
            "base"
        } else if w == v.third {
            "third"
        } else if w == v.past {
            "past"
        } else {
            continue;
        };
        // "they are passes": after a plural "be" an "-s" word is a plural noun.
        if w == v.participle
            || v.base == "be"
            || form == "third" && ["are", "were", "am"].contains(&be)
            || !crate::spelling::known(&v.participle)
        {
            continue;
        }
        let next = word(s, k + 1);
        // "is use of", "the step is build quality": a noun reading.
        if next == "of"
            || s.get(k + 1).is_some_and(|n| {
                n.is_word
                    && n.pos == "Noun"
                    && ![
                        "as", "by", "in", "on", "at", "to", "for", "with", "from", "into",
                    ]
                    .contains(&n.normalized.as_str())
            })
        {
            continue;
        }
        if !prefers(word(s, k - 1), w, &v.participle, 20) {
            continue;
        }
        push(
            req,
            edits,
            span(s, k, k),
            v.participle.clone(),
            "grammar.passive_participle",
            "Use a past participle in this passive verb phrase.",
            0.94,
        );
    }
}
/// "also know as", "best know for": the participle "known".
fn known_as(req: &Request, s: &[Token<'_>], edits: &mut Vec<Edit>) {
    for i in 1..s.len().saturating_sub(2) {
        if word(s, i) != "know" || !["as", "for"].contains(&word(s, i + 1)) {
            continue;
        }
        let adverb = word(s, i - 1);
        if ![
            "also",
            "best",
            "well",
            "commonly",
            "widely",
            "better",
            "formerly",
            "locally",
            "popularly",
            "previously",
            "originally",
            "otherwise",
            "generally",
            "internationally",
            "affectionately",
            "collectively",
            "informally",
            "officially",
            "colloquially",
            "mostly",
            "now",
            "later",
            "simply",
            "often",
            "sometimes",
            "usually",
        ]
        .contains(&adverb)
        {
            continue;
        }
        // "We also know as much": a subject before the adverb makes "know" its verb.
        if i >= 2
            && [
                "i", "you", "we", "they", "he", "she", "people", "everyone", "who", "to", "and",
            ]
            .contains(&word(s, i - 2))
        {
            continue;
        }
        let after = word(s, i + 2);
        if [
            "much", "well", "many", "long", "soon", "far", "little", "few", "if", "though", "a",
            "an", "it", "you", "we", "they", "i",
        ]
        .contains(&after)
        {
            continue;
        }
        push(
            req,
            edits,
            span(s, i, i),
            "known".into(),
            "grammar.known_as",
            "Use the participle “known” here.",
            0.95,
        );
    }
}
/// "You should starting", "can doing": a modal takes the bare verb.
fn modal_gerund(req: &Request, s: &[Token<'_>], edits: &mut Vec<Edit>) {
    const MODALS: [&str; 9] = [
        "should", "would", "could", "must", "might", "can", "will", "shall", "may",
    ];
    for i in 0..s.len().saturating_sub(1) {
        let m = word(s, i);
        if !MODALS.contains(&m) || s[i].surface.starts_with(char::is_uppercase) && i > 0 {
            continue;
        }
        // "the will", "a can of", "his free will": a noun, not a modal.
        if i > 0
            && [
                "the",
                "a",
                "an",
                "this",
                "that",
                "his",
                "her",
                "my",
                "your",
                "their",
                "our",
                "its",
                "free",
                "good",
                "last",
                "strong",
                "political",
                "own",
            ]
            .contains(&word(s, i - 1))
        {
            continue;
        }
        let mut k = i + 1;
        if [
            "not", "also", "just", "still", "never", "always", "only", "really",
        ]
        .contains(&word(s, k))
        {
            k += 1;
        }
        let w = word(s, k);
        if !w.ends_with("ing") || s[k].proper_name {
            continue;
        }
        let Some(v) = morphology::verb(w) else {
            continue;
        };
        if v.gerund != w || !crate::spelling::known(&v.base) {
            continue;
        }
        push(
            req,
            edits,
            span(s, k, k),
            v.base.clone(),
            "grammar.modal_base",
            "Use the base verb after a modal.",
            0.95,
        );
    }
}
/// "need to calculated the size", "to went there": "to" before a verb takes its base form.
fn infinitive_base(req: &Request, s: &[Token<'_>], edits: &mut Vec<Edit>) {
    for i in 0..s.len().saturating_sub(2) {
        if word(s, i) != "to" {
            continue;
        }
        let w = word(s, i + 1);
        let t = &s[i + 1];
        if w.is_empty() || t.proper_name || req.text[t.end_byte..].starts_with('-') {
            continue;
        }
        let Some(v) = morphology::verb(w) else {
            continue;
        };
        if w == v.base || w == v.gerund || v.base == "be" || !crate::spelling::known(&v.base) {
            continue;
        }
        // Only a verb with its object: "to paid plans" and "to used cars" are noun phrases.
        let after = word(s, i + 2);
        if ![
            "the", "a", "an", "my", "your", "our", "their", "his", "her", "me", "us", "them",
            "him", "it", "this", "that", "these", "those", "some", "any", "every", "all",
        ]
        .contains(&after)
        {
            continue;
        }
        if !prefers("to", w, &v.base, 20) {
            continue;
        }
        push(
            req,
            edits,
            span(s, i + 1, i + 1),
            v.base.clone(),
            "grammar.infinitive_base",
            "Use the base verb after “to”.",
            0.94,
        );
    }
}
