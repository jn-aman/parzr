// D1 tests: test-d1/ runs inside workerd (Miniflare) against a real local D1 database built from migrations/, with the
// bindings in wrangler.toml. `npm run test:d1`; no Cloudflare account or network needed.
import { cloudflareTest, readD1Migrations } from '@cloudflare/vitest-plugin';
import { defineConfig } from 'vitest/config';

export default defineConfig(async () => {
  const migrations = await readD1Migrations(new URL('./migrations', import.meta.url).pathname);
  return {
    plugins: [
      cloudflareTest({
        // The plugin's workerd (pinned with it) is newer than wrangler.toml's compatibility_date, so the tests run at
        // the deployed date.
        wrangler: { configPath: './wrangler.toml' },
        miniflare: { bindings: { TEST_MIGRATIONS: migrations, RATE_LIMIT_SALT: 'test-salt', DAILY_ROW_CAP: '60', CLIENT_DAILY_ROW_CAP: '30' } },
      }),
    ],
    test: { include: ['test-d1/**/*.test.ts'] },
  };
});
