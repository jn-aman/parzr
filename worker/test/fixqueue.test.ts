import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { build, DAY_CAP, isoWeek, previousWeek, toJSONL, toMarkdown, weekRange, type Row } from '../src/fixqueue.ts';

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
  const typo = { rule: 'spelling.typo', original: 'teh', replacement: 'the', start_utf16: 0, end_utf16: 3 };
  const rows = [
    // has -> have: three distinct sentences over two days.
    row(), row({ sentence: 'So I has a plan.', start_utf16: 5, end_utf16: 8 }), row({ received_day: '2026-10-15', app: 'com.apple.Notes' }),
    // teh -> the: one sentence sent five times on one day (a retry storm or a script) counts once.
    ...Array.from({ length: 5 }, () => row({ ...typo, sentence: 'teh end' })),
    // Ignored suggestions are no longer reported; old rows are skipped.
    row({ action: 'dismissed', sentence: 'I has it.' }),
    row({ action: 'dismissed', rule: 'style.other', original: 'x', replacement: 'y', sentence: 'x y' }),
  ];
  const entries = build(rows, '2026-W42');
  assert.deepEqual(entries.map((e) => e.rule), ['grammar.i_agreement', 'spelling.typo']);
  const top = entries[0];
  assert.equal(top.id, '2026-W42-001');
  assert.deepEqual(top.counts, { reported: 3, sentences: 2, days: 2 });
  assert.equal(top.score, 3, '2 distinct sentences on one day + 1 on another');
  assert.deepEqual(entries[1].counts, { reported: 5, sentences: 1, days: 1 });
  assert.equal(entries[1].score, 1);
  assert.deepEqual(top.apps, { 'com.apple.mail': 2, 'com.apple.Notes': 1 });
  assert.equal(top.examples.length, 2, 'repeated sentences are listed once');
  assert.ok(!top.examples.some((e) => e.text === 'I has it.'), 'dismissed rows are not examples');
  assert.equal(top.item.text, 'I has [number] dogs.');
  assert.equal(top.item.expected, null);
  const lines = toJSONL(entries).trim().split('\n');
  assert.equal(lines.length, 2);
  assert.equal(JSON.parse(lines[1]).rule, 'spelling.typo');
  const md = toMarkdown(entries, '2026-W42', rows.length);
  assert.match(md, /# Parzr fix queue 2026-W42/);
  assert.match(md, /2026-10-12 to 2026-10-18: 10 reports, 2 suggestions/);
  assert.match(md, /\| 001 \| 3 \| `grammar.i_agreement` \| rules \| has → have \| 2 \| 2 \|/);
  assert.ok(!/Accepted|Dismissed/.test(md));
});

test('one day cannot top the queue: each day adds at most DAY_CAP', () => {
  const burst = Array.from({ length: 40 }, (_, i) => row({ rule: 'spelling.burst', original: 'a', replacement: 'b', sentence: `a ${'x'.repeat(i)}`, start_utf16: 0, end_utf16: 1 }));
  const steady = ['2026-10-12', '2026-10-13', '2026-10-14', '2026-10-15'].map((d) => row({ received_day: d }));
  const entries = build([...burst, ...steady], '2026-W42');
  assert.equal(entries[0].rule, 'grammar.i_agreement', 'four days beat one noisy day');
  assert.equal(entries[0].score, 4);
  assert.equal(entries[1].score, DAY_CAP);
  assert.equal(entries[1].counts.sentences, 40);
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
