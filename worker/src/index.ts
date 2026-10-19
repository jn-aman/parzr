// Parzr suggestion reports: a Cloudflare Worker in front of a D1 database.
//
// POST /v1/reports  {"reports": [...]}  with an Idempotency-Key header (a random UUID per batch)
// GET  /v1/health
//
// Privacy: the Worker never reads, logs or stores the client's IP address or any header beyond Content-Type,
// Content-Length and Idempotency-Key. Rate limiting keys on a salted hash of the address, held only by Cloudflare's
// rate-limit counter (never written to D1). Each stored row keeps the day it arrived, not the time.

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
}

const JSON_HEADERS = { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' };
function reply(status: number, body: Record<string, unknown>, extra: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), { status, headers: { ...JSON_HEADERS, ...extra } });
}

/** UTC calendar day, the only time a row records. */
export function day(now: Date): string {
  return now.toISOString().slice(0, 10);
}

async function sha256(text: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('');
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

const INSERT_BATCH = 'INSERT INTO batches (key, received_day) VALUES (?, ?)';
const INSERT_REPORT =
  'INSERT INTO reports (received_day, sentence, start_utf16, end_utf16, original, replacement, rule, model, action, app, version) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)';

export async function store(env: Env, key: string, reports: Report[], today: string): Promise<'stored' | 'duplicate'> {
  // One transaction: the batch key and its reports go in together, or not at all.
  const statements = [env.DB.prepare(INSERT_BATCH).bind(key, today)];
  for (const r of reports) {
    statements.push(
      env.DB.prepare(INSERT_REPORT).bind(today, r.sentence, r.suggestion.start, r.suggestion.end, r.suggestion.original, r.suggestion.replacement, r.rule, r.model, r.action, r.app, r.version),
    );
  }
  try {
    await env.DB.batch(statements);
    return 'stored';
  } catch (error) {
    if (String((error as Error)?.message ?? error).includes('UNIQUE constraint failed')) return 'duplicate';
    throw error;
  }
}

export async function handleReports(request: Request, env: Env, now = new Date()): Promise<Response> {
  if (request.method !== 'POST') return reply(405, { error: 'method not allowed' }, { Allow: 'POST' });
  const type = request.headers.get('Content-Type') ?? '';
  if (!/^application\/json\b/i.test(type)) return reply(415, { error: 'expected application/json' });
  const key = (request.headers.get('Idempotency-Key') ?? '').toLowerCase();
  if (!BATCH_KEY.test(key)) return reply(400, { error: 'expected an Idempotency-Key UUID' });

  if (env.REPORTS_LIMITER) {
    // The address is hashed with a secret salt and the day, and only the hash reaches the counter.
    const address = request.headers.get('CF-Connecting-IP') ?? 'unknown';
    const hashed = (await sha256(`${env.RATE_LIMIT_SALT ?? ''}|${day(now)}|${address}`)).slice(0, 32);
    const { success } = await env.REPORTS_LIMITER.limit({ key: hashed });
    if (!success) return reply(429, { error: 'slow down' }, { 'Retry-After': '120' });
  }

  const body = await readBody(request, LIMITS.bodyBytes);
  if (body === null) return reply(413, { error: 'too large' });
  const result = validateBatch(body);
  if (!result.ok) return reply(result.status, { error: result.error });
  if (result.reports.length === 0) return reply(202, { stored: 0, dropped: result.dropped });
  try {
    const outcome = await store(env, key, result.reports, day(now));
    if (outcome === 'duplicate') return reply(200, { stored: 0, duplicate: true });
    return reply(202, { stored: result.reports.length, dropped: result.dropped });
  } catch {
    return reply(503, { error: 'try again later' }, { 'Retry-After': '300' });
  }
}

/** Daily: drop reports past retention, and batch keys (kept only to recognise retries) after 14 days. */
export async function prune(env: Env, now = new Date()): Promise<void> {
  const retention = Math.max(1, Number.parseInt(env.RETENTION_DAYS ?? '180', 10) || 180);
  const cutoff = (days: number) => day(new Date(now.getTime() - days * 86_400_000));
  await env.DB.batch([
    env.DB.prepare('DELETE FROM reports WHERE received_day < ?').bind(cutoff(retention)),
    env.DB.prepare('DELETE FROM batches WHERE received_day < ?').bind(cutoff(14)),
  ]);
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const { pathname } = new URL(request.url);
    if (pathname === '/v1/reports') return handleReports(request, env);
    if (pathname === '/v1/health' && request.method === 'GET') return reply(200, { ok: true });
    return reply(404, { error: 'not found' });
  },
  async scheduled(_event: unknown, env: Env, context: { waitUntil(promise: Promise<unknown>): void }): Promise<void> {
    context.waitUntil(prune(env));
  },
};
