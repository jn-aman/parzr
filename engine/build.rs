//! Builds the engine's static lookup tables from the attributed JSON data in `rules/` (see
//! `src/table.rs` for the format) into one file, `parzr-tables.dat` in OUT_DIR. Run time then reads them in place: no JSON parsing, no
//! per-word allocations, and the pages stay clean (a keyboard extension's memory limit is about
//! 60-70 MB; the old run-time maps peaked over 100 MB).
//!
//! The construction mirrors what `spelling.rs` and `context.rs` built at first use, entry for
//! entry, so every lookup answers exactly as before.
use std::collections::{HashMap, HashSet};
use std::{env, fs, path::Path};

#[allow(dead_code)]
#[path = "src/rules/literals.rs"]
mod literals;
#[allow(dead_code)]
#[path = "src/table.rs"]
mod table;

fn main() {
    println!("cargo:rerun-if-changed=rules/packs");
    for file in [
        "rules/grammar.json",
        "rules/tone.json",
        "rules/usage.json",
        "src/rules/literals.rs",
        "rules/lexicon.json",
        "rules/frequency.json",
        "rules/bigrams.json",
        "src/table.rs",
    ] {
        println!("cargo:rerun-if-changed={file}");
    }
    let out = env::var("OUT_DIR").expect("OUT_DIR");
    let out = Path::new(&out);
    rule_packs(out);
    let frequencies = frequencies();
    let frequency = write(
        frequencies
            .iter()
            .map(|(k, v)| (k.clone(), u32::from(*v).to_le_bytes().to_vec())),
        4,
        &[],
        &[],
    );
    let (lexicon, deletes) = lexicon(&frequencies);
    // One file, `tables::FILE_NAME`: embedded by default, shipped once in the Mac app's
    // Resources with the `external-tables` feature. Its hash and length are compiled into the
    // engine, which accepts only the exact file it was built with.
    let tables = table::bundle(&[&lexicon, &deletes, &frequency, &bigrams()]);
    fs::write(out.join("parzr-tables.dat"), &tables).unwrap();
    fs::write(
        out.join("tables_meta.rs"),
        format!(
            "pub(crate) const TABLES_HASH: u64 = {:#018x};\npub(crate) const TABLES_LEN: usize = {};\n",
            table::hash(&tables),
            tables.len()
        ),
    )
    .unwrap();
}

fn read(path: &str) -> serde_json::Value {
    let text = fs::read_to_string(path).unwrap_or_else(|e| panic!("{path}: {e}"));
    serde_json::from_str(&text).unwrap_or_else(|e| panic!("{path}: {e}"))
}

/// `rules/frequency.json`: word to frequency prior. A later duplicate wins, as when the engine
/// collected the entries into a map.
fn frequencies() -> HashMap<String, u16> {
    let prior = read("rules/frequency.json");
    assert_eq!(prior["metadata"]["license"], "CC-BY-SA-4.0");
    let mut map = HashMap::new();
    for entry in prior["entries"].as_array().expect("frequency entries") {
        let word = entry[0].as_str().expect("frequency word").to_string();
        let value =
            u16::try_from(entry[1].as_u64().expect("frequency value")).expect("u16 frequency");
        map.insert(word, value);
    }
    map
}

/// `rules/bigrams.json`: "a b" to count, a later duplicate winning.
fn bigrams() -> Vec<u8> {
    let data = read("rules/bigrams.json");
    assert!(
        data["metadata"]["source_sha256"]
            .as_str()
            .is_some_and(|s| s.len() == 64),
        "valid attributed word pairs"
    );
    let mut map: HashMap<String, u64> = HashMap::new();
    for entry in data["entries"].as_array().expect("word pairs") {
        map.insert(
            entry[0].as_str().expect("pair").to_string(),
            entry[1].as_u64().expect("pair count"),
        );
    }
    write(
        map.into_iter().map(|(k, v)| (k, v.to_le_bytes().to_vec())),
        8,
        &[],
        &[],
    )
}

/// The lexicon table (lowercase word: flags, ordinary-lowercase bit, canonical casing) and the
/// deletion index (a word with one byte deleted: the common words it comes from, sorted).
fn lexicon(frequencies: &HashMap<String, u16>) -> (Vec<u8>, Vec<u8>) {
    let frequency = |w: &str| frequencies.get(w).copied().unwrap_or(0);
    let data = read("rules/lexicon.json");
    let mut words: HashMap<String, u8> = HashMap::new();
    let mut lowercase: HashSet<String> = HashSet::new();
    let mut canonical: HashMap<String, String> = HashMap::new();
    for entry in data.as_array().expect("lexicon entries") {
        let word = entry[0].as_str().expect("lexicon word").to_string();
        let flags = u8::try_from(entry[1].as_u64().expect("lexicon flags")).expect("u8 flags");
        let lower = word.to_lowercase();
        if word == lower {
            lowercase.insert(word.clone());
        } else if word.chars().skip(1).any(char::is_uppercase)
            && word.chars().any(char::is_lowercase)
        {
            // Mixed case beyond a first capital ("McDonald", "iPhone"), not "Rahul" or "NASA".
            // The spelling with the most capitals wins ("McDonald" over "Mcdonald").
            let capitals = |w: &str| w.chars().filter(|c| c.is_uppercase()).count();
            let better = canonical
                .get(&lower)
                .is_none_or(|old| capitals(&word) > capitals(old));
            if better {
                canonical.insert(lower.clone(), word.clone());
            }
        }
        *words.entry(lower).or_insert(0) |= flags;
    }
    canonical.retain(|lower, _| !lowercase.contains(lower));

    let mut deletes: HashMap<String, Vec<String>> = HashMap::new();
    // Index common words only for suggestions; all words remain valid dictionary entries.
    for (word, flags) in &words {
        let common_form = flags & 1 != 0
            || frequency(word) >= 250
            || ["s", "es", "ed", "ing"].iter().any(|suffix| {
                word.strip_suffix(suffix).is_some_and(|stem| {
                    words.get(stem).is_some_and(|f| f & 1 != 0)
                        || words.get(&format!("{stem}e")).is_some_and(|f| f & 1 != 0)
                })
            });
        if !common_form || word.len() > 24 || !word.bytes().all(|b| b.is_ascii_lowercase()) {
            continue;
        }
        for i in 0..word.len() {
            let deleted = format!("{}{}", &word[..i], &word[i + 1..]);
            deletes.entry(deleted).or_default().push(word.clone());
        }
    }

    // Entries in key order, so the build is reproducible and the deletion index can name words
    // by entry number.
    let mut keys: Vec<&String> = words.keys().collect();
    keys.sort();
    let index: HashMap<&str, u32> = keys
        .iter()
        .enumerate()
        .map(|(i, k)| (k.as_str(), i as u32))
        .collect();
    let mut strings = Vec::new();
    let entries: Vec<(String, Vec<u8>)> = keys
        .iter()
        .map(|key| {
            let mut value = Vec::with_capacity(12);
            let bits = u32::from(words[*key]) | (u32::from(lowercase.contains(*key)) << 8);
            value.extend(bits.to_le_bytes());
            let (offset, len) = canonical.get(*key).map_or((0, 0), |c| {
                let offset = strings.len();
                strings.extend_from_slice(c.as_bytes());
                (offset as u32, c.len() as u32)
            });
            value.extend(offset.to_le_bytes());
            value.extend(len.to_le_bytes());
            ((*key).clone(), value)
        })
        .collect();
    let lexicon = write_sorted(entries, 12, &[], &strings);

    let mut extras = Vec::new();
    let mut deletion_keys: Vec<String> = deletes.keys().cloned().collect();
    deletion_keys.sort();
    let entries: Vec<(String, Vec<u8>)> = deletion_keys
        .into_iter()
        .map(|key| {
            let mut values = deletes.remove(&key).unwrap();
            values.sort();
            values.dedup();
            let start = extras.len() as u32;
            extras.extend(values.iter().map(|w| index[w.as_str()]));
            let mut value = start.to_le_bytes().to_vec();
            value.extend((values.len() as u32).to_le_bytes());
            (key, value)
        })
        .collect();
    let deletes = write_sorted(entries, 8, &extras, &[]);
    (lexicon, deletes)
}

fn write(
    entries: impl Iterator<Item = (String, Vec<u8>)>,
    value_size: usize,
    extras: &[u32],
    strings: &[u8],
) -> Vec<u8> {
    let mut entries: Vec<_> = entries.collect();
    entries.sort();
    write_sorted(entries, value_size, extras, strings)
}

/// Writes the table: header, slots (load at most 0.7), entries, extras, then `strings` and the
/// keys in one arena.
fn write_sorted(
    entries: Vec<(String, Vec<u8>)>,
    value_size: usize,
    extras: &[u32],
    strings: &[u8],
) -> Vec<u8> {
    let slots = ((entries.len() * 10).div_ceil(7))
        .max(1)
        .next_power_of_two();
    assert!(entries.len() <= table::MAX_ENTRIES, "table too large");
    let mut slot = vec![0u32; slots];
    let mut arena = strings.to_vec();
    let mut records = Vec::with_capacity(entries.len() * (8 + value_size));
    for (i, (key, value)) in entries.iter().enumerate() {
        assert_eq!(value.len(), value_size);
        let h = table::hash(key.as_bytes());
        let mut at = h as usize & (slots - 1);
        while slot[at] != 0 {
            at = (at + 1) & (slots - 1);
        }
        slot[at] = table::slot(h, i);
        records.extend((arena.len() as u32).to_le_bytes());
        records.extend((key.len() as u32).to_le_bytes());
        records.extend(value);
        arena.extend_from_slice(key.as_bytes());
    }
    let mut out = Vec::new();
    for field in [
        table::MAGIC,
        slots as u32,
        entries.len() as u32,
        value_size as u32,
        extras.len() as u32,
        arena.len() as u32,
    ] {
        out.extend(field.to_le_bytes());
    }
    assert_eq!(out.len(), table::HEADER);
    for s in slot {
        out.extend(s.to_le_bytes());
    }
    out.extend(records);
    for e in extras {
        out.extend(e.to_le_bytes());
    }
    out.extend(arena);
    out
}

/// Every `rules/packs/*.json` (one JSON array of contextual rules per file, in name order) joined
/// into one array, `rule-packs.json` in OUT_DIR, so a new category file is picked up without a
/// code change. Each rule gets a `pack` field naming its file.
fn rule_packs(out: &Path) {
    let dir = Path::new("rules/packs");
    let mut files: Vec<_> = fs::read_dir(dir)
        .map(|entries| {
            entries
                .filter_map(Result::ok)
                .map(|e| e.path())
                .filter(|p| p.extension().is_some_and(|x| x == "json"))
                .collect()
        })
        .unwrap_or_default();
    files.sort();
    let mut all = Vec::new();
    for path in files {
        println!("cargo:rerun-if-changed={}", path.display());
        let text = fs::read_to_string(&path).unwrap();
        let name = path.file_stem().unwrap().to_string_lossy().into_owned();
        let rules: Vec<serde_json::Value> = serde_json::from_str(&text)
            .unwrap_or_else(|e| panic!("{}: not a JSON array of rules: {e}", path.display()));
        for mut rule in rules {
            let object = rule
                .as_object_mut()
                .unwrap_or_else(|| panic!("{}: every rule is an object", path.display()));
            object.insert("pack".into(), serde_json::Value::String(name.clone()));
            all.push(rule);
        }
    }
    fs::write(
        out.join("rule-packs.json"),
        serde_json::to_string(&all).unwrap(),
    )
    .unwrap();
    // The prefilter literal of every rule (base files and packs), computed once here instead of
    // at every engine start: `rule-literals.json` maps a rule id to its set, or null.
    let mut lits = serde_json::Map::new();
    for text in [
        fs::read_to_string("rules/grammar.json").unwrap(),
        fs::read_to_string("rules/tone.json").unwrap(),
        fs::read_to_string("rules/usage.json").unwrap(),
    ]
    .into_iter()
    .chain(std::iter::once(serde_json::to_string(&all).unwrap()))
    {
        let rules: Vec<serde_json::Value> = serde_json::from_str(&text).unwrap();
        for rule in rules {
            let id = rule["id"].as_str().expect("rule id").to_owned();
            let pattern = rule["pattern"].as_str().expect("rule pattern");
            let set = literals::required(pattern).map(|set| {
                serde_json::Value::Array(set.into_iter().map(serde_json::Value::String).collect())
            });
            lits.insert(id, set.unwrap_or(serde_json::Value::Null));
        }
    }
    fs::write(
        out.join("rule-literals.json"),
        serde_json::to_string(&serde_json::Value::Object(lits)).unwrap(),
    )
    .unwrap();
}
