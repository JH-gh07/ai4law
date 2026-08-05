import { describe, expect, it } from "vitest";

import { getModuleDevPreset } from "./dev-presets";

describe("developer one-click preset file contracts", () => {
  it.each([
    ["bcr", [".docx", ".pdf"]],
    ["dpia", [".docx", ".pdf", ".png", ".jpg", ".jpeg"]],
    ["tia", [".docx", ".pdf"]],
    ["document_review", [".docx", ".pdf", ".md", ".csv", ".json"]],
  ] as const)("uses supported file extensions for %s", (module, extensions) => {
    const preset = getModuleDevPreset(module);
    expect(preset.backendFilePaths.length).toBeGreaterThan(0);
    for (const path of preset.backendFilePaths) {
      expect(extensions.some((extension) => path.toLowerCase().endsWith(extension)), path).toBe(true);
    }
  });
});
