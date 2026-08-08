import { defineConfig, devices } from "@playwright/test";

const evidenceDir = "../status/check/phase3_scc_firstrun_20260808/browser";

export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: "scc-local-firstrun.e2e.ts",
  outputDir: `${evidenceDir}/playwright-results`,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 180_000,
  expect: { timeout: 20_000 },
  reporter: [["list"], ["html", { outputFolder: `${evidenceDir}/playwright-report`, open: "never" }]],
  use: {
    baseURL: "http://127.0.0.1:5198",
    locale: "zh-CN",
    trace: "on",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: [
        "LLM_PROVIDER=none",
        "LLM_API_KEY=",
        "SILICONFLOW_API_KEY=",
        "SICICONFLOW_API_KEY=",
        "TENCENT_API_KEY=",
        "AI4LAW_LLM_PROVIDER=none",
        "AI4LAW_LLM_API_KEY=",
        "AI4LAW_SILICONFLOW_API_KEY=",
        "AI4LAW_TENCENT_API_KEY=",
        "AI4LAW_DELILEGAL_APP_ID=",
        "AI4LAW_DELILEGAL_SECRET=",
        "AI4LAW_RAG_AUTO_BUILD_INDEX=false",
        "AI4LAW_SCHEMA_FIRST_SCC_ENABLED=true",
        "AI4LAW_TASK_MODE=threaded",
        "AI4LAW_DATABASE_URL=sqlite:////tmp/ai4law-scc-browser-20260808.db",
        "AI4LAW_STORAGE_DIR=/tmp/ai4law-scc-browser-storage-20260808",
        "uv run uvicorn backend.main:app --host 127.0.0.1 --port 8011",
      ].join(" "),
      cwd: "..",
      url: "http://127.0.0.1:8011/health",
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: "VITE_ENABLE_DEV_ACCEL=false VITE_API_PROXY_TARGET=http://127.0.0.1:8011 npm run dev -- --port 5198 --strictPort",
      cwd: ".",
      url: "http://127.0.0.1:5198",
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
