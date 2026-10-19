// D1 tests: test-d1/ runs inside workerd (Miniflare) against a real local D1 database built from migrations/, with the
// bindings in wrangler.toml. `npm run test:d1`; no Cloudflare account or network needed.
import { cloudflareTest, readD1Migrations } from '@cloudflare/vitest-pool-workers';
import { defineConfig } from 'vitest/config';

export default defineConfig(async () => {
  const migrations = await readD1Migrations(new URL('./migrations', import.meta.url).pathname);
  return {
    plugins: [
      cloudflareTest({
        wrangler: { configPath: './wrangler.toml' },
        // The pool's workerd (pinned with it) predates wrangler.toml's compatibility_date; nothing this Worker uses
        // changed between the two dates.
        miniflare: { compatibilityDate: '2026-08-15', bindings: { TEST_MIGRATIONS: migrations, RATE_LIMIT_SALT: 'test-salt', DAILY_ROW_CAP: '60' } },
      }),
    ],
    test: { include: ['test-d1/**/*.test.ts'] },
  };
});
