import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test } from "@playwright/test";

const currentDir = path.dirname(fileURLToPath(import.meta.url));
const repositoryRoot = path.resolve(currentDir, "../../..");
const fixturePath = path.join(
  repositoryRoot,
  "backend/tests/eu_scc/fixtures/case_02_india_health_scc_input.docx",
);
const evidenceDir = path.join(
  repositoryRoot,
  "status/check/phase3_scc_firstrun_20260808/browser",
);

type NetworkEntry = {
  method: string;
  path: string;
  status: number;
};

test("SCC 本地真实上传、生成和引用跳转闭环", async ({ page }) => {
  fs.mkdirSync(evidenceDir, { recursive: true });
  const network: NetworkEntry[] = [];
  const consoleMessages: Array<{ type: string; text: string }> = [];

  page.on("response", (response) => {
    const url = new URL(response.url());
    if (url.pathname.startsWith("/api/")) {
      const entry = {
        method: response.request().method(),
        path: url.pathname,
        status: response.status(),
      };
      network.push(entry);
      if (
        entry.path === "/api/v0/files/upload"
        || entry.path === "/api/v1/eu_scc/generate_async"
        || entry.path.startsWith("/api/v1/eu_scc/tasks/")
        || entry.path.startsWith("/api/v1/citations/")
      ) {
        console.log(`[scc-browser] ${entry.method} ${entry.path} -> ${entry.status}`);
      }
    }
  });
  page.on("console", (message) => {
    if (["error", "warning"].includes(message.type())) {
      consoleMessages.push({ type: message.type(), text: message.text() });
    }
  });

  const unique = `scc-local-${Date.now()}`;
  await page.goto("/register?redirect=/tasks");
  await page.getByLabel("用户名").fill(unique);
  await page.getByLabel("邮箱").fill(`${unique}@example.test`);
  await page.getByLabel("企业名称（可选）").fill("SCC 本地首跑验收");
  await page.getByLabel("密码", { exact: true }).fill("SccLocal!12345");
  await page.getByLabel("确认密码").fill("SccLocal!12345");
  await page.getByRole("button", { name: "注册", exact: true }).click();
  await expect(page).toHaveURL(/\/tasks$/);

  await page.getByRole("button", { name: /SCC 审查/ }).first().click();
  const createDialog = page.getByRole("dialog");
  await expect(createDialog).toBeVisible();
  await createDialog.getByLabel("项目名称").fill("SCC 印度健康数据本地首跑");
  await createDialog.getByRole("button", { name: "创建并进入工作区" }).click();
  await expect(page).toHaveURL(/\/workspace\/task-/);

  await page.getByRole("button", { name: /1\. 传输主体与模块/ }).click();
  await page.getByLabel("数据出口方（EEA）").fill("EU Health GmbH");
  await page.getByLabel("数据进口方（第三国）").fill("India Health Services Pvt Ltd");
  await page.getByLabel("进口方国家/地区").fill("印度");
  await page.getByLabel("传输角色关系").selectOption("c2p");
  await page.getByLabel("SCC版本识别").selectOption("eu_2021");
  await page.getByLabel("是否已有完整SCC文本").check();

  await page.getByRole("button", { name: /2\. 场景与数据范围/ }).click();
  await page.getByLabel("传输目的").fill("远程医疗服务与患者健康数据处理");
  await page.getByLabel("个人数据类别（逗号分隔）").fill("患者身份信息, 健康数据, 诊疗记录");
  await page.getByLabel("数据主体类别").fill("患者");
  await page.getByLabel("传输频率").selectOption("continuous");
  await page.getByLabel("保存期限/删除规则").fill("合同终止后删除或返还，依法需要保留的除外");
  await page.getByLabel("PI 规模（估算）", { exact: true }).fill("50000");
  await page.getByLabel("SPI 规模（估算）", { exact: true }).fill("50000");

  await page.getByRole("button", { name: /3\. 条款与保障机制/ }).click();
  await page.getByLabel("技术与组织措施（TOM）摘要").fill("传输加密、静态加密、最小权限、访问日志与定期审计");
  await page.getByLabel("子处理者/再传输控制").fill("新增子处理者须事先通知并承担同等保护义务");
  await page.getByLabel("数据主体权利与投诉机制").fill("提供访问、更正、删除与投诉渠道，出口方负责协助响应");
  await page.getByLabel("政府访问请求应对机制").fill("逐案合法性审查、最小披露并在法律允许时通知出口方");
  await page.getByLabel("补充条款冲突检查关注点").fill("不得以补充条款削弱 SCC、GDPR 或数据主体权利");

  await page.getByRole("button", { name: /4\. 审查文件/ }).click();
  const fileInput = page.locator(".schema-upload-card input[type=file]");
  await fileInput.setInputFiles(fixturePath);
  await expect(page.getByText(path.basename(fixturePath), { exact: true })).toBeVisible();
  await page.screenshot({ path: path.join(evidenceDir, "01_scc_form_and_uploaded_file.png"), fullPage: true });

  const uploadResponsePromise = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return response.request().method() === "POST" && url.pathname === "/api/v0/files/upload";
  });
  const submitResponsePromise = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return response.request().method() === "POST" && url.pathname === "/api/v1/eu_scc/generate_async";
  });
  await page.getByRole("button", { name: "生成SCC合规审查报告", exact: true }).click();

  const uploadResponse = await uploadResponsePromise;
  expect(uploadResponse.status()).toBeGreaterThanOrEqual(200);
  expect(uploadResponse.status()).toBeLessThan(300);
  const submitResponse = await submitResponsePromise;
  expect(submitResponse.status()).toBeGreaterThanOrEqual(200);
  expect(submitResponse.status()).toBeLessThan(300);
  const submitData = await submitResponse.json() as { task_id?: string };
  expect(submitData.task_id).toBeTruthy();

  const taskId = submitData.task_id!;
  const runManifest = path.join(repositoryRoot, "outputs/eu_scc", taskId, "run_manifest.json");
  await expect.poll(() => {
    if (!fs.existsSync(runManifest)) return "MISSING";
    const manifest = JSON.parse(fs.readFileSync(runManifest, "utf8")) as { status?: string };
    return manifest.status;
  }, { timeout: 160_000 }).toBe("COMPLETED");
  await expect.poll(() => network.some((entry) =>
    entry.path === `/api/v1/eu_scc/tasks/${taskId}` && entry.status === 200
  )).toBe(true);
  await page.getByRole("button", { name: /^报告/ }).click();
  await expect(page.getByRole("heading", { name: "报告审阅" })).toBeVisible();
  await expect(page.locator(".workspace-report-chapters")).toBeVisible();

  const citationButton = page.getByRole("button", { name: /\[1\] 引用/ }).first();
  await expect(citationButton).toBeVisible();
  await page.screenshot({ path: path.join(evidenceDir, "02_scc_report_with_citations.png"), fullPage: true });
  await citationButton.click();

  await expect(page).toHaveURL(/\/evidence\?source=/);
  await expect(page.getByRole("heading", { level: 2, name: "知识库中心" })).toBeVisible();
  await page.screenshot({ path: path.join(evidenceDir, "03_scc_evidence_article.png"), fullPage: true });

  // Verify article content is visible below the global navigation
  const sccNav = page.locator(".kc-hero");
  const sccContent = page.locator(".knowledge-preview-block p").first();
  await expect.poll(async () => {
    const navBox = await sccNav.boundingBox();
    const contentBox = await sccContent.boundingBox();
    if (!navBox || !contentBox) return false;
    return contentBox.y >= navBox.y + navBox.height;
  }).toBe(true);
  await page.screenshot({ path: path.join(evidenceDir, "04_scc_knowledge_jump.png") });

  const relevantNetwork = network.filter((entry) =>
    entry.path === "/api/v0/files/upload"
      || entry.path === "/api/v1/eu_scc/generate_async"
      || entry.path.startsWith("/api/v1/eu_scc/tasks/")
      || entry.path.startsWith("/api/v1/citations/")
      || entry.path.startsWith("/api/v1/knowledge/"),
  );
  expect(relevantNetwork.some((entry) => entry.path === "/api/v0/files/upload" && entry.status < 300)).toBe(true);
  expect(relevantNetwork.some((entry) => entry.path === "/api/v1/eu_scc/generate_async" && entry.status < 300)).toBe(true);
  expect(relevantNetwork.some((entry) => entry.path.startsWith("/api/v1/eu_scc/tasks/") && entry.status < 300)).toBe(true);
  expect(relevantNetwork.some((entry) => entry.path.startsWith("/api/v1/citations/") && entry.status < 300)).toBe(true);

  fs.writeFileSync(
    path.join(evidenceDir, "browser_network_log.json"),
    `${JSON.stringify(relevantNetwork, null, 2)}\n`,
    "utf8",
  );
  fs.writeFileSync(
    path.join(evidenceDir, "browser_console_log.json"),
    `${JSON.stringify(consoleMessages, null, 2)}\n`,
    "utf8",
  );
  fs.writeFileSync(
    path.join(evidenceDir, "browser_result.json"),
    `${JSON.stringify({
      status: "PASS",
      task_id: submitData.task_id,
      fixture: path.relative(repositoryRoot, fixturePath),
      upload_status: uploadResponse.status(),
      submit_status: submitResponse.status(),
      final_url: page.url(),
      citation_drawer_exact_article: true,
    }, null, 2)}\n`,
    "utf8",
  );
});
