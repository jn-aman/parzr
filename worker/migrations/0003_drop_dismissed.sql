-- Ignoring a suggestion no longer sends anything (owner decision, 2026-10-19). Rows stored for an Ignore before then
-- are deleted rather than left to age out over the 180-day retention. A data change only: no schema is touched.
DELETE FROM reports WHERE action = 'dismissed';
