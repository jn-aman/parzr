import { defineConfig } from '@playwright/test';
// On CI: assertions wait up to 30 s (a cold runner loads the engine and model slowly) and a failed test runs once more;
// a test that passes only on its retry is reported as flaky in the list output and in dist/qa/browser-results.json.
export default defineConfig({ testDir: './tests', testMatch: 'browser.spec.mjs', timeout: process.env.CI ? 300000 : 20000, expect: { timeout: process.env.CI ? 30000 : 5000 }, retries: process.env.CI ? 1 : 0, workers: 1, reporter: [['list'],['json',{outputFile:'dist/qa/browser-results.json'}]], use: { headless: true }, outputDir: 'dist/browser-tests' });
