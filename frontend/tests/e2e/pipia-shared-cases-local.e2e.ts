import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test, type Page } from "@playwright/test";

const repositoryRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
const readScenario = (relativePath: string) =>
  JSON.parse(fs.readFileSync(path.join(repositoryRoot, relativePath), "utf8")) as { request: Record<string, any> };
const haitao = readScenario("benchmarks/cases/pipia/haitao_marketing_singapore/scenario.json");
const weilan = readScenario("benchmarks/cases/pipia/weilan_hr_exemption_us/scenario.json");
const eurocert = readScenario("benchmarks/cases/pipia/zhifutong_eurocert_de/scenario.json");
const escapeRegExp = (value: string) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

type SharedCase = {
  key: "haitao" | "weilan" | "eurocert";
  scenario: { request: Record<string, any> };
  fixture: string;
  route: string;
  expectedRisk: string;
  expectedStatus: string;
  expectedTitles: string[];
};

const CASES: SharedCase[] = [
  {
    key: "haitao",
    scenario: haitao,
    fixture: "benchmarks/source-materials/cn/legacy-docx/"认证_标准合同路径"测试案例及预期输出.docx",
    route: "scc_filing",
    expectedRisk: "MEDIUM",
    expectedStatus: "blocked",
    expectedTitles: ["缺少标准合同备案核心材料", "告知不充分", "敏感信息识别存疑", "同意记录不完整"],
  },
  {
    key: "weilan",
    scenario: weilan,
    fixture: "backend/tests/pipia/fixtures/weilan_employee_handbook_excerpt.txt",
    route: "hr_exemption",
    expectedRisk: "MEDIUM",
    expectedStatus: "supplement_required",
    expectedTitles: ["跨境人力资源管理豁免条件待验证", "集体合同和员工手册条款不充分", "境外接收方政策不透明", "薪酬等敏感信息需特殊保护"],
  },
  {
    key: "eurocert",
    scenario: eurocert,
    fixture: "backend/tests/pipia/fixtures/zhifutong_eurocert_contract_excerpt.txt",
    route: "certification",
    expectedRisk: "HIGH",
    expectedStatus: "blocked",
    expectedTitles: ["认证机构资质不符合中国个人信息保护认证要求", "合法性基础论证存在法律适用性争议", "法律文件管辖条款对中国个人信息主体维权构成障碍"],
  },
];

async function registerAndCreateWorkspace(page: Page, key: string) {
  const unique = `pipia-shared-${key}-${Date.now()}`;
  await page.goto("/register?redirect=/tasks");
  await page.getByLabel("用户名").fill(unique);
  await page.getByLabel("邮箱").fill(`${unique}@example.test`);
  await page.getByLabel("企业名称（可选）").fill(`PIPIA ${key} 共享案例验收`);
  await page.getByLabel("密码", { exact: true }).fill("PipiaLocal!12345");
  await page.getByLabel("确认密码").fill("PipiaLocal!12345");
  await page.getByRole("button", { name: "注册", exact: true }).click();
  await expect(page).toHaveURL(/\/tasks$/);
  await page.getByRole("button", { name: /认证\/标准合同路径/ }).first().click();
  const createDialog = page.getByRole("dialog");
  await createDialog.getByLabel("项目名称").fill(`PIPIA ${key} 共享案例验收`);
  await createDialog.getByRole("button", { name: "创建并进入工作区" }).click();
  await expect(page).toHaveURL(/\/workspace\/task-/);
}

async function fillSharedCase(page: Page, item: SharedCase) {
  const request = item.scenario.request;
  const profile = request.company_profile;
  const transfer = request.transfer_context;
  const scope = request.personal_info_scope;
  const rights = request.rights_protection;
  const emergency = request.emergency_plan;
  const evidence = request.path_evidence ?? {};
  const purposeParts = String(transfer.purpose).split("；");
  const legalParts = String(transfer.legal_basis).split("；");
  const escalationParts = String(emergency.escalation_path).split("；");
  const labeled = (parts: string[], label: string) => parts.find((value) => value.startsWith(label))?.slice(label.length).trim() ?? "";
  const unlabeled = (parts: string[], labels: string[]) => parts.filter((value) => !labels.some((label) => value.startsWith(label))).join("；");
  const tri = (value: boolean | null | undefined) => value === true ? "yes" : value === false ? "no" : "unknown";

  await page.getByRole("button", { name: /1\. 企业基本信息/ }).click();
  await page.getByLabel("企业名称", { exact: true }).fill(profile.company_name);
  await page.getByLabel("统一社会信用代码").fill(profile.company_uscc);
  await page.getByLabel("行业").fill(profile.industry);
  await page.getByLabel("处理个人信息规模").fill(String(profile.processing_person_count));
  await page.getByLabel("出境普通个人信息规模").fill(String(profile.outbound_pi_count));
  await page.getByLabel("出境敏感个人信息规模").fill(String(profile.outbound_spi_count));
  await page.getByLabel("整体业务概况").fill(labeled(purposeParts, "业务概况："));
  await page.getByLabel("处理活动概况").fill(labeled(purposeParts, "处理活动："));

  await page.getByRole("button", { name: /2\. 出境场景与范围/ }).click();
  await page.getByLabel("路径类型").selectOption(item.route);
  await page.getByLabel("出境场景名称").fill(labeled(purposeParts, "场景："));
  await page.getByLabel("出境频率").selectOption(labeled(purposeParts, "频率："));
  await page.getByLabel("出境方式（API/文件/同步）").fill(labeled(purposeParts, "方式："));
  await page.getByRole("textbox", { name: "出境目的", exact: true }).fill(unlabeled(purposeParts, ["场景：", "频率：", "方式：", "业务概况：", "处理活动："]));
  await page.getByLabel("境外接收方").fill(transfer.recipient_name);
  await page.getByLabel("接收方国家/地区").fill(transfer.recipient_country_region);
  await page.getByLabel("处理合法性基础").fill(unlabeled(legalParts, ["合法性论证：", "必要性论证："]));
  await page.getByLabel("合法性论证").fill(labeled(legalParts, "合法性论证："));
  await page.getByLabel("必要性论证").fill(labeled(legalParts, "必要性论证："));
  await page.getByLabel("普通个人信息类别（逗号分隔）").fill(scope.pi_categories.join(","));
  await page.getByLabel("敏感个人信息类别（逗号分隔）").fill(scope.spi_categories.join(","));
  await page.getByLabel("数据主体规模").fill(String(scope.subject_volume));

  await page.getByRole("button", { name: /3\. 权利保障与应急/ }).click();
  await page.getByLabel("告知机制").fill(rights.notice_mechanism);
  await page.getByLabel("同意机制").fill(rights.consent_mechanism);
  await page.getByLabel("权利请求渠道").fill(rights.dsar_channel);
  await page.getByLabel("保存与删除策略").fill(rights.retention_policy);
  await page.getByLabel("事件响应SLA（小时）").fill(String(emergency.incident_response_sla_hours));
  await page.getByLabel("升级路径").fill(unlabeled(escalationParts, ["链路：", "股权：", "控制人：", "境内外投资：", "组织与个保机构："]));
  await page.getByLabel("附件角色").selectOption(request.attachments[0].file_role);

  await page.getByRole("button", { name: /4\. 路径证据核验/ }).click();
  for (const field of [
    "接收方告知是否完整", "敏感信息分类是否确认", "同意证据是否完整", "标准合同必要条款是否完整",
    "HR制度是否依法制定", "员工手册是否含明确出境条款", "集体合同是否含明确出境条款", "接收方隐私政策是否已提供",
    "认证机构是否获中国认可", "认证法定义务条款是否已提供", "是否包含中国个人信息主体权利条款",
  ]) {
    const mapping: Record<string, string> = {
      "接收方告知是否完整": "recipient_notice_complete",
      "敏感信息分类是否确认": "sensitive_information_classification_confirmed",
      "同意证据是否完整": "consent_evidence_complete",
      "标准合同必要条款是否完整": "scc_required_clauses_complete",
      "HR制度是否依法制定": "hr_rules_lawfully_adopted",
      "员工手册是否含明确出境条款": "employee_handbook_has_explicit_cross_border_terms",
      "集体合同是否含明确出境条款": "collective_agreement_has_explicit_cross_border_terms",
      "接收方隐私政策是否已提供": "recipient_privacy_policy_provided",
      "认证机构是否获中国认可": "certification_body_china_recognized",
      "认证法定义务条款是否已提供": "certification_legal_obligation_citation_provided",
      "是否包含中国个人信息主体权利条款": "china_data_subject_rights_terms_present",
    };
    if (mapping[field] in evidence) await page.getByLabel(field).selectOption(tri(evidence[mapping[field]]));
  }
  if (item.key === "eurocert") {
    await page.getByLabel("合同适用法律").fill(evidence.contract_governing_law);
    await page.getByLabel("合同专属管辖").fill(evidence.contract_exclusive_jurisdiction);
  }

  const fixturePath = path.join(repositoryRoot, item.fixture);
  await page.locator(".schema-upload-card input[type=file]").setInputFiles(fixturePath);
  await expect(page.getByText(path.basename(fixturePath), { exact: true })).toBeVisible();
  return request;
}

for (const item of CASES) {
  test(`PIPIA 共享案例 ${item.key} 本地 HTTP、SSE 和结果一致性`, async ({ page }) => {
    const network: Array<{ path: string; status: number }> = [];
    page.on("response", (response) => {
      const url = new URL(response.url());
      if (url.pathname.startsWith("/api/")) network.push({ path: url.pathname, status: response.status() });
    });
    await registerAndCreateWorkspace(page, item.key);
    const expectedRequest = await fillSharedCase(page, item);
    const submitPromise = page.waitForResponse((response) =>
      response.request().method() === "POST" && new URL(response.url()).pathname === "/api/v1/pipia/generate_async",
    );
    await page.getByRole("button", { name: "运行 PIPIA", exact: true }).click();
    const submitResponse = await submitPromise;
    expect(submitResponse.status()).toBeLessThan(300);
    const taskId = (await submitResponse.json() as { task_id: string }).task_id;
    const submitted = submitResponse.request().postDataJSON() as Record<string, any>;
    expect({ ...submitted, attachments: [] }).toEqual({ ...expectedRequest, attachments: [] });
    expect(submitted.attachments).toHaveLength(expectedRequest.attachments.length);
    for (const [index, expectedAttachment] of expectedRequest.attachments.entries()) {
      const submittedAttachment = submitted.attachments[index];
      expect(submittedAttachment.file_role).toBe(expectedAttachment.file_role);
      expect(submittedAttachment.file_format).toBe(expectedAttachment.file_format);
      expect(submittedAttachment.file_name).toMatch(new RegExp(`${escapeRegExp(expectedAttachment.file_name)}$`));
      expect(path.basename(submittedAttachment.storage_uri)).toBe(submittedAttachment.file_name);
    }
    const token = await page.evaluate(() =>
      globalThis.sessionStorage.getItem("ai4law_auth_token_v1")
        ?? globalThis.localStorage.getItem("ai4law_auth_token_v1"),
    );
    expect(token).toBeTruthy();
    const authHeaders = { Authorization: `Bearer ${token}` };

    await expect.poll(async () => {
      const response = await page.request.get(`/api/v1/pipia/tasks/${taskId}`, { headers: authHeaders });
      if (!response.ok()) return null;
      const data = await response.json() as { state?: string; result?: { risk_level?: string; issues?: Array<{ title?: string }>; filing_readiness?: { status?: string } } };
      return data.state === "COMPLETED" ? data : null;
    }, { timeout: 120_000 }).toMatchObject({
      state: "COMPLETED",
      result: { risk_level: item.expectedRisk, filing_readiness: { status: item.expectedStatus } },
    });
    const finalResponse = await page.request.get(`/api/v1/pipia/tasks/${taskId}`, { headers: authHeaders });
    const finalData = await finalResponse.json() as { result: { issues: Array<{ title: string }>; output_files: Record<string, string> } };
    const titles = finalData.result.issues.map((issue) => issue.title);
    for (const title of item.expectedTitles) expect(titles).toContain(title);
    expect(Object.keys(finalData.result.output_files)).toEqual(expect.arrayContaining(["markdown", "docx", "pdf", "zip", "citation_map_json"]));
    expect(network.some((entry) => entry.path.includes(`/events/task/${taskId}/stream`) && entry.status === 200)).toBe(true);
    await expect(page.getByText(/任务执行完成 \(pipia\)/).first()).toBeVisible();
    const generatedResults = page.locator("button.ide-tree-row-root", { hasText: "生成结果" }).locator("small");
    await expect(generatedResults).toHaveText(/^[1-9]\d*$/, { timeout: 15_000 });
    fs.mkdirSync(path.join(repositoryRoot, "status/check/phase3_pipia_shared_local"), { recursive: true });
    await page.screenshot({ path: path.join(repositoryRoot, "status/check/phase3_pipia_shared_local", `${item.key}_execution_flow.png`), fullPage: true });
    const reportTab = page.getByRole("button", { name: /^报告/ });
    await reportTab.click();
    await expect(page.getByRole("heading", { name: "报告审阅" })).toBeVisible();
    await expect(page.getByText(item.expectedRisk, { exact: true })).toBeVisible();
    await expect(page.getByText("暂无可审阅报告。", { exact: true })).toHaveCount(0);
    await expect(page.locator(".workspace-report-chapters .workspace-report-chapter").first()).toBeVisible();
    await page.screenshot({ path: path.join(repositoryRoot, "status/check/phase3_pipia_shared_local", `${item.key}_report.png`), fullPage: true });
    const pdfTab = page.getByRole("tab", { name: "PDF 预览" });
    await expect(pdfTab).toBeEnabled();
    await pdfTab.click();
    const pdfCanvas = page.locator(".pdf-viewer-canvas");
    await expect(pdfCanvas).toBeVisible();
    await expect(page.locator(".pdf-viewer")).toHaveAttribute("aria-busy", "false");
    const nonWhitePixels = await pdfCanvas.evaluate((canvas: HTMLCanvasElement) => {
      const context = canvas.getContext("2d");
      if (!context) return 0;
      const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
      let count = 0;
      for (let index = 0; index < pixels.length; index += 4) {
        if (pixels[index] < 245 || pixels[index + 1] < 245 || pixels[index + 2] < 245) count += 1;
      }
      return count;
    });
    expect(nonWhitePixels).toBeGreaterThan(1_000);
    await page.screenshot({ path: path.join(repositoryRoot, "status/check/phase3_pipia_shared_local", `${item.key}_pdf.png`), fullPage: true });
    fs.writeFileSync(path.join(repositoryRoot, "status/check/phase3_pipia_shared_local", `${item.key}_network.json`), JSON.stringify(network, null, 2));
  });
}
