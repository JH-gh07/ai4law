import { defineConfig, devices } from "@playwright/test";

const evidenceDir = "../status/check/phase3_bcr_complete_20260808/browser";

export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: "bcr-local-firstrun.e2e.ts",
  outputDir: `${evidenceDir}/playwright-results`,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 180_000,
  expect: { timeout: 20_000 },
  reporter: [["list"], ["html", { outputFolder: `${evidenceDir}/playwright-report`, open: "never" }]],
  use: {
    baseURL: "http://127.0.0.1:5196",
    locale: "zh-CN",
    actionTimeout: 15_000,
    trace: "on",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: [
        "AI4LAW_DATABASE_URL=sqlite:////tmp/ai4law-bcr-browser-20260808.db",
        "AI4LAW_STORAGE_DIR=/tmp/ai4law-bcr-browser-storage-20260808",
        "AI4LAW_RAG_AUTO_BUILD_INDEX=false",
        "uv run uvicorn backend.tests.bcr_browser_app:app --host 127.0.0.1 --port 8014",
      ].join(" "),
      cwd: "..",
      url: "http://127.0.0.1:8014/health",
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: "VITE_ENABLE_DEV_ACCEL=false VITE_API_PROXY_TARGET=http://127.0.0.1:8014 npm run dev -- --port 5196 --strictPort",
      cwd: ".",
      url: "http://127.0.0.1:5196",
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
