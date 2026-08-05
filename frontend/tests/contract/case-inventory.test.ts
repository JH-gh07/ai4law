// @vitest-environment node

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import { DEV_TEST_CASES } from "../../src/lib/dev-test-cases";

const REPOSITORY_ROOT = fileURLToPath(new URL("../../../", import.meta.url));

type CaseInventory = {
  schema_version: string;
  assertion_floor: number;
  modules: Record<
    string,
    {
      module_id: string;
      frontend_cases: number;
      cli_cases: Array<{ case_id: string; assertions: number }>;
    }
  >;
};

const inventory = JSON.parse(
  readFileSync(resolve(REPOSITORY_ROOT, "config/case_inventory.json"), "utf-8"),
) as CaseInventory;

// The Python gate (scripts/check_case_parity.py) verifies the CLI half of this
// same file. Reading it here from the other side means a module added to one
// suite but not the other fails a gate instead of going unnoticed.
describe("developer cases against the committed case inventory", () => {
  it("declares the same modules as the inventory", () => {
    expect(Object.keys(DEV_TEST_CASES).sort()).toEqual(Object.keys(inventory.modules).sort());
  });

  it("carries the case count the inventory records for every module", () => {
    for (const [moduleKey, record] of Object.entries(inventory.modules)) {
      expect(
        DEV_TEST_CASES[moduleKey]?.length ?? 0,
        `${moduleKey}: inventory records ${record.frontend_cases} developer cases`,
      ).toBe(record.frontend_cases);
    }
  });

  it("keeps every module covered by both suites", () => {
    for (const [moduleKey, record] of Object.entries(inventory.modules)) {
      expect(record.frontend_cases, `${moduleKey} has no developer case`).toBeGreaterThan(0);
      expect(record.cli_cases.length, `${moduleKey} has no CLI case`).toBeGreaterThan(0);
    }
  });

  it("holds every CLI case at or above the assertion floor", () => {
    for (const [moduleKey, record] of Object.entries(inventory.modules)) {
      for (const cliCase of record.cli_cases) {
        expect(
          cliCase.assertions,
          `${moduleKey}/${cliCase.case_id} declares ${cliCase.assertions} assertions`,
        ).toBeGreaterThanOrEqual(inventory.assertion_floor);
      }
    }
  });

  it("agrees with the registry total", () => {
    const declared = Object.values(inventory.modules).reduce(
      (total, record) => total + record.frontend_cases,
      0,
    );
    expect(Object.values(DEV_TEST_CASES).flat()).toHaveLength(declared);
  });
});
