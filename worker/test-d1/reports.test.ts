// Runs inside workerd against a real local D1 database built from migrations/ (see vitest.config.ts).
import { applyD1Migrations, env, reset } from 'cloudflare:test';
import { beforeEach, describe, expect, it } from 'vitest';
import worker, { prune, store, type Env } from '../src/index.ts';
import type { Report } from '../src/validate.ts';

const report = (over: Partial<Report> = {}): Report => ({
  sentence: 'Thanks [name], I has [number] questions.',
  suggestion: { start: 17, end: 20, original: 'has', replacement: 'have' },
  rule: 'grammar.i_agreement',
  model: 'rules',
  action: 'reported',
  app: 'com.apple.mail',
  version: '0.6.0',
  ...over,
});
let address = 0;
/** Each request from its own address, so the 4-a-minute limit (a real binding here) stays out of the way. */
function post(reports: unknown[], key: string = crypto.randomUUID(), ip = `198.51.100.${++address % 250}`) {
  return worker.fetch(
    new Request('https://reports.parzr.app/v1/reports', {
      method: 'POST',
      body: JSON.stringify({ reports }),
      headers: { 'Content-Type': 'application/json', 'Idempotency-Key': key, 'CF-Connecting-IP': ip },
    }),
    env as unknown as Env,
  );
}
const count = async (sql = 'SELECT COUNT(*) AS n FROM reports') => ((await env.DB.prepare(sql).first<{ n: number }>())?.n ?? 0);

beforeEach(async () => {
  await reset();
  await applyD1Migrations(env.DB, env.TEST_MIGRATIONS);
});

describe('schema', () => {
  it('applies every migration, adds the counter, meta table and trigger, and drops the unused index', async () => {
    const { results } = await env.DB.prepare("SELECT type, name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' AND name NOT LIKE '_cf_%' ORDER BY type, name").all<{ type: string; name: string }>();
    const names = results.map((r) => `${r.type}:${r.name}`);
    expect(names).toEqual(expect.arrayContaining(['table:reports', 'table:batches', 'table:daily_counts', 'table:meta', 'index:reports_by_day', 'index:batches_by_day', 'trigger:reports_reported_only']));
    expect(names).not.toContain('index:reports_by_rule');
  });

  it('CHECK constraints and the trigger refuse rows the Worker would never write', async () => {
    const insert = (over: Record<string, unknown>) => {
      const row = { received_day: '2026-10-19', sentence: 'I has it.', start_utf16: 2, end_utf16: 5, original: 'has', replacement: 'have', rule: 'r', model: 'rules', action: 'reported', app: 'a.b', version: '1', ...over };
      return env.DB.prepare(`INSERT INTO reports (${Object.keys(row).join(', ')}) VALUES (${Object.keys(row).map(() => '?').join(', ')})`).bind(...Object.values(row)).run();
    };
    await expect(insert({})).resolves.toBeTruthy();
    await expect(insert({ action: 'dismissed' })).rejects.toThrow(/only reported/);
    await expect(insert({ action: 'accepted' })).rejects.toThrow();
    await expect(insert({ sentence: '' })).rejects.toThrow(/CHECK/);
    await expect(insert({ sentence: 'x'.repeat(1001) })).rejects.toThrow(/CHECK/);
    await expect(insert({ end_utf16: 1 })).rejects.toThrow(/CHECK/);
    await expect(insert({ received_day: '2026-10-1' })).rejects.toThrow(/CHECK/);
    await expect(insert({ version: 'x'.repeat(33) })).rejects.toThrow(/CHECK/);
    await expect(env.DB.prepare('INSERT INTO daily_counts (day, rows, cap) VALUES (?, ?, ?)').bind('2026-10-19', 11, 10).run()).rejects.toThrow(/CHECK/);
    expect(await count()).toBe(1);
  });
});

describe('POST /v1/reports', () => {
  it('stores a batch with its day, counts it, and stores a retried batch once', async () => {
    const key = crypto.randomUUID();
    const first = await post([report(), report()], key);
    expect(first.status).toBe(202);
    expect(await first.json()).toEqual({ stored: 2, dropped: 0 });
    const again = await post([report(), report()], key);
    expect(again.status).toBe(200);
    expect(await again.json()).toEqual({ stored: 0, duplicate: true });
    expect(await count()).toBe(2);
    expect(await count('SELECT rows AS n FROM daily_counts')).toBe(2);
    const row = await env.DB.prepare('SELECT * FROM reports LIMIT 1').first<Record<string, unknown>>();
    expect(Object.keys(row ?? {}).sort()).toEqual(['action', 'app', 'end_utf16', 'id', 'model', 'original', 'received_day', 'replacement', 'rule', 'sentence', 'start_utf16', 'version']);
    expect(JSON.stringify(row)).not.toContain('198.51.100');
  });

  it('a retry that races its first attempt is told apart by reading the database, not by the error text', async () => {
    const key = crypto.randomUUID();
    expect((await post([report()], key)).status).toBe(202);
    // The first read misses the stored key (as if both attempts read before either wrote); the insert then fails.
    let reads = 0;
    const racing = {
      ...(env as unknown as Env),
      DB: {
        prepare: (sql: string) => {
          const real = env.DB.prepare(sql);
          if (!sql.startsWith('SELECT (SELECT 1 FROM batches')) return real;
          return { bind: (...v: unknown[]) => { const bound = real.bind(...v); return { ...bound, first: async () => (reads++ === 0 ? { seen: null, used: 0 } : bound.first()) }; } };
        },
        batch: (statements: unknown[]) => env.DB.batch(statements as D1PreparedStatement[]),
      },
    } as unknown as Env;
    expect(await store(racing, key, [report()], new Date().toISOString().slice(0, 10))).toBe('duplicate');
    expect(await count()).toBe(1);
    expect(await count('SELECT rows AS n FROM daily_counts'), 'the failed batch rolled its count back').toBe(1);
  });

  it('drops ignored suggestions and anything private, and stores the rest', async () => {
    const response = await post([report(), report({ action: 'dismissed' as Report['action'] }), report({ sentence: 'mail a@b.co about it', suggestion: { start: 0, end: 4, original: 'mail', replacement: 'Mail' } })]);
    expect(await response.json()).toEqual({ stored: 1, dropped: 2 });
    expect(await count()).toBe(1);
  });

  it('the daily row cap: past it nothing is stored and the Worker answers 503 until midnight UTC', async () => {
    // DAILY_ROW_CAP is 60 in vitest.config.ts.
    const batch = Array.from({ length: 25 }, () => report());
    expect((await post(batch)).status).toBe(202);
    expect((await post(batch)).status).toBe(202);
    const full = await post(batch);
    expect(full.status).toBe(503);
    expect(Number(full.headers.get('Retry-After'))).toBeGreaterThan(0);
    expect(await count()).toBe(50);
    expect((await post(batch.slice(0, 10))).status).toBe(202);
    expect(await count()).toBe(60);
    expect((await post([report()])).status).toBe(503);
    expect(await count('SELECT rows AS n FROM daily_counts')).toBe(60);
  });

  it('the rate limit counts an IPv6 /64 as one client', async () => {
    const statuses: number[] = [];
    for (let i = 0; i < 6; i++) statuses.push((await post([report()], crypto.randomUUID(), `2001:db8:77:1::${i + 1}`)).status);
    expect(statuses.filter((s) => s === 429).length).toBeGreaterThan(0);
    expect((await post([report()], crypto.randomUUID(), '2001:db8:77:2::1')).status).toBe(202);
  });
});

describe('retention and health', () => {
  it('prunes old reports, batch keys and counters, and records the day it worked', async () => {
    const now = new Date('2026-10-19T03:17:00Z');
    const add = (day: string) =>
      env.DB.prepare("INSERT INTO reports (received_day, sentence, start_utf16, end_utf16, original, replacement, rule, model, action, app, version) VALUES (?, 'I has it.', 2, 5, 'has', 'have', 'r', 'rules', 'reported', 'a.b', '1')").bind(day).run();
    for (const day of ['2026-04-01', '2026-04-21', '2026-04-22', '2026-10-18']) await add(day);
    await env.DB.prepare('INSERT INTO batches (key, received_day) VALUES (?, ?), (?, ?)').bind('old', '2026-10-01', 'new', '2026-10-10').run();
    await env.DB.prepare('INSERT INTO daily_counts (day, rows, cap) VALUES (?, 1, 10), (?, 1, 10)').bind('2026-10-01', '2026-10-10').run();
    await prune(env as unknown as Env, now);
    const days = (await env.DB.prepare('SELECT received_day FROM reports ORDER BY received_day').all<{ received_day: string }>()).results.map((r) => r.received_day);
    expect(days, '180 days back from 2026-10-19 is 2026-04-22').toEqual(['2026-04-22', '2026-10-18']);
    expect((await env.DB.prepare('SELECT key FROM batches').all<{ key: string }>()).results.map((r) => r.key)).toEqual(['new']);
    expect(await count('SELECT COUNT(*) AS n FROM daily_counts')).toBe(1);
    expect((await env.DB.prepare("SELECT value FROM meta WHERE key = 'last_prune_ok'").first<{ value: string }>())?.value).toBe('2026-10-19');
  });

  it('the scheduled handler awaits the clean-up', async () => {
    await worker.scheduled({}, env as unknown as Env);
    expect(await count("SELECT COUNT(*) AS n FROM meta WHERE key = 'last_prune_ok'")).toBe(1);
  });

  it('health reads the database and reports the oldest row band and the clean-up', async () => {
    const empty = await worker.fetch(new Request('https://reports.parzr.app/v1/health'), env as unknown as Env);
    expect(empty.status).toBe(200);
    const body = (await empty.json()) as Record<string, unknown>;
    expect(body).toMatchObject({ ok: true, database: 'ok', oldest: 'empty', last_prune_ok: null, prune: 'ok' });
    expect(typeof body.version).toBe('string');
    await env.DB.prepare("INSERT INTO reports (received_day, sentence, start_utf16, end_utf16, original, replacement, rule, model, action, app, version) VALUES ('2025-01-01', 'I has it.', 2, 5, 'has', 'have', 'r', 'rules', 'reported', 'a.b', '1')").run();
    const stale = (await (await worker.fetch(new Request('https://reports.parzr.app/v1/health'), env as unknown as Env)).json()) as Record<string, unknown>;
    expect(stale).toMatchObject({ oldest: 'over-retention', prune: 'stale' });
    const head = await worker.fetch(new Request('https://reports.parzr.app/v1/health', { method: 'HEAD' }), env as unknown as Env);
    expect(head.status).toBe(200);
  });
});
