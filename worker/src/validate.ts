// Strict validation of a report batch. Only the fields listed here are accepted; anything else rejects the report,
// so nothing the app did not mean to send can be stored. Limits mirror SuggestionReport.Limits in
// mac/Sources/ParzrCore/Reports.swift.

export const LIMITS = {
  bodyBytes: 64 * 1024,
  reportsPerBatch: 50,
  sentence: 1000,
  text: 300,
  rule: 100,
  model: 40,
  app: 255,
  version: 32,
} as const;

export const ACTIONS = ['dismissed', 'reported', 'accepted'] as const;
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

// Defence in depth: the app redacts before sending, and the server refuses anything that still looks private.
const PLACEHOLDER = /\[(?:email|link|phone|number|name)\]/g;
const DIGIT = /\p{N}/u;
const EMAIL = /[\p{L}\p{N}._%+-]+@[\p{L}\p{N}-]+(?:\.[\p{L}\p{N}-]+)+/u;
const SCHEME = /\b[a-z][a-z0-9+.-]{1,20}:\/\/|\bwww\.|\bmailto:/i;
const DOMAIN = /(?<![\p{L}\p{N}@.-])(?:[\p{L}\p{N}](?:[\p{L}\p{N}-]{0,61}[\p{L}\p{N}])?\.)+(?:com|org|net|edu|gov|io|ai|app|dev|info|co\.uk|uk|de|fr)(?![\p{L}\p{N}-])/u;

/** True when `text` still holds a digit, an email address or a link once placeholders are removed. */
export function looksPrivate(text: string): boolean {
  const stripped = text.replace(PLACEHOLDER, ' ');
  return DIGIT.test(stripped) || EMAIL.test(stripped) || SCHEME.test(stripped) || DOMAIN.test(stripped);
}

function isString(value: unknown, max: number, pattern?: RegExp): value is string {
  return typeof value === 'string' && value.length > 0 && value.length <= max && (!pattern || pattern.test(value));
}
function isText(value: unknown, max: number): value is string {
  return typeof value === 'string' && value.length <= max && !/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/.test(value);
}
function exactKeys(value: object, keys: string[]): boolean {
  const own = Object.keys(value);
  return own.length === keys.length && keys.every((k) => Object.prototype.hasOwnProperty.call(value, k));
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
