//! Local stdio LSP. Full document sync, UTF-16 positions, versioned code actions; no sockets.
use parzr_engine::{Mode, Request, TextRange, rewrite};
use serde_json::{Value, json};
use std::{
    collections::HashMap,
    io::{self, BufRead, Read, Write},
};
const MAX_MESSAGE: usize = 524_288;
struct Document {
    text: String,
    version: i64,
    language: String,
}
fn read_message(input: &mut impl BufRead) -> Option<Value> {
    let mut length = None;
    for _ in 0..32 {
        let mut bytes = vec![];
        let n = input.take(1025).read_until(b'\n', &mut bytes).ok()?;
        if n == 0 || n > 1024 {
            return None;
        }
        let line = std::str::from_utf8(&bytes).ok()?.trim();
        if line.is_empty() {
            let length = length?;
            if length > MAX_MESSAGE {
                return None;
            }
            let mut body = vec![0; length];
            input.read_exact(&mut body).ok()?;
            return serde_json::from_slice(&body).ok();
        }
        if let Some((key, value)) = line.split_once(':')
            && key.eq_ignore_ascii_case("Content-Length")
        {
            if length.is_some() {
                return None;
            }
            length = Some(value.trim().parse::<usize>().ok()?);
        }
    }
    None
}
fn write_message(output: &mut impl Write, value: Value) -> io::Result<()> {
    let bytes = serde_json::to_vec(&value)?;
    write!(output, "Content-Length: {}\r\n\r\n", bytes.len())?;
    output.write_all(&bytes)?;
    output.flush()
}
fn position(text: &str, offset: usize) -> Value {
    let mut line = 0;
    let mut column = 0;
    let mut at = 0;
    for ch in text.chars() {
        if at == offset {
            break;
        }
        at += ch.len_utf16();
        if ch == '\n' {
            line += 1;
            column = 0;
        } else {
            column += ch.len_utf16();
        }
    }
    json!({"line":line,"character":column})
}
fn offset(text: &str, p: &Value) -> Option<usize> {
    let line = p["line"].as_u64()?;
    let column = p["character"].as_u64()?;
    let mut at = 0;
    let mut current_line = 0;
    let mut current_column = 0;
    for ch in text.chars() {
        if current_line == line && current_column == column {
            return Some(at);
        }
        if current_line == line && (ch == '\n' || current_column > column) {
            return None;
        }
        at += ch.len_utf16();
        if ch == '\n' {
            current_line += 1;
            current_column = 0;
        } else {
            current_column += ch.len_utf16() as u64;
        }
    }
    (current_line == line && current_column == column).then_some(at)
}
fn byte(text: &str, offset: usize) -> Option<usize> {
    let mut at = 0;
    for (i, ch) in text.char_indices() {
        if at == offset {
            return Some(i);
        }
        at += ch.len_utf16();
    }
    (at == offset).then_some(text.len())
}
fn editable(doc: &Document) -> bool {
    ["plaintext", "markdown"].contains(&doc.language.as_str())
        && doc.text.len() <= parzr_engine::MAX_TEXT_BYTES
}
fn request(text: &str, mode: Mode, options: &Value) -> Request {
    Request {
        text: text.into(),
        mode,
        dictionary: options["dictionary"]
            .as_array()
            .map(|v| {
                v.iter()
                    .filter_map(|x| x.as_str().map(String::from))
                    .collect()
            })
            .unwrap_or_default(),
        dialect: options["dialect"].as_str().unwrap_or("").into(),
        ..Request::default()
    }
}
fn diagnostics(uri: &str, doc: &Document, options: &Value) -> Value {
    let findings = if editable(doc) {
        rewrite(&request(&doc.text,Mode::Fix,options)).map(|r|r.edits.into_iter().map(|e|json!({"range":{"start":position(&doc.text,e.start_utf16),"end":position(&doc.text,e.end_utf16)},"severity":2,"source":"parzr","code":e.rule_id,"message":e.explanation})).collect::<Vec<_>>()).unwrap_or_default()
    } else {
        vec![]
    };
    json!({"jsonrpc":"2.0","method":"textDocument/publishDiagnostics","params":{"uri":uri,"version":doc.version,"diagnostics":findings}})
}
fn actions(uri: &str, doc: &Document, params: &Value, options: &Value) -> Value {
    if !editable(doc) {
        return json!([]);
    }
    let Some(a) = offset(&doc.text, &params["range"]["start"]) else {
        return json!([]);
    };
    let Some(b) = offset(&doc.text, &params["range"]["end"]) else {
        return json!([]);
    };
    if a > b {
        return json!([]);
    }
    let mut actions = vec![];
    let workspace = |title: &str, kind: &str, edits: Vec<Value>| json!({"title":title,"kind":kind,"edit":{"documentChanges":[{"textDocument":{"uri":uri,"version":doc.version},"edits":edits}]}});
    if let Ok(result) = rewrite(&request(&doc.text, Mode::Fix, options)) {
        for edit in result.edits.iter().filter(|e| {
            if a == b {
                e.start_utf16 <= a && e.end_utf16 >= a
            } else {
                e.start_utf16 < b && e.end_utf16 > a
            }
        }) {
            let related: Vec<_> = result.edits.iter().filter(|e| e.start_utf16 == edit.start_utf16 || edit.group_id.as_ref().is_some_and(|g| e.group_id.as_ref() == Some(g))).map(|e| json!({"range":{"start":position(&doc.text,e.start_utf16),"end":position(&doc.text,e.end_utf16)},"newText":e.replacement})).collect();
            actions.push(workspace(&edit.explanation, "quickfix", related));
        }
    }
    if a < b
        && let (Some(x), Some(y)) = (byte(&doc.text, a), byte(&doc.text, b))
    {
        let full = request(&doc.text, Mode::Fix, options);
        let protected = parzr_engine::protected_spans(&full);
        for (mode, title) in [
            (Mode::Fix, "parzr: Fix passage"),
            (Mode::Professional, "parzr: Professional"),
            (Mode::Friendly, "parzr: Friendly"),
            (Mode::Concise, "parzr: Concise"),
            (Mode::Direct, "parzr: Direct"),
        ] {
            let mut req = request(&doc.text[x..y], mode, options);
            req.deep = true;
            let prefix = doc.text[..x].trim_end_matches([' ', '\t']);
            req.sentence_start = prefix.is_empty() || prefix.ends_with(['.', '!', '?', '\n']);
            req.sentence_end =
                y == doc.text.len() || req.text.trim_end().ends_with(['.', '!', '?', '\n']);
            req.protected_ranges = protected
                .iter()
                .filter(|r| r.start_utf16 < b && r.end_utf16 > a)
                .map(|r| TextRange {
                    start_utf16: r.start_utf16.max(a) - a,
                    end_utf16: r.end_utf16.min(b) - a,
                })
                .collect();
            if let Ok(result) = rewrite(&req)
                && !result.edits.is_empty()
            {
                let edits=result.edits.iter().map(|e|json!({"range":{"start":position(&doc.text,a+e.start_utf16),"end":position(&doc.text,a+e.end_utf16)},"newText":e.replacement})).collect();
                actions.push(workspace(title, "refactor.rewrite", edits));
            }
        }
    }
    json!(actions)
}
fn main() {
    let mut input = io::stdin().lock();
    let mut output = io::stdout().lock();
    let mut docs = HashMap::<String, Document>::new();
    let mut options = json!({});
    let mut shutdown = false;
    while let Some(message) = read_message(&mut input) {
        let method = message["method"].as_str().unwrap_or("");
        let params = &message["params"];
        let uri = params["textDocument"]["uri"].as_str().unwrap_or("");
        let id = message.get("id");
        if method == "exit" {
            if shutdown {
                break;
            }
            std::process::exit(1);
        }
        let result = match method {
            "initialize" => {
                options = params["initializationOptions"].clone();
                Some(
                    json!({"capabilities":{"positionEncoding":"utf-16","textDocumentSync":{"openClose":true,"change":1},"codeActionProvider":{"codeActionKinds":["quickfix","refactor.rewrite"]}},"serverInfo":{"name":"parzr","version":"0.1.0"}}),
                )
            }
            "shutdown" => {
                shutdown = true;
                docs.clear();
                Some(Value::Null)
            }
            "textDocument/didOpen" if !shutdown => {
                if let (Some(text), Some(version), Some(language)) = (
                    params["textDocument"]["text"].as_str(),
                    params["textDocument"]["version"].as_i64(),
                    params["textDocument"]["languageId"].as_str(),
                ) && docs.len() < 32
                    && text.len() <= MAX_MESSAGE / 2
                {
                    let doc = Document {
                        text: text.into(),
                        version,
                        language: language.into(),
                    };
                    if write_message(&mut output, diagnostics(uri, &doc, &options)).is_err() {
                        break;
                    }
                    docs.insert(uri.into(), doc);
                }
                None
            }
            "textDocument/didChange" if !shutdown => {
                if let Some(doc) = docs.get_mut(uri)
                    && let Some(version) = params["textDocument"]["version"].as_i64()
                    && version > doc.version
                    && let Some(changes) = params["contentChanges"].as_array()
                    && changes.len() == 1
                    && changes[0].get("range").is_none()
                    && let Some(text) = changes[0]["text"].as_str()
                    && text.len() <= MAX_MESSAGE / 2
                {
                    doc.text = text.into();
                    doc.version = version;
                    if write_message(&mut output, diagnostics(uri, doc, &options)).is_err() {
                        break;
                    }
                }
                None
            }
            "textDocument/didClose" => {
                docs.remove(uri);
                if write_message(&mut output,json!({"jsonrpc":"2.0","method":"textDocument/publishDiagnostics","params":{"uri":uri,"diagnostics":[]}})).is_err(){break;}
                None
            }
            "textDocument/codeAction" if !shutdown => Some(
                docs.get(uri)
                    .map(|doc| actions(uri, doc, params, &options))
                    .unwrap_or(json!([])),
            ),
            _ => None,
        };
        if let Some(id) = id {
            let response = if let Some(result) = result {
                json!({"jsonrpc":"2.0","id":id,"result":result})
            } else {
                json!({"jsonrpc":"2.0","id":id,"error":{"code":-32601,"message":"Unsupported request."}})
            };
            if write_message(&mut output, response).is_err() {
                break;
            }
        }
    }
}
