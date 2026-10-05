import { defineConfig } from '@playwright/test';
export default defineConfig({ testDir: './tests', testMatch: 'browser.spec.mjs', timeout: 20000, workers: 1, reporter: [['list'],['json',{outputFile:'dist/qa/browser-results.json'}]], use: { headless: true }, outputDir: 'dist/browser-tests' });
