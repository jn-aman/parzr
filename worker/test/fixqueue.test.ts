import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { build, isoWeek, previousWeek, toJSONL, toMarkdown, weekRange, type Row } from '../src/fixqueue.ts';

const row = (over: Partial<Row> = {}): Row => ({
  received_day: '2026-10-14',
  sentence: 'I has [number] dogs.',
  start_utf16: 2,
  end_utf16: 5,
  original: 'has',
  replacement: 'have',
  rule: 'grammar.i_agreement',
  model: 'rules',
  action: 'reported',
  app: 'com.apple.mail',
  version: '0.5.0',
  ...over,
});

test('ISO weeks', () => {
  assert.equal(isoWeek(new Date('2026-10-19T00:00:00Z')), '2026-W43');
  assert.equal(isoWeek(new Date('2027-01-01T00:00:00Z')), '2026-W53');
  assert.deepEqual(weekRange('2026-W42'), { from: '2026-10-12', to: '2026-10-18' });
  assert.deepEqual(weekRange('2026-W01'), { from: '2025-12-29', to: '2026-01-04' });
  assert.equal(previousWeek(new Date('2026-10-19T09:00:00Z')), '2026-W42');
  assert.throws(() => weekRange('2026-42'));
  assert.throws(() => weekRange('2025-W53'));
});

test('suggestions are grouped, scored and ranked', () => {
  const rows = [
    row(), row({ action: 'dismissed', sentence: 'So I has a plan.', start_utf16: 5, end_utf16: 8 }), row({ action: 'accepted', app: 'com.apple.Notes' }),
    row({ rule: 'spelling.typo', original: 'teh', replacement: 'the', action: 'dismissed', sentence: 'teh end', start_utf16: 0, end_utf16: 3 }),
    // Accepted far more than turned down: the rule works, so it stays out of the queue.
    ...Array.from({ length: 4 }, () => row({ rule: 'spelling.good', original: 'recieve', replacement: 'receive', action: 'accepted', sentence: 'I recieve it.', start_utf16: 2, end_utf16: 9 })),
    row({ rule: 'spelling.good', original: 'recieve', replacement: 'receive', action: 'dismissed', sentence: 'I recieve it.', start_utf16: 2, end_utf16: 9 }),
  ];
  const entries = build(rows, '2026-W42');
  assert.deepEqual(entries.map((e) => e.rule), ['grammar.i_agreement', 'spelling.typo']);
  const top = entries[0];
  assert.equal(top.id, '2026-W42-001');
  assert.deepEqual(top.counts, { reported: 1, dismissed: 1, accepted: 1 });
  assert.equal(top.score, 3.5);
  assert.equal(top.wrong_rate, 0.67);
  assert.deepEqual(top.apps, { 'com.apple.mail': 2, 'com.apple.Notes': 1 });
  assert.equal(top.examples[0].action, 'reported', 'reported sentences come first');
  assert.equal(top.examples.length, 2, 'repeated sentences are listed once');
  assert.equal(top.item.text, 'I has [number] dogs.');
  assert.equal(top.item.expected, null);
  const lines = toJSONL(entries).trim().split('\n');
  assert.equal(lines.length, 2);
  assert.equal(JSON.parse(lines[1]).rule, 'spelling.typo');
  const md = toMarkdown(entries, '2026-W42', rows.length);
  assert.match(md, /# Parzr fix queue 2026-W42/);
  assert.match(md, /2026-10-12 to 2026-10-18: 9 reports, 2 suggestions/);
  assert.match(md, /\| 001 \| 3.5 \| `grammar.i_agreement` \| rules \| has → have \| 1 \| 1 \| 1 \| 67% \|/);
});

test('the export script writes the week from an input file', () => {
  const dir = mkdtempSync(join(tmpdir(), 'parzr-fixqueue-'));
  const input = join(dir, 'rows.json');
  writeFileSync(input, JSON.stringify([row(), row({ received_day: '2026-10-20' })]));
  const out = execFileSync(process.execPath, [join(import.meta.dirname, '../scripts/export-fix-queue.ts'), '--week', '2026-W42', '--input', input, '--out', dir], { encoding: 'utf8' });
  assert.match(out, /1 reports, 1 entries/);
  const lines = readFileSync(join(dir, '2026-W42.jsonl'), 'utf8').trim().split('\n');
  assert.equal(lines.length, 1);
  assert.ok(readFileSync(join(dir, '2026-W42.md'), 'utf8').startsWith('# Parzr fix queue 2026-W42'));
});
