use std::io::{self, BufRead, Read, Write};
/// One JSON request a line in, one JSON response a line out, until the input ends. `handle` runs
/// inside `parzr_engine::guarded`: a request that panics is answered with an error and the next
/// request is served.
fn serve(mut input: impl BufRead, mut output: impl Write, handle: impl Fn(&str) -> String) {
    loop {
        let mut bytes = Vec::new();
        let read = (&mut input)
            .take((parzr_engine::MAX_TEXT_BYTES * 8 + 1) as u64)
            .read_until(b'\n', &mut bytes);
        if !matches!(read, Ok(n) if n > 0) {
            break;
        }
        if bytes.len() > parzr_engine::MAX_TEXT_BYTES * 8 {
            let _ = writeln!(output, "{{\"error\":\"Request exceeds size limit.\"}}");
            break;
        }
        let response = match std::str::from_utf8(&bytes) {
            Ok(input) => parzr_engine::guarded(|| handle(input)),
            Err(_) => "{\"error\":\"Invalid UTF-8 request.\"}".into(),
        };
        if writeln!(output, "{response}").is_err() || output.flush().is_err() {
            break;
        }
    }
}
fn main() {
    serve(
        io::stdin().lock(),
        io::stdout().lock(),
        parzr_engine::process_json,
    );
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn a_panicking_request_is_answered_and_the_next_one_still_works() {
        // The test-only hook: a handler that panics on one request, as a bug in the engine would.
        let handle = |input: &str| {
            if input.contains("PANIC") {
                panic!("injected");
            }
            parzr_engine::process_json(input)
        };
        let input = "{\"text\":\"PANIC\"}\n{\"text\":\"I has a dog.\"}\n";
        let mut output = Vec::new();
        serve(input.as_bytes(), &mut output, handle);
        let lines: Vec<&str> = std::str::from_utf8(&output).unwrap().lines().collect();
        assert_eq!(lines.len(), 2, "{lines:?}");
        assert_eq!(lines[0], parzr_engine::PANICKED);
        // Served as it would be by a process that never panicked (timings aside).
        assert_ne!(lines[1], parzr_engine::PANICKED);
        let answer = |s: &str| {
            let v: serde_json::Value = serde_json::from_str(s).unwrap();
            (v["text"].clone(), v["edits"].clone(), v["error"].clone())
        };
        assert_eq!(
            answer(lines[1]),
            answer(&parzr_engine::process_json("{\"text\":\"I has a dog.\"}\n"))
        );
    }
}
