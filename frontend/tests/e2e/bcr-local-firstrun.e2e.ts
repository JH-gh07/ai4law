import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test } from "@playwright/test";

const currentDir = path.dirname(fileURLToPath(import.meta.url));
const repositoryRoot = path.resolve(currentDir, "../../..");
const fixturePath = path.join(
  repositoryRoot,
  "backend/tests/bcr/fixtures/case_02_healthdata_bcr_c_draft.docx",
);
const evidenceDir = path.join(
  repositoryRoot,
  "status/check/phase3_bcr_complete_20260808/browser",
);

type NetworkEntry = { method: string; path: string; status: number };
type BcrRequestPayload = {
  uploaded_documents?: Array<{ document_role?: string; file_name?: string }>;
};

test("BCR 本地真实上传、文档审查和引用跳转闭环", async ({ page }) => {
  fs.mkdirSync(evidenceDir, { recursive: true });
  const network: NetworkEntry[] = [];
  const consoleMessages: Array<{ type: string; text: string }> = [];
  let submittedRequest: BcrRequestPayload | undefined;

  page.on("request", (request) => {
    const url = new URL(request.url());
    if (request.method() === "POST" && url.pathname === "/api/v1/bcr/generate_async") {
      submittedRequest = request.postDataJSON() as BcrRequestPayload;
    }
  });
  page.on("response", (response) => {
    const url = new URL(response.url());
    if (url.pathname.startsWith("/api/")) {
      network.push({
        method: response.request().method(),
        path: url.pathname,
        status: response.status(),
      });
    }
  });
  page.on("console", (message) => {
    if (["error", "warning"].includes(message.type())) {
      consoleMessages.push({ type: message.type(), text: message.text() });
    }
  });

  const unique = `bcr-local-${Date.now()}`;
  await page.goto("/register?redirect=/tasks");
  await page.getByLabel("用户名").fill(unique);
  await page.getByLabel("邮箱").fill(`${unique}@example.test`);
  await page.getByLabel("企业名称（可选）").fill("BCR 本地首跑验收");
  await page.getByLabel("密码", { exact: true }).fill("BcrLocal!12345");
  await page.getByLabel("确认密码").fill("BcrLocal!12345");
  await page.getByRole("button", { name: "注册", exact: true }).click();
  await expect(page).toHaveURL(/\/tasks$/);

  await page.getByRole("button", { name: /BCR 审核/ }).first().click();
  const createDialog = page.getByRole("dialog");
  await createDialog.getByLabel("项目名称").fill("HealthData BCR-C 文档审查");
  await createDialog.getByRole("button", { name: "创建并进入工作区" }).click();
  await expect(page).toHaveURL(/\/workspace\/task-/);

  await page.getByRole("button", { name: /1\. 主体与范围/ }).click();
  await page.getByLabel("集团名称").fill("HealthData Alliance");
  await page.getByLabel("集团结构与申请主体").fill("由多家欧洲医疗机构组成的联盟，成员共同开展医疗研究数据处理活动");
  await page.getByLabel("申请实体与职责").fill("材料未指定欧盟责任实体");
  await page.getByLabel("BCR Lead 选择理由").fill("材料未说明主管监管机构选择理由");
  await page.getByLabel("数据流与处理活动范围").fill("联盟成员在多个国家之间共享医疗研究数据");

  await page.getByRole("button", { name: /2\. 约束力与权利机制/ }).click();
  await page.getByLabel("集团内部/员工约束机制").fill("材料仅称联盟章程具有约束力，未说明可执行的法律机制");
  await page.getByLabel("第三方受益人权利条款").fill("材料未赋予数据主体第三方受益人权利");
  await page.getByLabel("责任承担与赔偿能力说明").fill("材料未指定欧盟责任实体及赔偿安排");
  await page.getByLabel("对外公开与告知安排").fill("材料未说明公开方式");

  await page.getByRole("button", { name: /3\. 治理与监管协作/ }).click();
  await page.getByLabel("培训与审计制度").fill("材料未说明培训和定期审计制度");
  await page.getByLabel("与监管协作义务").fill("材料未明确监管协作程序");
  await page.getByLabel("数据保护原则与保障").fill("材料仅作原则性说明，缺少具体技术和组织措施");
  await page.getByLabel("第三国法律评估机制").fill("材料未包含第三国法律及实践评估机制");
  await page.getByLabel("政府访问请求处理机制").fill("材料未包含政府访问请求审查和通知流程");

  await page.getByRole("button", { name: /4\. 更新与文档材料/ }).click();
  await page.getByLabel("更新机制与成员清单维护").fill("材料未说明版本更新和成员清单维护程序");
  await page.getByLabel("定义表与术语清晰度").fill("材料术语体系不完整");
  await page.getByLabel("本次重点关注项").fill("核验约束力、第三方受益人权利、欧盟责任实体和第三国法律评估");
  await page.locator(".schema-upload-card input[type=file]").setInputFiles(fixturePath);
  const selectedFile = page.getByText(path.basename(fixturePath), { exact: true });
  await expect(selectedFile).toBeVisible();
  await selectedFile.scrollIntoViewIfNeeded();
  await page.screenshot({ path: path.join(evidenceDir, "01_bcr_form_and_uploaded_file.png"), fullPage: true });

  const uploadPromise = page.waitForResponse((response) =>
    response.request().method() === "POST"
      && new URL(response.url()).pathname === "/api/v0/files/upload"
  );
  const submitPromise = page.waitForResponse((response) =>
    response.request().method() === "POST"
      && new URL(response.url()).pathname === "/api/v1/bcr/generate_async"
  );
  await page.getByRole("button", { name: "生成BCR审查报告", exact: true }).click();

  const uploadResponse = await uploadPromise;
  const submitResponse = await submitPromise;
  expect(uploadResponse.status()).toBeGreaterThanOrEqual(200);
  expect(uploadResponse.status()).toBeLessThan(300);
  expect(submitResponse.status()).toBeGreaterThanOrEqual(200);
  expect(submitResponse.status()).toBeLessThan(300);
  const submitData = await submitResponse.json() as { task_id?: string };
  expect(submitData.task_id).toBeTruthy();
  const taskId = submitData.task_id!;

  expect(submittedRequest).toBeDefined();
  expect(submittedRequest!.uploaded_documents?.[0]?.document_role).toBe("main_bcr_document");
  expect(submittedRequest!.uploaded_documents?.[0]?.file_name).toMatch(
    new RegExp(`${path.basename(fixturePath).replaceAll(".", "\\.")}$`),
  );

  const runManifest = path.join(repositoryRoot, "outputs/bcr", taskId, "run_manifest.json");
  await expect.poll(() => {
    if (!fs.existsSync(runManifest)) return "MISSING";
    return (JSON.parse(fs.readFileSync(runManifest, "utf8")) as { status?: string }).status;
  }, { timeout: 120_000 }).toBe("COMPLETED");
  await expect.poll(() => network.some((entry) =>
    entry.path === `/api/v1/bcr/tasks/${taskId}` && entry.status === 200
  )).toBe(true);
  await expect(page.getByText(/任务执行完成 \(bcr\)/).first()).toBeVisible();

  const reportTab = page.locator(".workspace-browser-tab").filter({ hasText: "报告" }).first();
  const reportHeading = page.getByRole("heading", { name: "报告审阅" });
  const citationButton = page.getByRole("button", { name: /\[1\] 引用/ }).first();
  const reportKpis = page.locator(".workspace-report-kpi-row article");
  const issueCount = reportKpis.filter({ hasText: "告警数" }).locator("strong");
  const evidenceCount = reportKpis.filter({ hasText: "证据数" }).locator("strong");
  const riskLevel = reportKpis.filter({ hasText: "风险" }).locator("strong");
  await expect.poll(async () => {
    await reportTab.click();
    return await reportHeading.isVisible()
      && await citationButton.isVisible()
      && await page.getByText(/综合评级：高风险/).first().isVisible()
      && await issueCount.textContent() === "26"
      && await evidenceCount.textContent() === "2"
      && await riskLevel.textContent() === "高风险";
  }).toBe(true);
  await page.screenshot({ path: path.join(evidenceDir, "02_bcr_report_with_citations.png"), fullPage: true });

  await citationButton.click();
  await expect(page).toHaveURL(/\/evidence\?source=EU-LAW-001/);
  await expect(page.getByText(/GDPR \(EU\) 2016\/679/).first()).toBeVisible();
  await page.screenshot({ path: path.join(evidenceDir, "03_bcr_evidence_article.png"), fullPage: true });

  // Verify article content is visible below the global navigation
  const bcrNav = page.locator(".kc-hero");
  const bcrContent = page.locator(".knowledge-preview-block p").first();
  await expect.poll(async () => {
    const navBox = await bcrNav.boundingBox();
    const contentBox = await bcrContent.boundingBox();
    if (!navBox || !contentBox) return false;
    return contentBox.y >= navBox.y + navBox.height;
  }).toBe(true);
  await page.screenshot({ path: path.join(evidenceDir, "04_bcr_knowledge_jump.png") });

  const relevantNetwork = network.filter((entry) =>
    entry.path === "/api/v0/files/upload"
      || entry.path === "/api/v1/bcr/generate_async"
      || entry.path.startsWith("/api/v1/bcr/tasks/")
      || entry.path.startsWith("/api/v1/citations/")
      || entry.path.startsWith("/api/v1/knowledge/"),
  );
  expect(relevantNetwork.some((entry) => entry.path.startsWith("/api/v1/citations/") && entry.status < 300)).toBe(true);
  expect(relevantNetwork.some((entry) => entry.path.startsWith("/api/v1/knowledge/") && entry.status < 300)).toBe(true);
  expect(consoleMessages.filter((entry) => entry.type === "error")).toEqual([]);

  fs.writeFileSync(path.join(evidenceDir, "browser_network_log.json"), `${JSON.stringify(relevantNetwork, null, 2)}\n`);
  fs.writeFileSync(path.join(evidenceDir, "browser_console_log.json"), `${JSON.stringify(consoleMessages, null, 2)}\n`);
  fs.writeFileSync(path.join(evidenceDir, "browser_result.json"), `${JSON.stringify({
    status: "PASS",
    task_id: taskId,
    fixture: path.relative(repositoryRoot, fixturePath),
    upload_status: uploadResponse.status(),
    submit_status: submitResponse.status(),
    final_url: page.url(),
    document_review_request_verified: true,
    citation_drawer_exact_article: true,
  }, null, 2)}\n`);
});
