//! Reads JSON lines {"mode", "source", "output"} and writes {"keeps": bool, "reason": string}
//! for each: the meaning check tone rewrites pass. Used by scripts/run-tone-eval.py.
use std::io::{self, BufRead, Write};

#[derive(serde::Deserialize)]
struct Case {
    mode: parzr_engine::Mode,
    source: String,
    output: String,
}

fn main() {
    let mut out = io::stdout().lock();
    for line in io::stdin().lock().lines().map_while(Result::ok) {
        let verdict = match serde_json::from_str::<Case>(&line) {
            Ok(c) => parzr_engine::tone_keeps_meaning(c.mode, &c.source, &c.output),
            Err(e) => Err(format!("invalid case: {e}")),
        };
        let value = serde_json::json!({
            "keeps": verdict.is_ok(),
            "reason": verdict.err().unwrap_or_default(),
        });
        if writeln!(out, "{value}").is_err() {
            break;
        }
    }
}
