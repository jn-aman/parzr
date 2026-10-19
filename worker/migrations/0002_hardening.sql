-- Additive only (see worker/README.md, "Migrations"): this runs before the new Worker is deployed, so the version
-- still serving must keep working against it.

-- Nothing queries reports by rule; the fix-queue export reads one week by received_day.
DROP INDEX IF EXISTS reports_by_rule;

-- Rows stored per UTC day, across every client. The Worker raises `rows` in the same transaction as the reports, and
-- CHECK (rows <= cap) makes a batch that would pass the day's cap fail and roll back. Pruned after 14 days.
CREATE TABLE IF NOT EXISTS daily_counts (
  day  TEXT    PRIMARY KEY CHECK (length(day) = 10),
  rows INTEGER NOT NULL CHECK (rows >= 0),
  cap  INTEGER NOT NULL CHECK (cap > 0),
  CHECK (rows <= cap)
);

-- Operational notes the health check reads: last_prune_ok is the UTC day the retention clean-up last succeeded.
CREATE TABLE IF NOT EXISTS meta (
  key   TEXT PRIMARY KEY CHECK (length(key) BETWEEN 1 AND 64),
  value TEXT NOT NULL CHECK (length(value) <= 64)
);

-- Only "Report wrong suggestion" is stored. The reports table's CHECK still names 'dismissed' (changing a CHECK means
-- rebuilding the table), so this trigger refuses it instead.
CREATE TRIGGER IF NOT EXISTS reports_reported_only BEFORE INSERT ON reports
WHEN NEW.action <> 'reported'
BEGIN
  SELECT RAISE(ABORT, 'only reported suggestions are stored');
END;
