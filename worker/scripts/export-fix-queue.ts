#!/usr/bin/env node
// Exports one week of reports from D1 into the weekly fix queue.
//
//   node scripts/export-fix-queue.ts [--week 2026-W42] [--out ../dist/fix-queue] [--local [--persist-to DIR]] [--input rows.json]
//
// Without --input it runs `npx wrangler d1 execute parzr-reports --remote --json` (needs `wrangler login` or
// CLOUDFLARE_API_TOKEN); --local reads the local development database instead. --input takes a JSON array of rows
// (the shape wrangler prints) for offline runs and tests. Writes <out>/<week>.jsonl and <out>/<week>.md.

import { execFileSync } from 'node:child_process';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { build, previousWeek, toJSONL, toMarkdown, weekRange, type Row } from '../src/fixqueue.ts';

function option(name: string): string | undefined {
  const index = process.argv.indexOf(`--${name}`);
  return index >= 0 ? process.argv[index + 1] : undefined;
}

const week = option('week') ?? previousWeek(new Date());
const out = resolve(option('out') ?? join(import.meta.dirname, '../../dist/fix-queue'));
const { from, to } = weekRange(week);

function query(): Row[] {
  const input = option('input');
  if (input) {
    const rows = JSON.parse(readFileSync(input, 'utf8')) as Row[];
    return rows.filter((r) => r.received_day >= from && r.received_day <= to);
  }
  // Both values come from weekRange (digits and dashes only), so they are safe to put in the SQL text.
  const sql = `SELECT received_day, sentence, start_utf16, end_utf16, original, replacement, rule, model, action, app, version FROM reports WHERE received_day BETWEEN '${from}' AND '${to}' ORDER BY id`;
  const args = ['wrangler', 'd1', 'execute', 'parzr-reports', process.argv.includes('--local') ? '--local' : '--remote', '--json', '--command', sql];
  const persist = option('persist-to');
  if (persist) args.push('--persist-to', persist);
  const output = execFileSync('npx', args, { cwd: join(import.meta.dirname, '..'), encoding: 'utf8', maxBuffer: 512 * 1024 * 1024, stdio: ['ignore', 'pipe', 'inherit'] });
  const parsed = JSON.parse(output) as { results: Row[] }[];
  return parsed.flatMap((part) => part.results ?? []);
}

const rows = query();
const entries = build(rows, week);
mkdirSync(out, { recursive: true });
writeFileSync(join(out, `${week}.jsonl`), toJSONL(entries));
writeFileSync(join(out, `${week}.md`), toMarkdown(entries, week, rows.length));
console.log(`${week} (${from} to ${to}): ${rows.length} reports, ${entries.length} entries -> ${join(out, `${week}.jsonl`)}`);
