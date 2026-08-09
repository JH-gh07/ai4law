import { describe, expect, it } from "vitest";
import { listModules } from "../api/modules";
import { listModuleIdentities } from "./module-registry";
import {
  findTaskTemplate,
  listTaskTemplates,
  listTaskTemplatesByJurisdiction
} from "./task-templates";

describe("module registry contract", () => {
  it("has unique stable ids and frontend keys", () => {
    const identities = listModuleIdentities();
    expect(new Set(identities.map((item) => item.module_id)).size).toBe(identities.length);
    expect(new Set(identities.map((item) => item.frontend_key)).size).toBe(identities.length);
  });

  it("matches module adapter jurisdiction metadata", () => {
    const adapters = new Map(listModules().map((item) => [item.key, item]));
    for (const identity of listModuleIdentities()) {
      expect(adapters.get(identity.frontend_key)?.jurisdiction).toBe(
        identity.jurisdiction.toUpperCase()
      );
    }
  });

  it("maps every module to a matching task template", () => {
    for (const identity of listModuleIdentities()) {
      const template = findTaskTemplate(identity.task_template_id);
      expect(template?.module).toBe(identity.frontend_key);
      expect(template?.jurisdiction).toBe(identity.jurisdiction.toUpperCase());
    }
  });

  it("keeps frontend request endpoints inside the registered API prefix", () => {
    const adapters = new Map(listModules().map((item) => [item.key, item]));
    for (const identity of listModuleIdentities()) {
      const adapter = adapters.get(identity.frontend_key);
      expect(adapter?.syncEndpoint.startsWith(identity.v1_api_prefix + "/")).toBe(true);
      if (adapter?.asyncSubmitEndpoint) {
        expect(adapter.asyncSubmitEndpoint.startsWith(identity.v1_api_prefix + "/")).toBe(true);
      }
      if (adapter?.asyncStatusEndpoint) {
        expect(adapter.asyncStatusEndpoint("task-id").startsWith(identity.v1_api_prefix + "/")).toBe(true);
      }
    }
  });
  it("keeps the historical cn_flow key as a US compatibility entry", () => {
    const identity = listModuleIdentities().find((item) => item.frontend_key === "cn_flow");
    expect(identity).toMatchObject({
      module_id: "us.eo_14117_flow_review",
      jurisdiction: "us",
      lifecycle: "legacy-compatible"
    });
  });

  it("keeps cn_flow readable for historical tasks without offering it for new tasks", () => {
    expect(findTaskTemplate("us_14117_flow")?.module).toBe("cn_flow");
    expect(listTaskTemplates().map((item) => item.id)).not.toContain("us_14117_flow");
    expect(listTaskTemplatesByJurisdiction("US").map((item) => item.id)).toEqual([
      "us_14117",
      "us_cpra"
    ]);
  });

  it("does not expose the retired China standard-contract review module", () => {
    expect(listModuleIdentities().some((item) => item.module_id === "cn.scc_review")).toBe(false);
    expect(listModules().map((item) => String(item.key))).not.toContain("scc");
    expect(findTaskTemplate("cn_scc")).toBeUndefined();
  });
});
