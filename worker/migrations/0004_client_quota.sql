-- Additive only (see worker/README.md, "Migrations"): this runs before the new Worker is deployed, so the version
-- still serving must keep working against it (it never reads or writes this table).

-- Rows stored per client per UTC day, so one client cannot use up the day's global budget (daily_counts) for everyone.
-- `client` is the same salted, daily hash of the IPv4 address or IPv6 /64 that keys the rate limit: never the address,
-- and it changes every day. The Worker raises `rows` in the same transaction as the reports, and CHECK (rows <= cap)
-- makes a batch that would pass the client's quota fail and roll back. Pruned after two days.
CREATE TABLE IF NOT EXISTS client_counts (
  day    TEXT    NOT NULL CHECK (length(day) = 10),
  client TEXT    NOT NULL CHECK (length(client) = 32),
  rows   INTEGER NOT NULL CHECK (rows >= 0),
  cap    INTEGER NOT NULL CHECK (cap > 0),
  CHECK (rows <= cap),
  PRIMARY KEY (day, client)
) WITHOUT ROWID;
