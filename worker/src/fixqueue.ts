// The weekly fix queue: a week of report rows grouped by what was suggested, ranked by how often writers said it
// was wrong. Format documented in worker/README.md ("Fix-queue format").

export interface Row {
  received_day: string;
  sentence: string;
  start_utf16: number;
  end_utf16: number;
  original: string;
  replacement: string;
  rule: string;
  model: string;
  action: 'dismissed' | 'reported' | 'accepted';
  app: string;
  version: string;
}

export interface Example {
  text: string;
  start: number;
  end: number;
  action: Row['action'];
  app: string;
  version: string;
}

export interface Entry {
  id: string;
  week: string;
  rule: string;
  model: string;
  original: string;
  replacement: string;
  counts: { reported: number; dismissed: number; accepted: number };
  /** (reported + dismissed) / all: how often writers turned this suggestion down. */
  wrong_rate: number;
  /** 3 x reported + dismissed - accepted / 2; entries at or below zero are left out. */
  score: number;
  apps: Record<string, number>;
  versions: Record<string, number>;
  /** Up to five distinct sentences, reported ones first. */
  examples: Example[];
  /** A regression item to triage into dist/batches (scripts/everyday-batch.py): `expected` is filled in by a person. */
  item: { id: string; text: string; expected: null; note: string };
}

/** ISO 8601 week ("2026-W42") of a UTC date. */
export function isoWeek(date: Date): string {
  const d = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()));
  const weekday = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - weekday);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  const week = Math.ceil(((d.getTime() - yearStart.getTime()) / 86_400_000 + 1) / 7);
  return `${d.getUTCFullYear()}-W${String(week).padStart(2, '0')}`;
}

/** First and last UTC day ("YYYY-MM-DD") of an ISO week. */
export function weekRange(week: string): { from: string; to: string } {
  const match = /^(\d{4})-W(\d{2})$/.exec(week);
  if (!match) throw new Error(`expected a week like 2026-W42, got ${week}`);
  const [year, number] = [Number(match[1]), Number(match[2])];
  const jan4 = new Date(Date.UTC(year, 0, 4));
  const monday = new Date(jan4.getTime() - ((jan4.getUTCDay() || 7) - 1) * 86_400_000 + (number - 1) * 7 * 86_400_000);
  const sunday = new Date(monday.getTime() + 6 * 86_400_000);
  if (isoWeek(monday) !== week) throw new Error(`no such week: ${week}`);
  return { from: monday.toISOString().slice(0, 10), to: sunday.toISOString().slice(0, 10) };
}

/** The last complete ISO week before `now`. */
export function previousWeek(now: Date): string {
  return isoWeek(new Date(now.getTime() - 7 * 86_400_000));
}

export function build(rows: Row[], week: string): Entry[] {
  const groups = new Map<string, Row[]>();
  for (const row of rows) {
    const key = JSON.stringify([row.rule, row.original, row.replacement]);
    const list = groups.get(key);
    if (list) list.push(row);
    else groups.set(key, [row]);
  }
  const order: Record<Row['action'], number> = { reported: 0, dismissed: 1, accepted: 2 };
  const entries: Omit<Entry, 'id' | 'item'>[] = [];
  for (const list of groups.values()) {
    const counts = { reported: 0, dismissed: 0, accepted: 0 };
    const apps: Record<string, number> = {};
    const versions: Record<string, number> = {};
    const models: Record<string, number> = {};
    for (const row of list) {
      counts[row.action] += 1;
      apps[row.app] = (apps[row.app] ?? 0) + 1;
      versions[row.version] = (versions[row.version] ?? 0) + 1;
      models[row.model] = (models[row.model] ?? 0) + 1;
    }
    const total = counts.reported + counts.dismissed + counts.accepted;
    const score = 3 * counts.reported + counts.dismissed - counts.accepted / 2;
    if (score <= 0) continue;
    const seen = new Set<string>();
    const examples: Example[] = [];
    for (const row of [...list].sort((a, b) => order[a.action] - order[b.action])) {
      if (seen.has(row.sentence) || examples.length >= 5) continue;
      seen.add(row.sentence);
      examples.push({ text: row.sentence, start: row.start_utf16, end: row.end_utf16, action: row.action, app: row.app, version: row.version });
    }
    const model = Object.entries(models).sort((a, b) => b[1] - a[1])[0][0];
    entries.push({
      week,
      rule: list[0].rule,
      model,
      original: list[0].original,
      replacement: list[0].replacement,
      counts,
      wrong_rate: Math.round(((counts.reported + counts.dismissed) / total) * 100) / 100,
      score,
      apps,
      versions,
      examples,
    });
  }
  entries.sort((a, b) => b.score - a.score || b.counts.reported - a.counts.reported || a.rule.localeCompare(b.rule) || a.original.localeCompare(b.original));
  return entries.map((entry, index) => {
    const id = `${week}-${String(index + 1).padStart(3, '0')}`;
    return {
      id,
      ...entry,
      item: {
        id: `fq-${id}`,
        text: entry.examples[0].text,
        expected: null,
        note: `${entry.rule} suggested "${entry.original}" -> "${entry.replacement}"; turned down ${entry.counts.reported + entry.counts.dismissed} of ${entry.counts.reported + entry.counts.dismissed + entry.counts.accepted} times. Fill in the expected text, then add it to a batch.`,
      },
    } as Entry;
  });
}

export function toJSONL(entries: Entry[]): string {
  return entries.map((e) => JSON.stringify(e)).join('\n') + (entries.length ? '\n' : '');
}

function cell(text: string): string {
  return text.replace(/\|/g, '\\|').replace(/\n/g, ' ');
}

export function toMarkdown(entries: Entry[], week: string, totalRows: number): string {
  const range = weekRange(week);
  const lines = [
    `# Parzr fix queue ${week}`,
    '',
    `${range.from} to ${range.to}: ${totalRows} reports, ${entries.length} suggestions to look at (ranked by score = 3 x reported + dismissed - accepted / 2).`,
    '',
    '| # | Score | Rule | Model | Suggestion | Reported | Dismissed | Accepted | Wrong rate | Example |',
    '|---|---|---|---|---|---|---|---|---|---|',
  ];
  for (const e of entries) {
    const example = e.examples[0];
    lines.push(
      `| ${e.id.slice(-3)} | ${e.score} | \`${cell(e.rule)}\` | ${cell(e.model)} | ${cell(e.original || '(insert)')} → ${cell(e.replacement || '(remove)')} | ${e.counts.reported} | ${e.counts.dismissed} | ${e.counts.accepted} | ${Math.round(e.wrong_rate * 100)}% | ${cell(example.text)} |`,
    );
  }
  lines.push('', 'Each line of the matching .jsonl file holds every example and a regression `item` to triage into a batch.', '');
  return lines.join('\n');
}
