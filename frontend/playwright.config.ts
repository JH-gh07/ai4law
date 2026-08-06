import { defineConfig, devices } from "@playwright/test";

const isCi = Boolean(process.env.CI);

export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: "**/*.e2e.ts",
  outputDir: "./test-results/e2e",
  fullyParallel: false,
  workers: 1,
  retries: isCi ? 1 : 0,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: isCi
    ? [["line"], ["html", { outputFolder: "playwright-report", open: "never" }]]
    : [["list"], ["html", { outputFolder: "playwright-report", open: "never" }]],
  use: {
    baseURL: "http://127.0.0.1:5199",
    locale: "zh-CN",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command:
        "bash -o pipefail -c 'mkdir -p frontend/test-results; contract_root=$(mktemp -d /tmp/ai4law-browser-contract.XXXXXX); AI4LAW_CONTRACT_TMP_ROOT=$contract_root uv run --frozen uvicorn backend.tests.contract_app:app --host 127.0.0.1 --port 8012 2>&1 | tee frontend/test-results/backend-e2e.log'",
      cwd: "..",
      url: "http://127.0.0.1:8012/__contract__/state",
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command:
        "VITE_ENABLE_DEV_ACCEL=true VITE_API_PROXY_TARGET=http://127.0.0.1:8012 npm run dev -- --port 5199 --strictPort",
      cwd: ".",
      url: "http://127.0.0.1:5199",
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
