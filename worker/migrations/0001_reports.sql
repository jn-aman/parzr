-- Parzr suggestion reports. Every column is something the app sends (see SuggestionReport in
-- mac/Sources/ParzrCore/Reports.swift) except received_day, the UTC date the Worker stored the row.
-- There is no column for an IP address, user, device, session or time of day.

CREATE TABLE IF NOT EXISTS reports (
  id           INTEGER PRIMARY KEY,
  received_day TEXT    NOT NULL CHECK (length(received_day) = 10),
  sentence     TEXT    NOT NULL CHECK (length(sentence) BETWEEN 1 AND 1000),
  start_utf16  INTEGER NOT NULL CHECK (start_utf16 >= 0),
  end_utf16    INTEGER NOT NULL CHECK (end_utf16 >= start_utf16),
  original     TEXT    NOT NULL CHECK (length(original) <= 300),
  replacement  TEXT    NOT NULL CHECK (length(replacement) <= 300),
  rule         TEXT    NOT NULL CHECK (length(rule) BETWEEN 1 AND 100),
  model        TEXT    NOT NULL CHECK (length(model) BETWEEN 1 AND 40),
  action       TEXT    NOT NULL CHECK (action IN ('dismissed', 'reported')),
  app          TEXT    NOT NULL CHECK (length(app) BETWEEN 1 AND 255),
  version      TEXT    NOT NULL CHECK (length(version) BETWEEN 1 AND 32)
);
CREATE INDEX IF NOT EXISTS reports_by_day  ON reports (received_day);
CREATE INDEX IF NOT EXISTS reports_by_rule ON reports (rule, action);

-- Batch keys are random UUIDs the app makes per request, kept 14 days so a retried request is stored once.
CREATE TABLE IF NOT EXISTS batches (
  key          TEXT PRIMARY KEY,
  received_day TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS batches_by_day ON batches (received_day);
