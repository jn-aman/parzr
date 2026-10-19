import type { D1Migration } from 'cloudflare:test';

declare global {
  namespace Cloudflare {
    interface Env {
      DB: D1Database;
      REPORTS_LIMITER: RateLimit;
      RATE_LIMIT_SALT: string;
      RETENTION_DAYS: string;
      DAILY_ROW_CAP: string;
      CLIENT_DAILY_ROW_CAP: string;
      TEST_MIGRATIONS: D1Migration[];
    }
  }
}
