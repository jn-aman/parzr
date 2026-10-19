// The weekly fix queue: a week of "Report wrong suggestion" rows grouped by what was suggested, ranked by how many
// distinct sentences, on how many days, writers said it was wrong. Format documented in worker/README.md
// ("Fix-queue format").

export interface Row {
  received_day: string;
  sentence: string;
  start_utf16: number;
  end_utf16: number;
  original: string;
  replacement: string;
  rule: string;
  model: string;
  /** Only `reported` is sent and stored now; older `dismissed` rows are skipped. */
  action: string;
  app: string;
  version: string;
}

export interface Example {
  text: string;
  start: number;
  end: number;
  app: string;
  version: string;
}

/** The most one day can add to a suggestion's score: a burst from one place on one day cannot top the queue. */
export const DAY_CAP = 3;

export interface Entry {
  id: string;
  week: string;
  rule: string;
  model: string;
  original: string;
  replacement: string;
  /** Rows reported, the distinct sentences among them, and the distinct days they came in on. */
  counts: { reported: number; sentences: number; days: number };
  /** For each day, the distinct sentences reported that day (at most DAY_CAP), summed over the week. */
  score: number;
  apps: Record<string, number>;
  versions: Record<string, number>;
  /** Up to five distinct sentences. */
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
    if (row.action !== 'reported') continue;
    const key = JSON.stringify([row.rule, row.original, row.replacement]);
    const list = groups.get(key);
    if (list) list.push(row);
    else groups.set(key, [row]);
  }
  const entries: Omit<Entry, 'id' | 'item'>[] = [];
  for (const list of groups.values()) {
    const apps: Record<string, number> = {};
    const versions: Record<string, number> = {};
    const models: Record<string, number> = {};
    // Distinct sentences per day: the same sentence sent again, by one writer or a script, counts once.
    const byDay = new Map<string, Set<string>>();
    const sentences = new Set<string>();
    const examples: Example[] = [];
    for (const row of list) {
      apps[row.app] = (apps[row.app] ?? 0) + 1;
      versions[row.version] = (versions[row.version] ?? 0) + 1;
      models[row.model] = (models[row.model] ?? 0) + 1;
      const today = byDay.get(row.received_day) ?? new Set<string>();
      today.add(row.sentence);
      byDay.set(row.received_day, today);
      if (!sentences.has(row.sentence) && examples.length < 5) examples.push({ text: row.sentence, start: row.start_utf16, end: row.end_utf16, app: row.app, version: row.version });
      sentences.add(row.sentence);
    }
    let score = 0;
    for (const set of byDay.values()) score += Math.min(DAY_CAP, set.size);
    const model = Object.entries(models).sort((a, b) => b[1] - a[1])[0][0];
    entries.push({
      week,
      rule: list[0].rule,
      model,
      original: list[0].original,
      replacement: list[0].replacement,
      counts: { reported: list.length, sentences: sentences.size, days: byDay.size },
      score,
      apps,
      versions,
      examples,
    });
  }
  entries.sort(
    (a, b) =>
      b.score - a.score || b.counts.days - a.counts.days || b.counts.sentences - a.counts.sentences || a.rule.localeCompare(b.rule) || a.original.localeCompare(b.original),
  );
  return entries.map((entry, index) => {
    const id = `${week}-${String(index + 1).padStart(3, '0')}`;
    return {
      id,
      ...entry,
      item: {
        id: `fq-${id}`,
        text: entry.examples[0].text,
        expected: null,
        note: `${entry.rule} suggested "${entry.original}" -> "${entry.replacement}"; reported wrong in ${entry.counts.sentences} distinct sentences on ${entry.counts.days} days (${entry.counts.reported} reports). Fill in the expected text, then add it to a batch.`,
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
    `${range.from} to ${range.to}: ${totalRows} reports, ${entries.length} suggestions to look at (score: distinct sentences reported each day, at most ${DAY_CAP} a day, summed over the week).`,
    '',
    '| # | Score | Rule | Model | Suggestion | Sentences | Days | Example |',
    '|---|---|---|---|---|---|---|---|',
  ];
  for (const e of entries) {
    const example = e.examples[0];
    lines.push(
      `| ${e.id.slice(-3)} | ${e.score} | \`${cell(e.rule)}\` | ${cell(e.model)} | ${cell(e.original || '(insert)')} → ${cell(e.replacement || '(remove)')} | ${e.counts.sentences} | ${e.counts.days} | ${cell(example.text)} |`,
    );
  }
  lines.push('', 'Each line of the matching .jsonl file holds every example and a regression `item` to triage into a batch.', '');
  return lines.join('\n');
}
