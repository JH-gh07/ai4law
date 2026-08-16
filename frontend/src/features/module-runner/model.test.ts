import { describe, expect, it } from "vitest";

import {
  buildUserFacingResult,
  PIPIA_STEPS,
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

  it("exposes the HR exemption route in the PIPIA form", () => {
    const routeField = PIPIA_STEPS.flatMap((step) => step.fields)
      .find((field) => field.name === "route_type");
    expect(routeField?.options).toContain("hr_exemption");
  });

  it("maps a clarification control decision without mixing it with task state", () => {
    const result = buildUserFacingResult(
      {
        state: "COMPLETED",
        control_decision: {
          legal_control_status: "NEEDS_CLARIFICATION",
          reasons: ["关键事实缺失"],
          required_actions: ["补充事实"],
        },
        clarification_questions: ["是否属于关键信息基础设施运营者？"],
      },
      "zh",
    );

    expect(result.control).toEqual({
      status: "NEEDS_CLARIFICATION",
      reasons: ["关键事实缺失"],
      requiredActions: ["补充事实"],
      clarificationQuestions: ["是否属于关键信息基础设施运营者？"],
    });
    expect(result.chips).toContain("法律控制：NEEDS_CLARIFICATION");
  });

  it("keeps legacy responses without control fields compatible", () => {
    expect(buildUserFacingResult({ state: "COMPLETED" }, "zh").control).toBeNull();
  });
});
