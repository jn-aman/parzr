//! Whole-word edits for rewrites: a suggestion never cuts a word in two ("hat" to "t").
use crate::{Edit, TextRange};

fn apostrophe(c: char) -> bool {
    c == '\'' || c == '’'
}
/// A letter, digit or apostrophe: a character that can sit inside a word.
fn wordish(c: char) -> bool {
    c.is_alphanumeric() || apostrophe(c)
}

/// Expands every edit to whole words of both the source and the rewritten text, then merges
/// edits that overlap; with `join_spaces` also edits that touch or are separated only by spaces
/// or tabs (never a line break), so a rewritten phrase is one edit. Widening never enters
/// protected text. Applying the result to `source` gives the same text as `edits`.
pub(crate) fn whole_words(
    source: &str,
    edits: Vec<Edit>,
    protected: &[TextRange],
    join_spaces: bool,
) -> Vec<Edit> {
    let chars: Vec<char> = source.chars().collect();
    let n = chars.len();
    let mut units = Vec::with_capacity(n + 1);
    let mut sum = 0;
    for c in &chars {
        units.push(sum);
        sum += c.len_utf16();
    }
    units.push(sum);
    let index = |x: usize| units.binary_search(&x).ok();
    let Some(ranges) = edits
        .iter()
        .map(|e| Some((index(e.start_utf16)?, index(e.end_utf16)?)))
        .collect::<Option<Vec<_>>>()
    else {
        return edits;
    };
    let blocked = |i: usize| {
        protected
            .iter()
            .any(|p| units[i] >= p.start_utf16 && units[i] < p.end_utf16)
    };
    // Inside a source word: a letter or digit, or an apostrophe between two of them.
    let inner = |i: usize| {
        chars[i].is_alphanumeric()
            || (apostrophe(chars[i])
                && i > 0
                && i + 1 < n
                && chars[i - 1].is_alphanumeric()
                && chars[i + 1].is_alphanumeric())
    };
    // (start, end, first member, one past last member), in source characters.
    let mut groups: Vec<(usize, usize, usize, usize)> = vec![];
    for (k, (e, &(mut s, mut t))) in edits.iter().zip(&ranges).enumerate() {
        // The word left of the edit continues into it, in the source or in the rewrite.
        if s > 0 && wordish(chars[s - 1]) {
            let source_first = if s < t { chars.get(s) } else { chars.get(t) };
            let output_first = e.replacement.chars().next().or(chars.get(t).copied());
            if source_first.is_some_and(|c| wordish(*c)) || output_first.is_some_and(wordish) {
                while s > 0 && !blocked(s - 1) && inner(s - 1) {
                    s -= 1;
                }
            }
        }
        if t < n && wordish(chars[t]) {
            let source_last = if s < t {
                Some(chars[t - 1])
            } else {
                s.checked_sub(1).map(|i| chars[i])
            };
            let output_last = e
                .replacement
                .chars()
                .next_back()
                .or_else(|| s.checked_sub(1).map(|i| chars[i]));
            if source_last.is_some_and(wordish) || output_last.is_some_and(wordish) {
                while t < n && !blocked(t) && inner(t) {
                    t += 1;
                }
            }
        }
        let joins = |g: &(usize, usize, usize, usize)| {
            s < g.1
                || (join_spaces
                    && chars[g.1..s].iter().all(|c| *c == ' ' || *c == '\t')
                    && !(g.1..s).any(blocked))
        };
        match groups.last_mut() {
            Some(g) if joins(g) => {
                g.0 = g.0.min(s);
                g.1 = g.1.max(t);
                g.3 = k + 1;
            }
            _ => groups.push((s, t, k, k + 1)),
        }
    }
    let mut result: Vec<Edit> = vec![];
    for (s, t, a, b) in groups {
        let mut replacement = String::new();
        let mut cursor = s;
        for (e, &(cs, ce)) in edits[a..b].iter().zip(&ranges[a..b]) {
            replacement.extend(&chars[cursor..cs]);
            replacement.push_str(&e.replacement);
            cursor = ce;
        }
        replacement.extend(&chars[cursor..t]);
        let original: String = chars[s..t].iter().collect();
        if original == replacement {
            continue;
        }
        let members = &edits[a..b];
        let mut edit = members[0].clone();
        let mut reasons: Vec<&str> = vec![];
        let mut ids: Vec<&str> = vec![];
        for m in members {
            if !reasons.contains(&m.explanation.as_str()) {
                reasons.push(&m.explanation);
            }
            for id in m.rule_id.split('+') {
                if !ids.contains(&id) {
                    ids.push(id);
                }
            }
        }
        edit.explanation = reasons.join(" ");
        edit.rule_id = ids.join("+");
        edit.confidence = members.iter().map(|m| m.confidence).fold(1.0, f32::min);
        edit.group_id = members.iter().find_map(|m| m.group_id.clone());
        edit.start_utf16 = units[s];
        edit.end_utf16 = units[t];
        edit.original = original;
        edit.replacement = replacement;
        result.push(edit);
    }
    // A link between two edits that are now one, or whose partner merged elsewhere, is gone.
    let count = |g: &String| {
        result
            .iter()
            .filter(|e| e.group_id.as_ref() == Some(g))
            .count()
    };
    let lone: Vec<String> = result
        .iter()
        .filter_map(|e| e.group_id.clone())
        .filter(|g| count(g) != 2)
        .collect();
    for e in &mut result {
        if e.group_id.as_ref().is_some_and(|g| lone.contains(g)) {
            e.group_id = None;
        }
    }
    result
}

/// A rewrite that deletes the words before a kept one ("Could you review" to "Review") is two
/// edits, so the kept word's own text run (bold, a link) survives the replacement.
pub(crate) fn keep_anchor(all: Vec<Edit>) -> Vec<Edit> {
    let mut out = Vec::with_capacity(all.len());
    for mut e in all {
        let split = e
            .original
            .rfind(char::is_whitespace)
            .map(|i| i + e.original[i..].chars().next().map_or(1, char::len_utf8));
        match split {
            Some(split)
                if split < e.original.len()
                    && e.original[split..].to_lowercase() == e.replacement.to_lowercase() =>
            {
                let tail = e.original.split_off(split);
                let middle = e.start_utf16 + e.original.encode_utf16().count();
                let mut word = e.clone();
                e.end_utf16 = middle;
                e.replacement = String::new();
                word.start_utf16 = middle;
                word.original = tail;
                let changed = word.original != word.replacement;
                out.push(e);
                if changed {
                    out.push(word);
                }
            }
            _ => out.push(e),
        }
    }
    out
}

/// The edits of a rewrite as the card shows them: whole words, neighbouring words joined into
/// one phrase ("I hat it" to "It is"), a kept word's own text run left in place.
pub(crate) fn phrases(source: &str, edits: Vec<Edit>, protected: &[TextRange]) -> Vec<Edit> {
    keep_anchor(whole_words(source, edits, protected, true))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::apply_edits;
    use similar::{ChangeTag, TextDiff};

    /// Raw character edits from a diff, the way a model rewrite arrives before widening.
    fn raw(a: &str, b: &str) -> Vec<Edit> {
        let mut out = vec![];
        let (mut offset, mut original, mut replacement) = (0, String::new(), String::new());
        let mut flush = |offset: &mut usize, o: &mut String, r: &mut String| {
            if o.is_empty() && r.is_empty() {
                return;
            }
            let end = *offset + o.encode_utf16().count();
            out.push(Edit {
                start_utf16: *offset,
                end_utf16: end,
                original: std::mem::take(o),
                replacement: std::mem::take(r),
                category: "Style".into(),
                rule_id: "local-model".into(),
                explanation: "Suggested rewrite".into(),
                confidence: 1.0,
                group_id: None,
            });
            *offset = end;
        };
        for change in TextDiff::from_chars(a, b).iter_all_changes() {
            match change.tag() {
                ChangeTag::Delete => original.push_str(change.value()),
                ChangeTag::Insert => replacement.push_str(change.value()),
                ChangeTag::Equal => {
                    flush(&mut offset, &mut original, &mut replacement);
                    offset += change.value().encode_utf16().count();
                }
            }
        }
        flush(&mut offset, &mut original, &mut replacement);
        out
    }
    fn pairs(a: &str, b: &str, join: bool) -> Vec<(String, String)> {
        let edits = whole_words(a, raw(a, b), &[], join);
        assert_eq!(apply_edits(a, &edits).unwrap().0, b, "{a} -> {b}");
        edits
            .into_iter()
            .map(|e| (e.original, e.replacement))
            .collect()
    }
    fn p(a: &str, b: &str) -> (String, String) {
        (a.into(), b.into())
    }

    #[test]
    fn a_fragment_becomes_the_whole_word() {
        assert_eq!(
            pairs(
                "This is so bad. I hat it.",
                "This is so bad. I hate it.",
                true
            ),
            [p("hat", "hate")]
        );
        // The owner's report: never "hat" to "t" with "I" struck through; the phrase is one edit.
        assert_eq!(
            pairs("This is so bad. I hat it.", "This is so bad. It is.", true),
            [p("I hat it", "It is")]
        );
        assert_eq!(pairs("I am here", "I'm here", false), [p("I am", "I'm")]);
    }

    #[test]
    fn separate_words_stay_separate_without_joining() {
        assert_eq!(
            pairs(
                "pls send teh doc asap",
                "please send the document soon",
                false
            ),
            [
                p("pls", "please"),
                p("teh", "the"),
                p("doc", "document"),
                p("asap", "soon")
            ]
        );
        assert_eq!(
            pairs(
                "pls send teh doc asap",
                "please send the document soon",
                true
            ),
            [p("pls", "please"), p("teh doc asap", "the document soon")]
        );
    }

    #[test]
    fn lines_and_punctuation_are_not_joined() {
        assert_eq!(
            pairs("hi there\nok thx", "Hi there\nOK thanks", true),
            [p("hi", "Hi"), p("ok thx", "OK thanks")]
        );
        assert_eq!(pairs("so bad", "so bad!", true), [p("", "!")]);
    }

    #[test]
    fn widening_stops_at_protected_text() {
        let protected = [TextRange {
            start_utf16: 0,
            end_utf16: 4,
        }];
        let edits = whole_words("Mira42 ok", raw("Mira42 ok", "Mira43 ok"), &protected, true);
        assert_eq!(edits[0].original, "42");
        assert_eq!(edits[0].replacement, "43");
    }

    #[test]
    fn a_link_inside_one_merged_edit_is_dropped() {
        let text = "a b";
        let mut edits = raw(text, "x y");
        for e in &mut edits {
            e.group_id = Some("move".into());
        }
        let merged = whole_words(text, edits, &[], true);
        assert_eq!(merged.len(), 1);
        assert_eq!(merged[0].group_id, None);
    }
}
