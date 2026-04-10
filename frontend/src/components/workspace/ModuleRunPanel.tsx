import { useEffect, useMemo, useState } from "react";
import type { ModuleKey, RunMode } from "../../lib/domain";
import { findModule, getDefaultPayload, hasAsync, listModules, runModule } from "../../lib/module-adapter";
import { useLang } from "../../lib/language";

export type RunOutput = {
  module: ModuleKey;
  runMode: RunMode;
  request: unknown;
  response?: unknown;
  success: boolean;
  error?: string;
  asyncTaskId?: string;
  asyncState?: string;
};

type ModuleRunPanelProps = {
  onRunDone: (output: RunOutput) => void;
};

const JURISDICTIONS = ["CN", "EU", "US"] as const;

export function ModuleRunPanel({ onRunDone }: ModuleRunPanelProps) {
  const { t } = useLang();
  const [jurisdiction, setJurisdiction] = useState<(typeof JURISDICTIONS)[number]>("CN");
  const [moduleKey, setModuleKey] = useState<ModuleKey>("diagnosis");
  const [runMode, setRunMode] = useState<RunMode>("sync");
  const [payloadText, setPayloadText] = useState("");
  const [responseText, setResponseText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const modules = useMemo(
    () => listModules().filter((item) => item.jurisdiction === jurisdiction),
    [jurisdiction]
  );

  useEffect(() => {
    if (!modules.find((item) => item.key === moduleKey)) {
      setModuleKey(modules[0]?.key ?? "diagnosis");
    }
  }, [moduleKey, modules]);

  useEffect(() => {
    setPayloadText(JSON.stringify(getDefaultPayload(moduleKey), null, 2));
    setResponseText("");
    setError(null);
  }, [moduleKey]);

  const definition = findModule(moduleKey);
  const allowAsync = hasAsync(definition);

  const execute = async () => {
    let requestPayload: unknown;
    try {
      requestPayload = JSON.parse(payloadText);
    } catch (parseErr) {
      const message = parseErr instanceof Error ? parseErr.message : "Payload parse error";
      setError(message);
      onRunDone({ module: moduleKey, runMode, request: payloadText, success: false, error: message });
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const result = await runModule(definition, requestPayload, allowAsync ? runMode : "sync");
      setResponseText(JSON.stringify(result.response, null, 2));
      onRunDone({
        module: moduleKey,
        runMode: result.runMode,
        request: requestPayload,
        response: result.response,
        success: true,
        asyncTaskId: result.asyncTaskId,
        asyncState: result.asyncState
      });
    } catch (runErr) {
      const message = runErr instanceof Error ? runErr.message : "Request failed";
      setError(message);
      onRunDone({ module: moduleKey, runMode, request: requestPayload, success: false, error: message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="run-panel" data-guide="stage-run">
      <header className="run-panel-head">
        <div>
          <div className="runner-title">{t("runPanel")}</div>
          <h3 className="font-display text-xl text-ink">{definition.label}</h3>
        </div>
        <div className="run-mode-group">
          <button
            className={`pill-btn ${runMode === "sync" ? "active-mode" : ""}`}
            onClick={() => setRunMode("sync")}
          >
            {t("runSync")}
          </button>
          <button
            className={`pill-btn ${runMode === "async" ? "active-mode" : ""}`}
            onClick={() => setRunMode("async")}
            disabled={!allowAsync}
          >
            {t("runAsync")}
          </button>
        </div>
      </header>

      <div className="jurisdiction-tabs">
        {JURISDICTIONS.map((item) => (
          <button
            key={item}
            className={`tab-btn ${item === jurisdiction ? "active" : ""}`}
            onClick={() => setJurisdiction(item)}
          >
            {item}
          </button>
        ))}
      </div>

      <div className="module-tabs">
        {modules.map((item) => (
          <button
            key={item.key}
            className={`tab-btn ${item.key === moduleKey ? "active" : ""}`}
            onClick={() => setModuleKey(item.key)}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div className="runner-title">{t("payloadLabel")}</div>
      <textarea className="runner-textarea" value={payloadText} onChange={(event) => setPayloadText(event.target.value)} />

      <div className="mt-2 flex justify-end">
        <button className="pill-btn-primary" onClick={execute} disabled={loading}>
          {loading ? t("runningNow") : `${t("runNow")} ${definition.label}`}
        </button>
      </div>

      <div className="runner-title mt-3">{t("responseLabel")}</div>
      <textarea className="runner-textarea" value={responseText} readOnly placeholder={t("runResultPlaceholder")} />

      {error ? <div className="runner-error">{error}</div> : null}
    </section>
  );
}
