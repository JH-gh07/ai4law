import { useEffect, useMemo, useState } from "react";
import type { RuntimeProvider, RuntimeSettingsPayload } from "../lib/system-settings-api";
import { fetchRuntimeSettings, saveRuntimeSettings } from "../lib/system-settings-api";

const FALLBACK_MODELS = ["hunyuan-turbos-latest", "hunyuan-standard", "hunyuan-lite"];

const emptyPayload: RuntimeSettingsPayload = {
  delilegal: {
    base_url: "https://openapi.delilegal.com",
    app_id: "",
    secret: "",
    enabled: false,
  },
  llm: {
    provider: "tencent_hunyuan",
    api_key: "",
    api_url: "https://api.hunyuan.cloud.tencent.com/v1",
    model: "hunyuan-turbos-latest",
    model_options: FALLBACK_MODELS,
    enabled: false,
  },
  custom_providers: [],
};

export function SettingsPage() {
  const [form, setForm] = useState<RuntimeSettingsPayload>(emptyPayload);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<string>("");
  const llmModels = useMemo(() => {
    const opts = form.llm.model_options.length ? form.llm.model_options : FALLBACK_MODELS;
    if (!opts.includes(form.llm.model)) return [...opts, form.llm.model];
    return opts;
  }, [form.llm.model, form.llm.model_options]);

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
      custom_providers: prev.custom_providers.map((item) => (item.id === id ? { ...item, ...patch } : item)),
    }));
  };

  const addProvider = () => {
    const id = `provider-${Date.now()}`;
    setForm((prev) => ({
      ...prev,
      custom_providers: [
        ...prev.custom_providers,
        { id, name: "New Provider", api_key: "", api_url: "", model: "", enabled: false },
      ],
    }));
  };

  const removeProvider = (id: string) => {
    setForm((prev) => ({
      ...prev,
      custom_providers: prev.custom_providers.filter((item) => item.id !== id),
    }));
  };

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
        <p className="tasks-hero-subtitle">配置得理法搜、腾讯混元和其他 API Provider。</p>
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
          </section>

          <section className="settings-card">
            <h3>腾讯混元（LLM）</h3>
            <label>
              <span>Provider</span>
              <input
                value={form.llm.provider}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, llm: { ...prev.llm, provider: event.target.value } }))
                }
              />
            </label>
            <label>
              <span>API Key</span>
              <input
                type="password"
                value={form.llm.api_key}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, llm: { ...prev.llm, api_key: event.target.value } }))
                }
              />
            </label>
            <label>
              <span>API URL</span>
              <input
                value={form.llm.api_url}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, llm: { ...prev.llm, api_url: event.target.value } }))
                }
              />
            </label>
            <label>
              <span>模型选择</span>
              <select
                value={form.llm.model}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, llm: { ...prev.llm, model: event.target.value } }))
                }
              >
                {llmModels.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>自定义模型</span>
              <input
                value={form.llm.model}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, llm: { ...prev.llm, model: event.target.value } }))
                }
              />
            </label>
            <p className="settings-hint">{form.llm.enabled ? "当前已启用" : "当前未启用（缺少 API Key）"}</p>
          </section>

          <section className="settings-card settings-card-full">
            <div className="settings-card-head">
              <h3>其他 API Provider</h3>
              <button className="pill-btn" onClick={addProvider}>
                新增 Provider
              </button>
            </div>
            <div className="settings-provider-list">
              {form.custom_providers.map((provider) => (
                <article key={provider.id} className="settings-provider-item">
                  <label>
                    <span>名称</span>
                    <input value={provider.name} onChange={(event) => updateProvider(provider.id, { name: event.target.value })} />
                  </label>
                  <label>
                    <span>API URL</span>
                    <input value={provider.api_url} onChange={(event) => updateProvider(provider.id, { api_url: event.target.value })} />
                  </label>
                  <label>
                    <span>API Key</span>
                    <input type="password" value={provider.api_key} onChange={(event) => updateProvider(provider.id, { api_key: event.target.value })} />
                  </label>
                  <label>
                    <span>Model</span>
                    <input value={provider.model} onChange={(event) => updateProvider(provider.id, { model: event.target.value })} />
                  </label>
                  <label className="settings-provider-toggle">
                    <input
                      type="checkbox"
                      checked={provider.enabled}
                      onChange={(event) => updateProvider(provider.id, { enabled: event.target.checked })}
                    />
                    <span>启用</span>
                  </label>
                  <button className="tasks-save-btn is-danger" onClick={() => removeProvider(provider.id)}>
                    删除
                  </button>
                </article>
              ))}
              {form.custom_providers.length === 0 ? <p className="resource-empty">暂无自定义 Provider。</p> : null}
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
