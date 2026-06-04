export type RuntimeProvider = {
  id: string;
  name: string;
  provider_type: string;
  api_key: string;
  api_url: string;
  model: string;
  enabled: boolean;
  timeout: number;
  api_key_configured?: boolean;
};

export type RuntimeSettingsPayload = {
  delilegal: {
    base_url: string;
    app_id: string;
    secret: string;
    enabled: boolean;
  };
  llm: {
    active_provider_id: string;
    providers: RuntimeProvider[];
    model_options: string[];
    enabled: boolean;
  };
};

export type RuntimeProviderTestResult = {
  ok: boolean;
  provider_id: string;
  provider_type: string;
  model: string;
  latency_ms: number | null;
  usage: Record<string, number | string>;
  error: string;
};

const ENDPOINT = "/api/v1/system/settings/runtime";
const TEST_PROVIDER_ENDPOINT = "/api/v1/system/settings/llm/test-provider";

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

export async function testRuntimeProvider(provider: RuntimeProvider): Promise<RuntimeProviderTestResult> {
  const res = await fetch(TEST_PROVIDER_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider }),
  });
  const data = (await res.json()) as RuntimeProviderTestResult;
  if (!res.ok) {
    throw new Error(data.error || `Test provider failed: ${res.status}`);
  }
  return data;
}
