import { test } from 'node:test';
import assert from 'node:assert/strict';
import worker, { ABOUT, ageBand, handleReports, health, limitSubject, prune, type D1Database, type D1PreparedStatement, type Env, type RateLimit } from '../src/index.ts';
import { LIMITS, looksPrivate, validateBatch, validateReport } from '../src/validate.ts';

const report = (over: Record<string, unknown> = {}) => ({
  sentence: 'Thanks [name], I has [number] questions.',
  suggestion: { start: 17, end: 20, original: 'has', replacement: 'have' },
  rule: 'grammar.i_agreement',
  model: 'rules',
  action: 'reported',
  app: 'com.tinyspeck.slackmacgap',
  version: '0.5.0',
  ...over,
});
const KEY = '0f8fad5b-d9cb-469f-a165-70867728950e';
const KEY2 = '1f8fad5b-d9cb-469f-a165-70867728950e';
const allow: RateLimit = { limit: async () => ({ success: true }) };

/** An in-memory D1 that follows the Worker's statements: batch keys are unique, the day and per-client counters have caps, and a failed batch stores nothing. */
function fakeDB() {
  const rows: unknown[][] = [];
  const keys = new Set<string>();
  const days = new Map<string, number>();
  const clients = new Map<string, number>();
  const meta = new Map<string, string>();
  const executed: string[] = [];
  let fail = false;
  const statement = (sql: string, values: unknown[] = []): D1PreparedStatement & { sql: string; values: unknown[] } => ({
    sql,
    values,
    bind: (...v: unknown[]) => statement(sql, v),
    run: async () => ({ meta: { changes: 1 } }),
    first: async <T,>() => {
      if (fail) throw new Error('D1_ERROR: network');
      if (sql.startsWith('SELECT (SELECT 1 FROM batches')) return { seen: keys.has(values[0] as string) ? 1 : null, used: days.get(values[1] as string) ?? null, client_used: clients.get(`${values[1]}|${values[2]}`) ?? null } as T;
      if (sql.includes('MIN(received_day)')) return { oldest: (rows.map((r) => r[0] as string).sort()[0] ?? null), pruned: meta.get('last_prune_ok') ?? null } as T;
      return null;
    },
  });
  const db: D1Database = {
    prepare: (sql) => statement(sql),
    batch: async (list) => {
      if (fail) throw new Error('D1_ERROR: network');
      const all = list as ReturnType<typeof statement>[];
      const nextDays = new Map(days);
      const nextClients = new Map(clients);
      for (const s of all) {
        if (s.sql.startsWith('INSERT INTO client_counts')) {
          const [day, client, n, cap] = s.values as [string, string, number, number];
          const total = (nextClients.get(`${day}|${client}`) ?? 0) + n;
          if (total > cap) throw new Error('D1_ERROR: CHECK constraint failed');
          nextClients.set(`${day}|${client}`, total);
        }
        if (s.sql.startsWith('INSERT INTO daily_counts')) {
          const [day, n, cap] = s.values as [string, number, number];
          const total = (nextDays.get(day) ?? 0) + n;
          if (total > cap) throw new Error('D1_ERROR: CHECK constraint failed');
          nextDays.set(day, total);
        }
        if (s.sql.startsWith('INSERT INTO batches') && keys.has(s.values[0] as string)) throw new Error('D1_ERROR: UNIQUE constraint failed');
      }
      for (const [k, v] of nextDays) days.set(k, v);
      for (const [k, v] of nextClients) clients.set(k, v);
      for (const s of all) {
        executed.push(s.sql);
        if (s.sql.startsWith('INSERT INTO batches')) keys.add(s.values[0] as string);
        if (s.sql.startsWith('INSERT INTO reports')) rows.push(s.values);
        if (s.sql.startsWith('INSERT INTO meta')) meta.set('last_prune_ok', s.values[0] as string);
      }
      return all.map(() => ({ meta: { changes: 1 } }));
    },
  };
  return { db, rows, days, clients, meta, executed, failNext: () => (fail = true) };
}
const env = (db: D1Database, over: Partial<Env> = {}): Env => ({ DB: db, REPORTS_LIMITER: allow, RATE_LIMIT_SALT: 'pepper', ...over });

function post(body: unknown, headers: Record<string, string> = {}) {
  const text = typeof body === 'string' ? body : JSON.stringify(body);
  return new Request('https://reports.parzr.app/v1/reports', {
    method: 'POST',
    body: text,
    headers: { 'Content-Type': 'application/json', 'Idempotency-Key': KEY, 'CF-Connecting-IP': '203.0.113.9', ...headers },
  });
}

test('a valid report is accepted as sent', () => {
  assert.deepEqual(validateReport(report()), report());
});

test('only "Report wrong suggestion" is accepted: ignored and accepted suggestions are refused', () => {
  assert.equal(validateReport(report({ action: 'dismissed' })), null);
  assert.equal(validateReport(report({ action: 'accepted' })), null);
  assert.equal(validateReport(report({ action: 'REPORTED' })), null);
});

test('unknown fields, wrong types and bad offsets are refused', () => {
  assert.equal(validateReport({ ...report(), ip: '203.0.113.9' }), null, 'no extra fields');
  assert.equal(validateReport({ ...report(), suggestion: { ...report().suggestion, explanation: 'x' } }), null);
  const { app: _app, ...missing } = report();
  assert.equal(validateReport(missing), null, 'no missing fields');
  assert.equal(validateReport(report({ action: 'liked' })), null);
  assert.equal(validateReport(report({ model: 'gpt' })), null);
  assert.equal(validateReport(report({ app: 'my secret app' })), null);
  assert.equal(validateReport(report({ rule: 'rule with spaces' })), null);
  assert.equal(validateReport(report({ version: '' })), null);
  assert.equal(validateReport(report({ suggestion: { start: 17, end: 20, original: 'had', replacement: 'have' } })), null, 'original must match the sentence');
  assert.equal(validateReport(report({ suggestion: { start: 30, end: 99, original: 'has', replacement: 'have' } })), null);
  assert.equal(validateReport(report({ suggestion: { start: 1.5, end: 2, original: 'h', replacement: 'x' } })), null);
  assert.equal(validateReport(report({ sentence: '   ', suggestion: { start: 0, end: 0, original: '', replacement: 'x' } })), null);
  assert.equal(validateReport(report({ sentence: 'x'.repeat(LIMITS.sentence + 1) })), null);
  assert.equal(validateReport(null), null);
  assert.equal(validateReport([report()]), null);
});

test('malformed Unicode, control and bidirectional characters, and offsets inside a surrogate pair are refused', () => {
  const at = (sentence: string, start: number, end: number) => report({ sentence, suggestion: { start, end, original: sentence.slice(start, end), replacement: 'x' } });
  assert.equal(validateReport(at('a \uD800 b', 0, 1)), null, 'lone surrogate');
  assert.equal(validateReport(at('a \uDC00 b', 0, 1)), null, 'lone low surrogate');
  assert.equal(validateReport(at('a \u0085 b', 0, 1)), null, 'C1 control');
  assert.equal(validateReport(at('a \u0007 b', 0, 1)), null, 'C0 control');
  assert.equal(validateReport(at('a ‮ b', 0, 1)), null, 'bidi override');
  assert.equal(validateReport(at('a ⁦ b', 0, 1)), null, 'bidi isolate');
  assert.equal(validateReport(at('a ​ b', 0, 1)), null, 'zero-width space');
  assert.equal(validateReport(at('smile 😀 now', 7, 8)), null, 'an offset splitting the emoji');
  assert.ok(validateReport(at('smile 😀 now', 6, 8)), 'the whole emoji is fine');
  assert.ok(validateReport(at('line one\n\tline two', 0, 4)), 'tab and newline are fine');
  assert.ok(validateReport(at('family 👨‍👩‍👧 here', 0, 6)), 'emoji joiners are fine');
});

test('anything that still looks private is refused', () => {
  assert.equal(looksPrivate('call [phone] or [name] at [link] about [number] [email] [key]'), false);
  assert.equal(looksPrivate('I has a plan, e.g. this one; i.e. that.'), false);
  assert.equal(looksPrivate('one or two things'), false);
  assert.equal(looksPrivate('internationalization matters'), false);
  for (const leak of [
    'call 555', 'mail a@b.com', 'MAIL A@B.COM', 'see https://x', 'SEE HTTPS://X', 'at parzr.app now', 'at PARZR.APP now', 'www.example', '٣ cats',
    'visit example.museum', 'go to acme.engineering', 'my site is aman.photography', 'see bit.LY',
    'aman at gmail dot com', 'aman (at) gmail (dot) com', 'aman at gmail.com',
    'pin is four four two one', 'call nine eight seven', 'Seven-Two-Nine',
    'token ' + 'sk_' + 'live_abcdefghijk', 'gh' + 'p_abcdefghijklmnopqrstuv', 'xo' + 'xb-abc-def-ghi', 'key ' + 'AK' + 'IAABCDEFGHIJKLMNOP', 'jwt eyJhbGciOiJIUzI1NiJ9',
    'secret AbCdEfGhIjKlMnOpQrStUvWx', 'id abc_def_ghi_jkl_mno_pqr', 'tag #rahulsharma', 'ping @rahul',
  ]) assert.equal(looksPrivate(leak), true, leak);
  assert.equal(validateReport(report({ sentence: 'I has 2 dogs.', suggestion: { start: 2, end: 5, original: 'has', replacement: 'have' } })), null);
  assert.equal(validateReport(report({ suggestion: { start: 17, end: 20, original: 'has', replacement: 'have 5' } })), null);
});

test('the email check stays fast on long runs of word characters', () => {
  const nasty = 'a'.repeat(LIMITS.sentence - 1) + '@';
  const started = performance.now();
  for (let i = 0; i < 50; i++) looksPrivate(nasty), looksPrivate('a.'.repeat(500)), looksPrivate('a'.repeat(1000));
  assert.ok(performance.now() - started < 500, 'well under the CPU limit for a full batch');
});

test('batches: malformed bodies are rejected, bad reports dropped', () => {
  assert.deepEqual(validateBatch('{'), { ok: false, status: 400, error: 'invalid JSON' });
  assert.equal((validateBatch('[]') as { status: number }).status, 400);
  assert.equal((validateBatch('{"reports":[]}') as { status: number }).status, 400);
  assert.equal((validateBatch(JSON.stringify({ reports: [report()], extra: 1 })) as { status: number }).status, 400);
  assert.equal((validateBatch(JSON.stringify({ reports: Array(LIMITS.reportsPerBatch + 1).fill(report()) })) as { status: number }).status, 413);
  assert.equal((validateBatch('x'.repeat(LIMITS.bodyBytes + 1)) as { status: number }).status, 413);
  const mixed = validateBatch(JSON.stringify({ reports: [report(), report({ action: 'dismissed' })] }));
  assert.ok(mixed.ok);
  assert.equal(mixed.reports.length, 1);
  assert.equal(mixed.dropped, 1);
});

test('POST stores reports with the day only, and never the address', async () => {
  const { db, rows, days, clients } = fakeDB();
  const response = await handleReports(post({ reports: [report(), report()] }), env(db), new Date('2026-10-19T15:04:05Z'));
  assert.equal(response.status, 202);
  assert.deepEqual(await response.json(), { stored: 2, dropped: 0 });
  assert.equal(rows.length, 2);
  assert.deepEqual(rows[0], ['2026-10-19', report().sentence, 17, 20, 'has', 'have', 'grammar.i_agreement', 'rules', 'reported', 'com.tinyspeck.slackmacgap', '0.5.0']);
  assert.equal(days.get('2026-10-19'), 2);
  const [[clientKey, clientRows]] = [...clients];
  assert.match(clientKey, /^2026-10-19\|[0-9a-f]{32}$/, 'the per-client counter is keyed by the day and a salted hash');
  assert.equal(clientRows, 2);
  assert.ok(!clientKey.includes('203'));
  assert.ok(!JSON.stringify(rows).includes('203.0.113.9'));
  assert.ok(!JSON.stringify(rows).includes('15:04'));
});

test('a retried batch is stored once', async () => {
  const { db, rows } = fakeDB();
  assert.equal((await handleReports(post({ reports: [report()] }), env(db))).status, 202);
  const again = await handleReports(post({ reports: [report()] }), env(db));
  assert.equal(again.status, 200);
  assert.deepEqual(await again.json(), { stored: 0, duplicate: true });
  assert.equal(rows.length, 1);
});

test('the daily row cap answers 503 until midnight UTC and stores nothing past it', async () => {
  const { db, rows } = fakeDB();
  const capped = env(db, { DAILY_ROW_CAP: '3' });
  const now = new Date('2026-10-19T23:00:00Z');
  assert.equal((await handleReports(post({ reports: [report(), report()] }), capped, now)).status, 202);
  const full = await handleReports(post({ reports: [report(), report()] }, { 'Idempotency-Key': KEY2 }), capped, now);
  assert.equal(full.status, 503);
  assert.equal(full.headers.get('Retry-After'), '3600');
  assert.equal(rows.length, 2);
  assert.equal((await handleReports(post({ reports: [report()] }, { 'Idempotency-Key': KEY2 }), capped, now)).status, 202, 'what still fits is stored');
  assert.equal(rows.length, 3);
});

test('the per-client quota stops one client at its quota with 429, and only that client', async () => {
  const { db, rows, days } = fakeDB();
  const quota = env(db, { CLIENT_DAILY_ROW_CAP: '3' });
  const now = new Date('2026-10-19T23:00:00Z');
  const from = (ip: string, n: number) => handleReports(post({ reports: Array.from({ length: n }, () => report()) }, { 'Idempotency-Key': crypto.randomUUID(), 'CF-Connecting-IP': ip }), quota, now);
  assert.equal((await from('203.0.113.7', 2)).status, 202);
  const over = await from('203.0.113.7', 2);
  assert.equal(over.status, 429);
  assert.deepEqual(await over.json(), { error: 'daily quota reached' });
  assert.equal(over.headers.get('Retry-After'), '3600', 'until midnight UTC');
  assert.equal((await from('203.0.113.7', 1)).status, 202, 'what still fits the quota is stored');
  assert.equal((await from('203.0.113.7', 1)).status, 429);
  assert.equal((await from('198.51.100.20', 3)).status, 202, 'another network is unaffected');
  assert.equal(rows.length, 6);
  assert.equal(days.get('2026-10-19'), 6, 'refused batches never reached the global counter');
  assert.equal((await handleReports(post({ reports: [report()] }, { 'Idempotency-Key': crypto.randomUUID(), 'CF-Connecting-IP': '203.0.113.7' }), quota, new Date('2026-10-20T00:00:01Z'))).status, 202, 'a new day, a new quota');
});

test('a request without a usable client address is refused, unless local development allows it', async () => {
  const { db, rows } = fakeDB();
  const missing = () => new Request('https://reports.parzr.app/v1/reports', { method: 'POST', body: JSON.stringify({ reports: [report()] }), headers: { 'Content-Type': 'application/json', 'Idempotency-Key': KEY } });
  const refused = await handleReports(missing(), env(db));
  assert.equal(refused.status, 503);
  assert.deepEqual(await refused.json(), { error: 'client address unavailable' });
  assert.equal((await handleReports(post({ reports: [report()] }, { 'CF-Connecting-IP': '   ' }), env(db))).status, 503);
  const invalid = await handleReports(post({ reports: [report()] }, { 'CF-Connecting-IP': 'nonsense' }), env(db));
  assert.equal(invalid.status, 400);
  assert.deepEqual(await invalid.json(), { error: 'invalid client address' });
  assert.equal(rows.length, 0, 'nothing stored, nothing counted');
  // The limiter is never consulted for a refused request: there is no shared "unknown" bucket in production.
  const keys: string[] = [];
  const watching = env(db, { REPORTS_LIMITER: { limit: async ({ key }) => (keys.push(key), { success: true }) } });
  await handleReports(missing(), watching);
  assert.equal(keys.length, 0);
  assert.equal((await handleReports(missing(), { ...watching, ALLOW_MISSING_CLIENT_IP: '1' })).status, 202, 'local development opts in');
  assert.equal(keys.length, 1);
  assert.equal(rows.length, 1);
  assert.equal((await handleReports(post({ reports: [report()] }, { 'CF-Connecting-IP': 'nonsense', 'Idempotency-Key': KEY2 }), { ...watching, ALLOW_MISSING_CLIENT_IP: 'yes' })).status, 400, 'only "1" opts in');
});

test('requests are checked before anything is stored', async () => {
  const { db, rows } = fakeDB();
  assert.equal((await handleReports(post({ reports: [report()] }, { 'Content-Type': 'text/plain' }), env(db))).status, 415);
  assert.equal((await handleReports(post({ reports: [report()] }, { 'Idempotency-Key': 'not-a-uuid' }), env(db))).status, 400);
  assert.equal((await handleReports(post('x'.repeat(LIMITS.bodyBytes + 10)), env(db))).status, 413);
  assert.equal((await handleReports(new Request('https://reports.parzr.app/v1/reports'), env(db))).status, 405);
  assert.equal(rows.length, 0);
});

test('without its rate limiter or salt the Worker stores nothing', async () => {
  const { db, rows } = fakeDB();
  for (const broken of [env(db, { REPORTS_LIMITER: undefined }), env(db, { RATE_LIMIT_SALT: undefined }), env(db, { RATE_LIMIT_SALT: '' })]) {
    const response = await handleReports(post({ reports: [report()] }), broken);
    assert.equal(response.status, 503);
  }
  assert.equal(rows.length, 0);
});

test('rate limiting keys on a salted hash of the IPv4 address or IPv6 /64, never the address', async () => {
  const { db } = fakeDB();
  const seen: string[] = [];
  let ok = true;
  const limited = env(db, { REPORTS_LIMITER: { limit: async ({ key }) => (seen.push(key), { success: ok }) } });
  assert.equal((await handleReports(post({ reports: [report()] }), limited)).status, 202);
  ok = false;
  const refused = await handleReports(post({ reports: [report()] }, { 'Idempotency-Key': KEY2 }), limited);
  assert.equal(refused.status, 429);
  assert.equal(refused.headers.get('Retry-After'), '120');
  assert.match(seen[0], /^[0-9a-f]{32}$/);
  assert.ok(!seen[0].includes('203'));
  // Two addresses in one /64 share a key; another /64 does not.
  ok = true;
  seen.length = 0;
  for (const ip of ['2001:db8:1:2::1', '2001:0db8:0001:0002:ffff:ffff:ffff:ffff', '2001:db8:1:3::1']) {
    await handleReports(post({ reports: [report()] }, { 'CF-Connecting-IP': ip, 'Idempotency-Key': crypto.randomUUID() }), limited);
  }
  assert.equal(seen[0], seen[1]);
  assert.notEqual(seen[0], seen[2]);
});

test('the rate-limit subject', () => {
  assert.equal(limitSubject('203.0.113.9'), '203.0.113.9');
  assert.equal(limitSubject('2001:db8:1:2:3:4:5:6'), '2001:db8:1:2::/64');
  assert.equal(limitSubject('2001:DB8:0001:0002::'), '2001:db8:1:2::/64');
  assert.equal(limitSubject('2001:db8::1'), '2001:db8:0:0::/64');
  assert.equal(limitSubject('::1'), '0:0:0:0::/64');
  assert.equal(limitSubject('::ffff:198.51.100.7'), '198.51.100.7');
  assert.equal(limitSubject('64:ff9b::198.51.100.7'), '64:ff9b:0:0::/64');
  for (const bad of [null, '', 'nonsense', '1:2:3', '1::2::3', '1:2:3:4:5:6:7:8:9', '12345::1']) assert.equal(limitSubject(bad), 'unknown', String(bad));
});

test('a database failure asks the app to retry later', async () => {
  const { db, failNext } = fakeDB();
  failNext();
  const response = await handleReports(post({ reports: [report()] }), env(db));
  assert.equal(response.status, 503);
  assert.equal(response.headers.get('Retry-After'), '300');
});

test('routing, HEAD and the health check', async () => {
  const { db } = fakeDB();
  const e = env(db, { CF_VERSION_METADATA: { id: 'v-123' } });
  const get = await worker.fetch(new Request('https://reports.parzr.app/v1/health'), e);
  assert.equal(get.status, 200);
  assert.deepEqual(await get.json(), { ok: true, version: 'v-123', database: 'ok', oldest: 'empty', last_prune_ok: null, prune: 'ok' });
  const head = await worker.fetch(new Request('https://reports.parzr.app/v1/health', { method: 'HEAD' }), e);
  assert.equal(head.status, 200);
  assert.equal(await head.text(), '');
  assert.equal((await worker.fetch(new Request('https://reports.parzr.app/v1/health', { method: 'POST' }), e)).status, 405);
  for (const path of ['/index.html', '/v1', '/v1/report', '/favicon.ico', '/v2/reports']) assert.equal((await worker.fetch(new Request(`https://reports.parzr.app${path}`), e)).status, 404, path);
  const broken = fakeDB();
  broken.failNext();
  const down = await worker.fetch(new Request('https://reports.parzr.app/v1/health'), env(broken.db));
  assert.equal(down.status, 503);
  assert.equal((await down.json() as { database: string }).database, 'unavailable');
});

test('the root explains the endpoint in plain text, with nothing to run', async () => {
  const { db } = fakeDB();
  const root = await worker.fetch(new Request('https://reports.parzr.app/'), env(db));
  assert.equal(root.status, 200);
  assert.equal(root.headers.get('Content-Type'), 'text/plain; charset=utf-8');
  assert.equal(root.headers.get('Cache-Control'), 'no-store');
  assert.match(root.headers.get('Content-Security-Policy') ?? '', /default-src 'none'/);
  const text = await root.text();
  assert.equal(text, ABOUT);
  assert.match(text, /only when you click “Report wrong suggestion”/);
  assert.match(text, /https:\/\/parzr\.app\/privacy/);
  assert.match(text, /\/v1\/health/);
  const head = await worker.fetch(new Request('https://reports.parzr.app/', { method: 'HEAD' }), env(db));
  assert.equal(head.status, 200);
  assert.equal(await head.text(), '');
  assert.equal((await worker.fetch(new Request('https://reports.parzr.app/', { method: 'POST' }), env(db))).status, 405);
});

test('health reports a stale clean-up', async () => {
  const { db } = fakeDB();
  await handleReports(post({ reports: [report()] }), env(db), new Date('2026-10-01T10:00:00Z'));
  const late = await (await health(env(db), new Date('2026-10-19T10:00:00Z'))).json() as Record<string, unknown>;
  assert.equal(late.oldest, 'under-31-days');
  assert.equal(late.prune, 'stale', 'no clean-up recorded for weeks');
  await prune(env(db), new Date('2026-10-19T03:17:00Z'));
  const fresh = await (await health(env(db), new Date('2026-10-19T10:00:00Z'))).json() as Record<string, unknown>;
  assert.equal(fresh.last_prune_ok, '2026-10-19');
  assert.equal(fresh.prune, 'ok');
});

test('age bands', () => {
  const now = new Date('2026-10-19T12:00:00Z');
  assert.equal(ageBand(null, now, 180), 'empty');
  assert.equal(ageBand('2026-10-19', now, 180), 'under-8-days');
  assert.equal(ageBand('2026-10-01', now, 180), 'under-31-days');
  assert.equal(ageBand('2026-08-01', now, 180), 'under-91-days');
  assert.equal(ageBand('2026-06-01', now, 180), 'under-181-days');
  assert.equal(ageBand('2026-01-01', now, 180), 'over-retention');
});

test('the daily prune', async () => {
  const { db, executed } = fakeDB();
  await prune(env(db, { RETENTION_DAYS: '30' }), new Date('2026-10-19T03:17:00Z'));
  assert.deepEqual(executed.map((s) => s.split(' ').slice(0, 3).join(' ')), ['DELETE FROM reports', 'DELETE FROM batches', 'DELETE FROM daily_counts', 'DELETE FROM client_counts', 'INSERT INTO meta']);
  const failing = fakeDB();
  failing.failNext();
  await assert.rejects(worker.scheduled({}, env(failing.db)), 'a failed clean-up fails the cron run instead of vanishing in waitUntil');
});
