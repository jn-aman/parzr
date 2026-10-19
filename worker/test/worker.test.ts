import { test } from 'node:test';
import assert from 'node:assert/strict';
import worker, { handleReports, prune, type D1Database, type D1PreparedStatement, type Env } from '../src/index.ts';
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

/** An in-memory D1 that records statements and enforces the batches primary key like SQLite. */
function fakeDB() {
  const rows: unknown[][] = [];
  const keys = new Set<string>();
  const executed: string[] = [];
  let fail = false;
  const statement = (sql: string, values: unknown[] = []): D1PreparedStatement & { sql: string; values: unknown[] } => ({
    sql,
    values,
    bind: (...v: unknown[]) => statement(sql, v),
    run: async () => ({ meta: { changes: 1 } }),
  });
  const db: D1Database = {
    prepare: (sql) => statement(sql),
    batch: async (list) => {
      if (fail) throw new Error('D1_ERROR: network');
      const all = list as ReturnType<typeof statement>[];
      const batchKey = all.find((s) => s.sql.startsWith('INSERT INTO batches'))?.values[0] as string | undefined;
      if (batchKey && keys.has(batchKey)) throw new Error('D1_ERROR: UNIQUE constraint failed: batches.key: SQLITE_CONSTRAINT');
      if (batchKey) keys.add(batchKey);
      for (const s of all) {
        executed.push(s.sql);
        if (s.sql.startsWith('INSERT INTO reports')) rows.push(s.values);
      }
      return all.map(() => ({ meta: { changes: 1 } }));
    },
  };
  return { db, rows, executed, failNext: () => (fail = true) };
}

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
  assert.equal(validateReport(report({ sentence: '   ' , suggestion: { start: 0, end: 0, original: '', replacement: 'x' } })), null);
  assert.equal(validateReport(report({ sentence: 'x'.repeat(LIMITS.sentence + 1) })), null);
  assert.equal(validateReport(null), null);
  assert.equal(validateReport([report()]), null);
});

test('anything that still looks private is refused', () => {
  assert.equal(looksPrivate('call [phone] or [name] at [link] about [number] [email]'), false);
  for (const leak of ['call 555', 'mail a@b.com', 'see https://x', 'at parzr.app now', 'www.example', '٣ cats']) assert.equal(looksPrivate(leak), true, leak);
  assert.equal(validateReport(report({ sentence: 'I has 2 dogs.', suggestion: { start: 2, end: 5, original: 'has', replacement: 'have' } })), null);
  assert.equal(validateReport(report({ suggestion: { start: 17, end: 20, original: 'has', replacement: 'have 5' } })), null);
});

test('batches: malformed bodies are rejected, bad reports dropped', () => {
  assert.deepEqual(validateBatch('{'), { ok: false, status: 400, error: 'invalid JSON' });
  assert.equal((validateBatch('[]') as { status: number }).status, 400);
  assert.equal((validateBatch('{"reports":[]}') as { status: number }).status, 400);
  assert.equal((validateBatch(JSON.stringify({ reports: [report()], extra: 1 })) as { status: number }).status, 400);
  assert.equal((validateBatch(JSON.stringify({ reports: Array(LIMITS.reportsPerBatch + 1).fill(report()) })) as { status: number }).status, 413);
  assert.equal((validateBatch('x'.repeat(LIMITS.bodyBytes + 1)) as { status: number }).status, 413);
  const mixed = validateBatch(JSON.stringify({ reports: [report(), report({ action: 'nope' })] }));
  assert.ok(mixed.ok);
  assert.equal(mixed.reports.length, 1);
  assert.equal(mixed.dropped, 1);
});

test('POST stores reports with the day only, and never the address', async () => {
  const { db, rows } = fakeDB();
  const response = await handleReports(post({ reports: [report(), report({ action: 'dismissed' })] }), { DB: db }, new Date('2026-10-19T15:04:05Z'));
  assert.equal(response.status, 202);
  assert.deepEqual(await response.json(), { stored: 2, dropped: 0 });
  assert.equal(rows.length, 2);
  assert.deepEqual(rows[0], ['2026-10-19', report().sentence, 17, 20, 'has', 'have', 'grammar.i_agreement', 'rules', 'reported', 'com.tinyspeck.slackmacgap', '0.5.0']);
  assert.ok(!JSON.stringify(rows).includes('203.0.113.9'));
  assert.ok(!JSON.stringify(rows).includes('15:04'));
});

test('a retried batch is stored once', async () => {
  const { db, rows } = fakeDB();
  const env: Env = { DB: db };
  assert.equal((await handleReports(post({ reports: [report()] }), env)).status, 202);
  const again = await handleReports(post({ reports: [report()] }), env);
  assert.equal(again.status, 200);
  assert.deepEqual(await again.json(), { stored: 0, duplicate: true });
  assert.equal(rows.length, 1);
});

test('requests are checked before anything is stored', async () => {
  const { db, rows } = fakeDB();
  const env: Env = { DB: db };
  assert.equal((await handleReports(post({ reports: [report()] }, { 'Content-Type': 'text/plain' }), env)).status, 415);
  assert.equal((await handleReports(post({ reports: [report()] }, { 'Idempotency-Key': 'not-a-uuid' }), env)).status, 400);
  assert.equal((await handleReports(post('x'.repeat(LIMITS.bodyBytes + 10)), env)).status, 413);
  assert.equal((await handleReports(new Request('https://reports.parzr.app/v1/reports'), env)).status, 405);
  assert.equal(rows.length, 0);
});

test('rate limiting keys on a salted hash, never the address', async () => {
  const { db } = fakeDB();
  const seen: string[] = [];
  let allow = true;
  const env: Env = { DB: db, RATE_LIMIT_SALT: 'pepper', REPORTS_LIMITER: { limit: async ({ key }) => (seen.push(key), { success: allow }) } };
  assert.equal((await handleReports(post({ reports: [report()] }), env)).status, 202);
  allow = false;
  const limited = await handleReports(post({ reports: [report()] }, { 'Idempotency-Key': '1f8fad5b-d9cb-469f-a165-70867728950e' }), env);
  assert.equal(limited.status, 429);
  assert.equal(limited.headers.get('Retry-After'), '120');
  assert.match(seen[0], /^[0-9a-f]{32}$/);
  assert.ok(!seen[0].includes('203'));
});

test('a database failure asks the app to retry later', async () => {
  const { db, failNext } = fakeDB();
  failNext();
  const response = await handleReports(post({ reports: [report()] }), { DB: db });
  assert.equal(response.status, 503);
  assert.equal(response.headers.get('Retry-After'), '300');
});

test('routing and the daily prune', async () => {
  const { db, executed } = fakeDB();
  const env: Env = { DB: db, RETENTION_DAYS: '30' };
  assert.equal((await worker.fetch(new Request('https://reports.parzr.app/v1/health'), env)).status, 200);
  assert.equal((await worker.fetch(new Request('https://reports.parzr.app/'), env)).status, 404);
  await prune(env, new Date('2026-10-19T03:17:00Z'));
  assert.deepEqual(executed, ['DELETE FROM reports WHERE received_day < ?', 'DELETE FROM batches WHERE received_day < ?']);
});
