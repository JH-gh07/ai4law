import { useEffect, useState } from "react";
import type { DeliLegalTestResult, RuntimeProvider, RuntimeProviderTestResult, RuntimeSettingsPayload } from "../api/system-settings";
import { fetchRuntimeSettings, saveRuntimeSettings, testDeliLegal, testRuntimeProvider } from "../api/system-settings";

const FALLBACK_MODELS = ["deepseek-ai/DeepSeek-V3.2", "deepseek-ai/DeepSeek-V3", "Qwen/Qwen2.5-7B-Instruct", "Qwen/Qwen2.5-72B-Instruct"];

const emptyPayload: RuntimeSettingsPayload = {
  delilegal: {
    base_url: "https://openapi.delilegal.com",
    app_id: "",
    secret: "",
    enabled: false,
    secret_configured: false,
  },
  llm: {
    active_provider_id: "siliconflow",
    providers: [
      {
        id: "siliconflow",
        name: "SiliconFlow",
        provider_type: "openai_compatible",
        api_key: "",
        api_url: "https://api.siliconflow.cn/v1",
        model: "deepseek-ai/DeepSeek-V3.2",
        enabled: false,
        timeout: 60,
      },
    ],
    model_options: FALLBACK_MODELS,
    enabled: false,
  },
};

export function SettingsPage() {
  const [form, setForm] = useState<RuntimeSettingsPayload>(emptyPayload);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<string>("");
  const [testingProviderId, setTestingProviderId] = useState<string>("");
  const [testingDeliLegal, setTestingDeliLegal] = useState(false);
  const [deliLegalTestState, setDeliLegalTestState] = useState<DeliLegalTestResult | null>(null);
  const [providerTestState, setProviderTestState] = useState<Record<string, RuntimeProviderTestResult>>({});
  useEffect(() => {
    let alive = true;
    fetchRuntimeSettings()
      .then((payload) => {
        if (!alive) return;
        setForm(payload);
      })
      .catch((err) => {
        if (!alive) return;
        setMsg(`加载失败：${err instanceof Error ? err.message : String(err)}`);
      })
      .finally(() => {
        if (!alive) return;
        setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, []);

  const updateProvider = (id: string, patch: Partial<RuntimeProvider>) => {
    setForm((prev) => ({
      ...prev,
      llm: {
        ...prev.llm,
        providers: prev.llm.providers.map((item) => (item.id === id ? { ...item, ...patch } : item)),
      },
    }));
  };

  const addProvider = () => {
    const id = `provider-${Date.now()}`;
    setForm((prev) => ({
      ...prev,
      llm: {
        ...prev.llm,
        providers: [
          ...prev.llm.providers,
          {
            id,
            name: "New Provider",
            provider_type: "openai_compatible",
            api_key: "",
            api_url: "",
            model: "",
            enabled: true,
            timeout: 60,
          },
        ],
      },
    }));
  };

  const removeProvider = (id: string) => {
    setForm((prev) => ({
      ...prev,
      llm: {
        ...prev.llm,
        active_provider_id:
          prev.llm.active_provider_id === id
            ? prev.llm.providers.find((item) => item.id !== id)?.id || ""
            : prev.llm.active_provider_id,
        providers: prev.llm.providers.filter((item) => item.id !== id),
      },
    }));
  };

  const setActiveProvider = (id: string) => {
    setForm((prev) => ({
      ...prev,
      llm: {
        ...prev.llm,
        active_provider_id: id,
      },
    }));
  };

  const onTestProvider = async (provider: RuntimeProvider) => {
    setTestingProviderId(provider.id);
    try {
      const result = await testRuntimeProvider(provider);
      setProviderTestState((prev) => ({ ...prev, [provider.id]: result }));
    } catch (err) {
      setProviderTestState((prev) => ({
        ...prev,
        [provider.id]: {
          ok: false,
          provider_id: provider.id,
          provider_type: provider.provider_type,
          model: provider.model,
          latency_ms: null,
          usage: {},
          error_code: "REQUEST_FAILED",
          error_category: "network",
          error: err instanceof Error ? err.message : String(err),
          model_discovery: "not_run",
          available_models: [],
        },
      }));
    } finally {
      setTestingProviderId("");
    }
  };

  const getProviderTestLabel = (providerId: string) => {
    const state = providerTestState[providerId];
    if (!state) return "";
    if (!state.ok) {
      return `${state.error || "测试失败"}（${state.error_code || "PROVIDER_ERROR"}）`;
    }
    const discoveryLabel = state.model_discovery === "available" ? "模型列表已核验" : "模型列表不可用";
    return `连接成功 · ${state.latency_ms ?? "-"}ms · ${discoveryLabel}`;
  };

  const onTestDeliLegal = async () => {
    setTestingDeliLegal(true);
    try {
      setDeliLegalTestState(await testDeliLegal(form.delilegal));
    } catch (err) {
      setDeliLegalTestState({
        ok: false,
        base_url: form.delilegal.base_url,
        latency_ms: null,
        result_count: 0,
        error_code: "REQUEST_FAILED",
        error_category: "network",
        error: err instanceof Error ? err.message : String(err),
      });
    } finally {
      setTestingDeliLegal(false);
    }
  };

  const deliLegalTestLabel = deliLegalTestState
    ? deliLegalTestState.ok
      ? `连接成功 · ${deliLegalTestState.latency_ms ?? "-"}ms · 最小查询返回 ${deliLegalTestState.result_count} 条`
      : `${deliLegalTestState.error || "测试失败"}（${deliLegalTestState.error_code || "PROVIDER_ERROR"}）`
    : "";

  const activeProvider = form.llm.providers.find((item) => item.id === form.llm.active_provider_id) || null;

  const onSave = async () => {
    setSaving(true);
    setMsg("");
    try {
      const saved = await saveRuntimeSettings(form);
      setForm(saved);
      setMsg("保存成功，后续任务将使用新配置。");
    } catch (err) {
      setMsg(`保存失败：${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="page-shell settings-page">
      <header className="page-header">
        <h2>设置</h2>
        <p className="tasks-hero-subtitle">配置得理法搜与全局 LLM Provider。当前仅支持 OpenAI-compatible API。</p>
      </header>

      {loading ? <p className="resource-empty">加载中...</p> : null}
      {!loading ? (
        <div className="settings-grid">
          <section className="settings-card">
            <h3>得理法搜</h3>
            <label>
              <span>Base URL</span>
              <input
                value={form.delilegal.base_url}
                onChange={(event) =>
                  setForm((prev) => ({
                    ...prev,
                    delilegal: { ...prev.delilegal, base_url: event.target.value },
                  }))
                }
              />
            </label>
            <label>
              <span>App ID</span>
              <input
                value={form.delilegal.app_id}
                onChange={(event) =>
                  setForm((prev) => ({
                    ...prev,
                    delilegal: { ...prev.delilegal, app_id: event.target.value },
                  }))
                }
              />
            </label>
            <label>
              <span>Secret</span>
              <input
                type="password"
                value={form.delilegal.secret}
                onChange={(event) =>
                  setForm((prev) => ({
                    ...prev,
                    delilegal: { ...prev.delilegal, secret: event.target.value },
                  }))
                }
              />
            </label>
            <p className="settings-hint">{form.delilegal.enabled ? "当前已启用" : "当前未启用（缺少 app_id/secret）"}</p>
            <button className="pill-btn" onClick={onTestDeliLegal} disabled={testingDeliLegal}>
              {testingDeliLegal ? "测试中..." : "测试得理连接"}
            </button>
            {deliLegalTestState ? (
              <p className={`settings-provider-test ${deliLegalTestState.ok ? "is-success" : "is-error"}`}>
                {deliLegalTestLabel}
              </p>
            ) : null}
          </section>

          <section className="settings-card">
            <h3>当前生效 Provider</h3>
            {activeProvider ? (
              <>
                <div className="settings-provider-summary">
                  <div className="settings-provider-summary-title">
                    <strong>{activeProvider.name || "未命名 Provider"}</strong>
                    <span>{activeProvider.provider_type}</span>
                  </div>
                  <div className="settings-provider-summary-grid">
                    <div>
                      <span>ID</span>
                      <strong>{activeProvider.id || "-"}</strong>
                    </div>
                    <div>
                      <span>模型</span>
                      <strong>{activeProvider.model || "-"}</strong>
                    </div>
                    <div>
                      <span>API URL</span>
                      <strong>{activeProvider.api_url || "-"}</strong>
                    </div>
                    <div>
                      <span>Timeout</span>
                      <strong>{activeProvider.timeout || 60}s</strong>
                    </div>
                  </div>
                </div>
                <p className="settings-hint">
                  {form.llm.enabled ? "当前存在可用 Provider。" : "当前没有已启用且配置了 API Key 的 Provider。"}
                </p>
              </>
            ) : (
              <p className="resource-empty">暂无 Provider。</p>
            )}
          </section>

          <section className="settings-card settings-card-full">
            <div className="settings-card-head">
              <h3>LLM Provider 管理</h3>
              <button className="pill-btn" onClick={addProvider}>
                新增 Provider
              </button>
            </div>
            <div className="settings-provider-list">
              {form.llm.providers.map((provider) => (
                <article key={provider.id} className="settings-provider-item">
                  <div className="settings-provider-item-head">
                    <div className="settings-provider-item-title">
                      <strong>{provider.name || "未命名 Provider"}</strong>
                      <span>{provider.provider_type}</span>
                    </div>
                    <div className="settings-provider-item-badges">
                      <span className={`settings-provider-badge ${provider.enabled ? "is-enabled" : "is-disabled"}`}>
                        {provider.enabled ? "已启用" : "已禁用"}
                      </span>
                      <span className={`settings-provider-badge ${form.llm.active_provider_id === provider.id ? "is-active" : ""}`}>
                        {form.llm.active_provider_id === provider.id ? "当前使用" : "候选 Provider"}
                      </span>
                    </div>
                  </div>
                  <div className="settings-provider-fields">
                    <label>
                      <span>ID</span>
                      <input value={provider.id} onChange={(event) => updateProvider(provider.id, { id: event.target.value })} />
                    </label>
                    <label>
                      <span>名称</span>
                      <input value={provider.name} onChange={(event) => updateProvider(provider.id, { name: event.target.value })} />
                    </label>
                    <label>
                      <span>Provider 类型</span>
                      <select
                        value={provider.provider_type}
                        onChange={(event) => updateProvider(provider.id, { provider_type: event.target.value })}
                      >
                        <option value="openai_compatible">OpenAI Compatible</option>
                      </select>
                    </label>
                    <label>
                      <span>Timeout</span>
                      <input
                        type="number"
                        value={provider.timeout}
                        onChange={(event) => updateProvider(provider.id, { timeout: Number(event.target.value) || 60 })}
                      />
                    </label>
                    <label className="settings-provider-field-wide">
                      <span>API URL</span>
                      <input value={provider.api_url} onChange={(event) => updateProvider(provider.id, { api_url: event.target.value })} />
                    </label>
                    <label className="settings-provider-field-wide">
                      <span>API Key</span>
                      <input
                        type="password"
                        value={provider.api_key}
                        placeholder="请输入 API Key"
                        onChange={(event) => updateProvider(provider.id, { api_key: event.target.value })}
                      />
                    </label>
                    <label className="settings-provider-field-wide">
                      <span>Model</span>
                      <input
                        value={provider.model}
                        list={`provider-models-${provider.id}`}
                        onChange={(event) => updateProvider(provider.id, { model: event.target.value })}
                      />
                      <datalist id={`provider-models-${provider.id}`}>
                        {(providerTestState[provider.id]?.available_models || []).map((model) => (
                          <option key={model} value={model} />
                        ))}
                      </datalist>
                    </label>
                  </div>
                  <div className="settings-provider-meta">
                    <label className="settings-provider-toggle">
                      <input
                        type="checkbox"
                        checked={provider.enabled}
                        onChange={(event) => updateProvider(provider.id, { enabled: event.target.checked })}
                      />
                      <span>启用该 Provider</span>
                    </label>
                    <p className="settings-hint">
                      {provider.api_key || provider.api_key_configured ? "API Key 已配置" : "API Key 未配置"}
                    </p>
                  </div>
                  <div className="settings-provider-actions">
                    <button
                      className={form.llm.active_provider_id === provider.id ? "pill-btn-primary" : "pill-btn"}
                      onClick={() => setActiveProvider(provider.id)}
                    >
                      {form.llm.active_provider_id === provider.id ? "当前使用" : "设为当前"}
                    </button>
                    <button className="pill-btn" onClick={() => onTestProvider(provider)} disabled={testingProviderId === provider.id}>
                      {testingProviderId === provider.id ? "测试中..." : "测试连接"}
                    </button>
                    <button className="tasks-save-btn is-danger" onClick={() => removeProvider(provider.id)}>
                      删除
                    </button>
                  </div>
                  {provider.id in providerTestState ? (
                    <p className={`settings-provider-test ${providerTestState[provider.id]?.ok ? "is-success" : "is-error"}`}>
                      {getProviderTestLabel(provider.id)}
                    </p>
                  ) : null}
                </article>
              ))}
              {form.llm.providers.length === 0 ? <p className="resource-empty">暂无 Provider。</p> : null}
            </div>
          </section>
        </div>
      ) : null}

      <div className="settings-foot">
        <button className="pill-btn-primary" onClick={onSave} disabled={saving || loading}>
          {saving ? "保存中..." : "保存设置"}
        </button>
        {msg ? <span className="settings-message">{msg}</span> : null}
      </div>
    </section>
  );
}
