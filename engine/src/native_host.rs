//! Chrome/Firefox native messaging host: framed local stdin/stdout; no socket or HTTP server.
use std::io::{self, Read, Write};
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
            Ok(input) => parzr_engine::process_json(input),
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
