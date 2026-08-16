import path from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test, type Page } from "@playwright/test";

type ModuleScenario = {
  module: string;
  templateTitle: string;
  caseName: string;
  runButton: string;
  submitPath: string;
  statusPrefix?: string;
  reviewUpload?: boolean;
};

const scenarios: ModuleScenario[] = [
  { module: "diagnosis", templateTitle: "合规路径诊断", caseName: "task01_case1 · 模拟 · 未签署", runButton: "运行 Diagnosis", submitPath: "/api/v1/diagnosis/report" },
  { module: "assessment", templateTitle: "安全评估路径", caseName: "task02_case1 · 模拟 · 未签署", runButton: "运行 Assessment", submitPath: "/api/v1/assessment/generate_async", statusPrefix: "/api/v1/assessment/tasks" },
  { module: "pipia", templateTitle: "认证/标准合同路径", caseName: "task03_case1 · 模拟 · 未签署", runButton: "运行 PIPIA", submitPath: "/api/v1/pipia/generate_async", statusPrefix: "/api/v1/pipia/tasks" },
  { module: "review", templateTitle: "文档专项智能审查", caseName: "task04_case1 · 源数据 · 未签署", runButton: "执行审查", submitPath: "/api/v1/review/generate_async", statusPrefix: "/api/v1/review/tasks", reviewUpload: true },
  { module: "eu_scc", templateTitle: "SCC 审查", caseName: "task05_case1 · 模拟 · 未签署", runButton: "生成SCC合规审查报告", submitPath: "/api/v1/eu_scc/generate_async", statusPrefix: "/api/v1/eu_scc/tasks" },
  { module: "bcr", templateTitle: "BCR 审核", caseName: "task06_case1 · 源数据 · 未签署", runButton: "生成BCR审查报告", submitPath: "/api/v1/bcr/generate_async", statusPrefix: "/api/v1/bcr/tasks" },
  { module: "dpia", templateTitle: "DPIA 草案生成", caseName: "task07_case1 · 源数据 · 未签署", runButton: "生成DPIA草案", submitPath: "/api/v1/dpia/generate_async", statusPrefix: "/api/v1/dpia/tasks" },
  { module: "tia", templateTitle: "TIA 草案生成", caseName: "task08_case1 · 源数据 · 未签署", runButton: "生成TIA草案", submitPath: "/api/v1/tia/generate_async", statusPrefix: "/api/v1/tia/tasks" },
  { module: "us_14117", templateTitle: "14117 行政令合规", caseName: "task09_case1 · 模拟 · 未签署", runButton: "运行 EO 14117 评估", submitPath: "/api/v1/us_14117/generate_async", statusPrefix: "/api/v1/us_14117/tasks" },
  { module: "cpra", templateTitle: "CPRA 合规", caseName: "task10_case1 · 模拟 · 未签署", runButton: "生成CPRA合规全景报告", submitPath: "/api/v1/cpra/generate_async", statusPrefix: "/api/v1/cpra/tasks" },
];

const networkLogs = new WeakMap<Page, Array<{ method: string; status: number; url: string }>>();
const currentDir = path.dirname(fileURLToPath(import.meta.url));
const reviewFixture = path.resolve(
  currentDir,
  "../../../resources/legal/sources/cn/snapshots/cn-tpl-022_隐私政策样例_510dc5fc.md",
);

function readRuns(): Array<Record<string, unknown>> {
  const raw = localStorage.getItem("ai4law_app_state_v2");
  if (!raw) return [];
  const parsed = JSON.parse(raw) as { moduleRuns?: Array<Record<string, unknown>> };
  return parsed.moduleRuns ?? [];
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("ai4law_ui_lang", "zh");
    localStorage.setItem("ai4law_quick_start_dismissed_v1", "1");
  });
  const logs: Array<{ method: string; status: number; url: string }> = [];
  networkLogs.set(page, logs);
  page.on("response", (response) => {
    const url = new URL(response.url());
    if (url.pathname.startsWith("/api/")) {
      logs.push({ method: response.request().method(), status: response.status(), url: url.pathname });
    }
  });
});

test.afterEach(async ({ page }, testInfo) => {
  await testInfo.attach("network-log", {
    body: JSON.stringify(networkLogs.get(page) ?? [], null, 2),
    contentType: "application/json",
  });
  if (testInfo.status !== testInfo.expectedStatus) {
    await testInfo.attach("page-text", {
      body: await page.locator("body").innerText().catch(() => "<body unavailable>"),
      contentType: "text/plain",
    });
  }
});

for (const scenario of scenarios) {
  test(`${scenario.module}: case selection submits and records this run`, async ({ page }) => {
    const unique = `${scenario.module.replace(/_/g, "-")}-${Date.now()}`;

    if (scenario.statusPrefix) {
      await page.route(`**${scenario.statusPrefix}/*`, async (route) => {
        const taskId = new URL(route.request().url()).pathname.split("/").pop() ?? "missing-task";
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            task_id: taskId,
            module: scenario.module,
            state: "completed",
            progress: 100,
            result: {
              report_path: `outputs/e2e/${taskId}.md`,
              output_files: { markdown: `outputs/e2e/${taskId}.md` },
              risk_level: "LOW",
              chapters: [{ title: "E2E", content: `Completed ${taskId}` }],
            },
          }),
        });
      });
    }

    await page.goto("/register?redirect=/tasks");
    await page.getByLabel("用户名").fill(unique);
    await page.getByLabel("邮箱").fill(`${unique}@example.test`);
    await page.getByLabel("企业名称（可选）").fill(`E2E ${scenario.module}`);
    await page.getByLabel("密码", { exact: true }).fill("E2ePass!12345");
    await page.getByLabel("确认密码").fill("E2ePass!12345");
    await page.getByRole("button", { name: "注册", exact: true }).click();
    await expect(page).toHaveURL(/\/tasks$/);

    await page.getByRole("button", { name: new RegExp(scenario.templateTitle) }).first().click();
    const createDialog = page.getByRole("dialog");
    await expect(createDialog).toBeVisible();
    await createDialog.getByLabel("项目名称").fill(`E2E ${scenario.module}`);
    await createDialog.getByRole("button", { name: "创建并进入工作区" }).click();
    await expect(page).toHaveURL(/\/workspace\/task-/);

    const runCountBefore = await page.evaluate(readRuns).then((runs) => runs.length);
    await page.getByRole("button", { name: /测试案例/ }).first().click();
    await page.getByText(scenario.caseName, { exact: true }).click();

    if (scenario.reviewUpload) {
      await page.locator(".doc-review-upload-drop input[type=file]").setInputFiles(reviewFixture);
      await expect(page.getByText(path.basename(reviewFixture), { exact: true }).first()).toBeVisible();
    }

    const submitResponsePromise = page.waitForResponse((response) => {
      const url = new URL(response.url());
      return response.request().method() === "POST" && url.pathname === scenario.submitPath;
    });
    const uploadResponsePromise = scenario.reviewUpload
      ? page.waitForResponse((response) => {
        const url = new URL(response.url());
        return response.request().method() === "POST" && url.pathname === "/api/v0/files/upload";
      })
      : null;

    await page.getByRole("button", { name: scenario.runButton, exact: true }).click();
    const submitResponse = await submitResponsePromise;
    expect(submitResponse.status()).toBeGreaterThanOrEqual(200);
    expect(submitResponse.status()).toBeLessThan(300);
    if (uploadResponsePromise) {
      const uploadResponse = await uploadResponsePromise;
      expect(uploadResponse.status()).toBeGreaterThanOrEqual(200);
      expect(uploadResponse.status()).toBeLessThan(300);
    }

    const submitBody = await submitResponse.json() as { task_id?: string };
    const taskId = submitBody.task_id;

    const rawPostData = submitResponse.request().postData();
    const requestBody = rawPostData ? (JSON.parse(rawPostData) as Record<string, unknown>) : null;
    if (scenario.module === "dpia") {
      expect(requestBody).not.toBeNull();
      expect(requestBody?.identified_risks).toEqual([]);
      expect(requestBody?.mitigation_measures).toEqual([]);
      const uploadedFiles = (requestBody?.uploaded_files ?? []) as string[];
      expect(uploadedFiles[0]).toContain("task07_case1.docx");
    }
    if (scenario.module === "cpra") {
      expect(requestBody).not.toBeNull();
      const attachments = (requestBody?.attachments ?? []) as Array<Record<string, unknown>>;
      expect(attachments[0]?.file_role).toBe("privacy_policy");
      expect(attachments[0]?.storage_uri).toContain("task10_case1.docx");
    }

    await expect.poll(async () => (await page.evaluate(readRuns)).length).toBe(runCountBefore + 1);

    const recordedRun = await page.evaluate(({ module, taskId }) => {
      const raw = localStorage.getItem("ai4law_app_state_v2");
      const runs = raw
        ? ((JSON.parse(raw) as { moduleRuns?: Array<Record<string, unknown>> }).moduleRuns ?? [])
        : [];
      return runs.find((run) =>
        run.module === module && (taskId ? run.asyncTaskId === taskId : run.success === true)
      ) ?? null;
    }, { module: scenario.module, taskId });

    expect(recordedRun).not.toBeNull();
    expect(recordedRun?.success).toBe(true);
    expect(recordedRun?.error).toBeUndefined();
    if (scenario.statusPrefix) {
      expect(taskId).toBeTruthy();
      expect(recordedRun?.asyncTaskId).toBe(taskId);
      expect(recordedRun?.asyncState).toBe("completed");
      const generatedResults = page.locator(".ide-tree-row-root").filter({ hasText: "生成结果" });
      await expect(generatedResults.locator("small")).toHaveText("1");
      const relevantStatus = (networkLogs.get(page) ?? []).filter((entry) =>
        entry.method === "GET" && entry.url.startsWith(`${scenario.statusPrefix}/`)
      );
      expect(relevantStatus.length).toBeGreaterThan(0);
      expect(relevantStatus.every((entry) => entry.status >= 200 && entry.status < 300)).toBe(true);
    }
  });
}
