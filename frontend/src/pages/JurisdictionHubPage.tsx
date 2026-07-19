import { Link, useParams } from "react-router-dom";
import { listModules } from "../api/modules";
import { useLang } from "../lib/language";

type JurisdictionHubPageProps = {
  onStart: () => void;
};

type JurisdictionCode = "cn" | "eu" | "us";

const JURISDICTION_META: Record<JurisdictionCode, { banner: string; summary: string; modules: string[] }> = {
  cn: {
    banner: "从中国大陆向境外传输数据",
    summary: "适用于个人信息、重要数据出境合规分析与申报材料准备。",
    modules: ["diagnosis", "assessment", "pipia", "scc"]
  },
  eu: {
    banner: "从欧盟向境外传输数据",
    summary: "围绕 SCC、BCR、DPIA、TIA 的跨境传输合规支持。",
    modules: ["scc", "bcr", "dpia", "tia"]
  },
  us: {
    banner: "从美国向境外传输数据",
    summary: "覆盖 EO14117 与 CPRA 的风险结论与治理检查。",
    modules: ["cn_flow", "cpra"]
  }
};

const MODULE_TEXT: Record<string, { input: string; output: string; scene: string }> = {
  diagnosis: { input: "动态问答", output: "合规路径诊断报告", scene: "首次判定路径" },
  assessment: { input: "表单 + 附件", output: "数据出境风险自评估报告", scene: "安全评估路径材料准备" },
  pipia: { input: "表单 + 附件", output: "PIPIA 报告草案", scene: "认证/标准合同备案准备" },
  scc: { input: "SCC 文本/附件", output: "SCC 合规审查报告", scene: "标准合同条款审阅" },
  bcr: { input: "BCR 文本 + 集团信息", output: "BCR 审查报告", scene: "集团规则审查" },
  dpia: { input: "问卷式风险信息", output: "DPIA 草案", scene: "处理活动风险评估" },
  tia: { input: "国家 + 接收方 + 补充措施", output: "TIA 草案", scene: "第三国保护水平评估" },
  cn_flow: { input: "实体/数据清单", output: "14117 风险评估结论报告", scene: "限制性传输风险判断" },
  cpra: { input: "数据映射与制度材料", output: "CPRA 合规全景报告", scene: "加州隐私治理检查" }
};

export function JurisdictionHubPage({ onStart }: JurisdictionHubPageProps) {
  const { t } = useLang();
  const params = useParams();
  const code = (params.code ?? "cn").toLowerCase() as JurisdictionCode;
  const meta = JURISDICTION_META[code] ?? JURISDICTION_META.cn;
  const modules = listModules().filter((item) => meta.modules.includes(item.key));

  return (
    <section className="page-shell jurisdiction-shell">
      <header className="jurisdiction-head">
        <p className="jurisdiction-kicker">{t("jurisdictionKicker")}</p>
        <h2>{meta.banner}</h2>
        <p className="jurisdiction-summary">{meta.summary}</p>
        <div className="jurisdiction-actions">
          <button className="pill-btn-primary" onClick={onStart}>{t("startCta")}</button>
          <Link className="pill-btn" to="/tasks">{t("openWorkspace")}</Link>
        </div>
      </header>

      <section className="jurisdiction-modules">
        {modules.map((module) => {
          const text = MODULE_TEXT[module.key];
          return (
            <article key={module.key} className="jurisdiction-module-card">
              <div className="jurisdiction-module-head">
                <h3>{module.label}</h3>
                <span>{module.jurisdiction}</span>
              </div>
              <p>{text.scene}</p>
              <dl>
                <div>
                  <dt>{t("moduleInputLabel")}</dt>
                  <dd>{text.input}</dd>
                </div>
                <div>
                  <dt>{t("moduleOutputLabel")}</dt>
                  <dd>{text.output}</dd>
                </div>
              </dl>
              <div className="jurisdiction-module-actions">
                <Link className="pill-btn" to="/workspace">{t("navWorkspace")}</Link>
                <Link className="pill-btn" to="/reports">{t("navReports")}</Link>
              </div>
            </article>
          );
        })}
      </section>
    </section>
  );
}

