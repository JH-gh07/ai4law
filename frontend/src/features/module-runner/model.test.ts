import { describe, expect, it } from "vitest";

import {
  inferAttachmentFormat,
  inferCnFlowAttachmentFormat,
  inferDpiaAttachmentFormat,
  isValidUrl,
  parseRecipientRows,
  splitCsv,
  toBcrScore,
} from "./model";

describe("module runner model helpers", () => {
  it("normalizes comma and newline separated values", () => {
    expect(splitCsv("姓名, 邮箱，手机号\n地址"))
      .toEqual(["姓名", "邮箱", "手机号", "地址"]);
  });

  it("infers supported attachment formats without changing fallbacks", () => {
    expect(inferAttachmentFormat("contract.DOCX")).toBe("docx");
    expect(inferAttachmentFormat("notes.unknown")).toBe("txt");
    expect(inferDpiaAttachmentFormat("diagram.jpeg")).toBe("jpg");
    expect(inferCnFlowAttachmentFormat("inventory.xlsx")).toBe("xlsx");
    expect(inferCnFlowAttachmentFormat("archive.zip")).toBeNull();
  });

  it("parses recipient rows and ignores incomplete entries", () => {
    expect(
      parseRecipientRows([
        "Example LLC | US | controller | yes",
        "Vendor GmbH,DE,vendor,false",
        "missing-country",
      ].join("\n")),
    ).toEqual([
      {
        entity_name: "Example LLC",
        country_region: "US",
        entity_role: "controller",
        is_restricted_party: true,
      },
      {
        entity_name: "Vendor GmbH",
        country_region: "DE",
        entity_role: "vendor",
        is_restricted_party: false,
      },
    ]);
  });

  it("keeps BCR score boundaries deterministic", () => {
    expect(toBcrScore("short")).toBe("non_compliant");
    expect(toBcrScore("x".repeat(16))).toBe("partial");
    expect(toBcrScore("x".repeat(48))).toBe("compliant");
  });

  it("accepts only explicit HTTP(S) URLs", () => {
    expect(isValidUrl("https://example.com/legal")).toBe(true);
    expect(isValidUrl("http://example.com")).toBe(true);
    expect(isValidUrl("example.com")).toBe(false);
  });
});
