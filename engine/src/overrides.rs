//! Development overrides: `PARZR_*` environment variables that point the engine at other model
//! files, another model runtime, another models folder or another tables file (tests, benchmarks,
//! local development). They are honoured only in builds with the `dev-overrides` feature, which is
//! on by default for `cargo build` and `cargo test`. The Mac app's release build
//! (scripts/build.py) turns it off, so a shipped engine reads only its own bundle and the verified
//! model packs, whatever the environment says.
use std::ffi::OsString;

/// True when this build honours `PARZR_*` overrides.
pub const ENABLED: bool = cfg!(feature = "dev-overrides");

/// The variable's value, when overrides are enabled and it is set and not empty.
pub fn var(name: &str) -> Option<OsString> {
    lookup(name, |n| std::env::var_os(n))
}

/// `var` with the environment passed in, so both feature sets can be tested without touching the
/// process environment.
fn lookup(name: &str, read: impl Fn(&str) -> Option<OsString>) -> Option<OsString> {
    if !ENABLED {
        return None;
    }
    read(name).filter(|v| !v.is_empty())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn overrides_follow_the_feature() {
        let set = |_: &str| Some(OsString::from("/elsewhere"));
        let got = lookup("PARZR_MODELS_DIR", set);
        if cfg!(feature = "dev-overrides") {
            assert_eq!(got, Some(OsString::from("/elsewhere")));
        } else {
            // A release build ignores every override.
            assert_eq!(got, None);
            for name in [
                "PARZR_MODELS_DIR",
                "PARZR_MODEL_PATH",
                "PARZR_GEC_DIR",
                "PARZR_SLIP_DIR",
                "PARZR_MODEL_RUNTIME",
                "PARZR_GEC_RUNTIME",
                "PARZR_TABLES_PATH",
                "PARZR_TONE_TRACE",
            ] {
                assert_eq!(lookup(name, set), None, "{name}");
            }
        }
        // An empty value never counts.
        assert_eq!(lookup("PARZR_MODELS_DIR", |_| Some(OsString::new())), None);
        assert_eq!(lookup("PARZR_MODELS_DIR", |_| None), None);
    }
}
