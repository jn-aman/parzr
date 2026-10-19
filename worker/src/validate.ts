// Strict validation of a report batch. Only the fields listed here are accepted; anything else rejects the report,
// so nothing the app did not mean to send can be stored. Limits mirror SuggestionReport.Limits in
// mac/Sources/ParzrCore/Reports.swift.

export const LIMITS = {
  bodyBytes: 64 * 1024,
  reportsPerBatch: 25,
  sentence: 1000,
  text: 300,
  rule: 100,
  model: 40,
  app: 255,
  version: 32,
} as const;

// A report is sent only when the writer clicks "Report wrong suggestion". Ignored ("dismissed") and accepted
// suggestions are never sent, and are refused here (older app versions still send "dismissed").
export const ACTIONS = ['reported'] as const;
export type Action = (typeof ACTIONS)[number];

export interface Report {
  sentence: string;
  suggestion: { start: number; end: number; original: string; replacement: string };
  rule: string;
  model: string;
  action: Action;
  app: string;
  version: string;
}

export type BatchResult =
  | { ok: true; reports: Report[]; dropped: number }
  | { ok: false; status: number; error: string };

const RULE = /^[A-Za-z0-9._:-]+$/;
const MODEL = /^(?:rules|gector|qwen(?::[a-z]+)?|unknown)$/;
const APP = /^[A-Za-z0-9._-]+$/;
const VERSION = /^[A-Za-z0-9.+-]+$/;
export const BATCH_KEY = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

// Defence in depth: the app redacts before sending (mac/Sources/ParzrCore/Redaction.swift), and the server refuses
// anything that still looks private. Every pattern is case-insensitive and bounded, so a 1,000-character field costs
// microseconds whatever it holds.
const PLACEHOLDER = /\[(?:email|link|key|phone|number|name)\]/gi;
const DIGIT = /\p{N}/u;
// Bounded local part and labels: no quadratic backtracking on long runs of word characters.
const EMAIL = /[\p{L}\p{N}._%+-]{1,64}@[\p{L}\p{N}-]{1,63}(?:\.[\p{L}\p{N}-]{1,63}){1,8}/iu;
// "aman at gmail dot com", "aman (at) gmail (dot) com", "aman at gmail.com".
const SPELLED_EMAIL = /[\p{L}\p{N}._%+-]{1,64}\s{0,3}(?:\bat\b|\(at\)|\[at\])\s{0,3}[\p{L}\p{N}-]{1,63}(?:\s{0,3}(?:\bdot\b|\(dot\)|\[dot\])\s{0,3}|\.)[\p{L}\p{N}-]{2,63}/iu;
const SCHEME = /\b[a-z][a-z0-9+.-]{1,20}:\/\/|\bwww\.|\bmailto:/i;
// Any domain-shaped token: labels, a dot, and a 2 to 24 letter top-level domain, in any case. Stricter than the app
// (which needs a known lowercase TLD so "home.So tired" stays a typo); here a dropped report is the safe outcome.
const DOMAIN = /(?<![\p{L}\p{N}@.-])(?:[\p{L}\p{N}](?:[\p{L}\p{N}-]{0,61}[\p{L}\p{N}])?\.){1,8}\p{L}{2,24}(?![\p{L}\p{N}-])/iu;
const HASHTAG = /(?<![\p{L}\p{N}_&])#[\p{L}_][\p{L}\p{N}_]*/u;
const HANDLE = /(?<![\p{L}\p{N}_@.])@[\p{L}\p{N}_]/u;
// Access keys and tokens: well-known prefixes, and any long unbroken run that mixes cases, digits or underscores.
const KEY_PREFIX = /\b(?:(?:sk|pk|rk)_(?:live|test)_|sk-(?:proj-|ant-)?|gh[pousr]_|github_pat_|xox[abposr]-|glpat-|AKIA|ASIA|AIza|eyJ)[A-Za-z0-9_-]{4,}/i;
const LONG_TOKEN = /[A-Za-z0-9_+/=-]{20,}/g;
// Three or more number words in a row: a PIN, a phone number or an account number read out.
const NUMBER_WORD = '(?:zero|oh|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|double|triple)';
const SPELLED_NUMBERS = new RegExp(`\\b${NUMBER_WORD}(?:[\\s,-]{1,3}(?:and[\\s]{1,3})?${NUMBER_WORD}){2,}\\b`, 'i');

function keyLike(text: string): boolean {
  if (KEY_PREFIX.test(text)) return true;
  for (const [token] of text.matchAll(LONG_TOKEN)) {
    const mixedCase = /[a-z]/.test(token) && /[A-Z]/.test(token.slice(1));
    if (/\d/.test(token) || token.includes('_') || mixedCase) return true;
  }
  return false;
}

/** True when `text` still holds a digit, an email address, a link, a handle or hashtag, a key, or spelled-out digits, once placeholders are removed. */
export function looksPrivate(text: string): boolean {
  const stripped = text.replace(PLACEHOLDER, ' ');
  if (DIGIT.test(stripped) || SCHEME.test(stripped) || DOMAIN.test(stripped)) return true;
  if (stripped.includes('@') && (EMAIL.test(stripped) || HANDLE.test(stripped))) return true;
  if (stripped.includes('#') && HASHTAG.test(stripped)) return true;
  return SPELLED_EMAIL.test(stripped) || SPELLED_NUMBERS.test(stripped) || keyLike(stripped);
}

// C0 and C1 controls except tab and newline; bidirectional controls (which can make stored text read differently from
// what it holds); and invisible format characters other than the joiners emoji and some scripts need.
const FORBIDDEN = /[\p{Cc}؜​‎‏‪-‮⁠-⁤⁦-⁩﻿]/u;
function isText(value: unknown, max: number): value is string {
  if (typeof value !== 'string' || value.length > max || !value.isWellFormed()) return false;
  return !FORBIDDEN.test(value.replace(/[\t\n]/g, ''));
}
function isString(value: unknown, max: number, pattern?: RegExp): value is string {
  return typeof value === 'string' && value.length > 0 && value.length <= max && (!pattern || pattern.test(value));
}
function exactKeys(value: object, keys: string[]): boolean {
  const own = Object.keys(value);
  return own.length === keys.length && keys.every((k) => Object.prototype.hasOwnProperty.call(value, k));
}
/** False when a UTF-16 offset falls between the two halves of a surrogate pair. */
function onBoundary(text: string, offset: number): boolean {
  if (offset <= 0 || offset >= text.length) return true;
  const before = text.charCodeAt(offset - 1), after = text.charCodeAt(offset);
  return !(before >= 0xd800 && before <= 0xdbff && after >= 0xdc00 && after <= 0xdfff);
}

/** One report, or null when it breaks any rule. */
export function validateReport(input: unknown): Report | null {
  if (typeof input !== 'object' || input === null || Array.isArray(input)) return null;
  const r = input as Record<string, unknown>;
  if (!exactKeys(r, ['sentence', 'suggestion', 'rule', 'model', 'action', 'app', 'version'])) return null;
  const s = r.suggestion as Record<string, unknown>;
  if (typeof s !== 'object' || s === null || Array.isArray(s) || !exactKeys(s, ['start', 'end', 'original', 'replacement'])) return null;
  if (!isText(r.sentence, LIMITS.sentence) || (r.sentence as string).trim() === '') return null;
  if (!isText(s.original, LIMITS.text) || !isText(s.replacement, LIMITS.text)) return null;
  const sentence = r.sentence as string;
  const { start, end } = s;
  // Offsets are UTF-16, as in the app: JavaScript string indices.
  if (!Number.isInteger(start) || !Number.isInteger(end) || (start as number) < 0 || (end as number) < (start as number) || (end as number) > sentence.length) return null;
  if (!onBoundary(sentence, start as number) || !onBoundary(sentence, end as number)) return null;
  if (sentence.slice(start as number, end as number) !== s.original) return null;
  if (!isString(r.rule, LIMITS.rule, RULE) || !isString(r.model, LIMITS.model, MODEL)) return null;
  if (typeof r.action !== 'string' || !(ACTIONS as readonly string[]).includes(r.action)) return null;
  if (!isString(r.app, LIMITS.app, APP) || !isString(r.version, LIMITS.version, VERSION)) return null;
  if ([sentence, s.original as string, s.replacement as string].some(looksPrivate)) return null;
  return {
    sentence,
    suggestion: { start: start as number, end: end as number, original: s.original as string, replacement: s.replacement as string },
    rule: r.rule as string,
    model: r.model as string,
    action: r.action as Action,
    app: r.app as string,
    version: r.version as string,
  };
}

/** A whole request body: `{"reports": [...]}`. Bad reports are dropped; a malformed body rejects the batch. */
export function validateBatch(body: string): BatchResult {
  if (new TextEncoder().encode(body).length > LIMITS.bodyBytes) return { ok: false, status: 413, error: 'too large' };
  let parsed: unknown;
  try {
    parsed = JSON.parse(body);
  } catch {
    return { ok: false, status: 400, error: 'invalid JSON' };
  }
  if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed) || !exactKeys(parsed, ['reports'])) return { ok: false, status: 400, error: 'expected {"reports": [...]}' };
  const list = (parsed as { reports: unknown }).reports;
  if (!Array.isArray(list) || list.length === 0) return { ok: false, status: 400, error: 'no reports' };
  if (list.length > LIMITS.reportsPerBatch) return { ok: false, status: 413, error: 'too many reports' };
  const reports = list.map(validateReport).filter((r): r is Report => r !== null);
  return { ok: true, reports, dropped: list.length - reports.length };
}
