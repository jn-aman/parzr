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
    serve(io::stdin().lock(), io::stdout().lock(), |input| {
        parzr_engine::process_json(&with_known_words(input))
    });
}
/// Native-messaging frames (a 4-byte little-endian length, then JSON) in and out until the input
/// ends. `handle` runs inside `parzr_engine::guarded`: a request that panics is answered with an
/// error and the next request is served.
fn serve(mut input: impl Read, mut output: impl Write, handle: impl Fn(&str) -> String) {
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
            Ok(input) => parzr_engine::guarded(|| handle(input)),
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
#[cfg(test)]
mod tests {
    use super::*;
    fn frame(json: &str) -> Vec<u8> {
        let mut bytes = (json.len() as u32).to_le_bytes().to_vec();
        bytes.extend_from_slice(json.as_bytes());
        bytes
    }
    fn frames(mut bytes: &[u8]) -> Vec<String> {
        let mut out = vec![];
        while bytes.len() >= 4 {
            let n = u32::from_le_bytes(bytes[..4].try_into().unwrap()) as usize;
            out.push(String::from_utf8(bytes[4..4 + n].to_vec()).unwrap());
            bytes = &bytes[4 + n..];
        }
        out
    }
    #[test]
    fn a_panicking_request_is_answered_and_the_next_one_still_works() {
        // The test-only hook: a handler that panics on one request, as a bug in the engine would.
        let handle = |input: &str| {
            if input.contains("PANIC") {
                panic!("injected");
            }
            parzr_engine::process_json(input)
        };
        let mut input = frame(r#"{"text":"PANIC"}"#);
        input.extend(frame(r#"{"text":"I has a dog."}"#));
        let mut output = Vec::new();
        serve(input.as_slice(), &mut output, handle);
        let responses = frames(&output);
        assert_eq!(responses.len(), 2, "{responses:?}");
        assert_eq!(responses[0], parzr_engine::PANICKED);
        // Served as it would be by a process that never panicked (timings aside).
        assert_ne!(responses[1], parzr_engine::PANICKED);
        let answer = |s: &str| {
            let v: Value = serde_json::from_str(s).unwrap();
            (v["text"].clone(), v["edits"].clone(), v["error"].clone())
        };
        assert_eq!(
            answer(&responses[1]),
            answer(&parzr_engine::process_json(r#"{"text":"I has a dog."}"#))
        );
    }
}
