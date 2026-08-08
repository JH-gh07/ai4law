import { describe, expect, it } from "vitest";

import { formatLegalLocator } from "./legal-locator";

describe("formatLegalLocator", () => {
  it("formats numeric article numbers by language", () => {
    expect(formatLegalLocator("39", "zh")).toBe("第39条");
    expect(formatLegalLocator("39", "en")).toBe("Article 39");
  });

  it("does not wrap paragraph and clause locators as Chinese articles", () => {
    expect(formatLegalLocator("段落6", "zh")).toBe("段落6");
    expect(formatLegalLocator("Recital 22", "zh")).toBe("Recital 22");
    expect(formatLegalLocator("Clause 15", "zh")).toBe("Clause 15");
  });
});
