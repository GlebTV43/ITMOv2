const { defineConfig } = require('@playwright/test');

const python = process.env.BOOKSHARE_BROWSER_PYTHON || 'python';

module.exports = defineConfig({
  testDir: './browser_tests',
  workers: 1,
  reporter: 'list',
  preserveOutput: 'always',
  use: {
    baseURL: 'http://127.0.0.1:8764',
    viewport: { width: 1280, height: 850 },
    trace: 'retain-on-failure',
  },
  webServer: {
    command: `"${python}" -m browser_tests.server`,
    url: 'http://127.0.0.1:8764/',
    timeout: 45_000,
    reuseExistingServer: false,
  },
});
