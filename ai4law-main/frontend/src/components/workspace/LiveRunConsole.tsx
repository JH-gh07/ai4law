import { useEffect, useMemo, useState } from "react";
import { buildDemoPayload } from "../../lib/demoPayloads";
import { runModuleRequest } from "../../lib/api";
import type { ModuleKey } from "../../lib/domain";
import { extractInsight } from "../../lib/workspace";

type LiveRunConsoleProps = {
  onRunDone: (result: ApiRunResult) => void;
};

export type ApiRunResult = {
  module: ModuleKey;
  request: unknown;
  response?: unknown;
  success: boolean;
  error?: string;
  createdAt: string;
};

type ModuleMeta = {
  key: ModuleKey;
  label: string;
  desc: string;
};

const MODULES: ModuleMeta[] = [
  { key: "diagnosis", label: "Diagnosis", desc: "路径诊断并生成报告" },
  { key: "assessment", label: "Assessment", desc: "安全评估草案生成" },
  { key: "scc", label: "SCC", desc: "标准合同条款审查" },
  { key: "pipia", label: "PIPIA", desc: "个人信息保护影响评估" },
  { key: "bcr", label: "BCR", desc: "集团内部规则审查" },
  { key: "dpia", label: "DPIA", desc: "欧盟影响评估" },
  { key: "tia", label: "TIA", desc: "传输影响评估" },
  { key: "cn_flow", label: "CN_FLOW", desc: "14117 对华流动评估" },
  { key: "cpra", label: "CPRA", desc: "美国加州合规全景" }
];

export function LiveRunConsole({ onRunDone }: LiveRunConsoleProps) {
  const [module, setModule] = useState<ModuleKey>("diagnosis");
  const [payloadText, setPayloadText] = useState("");
  const [responseText, setResponseText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const moduleMeta = useMemo(() => MODULES.find((item) => item.key === module) ?? MODULES[0], [module]);

  useEffect(() => {
    setPayloadText(JSON.stringify(buildDemoPayload(module), null, 2));
    setResponseText("");
    setError(null);
  }, [module]);

  const runNow = async () => {
    let payload: unknown;
    try {
      payload = JSON.parse(payloadText);
    } catch (parseErr) {
      const message = parseErr instanceof Error ? parseErr.message : "Payload JSON parse failed";
      setError(message);
      onRunDone({
        module,
        request: payloadText,
        success: false,
        error: message,
        createdAt: new Date().toISOString()
      });
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await runModuleRequest(module, payload);
      setResponseText(JSON.stringify(response, null, 2));
      onRunDone({
        module,
        request: payload,
        response,
        success: true,
        createdAt: new Date().toISOString()
      });
    } catch (runErr) {
      const message = runErr instanceof Error ? runErr.message : "Request failed";
      setError(message);
      setResponseText("");
      onRunDone({
        module,
        request: payload,
        success: false,
        error: message,
        createdAt: new Date().toISOString()
      });
    } finally {
      setLoading(false);
    }
  };

  const insight = extractInsight(responseText ? JSON.parse(responseText) : undefined);

  return (
    <div className="space-y-3">
      <div className="run-meta-row">
        <div>
          <div className="text-xs tracking-[0.2em] text-scientific-700/70">MODULE RUNNER</div>
          <h4 className="font-display text-xl text-ink">{moduleMeta.label}</h4>
          <p className="text-sm text-scientific-800/80">{moduleMeta.desc}</p>
        </div>
        <select value={module} onChange={(event) => setModule(event.target.value as ModuleKey)} className="runner-select">
          {MODULES.map((item) => (
            <option key={item.key} value={item.key}>
              {item.label}
            </option>
          ))}
        </select>
      </div>

      <div className="grid gap-3 xl:grid-cols-2">
        <div>
          <div className="runner-title">Request Payload</div>
          <textarea className="runner-textarea" value={payloadText} onChange={(event) => setPayloadText(event.target.value)} />
          <div className="mt-2 flex justify-end">
            <button className="pill-btn-primary" onClick={runNow} disabled={loading}>
              {loading ? "Running..." : `Run ${moduleMeta.label}`}
            </button>
          </div>
        </div>

        <div>
          <div className="runner-title">Response</div>
          <textarea className="runner-textarea" value={responseText} readOnly placeholder="Run module to view response JSON" />
        </div>
      </div>

      {error ? <div className="runner-error">{error}</div> : null}

      {(insight.reportPath || insight.recommendedPath || insight.riskLevel || Object.keys(insight.outputFiles).length > 0) ? (
        <div className="runner-insight">
          <div className="runner-title">Run Summary</div>
          {insight.recommendedPath ? <div>Recommended Path: {insight.recommendedPath}</div> : null}
          {insight.riskLevel ? <div>Risk Level: {insight.riskLevel}</div> : null}
          {insight.reportPath ? <div>Report Path: <code>{insight.reportPath}</code></div> : null}
          {Object.keys(insight.outputFiles).length > 0 ? (
            <ul className="list-disc pl-5">
              {Object.entries(insight.outputFiles).map(([key, value]) => (
                <li key={key}>
                  {key}: <code>{value}</code>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
