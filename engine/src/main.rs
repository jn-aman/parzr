use std::io::{self, BufRead, Read, Write};
fn main() {
    let mut input = io::stdin().lock();
    let mut output = io::stdout().lock();
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
            Ok(input) => parzr_engine::process_json(input),
            Err(_) => "{\"error\":\"Invalid UTF-8 request.\"}".into(),
        };
        if writeln!(output, "{response}").is_err() || output.flush().is_err() {
            break;
        }
    }
}
