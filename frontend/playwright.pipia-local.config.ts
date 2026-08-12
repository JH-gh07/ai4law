import { defineConfig, devices } from "@playwright/test";

const transientArtifactDir = "../tmp/verify/pipia-playwright";

export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: /pipia.*local.*\.e2e\.ts/,
  outputDir: `${transientArtifactDir}/results`,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 180_000,
  expect: { timeout: 20_000 },
  reporter: [["list"], ["html", { outputFolder: `${transientArtifactDir}/report`, open: "never" }]],
  use: {
    baseURL: "http://127.0.0.1:5197",
    locale: "zh-CN",
    actionTimeout: 15_000,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: [
        "AI4LAW_DATABASE_URL=sqlite:////tmp/ai4law-pipia-browser-20260808.db",
        "AI4LAW_STORAGE_DIR=/tmp/ai4law-pipia-browser-storage-20260808",
        "AI4LAW_RAG_AUTO_BUILD_INDEX=false",
        "uv run uvicorn backend.tests.pipia_browser_app:app --host 127.0.0.1 --port 8013",
      ].join(" "),
      cwd: "..",
      url: "http://127.0.0.1:8013/health",
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: "VITE_ENABLE_DEV_ACCEL=false VITE_API_PROXY_TARGET=http://127.0.0.1:8013 npm run dev -- --port 5197 --strictPort",
      cwd: ".",
      url: "http://127.0.0.1:5197",
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
