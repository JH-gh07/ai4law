import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test } from "@playwright/test";

const currentDir = path.dirname(fileURLToPath(import.meta.url));
const repositoryRoot = path.resolve(currentDir, "../../..");
const fixturePath = path.join(
  repositoryRoot,
  "backend/tests/pipia/fixtures/case_03_seacommerce_scc_draft.md",
);
const evidenceDir = path.join(
  repositoryRoot,
  "status/check/phase3_pipia_firstrun_20260808/browser",
);

type NetworkEntry = { method: string; path: string; status: number };

test("PIPIA 本地真实上传、生成和引用跳转闭环", async ({ page }) => {
  fs.mkdirSync(evidenceDir, { recursive: true });
  const network: NetworkEntry[] = [];
  const consoleMessages: Array<{ type: string; text: string }> = [];

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

  const unique = `pipia-local-${Date.now()}`;
  await page.goto("/register?redirect=/tasks");
  await page.getByLabel("用户名").fill(unique);
  await page.getByLabel("邮箱").fill(`${unique}@example.test`);
  await page.getByLabel("企业名称（可选）").fill("PIPIA 本地首跑验收");
  await page.getByLabel("密码", { exact: true }).fill("PipiaLocal!12345");
  await page.getByLabel("确认密码").fill("PipiaLocal!12345");
  await page.getByRole("button", { name: "注册", exact: true }).click();
  await expect(page).toHaveURL(/\/tasks$/);

  await page.getByRole("button", { name: /认证\/标准合同路径/ }).first().click();
  const createDialog = page.getByRole("dialog");
  await createDialog.getByLabel("项目名称").fill("海淘优选 PIPIA 本地首跑");
  await createDialog.getByRole("button", { name: "创建并进入工作区" }).click();
  await expect(page).toHaveURL(/\/workspace\/task-/);

  await page.getByRole("button", { name: /1\. 企业基本信息/ }).click();
  await page.getByLabel("企业名称", { exact: true }).fill("海淘优选（杭州）科技有限公司");
  await page.getByLabel("统一社会信用代码").fill("原始测试案例未提供");
  await page.getByLabel("行业").fill("跨境电子商务");
  await page.getByLabel("处理个人信息规模").fill("8000000");
  await page.getByLabel("出境普通个人信息规模").fill("500000");
  await page.getByLabel("出境敏感个人信息规模").fill("10000");

  await page.getByRole("button", { name: /2\. 出境场景与范围/ }).click();
  await page.getByLabel("路径类型").selectOption("scc_filing");
  await page.getByRole("textbox", { name: "出境目的", exact: true }).fill("个性化营销与市场分析");
  await page.getByRole("textbox", { name: "境外接收方", exact: true }).fill("SeaCommerce Pte. Ltd.");
  await page.getByLabel("接收方国家/地区").fill("新加坡");
  await page.getByLabel("处理合法性基础").fill("单独同意；合同履行必要性主张待复核");
  await page.getByLabel("普通个人信息类别（逗号分隔）").fill("偏好标签,浏览记录,订单摘要");
  await page.getByLabel("敏感个人信息类别（逗号分隔）").fill("可能推断健康状态的偏好标签");
  await page.getByLabel("数据主体规模").fill("500000");

  await page.getByRole("button", { name: /3\. 权利保障与应急/ }).click();
  await page.getByLabel("告知机制").fill("隐私政策未明确披露新加坡接收方");
  await page.getByLabel("同意机制").fill("单独同意记录待批量核验");
  await page.getByLabel("权利请求渠道").fill("privacy@example.com");
  await page.getByLabel("保存与删除策略").fill("按最短必要期限保存，终止后删除或返还");
  await page.getByLabel("事件响应SLA（小时）").fill("72");
  await page.getByLabel("升级路径").fill("隐私负责人 -> 法务 -> 管理层");
  await page.getByLabel("附件角色").selectOption("scc_contract");

  await page.getByRole("button", { name: /4\. 路径证据核验/ }).click();
  await page.getByLabel("接收方告知是否完整").selectOption("no");
  await page.getByLabel("敏感信息分类是否确认").selectOption("no");
  await page.getByLabel("同意证据是否完整").selectOption("no");
  await page.getByLabel("标准合同必要条款是否完整").selectOption("no");
  await page.locator(".schema-upload-card input[type=file]").setInputFiles(fixturePath);
  await expect(page.getByText(path.basename(fixturePath), { exact: true })).toBeVisible();
  await page.screenshot({ path: path.join(evidenceDir, "01_pipia_form_and_uploaded_file.png"), fullPage: true });

  const uploadPromise = page.waitForResponse((response) =>
    response.request().method() === "POST" && new URL(response.url()).pathname === "/api/v0/files/upload"
  );
  const submitPromise = page.waitForResponse((response) =>
    response.request().method() === "POST" && new URL(response.url()).pathname === "/api/v1/pipia/generate_async"
  );
  await page.getByRole("button", { name: "运行 PIPIA", exact: true }).click();

  const uploadResponse = await uploadPromise;
  const submitResponse = await submitPromise;
  expect(uploadResponse.status()).toBeGreaterThanOrEqual(200);
  expect(uploadResponse.status()).toBeLessThan(300);
  expect(submitResponse.status()).toBeGreaterThanOrEqual(200);
  expect(submitResponse.status()).toBeLessThan(300);
  const submitData = await submitResponse.json() as { task_id?: string };
  expect(submitData.task_id).toBeTruthy();
  const taskId = submitData.task_id!;

  const runManifest = path.join(repositoryRoot, "outputs/pipia", taskId, "run_manifest.json");
  await expect.poll(() => {
    if (!fs.existsSync(runManifest)) return "MISSING";
    return (JSON.parse(fs.readFileSync(runManifest, "utf8")) as { status?: string }).status;
  }, { timeout: 120_000 }).toBe("COMPLETED");
  await expect.poll(() => network.some((entry) =>
    entry.path === `/api/v1/pipia/tasks/${taskId}` && entry.status === 200
  )).toBe(true);
  await expect(page.getByText(/任务执行完成 \(pipia\)/).first()).toBeVisible();

  const reportTab = page.getByRole("button", { name: /^报告/ });
  const reportHeading = page.getByRole("heading", { name: "报告审阅" });
  const citationButton = page.getByRole("button", { name: /\[1\] 引用/ }).first();
  await expect.poll(async () => {
    if (await reportHeading.isVisible() && await citationButton.isVisible()) {
      return true;
    }
    await reportTab.click();
    return false;
  }).toBe(true);
  await page.screenshot({ path: path.join(evidenceDir, "02_pipia_report_with_citations.png"), fullPage: true });
  const knowledgeIndexPromise = page.waitForResponse((response) =>
    new URL(response.url()).pathname === "/api/v1/knowledge/index" && response.status() < 300,
  );
  await citationButton.click();
  await expect(page).toHaveURL(/\/evidence\?source=CN-LAW-003/);
  await knowledgeIndexPromise;
  await expect(page.getByText(/第.*条/, { exact: false }).first()).toBeVisible();
  await page.screenshot({ path: path.join(evidenceDir, "03_pipia_evidence_article.png"), fullPage: true });
  // Verify article content is visible below the global navigation
  const evidenceNav = page.locator(".kc-hero");
  const articleContent = page.locator(".knowledge-preview-block p").first();
  await expect.poll(async () => {
    const navBox = await evidenceNav.boundingBox();
    const contentBox = await articleContent.boundingBox();
    if (!navBox || !contentBox) return false;
    return contentBox.y >= navBox.y + navBox.height;
  }).toBe(true);
  await page.screenshot({ path: path.join(evidenceDir, "04_pipia_knowledge_jump.png") });

  const relevantNetwork = network.filter((entry) =>
    entry.path === "/api/v0/files/upload"
      || entry.path === "/api/v1/pipia/generate_async"
      || entry.path.startsWith("/api/v1/pipia/tasks/")
      || entry.path.startsWith("/api/v1/citations/")
      || entry.path.startsWith("/api/v1/knowledge/"),
  );
  expect(relevantNetwork.some((entry) => entry.path.startsWith("/api/v1/citations/") && entry.status < 300)).toBe(true);
  expect(relevantNetwork.some((entry) => entry.path === "/api/v1/knowledge/index" && entry.status < 300)).toBe(true);
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
    citation_drawer_exact_article: true,
  }, null, 2)}\n`);
});
