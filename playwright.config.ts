import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: 'tests/e2e',
  /* Maximum time one test can run for. */
  timeout: 60_000,
  expect: { timeout: 5_000 },
  /* Run tests in files in parallel */
  fullyParallel: true,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: 'list',
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    baseURL: 'http://127.0.0.1:8000',
    trace: 'on-first-retry',
    actionTimeout: 15_000,
    navigationTimeout: 20_000,
  },

  /* Start a local static server for the docs */
  webServer: {
    command: 'python3 -m http.server 8000',
    port: 8000,
    timeout: 120_000,
    reuseExistingServer: true,
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});

