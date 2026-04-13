export type RuntimeProvider = {
  id: string;
  name: string;
  api_key: string;
  api_url: string;
  model: string;
  enabled: boolean;
};

export type RuntimeSettingsPayload = {
  delilegal: {
    base_url: string;
    app_id: string;
    secret: string;
    enabled: boolean;
  };
  llm: {
    provider: string;
    api_key: string;
    api_url: string;
    model: string;
    model_options: string[];
    enabled: boolean;
  };
  custom_providers: RuntimeProvider[];
};

const ENDPOINT = "/api/v1/system/settings/runtime";

export async function fetchRuntimeSettings(): Promise<RuntimeSettingsPayload> {
  const res = await fetch(ENDPOINT);
  if (!res.ok) {
    throw new Error(`Load settings failed: ${res.status}`);
  }
  return (await res.json()) as RuntimeSettingsPayload;
}

export async function saveRuntimeSettings(payload: RuntimeSettingsPayload): Promise<RuntimeSettingsPayload> {
  const res = await fetch(ENDPOINT, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Save settings failed: ${res.status} ${text}`);
  }
  return (await res.json()) as RuntimeSettingsPayload;
}
