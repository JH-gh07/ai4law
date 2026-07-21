import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  fetchRuntimeSettings,
  testRuntimeProvider,
} from "../api/system-settings";
import { SettingsPage } from "./SettingsPage";

vi.mock("../api/system-settings", () => ({
  fetchRuntimeSettings: vi.fn(),
  saveRuntimeSettings: vi.fn(),
  testRuntimeProvider: vi.fn(),
}));

const fetchSettings = vi.mocked(fetchRuntimeSettings);
const testProvider = vi.mocked(testRuntimeProvider);

describe("SettingsPage provider health", () => {
  beforeEach(() => {
    fetchSettings.mockResolvedValue({
      delilegal: {
        base_url: "https://openapi.delilegal.com",
        app_id: "",
        secret: "",
        enabled: false,
      },
      llm: {
        active_provider_id: "demo",
        enabled: true,
        model_options: [],
        providers: [
          {
            id: "demo",
            name: "Demo Provider",
            provider_type: "openai_compatible",
            api_key: "",
            api_key_configured: true,
            api_url: "https://example.com/v1",
            model: "missing-model",
            enabled: true,
            timeout: 30,
          },
        ],
      },
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("shows an actionable error code and discovered model choices", async () => {
    testProvider.mockResolvedValue({
      ok: false,
      provider_id: "demo",
      provider_type: "openai_compatible",
      model: "missing-model",
      latency_ms: 31,
      usage: {},
      error_code: "MODEL_NOT_FOUND",
      error_category: "model",
      error: "配置的模型不存在",
      model_discovery: "available",
      available_models: ["available-model"],
    });
    render(<SettingsPage />);

    fireEvent.click(await screen.findByRole("button", { name: "测试连接" }));

    expect(await screen.findByText(/配置的模型不存在/)).toHaveTextContent(
      "MODEL_NOT_FOUND",
    );
    expect(document.querySelector('option[value="available-model"]')).not.toBeNull();
  });
});
