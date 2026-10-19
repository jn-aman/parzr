// Parzr suggestion reports: a Cloudflare Worker in front of a D1 database.
//
// POST /v1/reports  {"reports": [...]}  with an Idempotency-Key header (a random UUID per batch)
// GET  /v1/health   (HEAD too): the deployed version, a database read, the age of the oldest row, the last clean-up
//
// Privacy: the Worker reads the Content-Type, Content-Length and Idempotency-Key headers, and CF-Connecting-IP only to
// derive the rate-limit key: the address (an IPv6 address cut to its /64 network) is hashed with a secret salt and the
// day, and only that hash reaches Cloudflare's rate-limit counter. The address is never written to D1 or logged, and
// Workers observability is off. Each stored row keeps the UTC day it arrived, not the time.

import { BATCH_KEY, LIMITS, validateBatch, type Report } from './validate.ts';

export interface RateLimit {
  limit(options: { key: string }): Promise<{ success: boolean }>;
}
export interface D1Result {
  meta?: { changes?: number };
}
export interface D1PreparedStatement {
  bind(...values: unknown[]): D1PreparedStatement;
  run(): Promise<D1Result>;
  first<T = Record<string, unknown>>(): Promise<T | null>;
}
export interface D1Database {
  prepare(query: string): D1PreparedStatement;
  batch(statements: D1PreparedStatement[]): Promise<D1Result[]>;
}
export interface Env {
  DB: D1Database;
  REPORTS_LIMITER?: RateLimit;
  /** Secret: salts the address hash used as the rate-limit key. */
  RATE_LIMIT_SALT?: string;
  /** Days a report is kept (default 180). */
  RETENTION_DAYS?: string;
  /** The most report rows stored per UTC day, across every client (default 20000). */
  DAILY_ROW_CAP?: string;
  /** The deployed version, for the health check (wrangler.toml [version_metadata]). */
  CF_VERSION_METADATA?: { id: string };
}

const JSON_HEADERS = { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' };
function reply(status: number, body: Record<string, unknown> | null, extra: Record<string, string> = {}): Response {
  return new Response(body === null ? null : JSON.stringify(body), { status, headers: { ...JSON_HEADERS, ...extra } });
}

/** UTC calendar day, the only time a row records. */
export function day(now: Date): string {
  return now.toISOString().slice(0, 10);
}
function daysBefore(now: Date, days: number): string {
  return day(new Date(now.getTime() - days * 86_400_000));
}
function setting(value: string | undefined, fallback: number): number {
  const parsed = Number.parseInt(value ?? '', 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}
export const retentionDays = (env: Env) => setting(env.RETENTION_DAYS, 180);
export const dailyCap = (env: Env) => setting(env.DAILY_ROW_CAP, 20_000);
/** Batch keys are kept this long so a retried batch is stored once; the app drops reports queued longer than this. */
export const BATCH_KEY_DAYS = 14;

async function sha256(text: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

/**
 * What the rate limit counts: an IPv4 address as is, an IPv6 address by its /64 network (one subscriber usually holds a
 * whole /64, so rotating the low bits must not buy more requests). Anything unparsable shares one bucket.
 */
export function limitSubject(address: string | null): string {
  const raw = (address ?? '').trim().toLowerCase();
  if (/^\d{1,3}(?:\.\d{1,3}){3}$/.test(raw)) return raw;
  if (!raw.includes(':') || !/^[0-9a-f:.]+$/.test(raw)) return 'unknown';
  // IPv4-mapped (::ffff:192.0.2.1) counts as the IPv4 address.
  const mapped = /^(?:0{0,4}:){0,5}:?ffff:(\d{1,3}(?:\.\d{1,3}){3})$/.exec(raw);
  if (mapped) return mapped[1];
  const halves = raw.split('::');
  if (halves.length > 2) return 'unknown';
  const head = halves[0] ? halves[0].split(':') : [];
  const tail = halves.length === 2 && halves[1] ? halves[1].split(':') : [];
  if (tail.some((g) => g.includes('.'))) tail.splice(tail.length - 1, 1, '0', '0'); // embedded IPv4 is in the low 64 bits
  const missing = 8 - head.length - tail.length;
  if (halves.length === 1 ? missing !== 0 : missing < 1) return 'unknown';
  const groups = [...head, ...Array(halves.length === 2 ? missing : 0).fill('0'), ...tail];
  if (groups.length !== 8 || groups.some((g) => !/^[0-9a-f]{1,4}$/.test(g))) return 'unknown';
  return `${groups.slice(0, 4).map((g) => g.replace(/^0+(?=.)/, '')).join(':')}::/64`;
}

/** Reads at most `limit` bytes of the body; null when it is longer. */
async function readBody(request: Request, limit: number): Promise<string | null> {
  const declared = Number(request.headers.get('Content-Length') ?? '0');
  if (declared > limit) return null;
  if (!request.body) return '';
  const reader = request.body.getReader();
  const chunks: Uint8Array[] = [];
  let size = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    size += value.byteLength;
    if (size > limit) {
      await reader.cancel();
      return null;
    }
    chunks.push(value);
  }
  const all = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) {
    all.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return new TextDecoder().decode(all);
}

const SEEN = 'SELECT (SELECT 1 FROM batches WHERE key = ?1) AS seen, (SELECT rows FROM daily_counts WHERE day = ?2) AS used';
// The day's counter goes up in the same transaction as the rows. The table's CHECK (rows <= cap) fails the statement
// when a batch would pass the cap, and D1 then rolls the whole batch back: nothing is stored.
const COUNT = 'INSERT INTO daily_counts (day, rows, cap) VALUES (?1, ?2, ?3) ON CONFLICT (day) DO UPDATE SET rows = rows + excluded.rows, cap = excluded.cap';
const INSERT_BATCH = 'INSERT INTO batches (key, received_day) VALUES (?, ?)';
const INSERT_REPORT =
  'INSERT INTO reports (received_day, sentence, start_utf16, end_utf16, original, replacement, rule, model, action, app, version) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)';

export type StoreOutcome = 'stored' | 'duplicate' | 'full';

export async function store(env: Env, key: string, reports: Report[], today: string): Promise<StoreOutcome> {
  const cap = dailyCap(env);
  const seen = () => env.DB.prepare(SEEN).bind(key, today).first<{ seen: number | null; used: number | null }>();
  const before = await seen();
  if (before?.seen) return 'duplicate';
  if ((before?.used ?? 0) + reports.length > cap) return 'full';
  // One transaction: the day's count, the batch key and its reports go in together, or not at all.
  const statements = [env.DB.prepare(COUNT).bind(today, reports.length, cap), env.DB.prepare(INSERT_BATCH).bind(key, today)];
  for (const r of reports) {
    statements.push(
      env.DB.prepare(INSERT_REPORT).bind(today, r.sentence, r.suggestion.start, r.suggestion.end, r.suggestion.original, r.suggestion.replacement, r.rule, r.model, r.action, r.app, r.version),
    );
  }
  try {
    await env.DB.batch(statements);
    return 'stored';
  } catch (error) {
    // Decided by reading the database again, not by the error's wording: a retry that raced its first attempt, or a
    // cap another request reached first.
    const after = await seen().catch(() => null);
    if (after?.seen) return 'duplicate';
    if (after && (after.used ?? 0) + reports.length > cap) return 'full';
    throw error;
  }
}

/** Seconds until the next UTC midnight, when the daily cap resets. */
function untilTomorrow(now: Date): number {
  const next = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + 1);
  return Math.max(60, Math.ceil((next - now.getTime()) / 1000));
}

export async function handleReports(request: Request, env: Env, now = new Date()): Promise<Response> {
  if (request.method !== 'POST') return reply(405, { error: 'method not allowed' }, { Allow: 'POST' });
  // Fail closed: without its limiter or salt the Worker takes nothing.
  if (!env.REPORTS_LIMITER || !env.RATE_LIMIT_SALT) return reply(503, { error: 'not configured' }, { 'Retry-After': '3600' });
  const type = request.headers.get('Content-Type') ?? '';
  if (!/^application\/json\b/i.test(type)) return reply(415, { error: 'expected application/json' });
  const key = (request.headers.get('Idempotency-Key') ?? '').toLowerCase();
  if (!BATCH_KEY.test(key)) return reply(400, { error: 'expected an Idempotency-Key UUID' });

  const subject = limitSubject(request.headers.get('CF-Connecting-IP'));
  const hashed = (await sha256(`${env.RATE_LIMIT_SALT}|${day(now)}|${subject}`)).slice(0, 32);
  const { success } = await env.REPORTS_LIMITER.limit({ key: hashed });
  if (!success) return reply(429, { error: 'slow down' }, { 'Retry-After': '120' });

  const body = await readBody(request, LIMITS.bodyBytes);
  if (body === null) return reply(413, { error: 'too large' });
  const result = validateBatch(body);
  if (!result.ok) return reply(result.status, { error: result.error });
  if (result.reports.length === 0) return reply(202, { stored: 0, dropped: result.dropped });
  try {
    const outcome = await store(env, key, result.reports, day(now));
    if (outcome === 'duplicate') return reply(200, { stored: 0, duplicate: true });
    if (outcome === 'full') return reply(503, { error: 'daily limit reached' }, { 'Retry-After': String(untilTomorrow(now)) });
    return reply(202, { stored: result.reports.length, dropped: result.dropped });
  } catch {
    return reply(503, { error: 'try again later' }, { 'Retry-After': '300' });
  }
}

/** Daily: drop reports past retention, batch keys and day counters after 14 days, then note the day it worked. */
export async function prune(env: Env, now = new Date()): Promise<void> {
  await env.DB.batch([
    env.DB.prepare('DELETE FROM reports WHERE received_day < ?').bind(daysBefore(now, retentionDays(env))),
    env.DB.prepare('DELETE FROM batches WHERE received_day < ?').bind(daysBefore(now, BATCH_KEY_DAYS)),
    env.DB.prepare('DELETE FROM daily_counts WHERE day < ?').bind(daysBefore(now, BATCH_KEY_DAYS)),
    env.DB.prepare("INSERT INTO meta (key, value) VALUES ('last_prune_ok', ?) ON CONFLICT (key) DO UPDATE SET value = excluded.value").bind(day(now)),
  ]);
}

/** How old the oldest stored row is, in bands (never a date): "over-retention" means the clean-up is not running. */
export function ageBand(oldest: string | null, now: Date, retention: number): string {
  if (!oldest) return 'empty';
  const age = Math.floor((Date.parse(`${day(now)}T00:00:00Z`) - Date.parse(`${oldest}T00:00:00Z`)) / 86_400_000);
  if (!Number.isFinite(age)) return 'unknown';
  if (age > retention) return 'over-retention';
  if (age <= 7) return 'under-8-days';
  if (age <= 30) return 'under-31-days';
  if (age <= 90) return 'under-91-days';
  return `under-${retention + 1}-days`;
}

export async function health(env: Env, now = new Date()): Promise<Response> {
  const version = env.CF_VERSION_METADATA?.id ?? 'unknown';
  try {
    const row = await env.DB.prepare("SELECT (SELECT MIN(received_day) FROM reports) AS oldest, (SELECT value FROM meta WHERE key = 'last_prune_ok') AS pruned").first<{ oldest: string | null; pruned: string | null }>();
    const retention = retentionDays(env);
    const oldest = ageBand(row?.oldest ?? null, now, retention);
    const pruned = row?.pruned ?? null;
    // The clean-up runs daily; two missed days (or rows past retention) mean it is failing.
    const pruneOk = oldest !== 'over-retention' && (pruned === null ? oldest === 'empty' || oldest === 'under-8-days' : pruned >= daysBefore(now, 2));
    return reply(200, { ok: true, version, database: 'ok', oldest, last_prune_ok: pruned, prune: pruneOk ? 'ok' : 'stale' });
  } catch {
    return reply(503, { ok: false, version, database: 'unavailable' }, { 'Retry-After': '60' });
  }
}

/** What a person opening reports.parzr.app in a browser sees: plain text, nothing to run. */
export const ABOUT =
  'Parzr suggestion reports endpoint.\n\n' +
  'Parzr sends a report here only when you click “Report wrong suggestion”.\n' +
  'What is sent and kept: https://parzr.app/privacy\n' +
  'Health: /v1/health\n';
const ABOUT_HEADERS = {
  'Content-Type': 'text/plain; charset=utf-8',
  'Cache-Control': 'no-store',
  'Content-Security-Policy': "default-src 'none'; frame-ancestors 'none'",
  'X-Content-Type-Options': 'nosniff',
};

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const { pathname } = new URL(request.url);
    if (pathname === '/v1/reports') return handleReports(request, env);
    if (pathname === '/') {
      if (request.method === 'GET') return new Response(ABOUT, { headers: ABOUT_HEADERS });
      if (request.method === 'HEAD') return new Response(null, { headers: ABOUT_HEADERS });
      return reply(405, { error: 'method not allowed' }, { Allow: 'GET, HEAD' });
    }
    if (pathname === '/v1/health') {
      if (request.method === 'HEAD') {
        const response = await health(env);
        return new Response(null, { status: response.status, headers: response.headers });
      }
      if (request.method === 'GET') return health(env);
      return reply(405, { error: 'method not allowed' }, { Allow: 'GET, HEAD' });
    }
    return reply(404, { error: 'not found' });
  },
  // Awaited, not handed to waitUntil: a failed clean-up fails the cron invocation, and health reports `prune: stale`.
  async scheduled(_event: unknown, env: Env): Promise<void> {
    await prune(env);
  },
};
