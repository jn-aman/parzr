//! Chrome/Firefox native messaging host: framed local stdin/stdout; no socket or HTTP server.
use serde_json::Value;
use std::io::{self, Read, Write};
#[path = "known_words.rs"]
mod known_words;
/// Adds the app's dictionary and names to a request; anything unparsable passes through untouched.
fn with_known_words(input: &str) -> String {
    let known = known_words::current();
    if known.dictionary.is_empty() && known.names.is_empty() {
        return input.into();
    }
    let Ok(mut request) = serde_json::from_str::<Value>(input) else {
        return input.into();
    };
    let Some(object) = request.as_object_mut() else {
        return input.into();
    };
    for (key, extra, cap) in [
        ("dictionary", &known.dictionary, known_words::MAX_DICTIONARY),
        ("names", &known.names, known_words::MAX_NAMES),
    ] {
        if extra.is_empty() {
            continue;
        }
        let own = object
            .get(key)
            .map(|v| {
                v.as_array()
                    .into_iter()
                    .flatten()
                    .filter_map(|x| x.as_str().map(String::from))
                    .collect()
            })
            .unwrap_or_default();
        object.insert(key.into(), known_words::merge(own, extra, cap).into());
    }
    request.to_string()
}
fn main() {
    let mut input = io::stdin().lock();
    let mut output = io::stdout().lock();
    loop {
        let mut header = [0u8; 4];
        if input.read_exact(&mut header).is_err() {
            break;
        }
        let length = u32::from_le_bytes(header) as usize;
        if length > parzr_engine::MAX_TEXT_BYTES * 8 {
            break;
        }
        let mut bytes = vec![0u8; length];
        if input.read_exact(&mut bytes).is_err() {
            break;
        }
        let response = match std::str::from_utf8(&bytes) {
            Ok(input) => parzr_engine::process_json(&with_known_words(input)),
            Err(_) => r#"{"error":"Invalid UTF-8 request."}"#.to_string(),
        };
        let data = response.as_bytes();
        if output
            .write_all(&(data.len() as u32).to_le_bytes())
            .is_err()
            || output.write_all(data).is_err()
            || output.flush().is_err()
        {
            break;
        }
    }
}
