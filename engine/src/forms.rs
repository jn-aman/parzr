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
            // Without a tagger hint, a dictionary noun that is no adjective.
            && (t.pos == "Noun"
                || t.pos.is_empty()
                    && crate::spelling::flags(x) & 2 != 0
                    && crate::spelling::flags(x) & 8 == 0)
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
    s[i].pos == "Adjective" && !PREDICATE_ADJECTIVES.contains(&w) && after.is_some_and(noun)
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
    noun_number(req, s, edits);
    agreement(req, s, edits);
    word_form(req, s, edits);
    slips(req, s, edits);
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
        let Some(t) = s.get(k) else {
            continue;
        };
        if w.is_empty()
            || t.proper_name
            || t.surface.starts_with(char::is_uppercase)
            || req.text[t.end_byte..].starts_with('-')
        {
            continue;
        }
        // "This is mark from the design team", "This is bill": a lowercase name, not a verb.
        if crate::names::is_bundled_name(w)
            || crate::names::name_word(w)
            || ["this", "that", "here", "who"].contains(&word(s, i - 1)) && k == i + 1
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
        // "might be attributes": an "-s" word after "be" is mostly a plural noun; only "been
        // resolves" is a sure slip. "is save" is "is safe" mistyped.
        if w == v.participle
            || v.base == "be"
            || form == "third" && be != "been"
            || ["save", "lay", "lie", "found", "wound", "ground"].contains(&w)
            // "The students were mean": an adjective, not "meant".
            || crate::spelling::flags(w) & 8 != 0 && morphology::extra(&v.base)
            || !crate::spelling::known(&v.participle)
        {
            continue;
        }
        let next = word(s, k + 1);
        // After "is" or "was" a bare verb is often a dropped "-ing" or "-s" ("is match with", "is
        // want"): only a passive's usual next words count there ("was build in 1900").
        if form == "base"
            && ["is", "are", "was", "were", "am"].contains(&prev_be(s, k))
            && !s.get(k + 1).is_none_or(|n| {
                [".", ",", ";", ":", ")", "!", "?"].contains(&n.surface)
                    || [
                        "by", "in", "on", "at", "to", "as", "from", "into", "under", "during",
                        "after", "before", "for", "using", "via", "through", "and", "or",
                    ]
                    .contains(&n.normalized.as_str())
            })
        {
            continue;
        }
        // "are use more chemicals": an object after the verb makes it active ("was play with" or
        // "be get" wanted "-ing"), except for verbs with two objects ("was given a medal").
        if [
            "the", "a", "an", "my", "your", "our", "their", "his", "her", "me", "us", "them",
            "him", "it", "this", "these", "those", "some", "more", "any",
        ]
        .contains(&next)
            && ![
                "give", "send", "show", "tell", "offer", "award", "grant", "teach", "ask", "pay",
                "promise", "deny", "lend", "call", "name", "elect", "appoint", "make", "consider",
            ]
            .contains(&v.base.as_str())
        {
            continue;
        }
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
        // The participle must also beat the "-ing" form, or the writer may have meant a
        // progressive ("he was play with" is "playing").
        let prev = word(s, k - 1);
        if !prefers(prev, w, &v.participle, 20)
            || crate::context::count(prev, &v.participle)
                < 3 * crate::context::count(prev, &v.gerund)
        {
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
/// The form of "be" before the verb at `k`, past one adverb.
fn prev_be<'t>(s: &'t [Token<'_>], k: usize) -> &'t str {
    let p = word(s, k - 1);
    if MID_ADVERBS.contains(&p) && k >= 2 {
        word(s, k - 2)
    } else {
        p
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
        // "Should smoking be banned?": an opening modal asks a question about a gerund subject.
        if !MODALS.contains(&m) || i == 0 || s[i].surface.starts_with(char::is_uppercase) {
            continue;
        }
        // "as will adding a little hay", "than can smoking": the modal comes first, so a gerund
        // after it is the subject.
        if ["as", "than", "so", "nor", "neither"].contains(&word(s, i - 1)) {
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
        // "can smoking be" or "will cooking help": a gerund subject of a question or clause.
        if v.gerund != w
            || !crate::spelling::known(&v.base)
            || s.get(k + 1).is_some_and(crate::punctuation::finite)
            || word(s, k + 1) == "be"
        {
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
        // "to lay the carpet", "to found a company": a past form that is also another verb's base.
        if w == v.base
            || w == v.gerund
            || v.base == "be"
            || morphology::also_base(w)
            || !crate::spelling::known(&v.base)
        {
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
/// Irregular plurals: (singular, plural).
const IRREGULAR_PLURALS: &[(&str, &str)] = &[
    ("man", "men"),
    ("woman", "women"),
    ("child", "children"),
    ("foot", "feet"),
    ("tooth", "teeth"),
    ("mouse", "mice"),
    ("goose", "geese"),
    ("life", "lives"),
    ("wife", "wives"),
    ("knife", "knives"),
    ("leaf", "leaves"),
    ("half", "halves"),
    ("shelf", "shelves"),
    ("thief", "thieves"),
    ("wolf", "wolves"),
];
/// Nouns whose singular also counts as a group or amount ("two dozen", "many a time").
const NUMBERLESS: &[&str] = &[
    "percent", "dozen", "hundred", "thousand", "million", "billion", "trillion", "staff", "data",
    "family", "team", "group", "crowd", "public", "gang", "series", "species", "means", "news",
    "fish", "sheep", "deer", "aircraft", "people", "police", "kind", "sort", "type", "part", "lot",
    "bit", "couple", "pair", "number", "time", "way", "thing", "one", "other", "few", "more",
    "most", "less", "much", "all", "each", "rest", "same", "next", "last", "first", "majority",
    "minority", "half", "per", "cent", "degree", "story", "storey", "piece", "page", "point",
];
/// Nouns that are mostly uncountable or keep one form ("many anime", "various content").
const MASS: &[&str] = &[
    "music",
    "anime",
    "content",
    "evidence",
    "information",
    "advice",
    "equipment",
    "furniture",
    "software",
    "hardware",
    "research",
    "knowledge",
    "homework",
    "luggage",
    "baggage",
    "news",
    "traffic",
    "money",
    "water",
    "weather",
    "sigma",
    "youth",
    "feedback",
    "stuff",
    "staff",
    "art",
    "work",
    "help",
    "fun",
    "health",
    "media",
    "following",
    "favourite",
    "favorite",
];
/// Units that also make compound modifiers ("a two year contract", "a two dollar bill"): plural
/// only where the phrase plainly ends ("two year ago").
const UNITS: &[&str] = &[
    "metre",
    "meter",
    "pound",
    "dollar",
    "euro",
    "year",
    "month",
    "week",
    "day",
    "hour",
    "minute",
    "second",
    "mile",
    "inch",
    "foot",
    "kilometer",
    "kilometre",
];
fn noun_like(t: &Token<'_>) -> bool {
    let w = t.normalized.as_str();
    t.is_word
        && !t.proper_name
        // Without a tagger hint, any dictionary noun (its adjective flag is too generous to use).
        && (t.pos == "Noun" || t.pos.is_empty() && crate::spelling::flags(w) & 2 != 0)
}
/// The plural of a singular count noun the dictionary knows as a plural ("problem" to "problems").
fn plural_of(w: &str) -> Option<String> {
    if let Some((_, p)) = IRREGULAR_PLURALS.iter().find(|(s, _)| *s == w) {
        return Some((*p).to_owned());
    }
    let plural = |x: &str| crate::spelling::flags(x) & 16 != 0 && crate::spelling::ordinary(x);
    let mut forms = vec![format!("{w}s"), format!("{w}es")];
    if let Some(stem) = w.strip_suffix('y')
        && !stem.ends_with(['a', 'e', 'i', 'o', 'u'])
    {
        forms.insert(0, format!("{stem}ies"));
    }
    forms.into_iter().find(|f| plural(f))
}
/// The singular of a plural noun the dictionary knows ("students" to "student").
fn singular_of(w: &str) -> Option<String> {
    if let Some((s, _)) = IRREGULAR_PLURALS.iter().find(|(_, p)| *p == w) {
        return Some((*s).to_owned());
    }
    if crate::spelling::flags(w) & 16 == 0 {
        return None;
    }
    let noun = |x: &str| {
        crate::spelling::flags(x) & 2 != 0
            && crate::spelling::flags(x) & 16 == 0
            && crate::spelling::ordinary(x)
    };
    let mut forms = vec![];
    if let Some(stem) = w.strip_suffix("ies") {
        forms.push(format!("{stem}y"));
    }
    if let Some(stem) = w.strip_suffix("es") {
        forms.push(stem.to_owned());
    }
    if let Some(stem) = w.strip_suffix('s')
        && !stem.ends_with('s')
    {
        forms.push(stem.to_owned());
    }
    forms.into_iter().find(|f| noun(f))
}
/// Whether the noun at `i` plainly ends its phrase: a stop or a function word follows, never
/// another noun or modifier ("two crew members", "a six speed manual").
fn phrase_end(req: &Request, s: &[Token<'_>], i: usize) -> bool {
    if req.text[s[i].end_byte..].starts_with(['-', '\'', '’', '/', '(']) {
        return false;
    }
    s.get(i + 1).is_none_or(|n| {
        [".", ",", ";", ":", "!", "?", ")"].contains(&n.surface)
            || [
                "of",
                "in",
                "on",
                "at",
                "for",
                "with",
                "from",
                "to",
                "by",
                "but",
                "that",
                "which",
                "who",
                "are",
                "were",
                "have",
                "had",
                "will",
                "would",
                "can",
                "could",
                "should",
                "may",
                "might",
                "must",
                "do",
                "did",
                "ago",
                "later",
                "per",
                "than",
                "as",
                "into",
                "about",
                "after",
                "before",
                "during",
                "since",
                "until",
                "over",
                "under",
                "is",
                "was",
                "has",
                "because",
                "when",
                "if",
                "so",
                "too",
                "again",
                "here",
                "there",
                "now",
                "today",
                "yesterday",
                "every",
                "each",
                "left",
                "remaining",
            ]
            .contains(&n.normalized.as_str())
    })
}
/// "many problem", "two car", "one of the best player", "each students", "all kind of": a noun
/// takes the number its quantifier gives it.
fn noun_number(req: &Request, s: &[Token<'_>], edits: &mut Vec<Edit>) {
    const MANY: &[&str] = &[
        "many",
        "several",
        "various",
        "numerous",
        "few",
        "multiple",
        "two",
        "three",
        "four",
        "five",
        "six",
        "seven",
        "eight",
        "nine",
        "ten",
        "twelve",
        "twenty",
        "hundreds",
        "thousands",
        "dozens",
        "millions",
    ];
    const POSSESSIVE: &[&str] = &[
        "the", "my", "your", "his", "her", "its", "our", "their", "these", "those",
    ];
    let fix = |edits: &mut Vec<Edit>, k: usize, r: String, why: &str| {
        push(
            req,
            edits,
            span(s, k, k),
            crate::match_case(&r, s[k].surface),
            "grammar.noun_number",
            why,
            0.94,
        );
    };
    for i in 0..s.len().saturating_sub(1) {
        let q = word(s, i);
        // "all kind of", "different type of": a plural quantifier before "kind of".
        if [
            "all",
            "different",
            "many",
            "various",
            "several",
            "both",
            "numerous",
        ]
        .contains(&q)
            && ["kind", "type", "sort"].contains(&word(s, i + 1))
            && word(s, i + 2) == "of"
            && !(q == "all" && i > 0 && ["at", "of"].contains(&word(s, i - 1)))
            // "a different type of film" is one type.
            && !(i > 0
                && ["a", "an", "one", "each", "every", "this", "that", "any"]
                    .contains(&word(s, i - 1)))
        {
            fix(
                edits,
                i + 1,
                format!("{}s", word(s, i + 1)),
                "Use the plural after a word for more than one.",
            );
            continue;
        }
        // "a lots of".
        if q == "a" && word(s, i + 1) == "lots" && word(s, i + 2) == "of" {
            fix(
                edits,
                i + 1,
                "lot".into(),
                "“A lot of” takes the singular “lot”.",
            );
            continue;
        }
        let mut k = i + 1;
        if MANY.contains(&q) {
            // "a few", "the many": both count; "many a time" and "few of" are no plural noun phrase.
            // A noun before the number labels it ("chapter two"); a verb that is also a noun
            // ("have") counts only with the tagger's word.
            let labelled = i > 0
                && noun_like(&s[i - 1])
                && (!s[i - 1].pos.is_empty() || crate::spelling::flags(word(s, i - 1)) & 4 == 0);
            if labelled && !["a", "the"].contains(&word(s, i - 1)) {
                continue;
            }
            // "top ten list", "BBC Two drama", "lean six sigma", "best-of-seven format",
            // "electric multiple unit": a number or quantifier inside a name or label.
            if i > 0
                && (["top", "bottom", "best", "worst", "first", "last", "next"]
                    .contains(&word(s, i - 1))
                    || s[i - 1].surface.starts_with(char::is_uppercase)
                    || s[i - 1].pos == "Adjective"
                    || req.text[..s[i].start_byte].ends_with('-'))
            {
                continue;
            }
            // "the two form a bond": a number standing for its noun.
            if i > 0
                && ["the", "these", "those", "other", "all"].contains(&word(s, i - 1))
                && !["many", "few"].contains(&q)
            {
                continue;
            }
            // "several big problem"; after a number an adjective makes a compound ("three
            // dimensional art").
            if ["many", "several", "various", "numerous", "multiple"].contains(&q)
                && s.get(k).is_some_and(|t| t.pos == "Adjective")
                && s.get(k + 1).is_some_and(noun_like)
            {
                k += 1;
            }
            let Some(t) = s.get(k) else { continue };
            let w = t.normalized.as_str();
            let unit_ends = s.get(k + 1).is_none_or(|n| {
                [".", ",", ";", "!", "?", ")"].contains(&n.surface)
                    || ["ago", "later", "earlier", "long"].contains(&n.normalized.as_str())
            });
            let numeral =
                !["many", "several", "various", "numerous", "multiple", "few"].contains(&q);
            let next = word(s, k + 1);
            if !noun_like(t)
                || t.surface.starts_with(char::is_uppercase)
                || NUMBERLESS.contains(&w)
                || MASS.contains(&w)
                || UNITS.contains(&w) && (!unit_ends || word(s, k + 1).is_empty() && s.get(k + 1).is_some_and(|n| n.surface == ","))
                // "a six cylinder, water-cooled engine": a list of modifiers.
                || numeral && s.get(k + 1).is_some_and(|n| n.surface == ",")
                // "many feel that", "several minor to moderate injuries".
                || crate::spelling::flags(w) & 4 != 0 && ["that", "it", "the", "a", "this", "them"].contains(&next)
                || crate::spelling::flags(w) & 8 != 0 && ["to", "and", "or"].contains(&next)
                || crate::spelling::flags(w) & 16 != 0
                || crate::spelling::flags(w) & 4 != 0 && t.pos != "Noun"
                || !phrase_end(req, s, k)
            {
                continue;
            }
            // "too many food" wants "much": the plural must be the usual phrase.
            if let Some(p) = plural_of(w)
                && (numeral
                    || crate::context::count("many", &p) >= 2 * crate::context::count("much", w))
            {
                fix(
                    edits,
                    k,
                    p,
                    "Use the plural noun after a word for more than one.",
                );
            }
            continue;
        }
        // "each students", "every parts".
        if ["each", "every"].contains(&q) {
            let Some(t) = s.get(k) else { continue };
            let w = t.normalized.as_str();
            if !noun_like(t)
                || t.surface.starts_with(char::is_uppercase)
                || [
                    "others",
                    "news",
                    "series",
                    "species",
                    "means",
                    "sports",
                    "thanks",
                    "times",
                    "clothes",
                    "glasses",
                    "pants",
                    "jeans",
                    "scissors",
                    "goods",
                    "arms",
                    "savings",
                    "headquarters",
                    "premises",
                ]
                .contains(&w)
                || !phrase_end(req, s, k)
            {
                continue;
            }
            if let Some(one) = singular_of(w) {
                fix(edits, k, one, "“Each” and “every” take a singular noun.");
            }
            continue;
        }
        // "one of the best player".
        // "phase one of the project", "reminds one of the sea": no "one of" a group.
        if q == "one"
            && word(s, i + 1) == "of"
            && POSSESSIVE.contains(&word(s, i + 2))
            && !(i > 0
                && (noun_like(&s[i - 1])
                    || s[i - 1].surface.starts_with(char::is_uppercase)
                    || ["remind", "reminds", "reminded", "reminding"].contains(&word(s, i - 1))))
        {
            k = i + 3;
            while s.get(k).is_some_and(|t| {
                t.pos == "Adjective"
                    || [
                        "most", "best", "worst", "biggest", "largest", "greatest", "main", "few",
                    ]
                    .contains(&t.normalized.as_str())
            }) && s.get(k + 1).is_some_and(|t| t.is_word)
                && k < i + 6
            {
                k += 1;
            }
            let Some(t) = s.get(k) else { continue };
            let w = t.normalized.as_str();
            if !noun_like(t)
                || t.surface.starts_with(char::is_uppercase)
                || NUMBERLESS.contains(&w)
                || MASS.contains(&w)
                || crate::spelling::flags(w) & 16 != 0
                || !phrase_end(req, s, k)
            {
                continue;
            }
            if let Some(p) = plural_of(w) {
                fix(edits, k, p, "After “one of the”, use the plural noun.");
            }
        }
    }
}

/// Nouns that name a group and may take a plural verb in British English ("the team have").
const COLLECTIVE: &[&str] = &[
    "theatre",
    "theater",
    "school",
    "university",
    "college",
    "hospital",
    "church",
    "city",
    "country",
    "nation",
    "state",
    "world",
    "industry",
    "community",
    "press",
    "following",
    "family",
    "team",
    "government",
    "company",
    "staff",
    "police",
    "group",
    "crowd",
    "public",
    "band",
    "club",
    "committee",
    "council",
    "party",
    "board",
    "army",
    "navy",
    "crew",
    "audience",
    "class",
    "jury",
    "couple",
    "majority",
    "minority",
    "number",
    "rest",
    "total",
    "management",
    "union",
    "firm",
    "office",
    "department",
    "ministry",
    "parliament",
    "congress",
    "senate",
    "cabinet",
    "squad",
    "side",
    "media",
    "data",
    "lot",
    "half",
    "variety",
    "series",
    "pair",
];
/// Pronouns that take a singular verb.
const SINGULAR_PRONOUNS: &[&str] = &[
    "everyone",
    "everybody",
    "someone",
    "somebody",
    "nobody",
    "anyone",
    "anybody",
    "everything",
    "something",
    "nothing",
    "anything",
];
/// Verbs whose "-s" form is no common noun, so "is depends" can only be a stray "is".
const S_VERBS: &[&str] = &[
    "depends",
    "seems",
    "belongs",
    "consists",
    "exists",
    "contains",
    "includes",
    "requires",
    "provides",
    "allows",
    "becomes",
    "remains",
    "happens",
    "involves",
    "refers",
    "relies",
    "occurs",
    "applies",
    "affects",
    "appears",
    "deserves",
    "describes",
    "explains",
];
/// "My father have a car", "Everyone have", "Computers is useful", "there is problems", "is
/// depends on": a clear subject and the helping verb after it disagree.
fn agreement(req: &Request, s: &[Token<'_>], edits: &mut Vec<Edit>) {
    let fix = |edits: &mut Vec<Edit>, k: usize, r: &str, id: &str, why: &str| {
        push(
            req,
            edits,
            span(s, k, k),
            crate::match_case(r, s[k].surface),
            id,
            why,
            0.94,
        );
    };
    // "requires that an organization have": the subjunctive keeps the bare verb.
    let mandative = |i: usize| {
        i >= 2
            && word(s, i - 1) == "that"
            && [
                "require",
                "requires",
                "required",
                "suggest",
                "suggests",
                "suggested",
                "recommend",
                "recommends",
                "recommended",
                "insist",
                "insists",
                "insisted",
                "demand",
                "demands",
                "demanded",
                "ask",
                "asks",
                "asked",
                "propose",
                "proposed",
                "important",
                "essential",
                "necessary",
                "vital",
                "crucial",
                "request",
                "requested",
                "urge",
                "urged",
            ]
            .contains(&word(s, i - 2))
    };
    for i in 0..s.len().saturating_sub(1) {
        let w = word(s, i);
        if mandative(i) {
            continue;
        }
        // A determiner and one singular noun at the start of a clause, then "have".
        let det = [
            "the", "my", "your", "his", "her", "its", "our", "their", "this", "that", "each",
            "every", "a", "an",
        ]
        .contains(&w)
            && crate::clause_repairs::clause_start(s, i)
            && !(i > 0 && ["and", "or", "nor", "both"].contains(&word(s, i - 1)));
        if det
            && let Some(n) = s.get(i + 1)
            && noun_like(n)
            && (n.pos == "Noun"
                || n.pos.is_empty() && crate::spelling::flags(&n.normalized) & 4 == 0)
            && crate::spelling::flags(&n.normalized) & 16 == 0
            && !n.normalized.ends_with('s')
            && plural_of(&n.normalized).is_some()
            && !COLLECTIVE.contains(&n.normalized.as_str())
            && !NUMBERLESS.contains(&n.normalized.as_str())
            && word(s, i + 2) == "have"
            && !req.text[n.end_byte..].starts_with(['\'', '’', '-'])
        {
            fix(
                edits,
                i + 2,
                "has",
                "grammar.subject_have",
                "Use “has” with a singular subject.",
            );
            continue;
        }
        // "Everyone have", "Nobody have".
        if SINGULAR_PRONOUNS.contains(&w)
            && crate::clause_repairs::clause_start(s, i)
            && word(s, i + 1) == "have"
            && word(s, i + 2) != "to"
        {
            fix(
                edits,
                i + 1,
                "has",
                "grammar.subject_have",
                "Use “has” with a singular subject.",
            );
            continue;
        }
        // A plural noun opening the sentence ("Computers is", "Such clothes is").
        let lead = match (i, w) {
            (0, "such" | "most" | "many" | "several" | "both" | "few") => Some(1),
            (0, _) => Some(0),
            _ => None,
        };
        if let Some(lead) = lead
            // "AIDS is": an acronym may be one thing.
            && s.get(lead).is_some_and(|n| {
                noun_like(n)
                    && (lead > 0 || n.pos == "Noun")
                    && n.surface.chars().skip(1).all(char::is_lowercase)
            })
        {
            let n = &s[lead];
            let nw = n.normalized.as_str();
            let verb = word(s, lead + 1);
            if crate::spelling::flags(nw) & 16 != 0
                && singular_of(nw).is_some()
                && !nw.ends_with("ics")
                && !MASS.contains(&nw)
                && !COLLECTIVE.contains(&nw)
                && ![
                    "news", "series", "species", "means", "measles", "lots", "thanks",
                ]
                .contains(&nw)
                && ["is", "was", "has"].contains(&verb)
            {
                let r = match verb {
                    "is" => "are",
                    "was" => "were",
                    _ => "have",
                };
                fix(
                    edits,
                    lead + 1,
                    r,
                    "grammar.subject_copula",
                    "Match the verb to its plural subject.",
                );
                continue;
            }
        }
        // "There is problems": a bare plural noun after "there is".
        if w == "there"
            && ["is", "was"].contains(&word(s, i + 1))
            && let Some(n) = s.get(i + 2)
            && noun_like(n)
            && crate::spelling::flags(&n.normalized) & 16 != 0
            && singular_of(&n.normalized).is_some()
            && !MASS.contains(&n.normalized.as_str())
            && !COLLECTIVE.contains(&n.normalized.as_str())
            && ![
                "news", "series", "species", "means", "lots", "thanks", "politics",
            ]
            .contains(&n.normalized.as_str())
        {
            let r = if word(s, i + 1) == "is" {
                "are"
            } else {
                "were"
            };
            fix(
                edits,
                i + 1,
                r,
                "grammar.there_agreement",
                "After “there”, the verb agrees with the noun that follows.",
            );
            continue;
        }
        // "It is depends on": a stray "be" before a verb in "-s".
        if ["is", "are", "am"].contains(&w)
            && i > 0
            && S_VERBS.contains(&word(s, i + 1))
            && [
                "on", "to", "that", "the", "a", "an", "in", "like", "it", "me", "you", "us",
                "them", "him", "her", "my", "your", "our", "their", "his", "its", "upon",
            ]
            .contains(&word(s, i + 2))
            && !["there", "here", "what", "which"].contains(&word(s, i - 1))
        {
            push(
                req,
                edits,
                (s[i - 1].end_utf16, s[i].end_utf16),
                String::new(),
                "grammar.extra_be",
                "This “be” does not belong before the verb.",
                0.94,
            );
        }
    }
}
/// Adjectives a writer often leaves without "-ly" before a verb ("was original built").
const ADVERB_STEMS: &[&str] = &[
    "easy",
    "simple",
    "quick",
    "careful",
    "original",
    "current",
    "recent",
    "previous",
    "final",
    "actual",
    "usual",
    "general",
    "typical",
    "initial",
    "absolute",
    "entire",
    "exact",
    "slight",
    "significant",
    "successful",
    "automatic",
    "basic",
    "specific",
    "primary",
    "frequent",
    "extreme",
    "relative",
    "incredible",
    "reasonable",
    "particular",
    "possible",
    "proper",
    "correct",
    "official",
    "eventual",
    "subsequent",
    "mere",
    "sole",
    "main",
    "real",
];
fn adverb_of(adj: &str) -> Option<String> {
    let adv = if let Some(stem) = adj.strip_suffix('y') {
        format!("{stem}ily")
    } else if let Some(stem) = adj.strip_suffix("le") {
        format!("{stem}ly")
    } else if adj.ends_with("ic") {
        format!("{adj}ally")
    } else {
        format!("{adj}ly")
    };
    crate::spelling::known(&adv).then_some(adv)
}
/// "dependant on", "world renown", "I am interesting in", "can easy find", "was original built":
/// the word's form, not its meaning, is wrong.
fn word_form(req: &Request, s: &[Token<'_>], edits: &mut Vec<Edit>) {
    let fix = |edits: &mut Vec<Edit>, k: usize, r: String, id: &str, why: &str| {
        push(
            req,
            edits,
            span(s, k, k),
            crate::match_case(&r, s[k].surface),
            id,
            why,
            0.94,
        );
    };
    for i in 0..s.len() {
        let w = word(s, i);
        let next = word(s, i + 1);
        let prev = if i > 0 { word(s, i - 1) } else { "" };
        if w == "dependant" && ["on", "upon"].contains(&next) {
            fix(
                edits,
                i,
                "dependent".into(),
                "grammar.word_form",
                "The adjective is “dependent”; a “dependant” is a person.",
            );
            continue;
        }
        // "whose renown for dubbing" is the noun.
        if w == "renown"
            && ![
                "whose",
                "his",
                "her",
                "their",
                "its",
                "our",
                "my",
                "your",
                "the",
                "of",
                "great",
                "international",
                "worldwide",
                "much",
                "some",
            ]
            .contains(&prev)
            // "gain renown for" is the noun: only after "be" or a degree word.
            && [
                "world", "internationally", "highly", "well", "widely", "is", "was", "are", "were",
                "be", "been", "become", "became",
            ]
            .contains(&prev)
        {
            fix(
                edits,
                i,
                "renowned".into(),
                "grammar.word_form",
                "Use the adjective “renowned”.",
            );
            continue;
        }
        // "I am interesting in", "We were exciting about": the feeling takes "-ed".
        if [
            "interesting",
            "exciting",
            "boring",
            "confusing",
            "tiring",
            "disappointing",
            "frightening",
            "worrying",
            "embarrassing",
        ]
        .contains(&w)
            && ["in", "about", "with", "by", "to", "that", "for"].contains(&next)
        {
            let mut k = i - usize::from(i > 0);
            if [
                "very",
                "really",
                "so",
                "quite",
                "more",
                "most",
                "too",
                "extremely",
                "not",
            ]
            .contains(&word(s, k))
                && k > 0
            {
                k -= 1;
            }
            let be = word(s, k);
            let subject = if k > 0 { word(s, k - 1) } else { "" };
            if (["am", "'m"].contains(&be) || ["i'm", "we're"].contains(&be))
                || ["was", "were", "are", "felt", "feel", "get", "got", "became"].contains(&be)
                    && ["i", "we"].contains(&subject)
            {
                let ed = morphology::verb(w).map_or_else(
                    || format!("{}ed", w.strip_suffix("ing").unwrap_or(w)),
                    |v| v.participle,
                );
                if crate::spelling::known(&ed) {
                    fix(
                        edits,
                        i,
                        ed,
                        "grammar.participle_adjective",
                        "A feeling takes the “-ed” form: “interested”, “excited”.",
                    );
                }
                continue;
            }
        }
        // "can easy find", "was original built", "is current being": an adjective between a
        // helping verb and its verb is the adverb.
        if ADVERB_STEMS.contains(&w)
            && [
                "can", "could", "will", "would", "should", "must", "may", "might", "to", "is",
                "are", "was", "were", "be", "been", "has", "have", "had",
            ]
            .contains(&prev)
            && let Some(t) = s.get(i + 1)
            && (t.pos == "Verb" || t.pos.is_empty() && crate::spelling::flags(next) & 4 != 0)
            && let Some(v) = morphology::verb(next)
        {
            let modal = [
                "can", "could", "will", "would", "should", "must", "may", "might", "to",
            ]
            .contains(&prev);
            // "would be easy talking to her" keeps the adjective before a gerund.
            let fits = if modal {
                next == v.base
            } else {
                next == v.participle && next != v.gerund
            };
            if fits && let Some(adv) = adverb_of(w) {
                fix(
                    edits,
                    i,
                    adv,
                    "grammar.adverb_form",
                    "Use the adverb to describe the verb.",
                );
            }
        }
    }
}
/// Verbs that take an object and then "in" ("put it in the box").
pub(crate) const PUT_IN: &[&str] = &[
    "put", "puts", "putting", "plug", "plugged", "fill", "filled", "turn", "turned", "hand",
    "handed", "bring", "brought", "send", "sent", "type", "typed", "drop", "dropped", "pop",
    "popped", "stick", "throw", "toss", "add", "added", "paste", "pasted", "copy", "copied",
    "move", "moved", "save", "saved", "leave", "left", "set", "keep", "kept", "lock", "locked",
    "factor", "mix", "load", "loaded", "write", "wrote", "pass", "passed", "feed", "fed",
];
/// Word slips that only one reading of the clause fits: "put in in the model" ("it in"), "let me
/// no", "is of today", "borrow me your pen", "It just the part", "Each of the reports need", "as
/// well costs", "Worse case".
fn slips(req: &Request, s: &[Token<'_>], edits: &mut Vec<Edit>) {
    let fix = |edits: &mut Vec<Edit>, k: usize, r: &str, id: &str, why: &str| {
        push(
            req,
            edits,
            span(s, k, k),
            crate::match_case(r, s[k].surface),
            id,
            why,
            0.93,
        );
    };
    for i in 0..s.len() {
        let w = word(s, i);
        let next = word(s, i + 1);
        let prev = if i > 0 { word(s, i - 1) } else { "" };
        // "Just put in in the model": the first "in" is a slip for "it".
        // "should be put in in the box" is a passive: no "it".
        if w == "in"
            && next == "in"
            && PUT_IN.contains(&prev)
            && !(i >= 2
                && [
                    "be", "been", "being", "is", "are", "was", "were", "get", "got",
                ]
                .contains(&word(s, i - 2)))
        {
            fix(edits, i, "it", "grammar.it_in", "Did you mean “it in”?");
            continue;
        }
        // "We all of us already have": the pronoun is said twice; "We, all of us," with commas
        // is an aside and stays.
        if let Some(object) = match w {
            "we" => Some("us"),
            "you" => Some("you"),
            "they" => Some("them"),
            _ => None,
        } && ["all", "both", "each"].contains(&next)
            && word(s, i + 2) == "of"
            && word(s, i + 3) == object
            && s.get(i + 4).is_some_and(|t| t.is_word)
            // "Thank you all of you" has "you" as an object: only a subject counts.
            && (w != "you" || crate::clause_repairs::clause_start(s, i))
        {
            push(
                req,
                edits,
                (s[i + 1].end_utf16, s[i + 3].end_utf16),
                String::new(),
                "grammar.pronoun_twice",
                "The pronoun is already the subject: “we all”, not “we all of us”.",
                0.95,
            );
            continue;
        }
        // "let me no your thoughts", "I don't no": the verb "know".
        if w == "no"
            && (["me", "us"].contains(&prev) && i >= 2 && word(s, i - 2) == "let"
                || ["don't", "didn't", "doesn't", "dont", "didnt"].contains(&prev))
            && ![
                "longer", "more", "less", "one", "doubt", "matter", "way", "problem", "thanks",
            ]
            .contains(&next)
        {
            fix(edits, i, "know", "grammar.no_know", "Did you mean “know”?");
            continue;
        }
        // "The meeting is of today": "off".
        if w == "of"
            && [
                "is", "are", "was", "were", "be", "am", "i'm", "it's", "he's", "she's", "we're",
                "they're",
            ]
            .contains(&prev)
            && ["today", "tomorrow", "tonight", "work", "duty", "sick"].contains(&next)
            && s.get(i + 2).is_none_or(|t| {
                !t.is_word
                    || ["and", "but", "so", "because", "for"].contains(&t.normalized.as_str())
            })
        {
            fix(edits, i, "off", "grammar.of_off", "Did you mean “off”?");
            continue;
        }
        // "Can you borrow me your pen?": you lend something to someone.
        if w == "borrow" && ["me", "us", "him", "her", "them"].contains(&next) {
            fix(
                edits,
                i,
                "lend",
                "grammar.lend_borrow",
                "You lend something to someone; you borrow it from them.",
            );
            continue;
        }
        // "It just the part I need": "it's".
        if (w == "it" && crate::clause_repairs::clause_start(s, i) || w == "that" && i == 0)
            && [
                "just",
                "only",
                "also",
                "still",
                "really",
                "definitely",
                "probably",
                "actually",
            ]
            .contains(&next)
            && [
                "the", "a", "an", "my", "your", "our", "their", "his", "her", "not",
            ]
            .contains(&word(s, i + 2))
        {
            fix(
                edits,
                i,
                if w == "it" { "it's" } else { "that's" },
                "grammar.missing_copula",
                "A form of “be” looks missing here.",
            );
            continue;
        }
        // "Each of the reports need": the verb agrees with "each".
        if ["each", "one", "neither", "either"].contains(&w)
            && crate::clause_repairs::clause_start(s, i)
            && next == "of"
            && [
                "the", "these", "those", "my", "your", "our", "their", "his", "her", "them", "us",
            ]
            .contains(&word(s, i + 2))
        {
            let mut k = i + 3;
            if word(s, i + 2) != "them" && word(s, i + 2) != "us" {
                while s.get(k).is_some_and(|t| t.pos == "Adjective") && k < i + 5 {
                    k += 1;
                }
                if !s
                    .get(k)
                    .is_some_and(|t| t.is_word && crate::spelling::flags(&t.normalized) & 16 != 0)
                {
                    continue;
                }
                k += 1;
            }
            let v = word(s, k);
            let r = match v {
                "have" => Some("has".to_owned()),
                "are" => Some("is".to_owned()),
                "were" => Some("was".to_owned()),
                "do" => Some("does".to_owned()),
                "don't" => Some("doesn't".to_owned()),
                _ => morphology::verb(v)
                    .filter(|x| {
                        x.base == v
                            && x.third != v
                            && crate::spelling::flags(v) & 4 != 0
                            && morphology::predicate(&x.base)
                    })
                    .map(|x| x.third),
            };
            if let Some(r) = r {
                fix(
                    edits,
                    k,
                    &r,
                    "grammar.each_of_agreement",
                    "After “each of” or “one of”, the verb is singular.",
                );
            }
            continue;
        }
        // "as well costs": "as well as".
        if w == "well"
            && prev == "as"
            && !(i >= 2 && ["may", "might", "could", "just"].contains(&word(s, i - 2)))
            && s.get(i + 1).is_some_and(|t| {
                [
                    "the", "a", "an", "my", "your", "our", "their", "his", "her", "its", "this",
                    "these", "those", "some", "other",
                ]
                .contains(&t.normalized.as_str())
                    || t.pos == "Noun" && crate::spelling::flags(&t.normalized) & 16 != 0
            })
        {
            push(
                req,
                edits,
                (s[i].end_utf16, s[i].end_utf16),
                " as".into(),
                "grammar.as_well_as",
                "Did you mean “as well as”?",
                0.93,
            );
            continue;
        }
        // "Worse case scenario", "In the worse case,": "worst".
        if w == "worse"
            && next == "case"
            && (word(s, i + 2) == "scenario"
                || s.get(i + 2)
                    .is_some_and(|t| [",", ":"].contains(&t.surface))
                    && (i == 0 || ["the", "in"].contains(&prev)))
        {
            fix(
                edits,
                i,
                "worst",
                "grammar.worst_case",
                "The phrase is “worst case”.",
            );
        }
    }
}
