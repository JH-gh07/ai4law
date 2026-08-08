import { expect, test } from "@playwright/test";

test("resource explorer shows real inputs and user deliverables only", async ({ page }, testInfo) => {
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  await page.addInitScript(() => {
    localStorage.setItem("ai4law_ui_lang", "zh");
    localStorage.setItem("ai4law_quick_start_dismissed_v1", "1");
  });

  await page.route("**/api/v1/assessment/tasks/*", async (route) => {
    const taskId = new URL(route.request().url()).pathname.split("/").pop() ?? "assessment-sidebar";
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        task_id: taskId,
        module: "assessment",
        state: "completed",
        progress: 100,
        result: {
          report_path: `outputs/e2e/${taskId}.md`,
          output_files: {
            markdown: `outputs/e2e/${taskId}.md`,
            docx: `outputs/e2e/${taskId}.docx`,
            citation_map_json: `outputs/e2e/${taskId}_citation_map.json`,
            facts_json: `outputs/e2e/${taskId}_facts.json`,
          },
          risk_level: "LOW",
          chapters: [{ title: "E2E", content: "Resource explorer verification" }],
        },
      }),
    });
  });
  await page.route("**/api/v1/artifacts/preview?*", async (route) => {
    const requestedPath = new URL(route.request().url()).searchParams.get("path") ?? "outputs/e2e/report.md";
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        path: requestedPath,
        file_name: requestedPath.split("/").pop() ?? "report.md",
        kind: "md",
        render_mode: "text",
        content: "# Resource explorer verification",
        file_url: null,
      }),
    });
  });

  const unique = `sidebar-${Date.now()}`;
  await page.goto("/register?redirect=/tasks");
  await page.getByLabel("用户名").fill(unique);
  await page.getByLabel("邮箱").fill(`${unique}@example.test`);
  await page.getByLabel("密码", { exact: true }).fill("E2ePass!12345");
  await page.getByLabel("确认密码").fill("E2ePass!12345");
  await page.getByRole("button", { name: "注册", exact: true }).click();

  await page.getByRole("button", { name: /安全评估路径/ }).first().click();
  const createDialog = page.getByRole("dialog");
  await createDialog.getByLabel("项目名称").fill("侧边文件栏验收");
  await createDialog.getByRole("button", { name: "创建并进入工作区" }).click();

  await page.getByRole("button", { name: /测试案例/ }).first().click();
  await page.getByText("评估-1: 东方信托 CIIO金融机构", { exact: true }).click();
  await page.getByRole("button", { name: "运行 Assessment", exact: true }).click();

  const inputRoot = page.locator(".ide-tree-row-root").filter({ hasText: "已提交材料" });
  const outputRoot = page.locator(".ide-tree-row-root").filter({ hasText: "生成结果" });
  await expect(inputRoot.locator("small")).not.toHaveText("0");
  await expect(outputRoot.locator("small")).toHaveText("2");
  await expect(page.getByText(/基础信息表单/)).toHaveCount(0);
  await expect(page.getByText(/citation_map|facts\.json/i)).toHaveCount(0);

  await page.getByRole("button", { name: /第1次生成结果/ }).click();
  await expect(page.getByRole("button", { name: /审查报告（MD）/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /报告 Word 版/ })).toBeVisible();

  await testInfo.attach("resource-explorer", {
    body: await page.screenshot({ fullPage: true }),
    contentType: "image/png",
  });
  expect(consoleErrors).toEqual([]);
});
