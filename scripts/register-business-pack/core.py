"""Shared helpers for the register-business pack generator."""
RULES = []
# What runs in Fix mode: misspellings, nonstandard forms, plain redundancies and comma conventions. Every other rule is a
# plain-language suggestion for text that is correct as written ("in order to", "prior to", "as per", "kindly"), which the
# owner's quality gates (everyday set: such sentences must stay unchanged) keep out of Fix; like the base concise rules in
# tone.json they run only in the concise and direct tone modes.
FIX = {
    "email.thanks_in_advanced", "email.please_kindly", "email.kindly_please",
    "email.attached_herewith", "email.herewith_attached", "email.verb_herewith",
    "email.am_in_the_morning", "email.pm_in_the_evening", "wordy.previous_to",
    "signoff.regards_comma", "signoff.closing_comma", "signoff.regards_name_same_line", "signoff.dear_comma",
    "signoff.hi_comma_name", "signoff.regards_misspelled", "signoff.regard_singular", "signoff.wishes_misspelled",
}
TONE_MODES = ["concise", "direct"]
COVERAGE = []  # (section, construction, outcome) rows for the coverage map
PROV = "parzr original rule (business and email register)"
import re
def _normalize(pattern):
    """The prefilter parser (engine/src/rules/literals.rs) understands neither \\r nor \\uXXXX: write the characters."""
    pattern = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), pattern)
    return pattern.replace("\\r", "\\x0d")
def rule(rid, pattern, replacement, category, confidence, reason, positive, negative, expect, family=None):
    """expect: the whole sentence the engine must produce from `positive` (checked end to end by e2e.py)."""
    RULES.append({
        "id": "register." + rid,
        **({} if rid in FIX else {"modes": TONE_MODES}),
        "pattern": _normalize(pattern),
        "replacement": replacement,
        "category": category,
        "confidence": confidence,
        "reason": reason,
        "provenance": PROV,
        "positive": positive,
        "negative": negative,
        "_expect": expect,
        "_family": family or rid.split(".")[0],
    })
def note(section, construction, outcome):
    COVERAGE.append((section, construction, outcome))
