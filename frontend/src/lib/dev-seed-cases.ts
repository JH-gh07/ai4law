import type { DevCaseModule } from "../api/api-contract";
import seedCaseIndex from "../../../benchmarks/datasets/seed-cases-v1/frontend-cases/index.json";

export type SeedDevCase = {
  caseId: string;
  moduleKey: DevCaseModule;
  name: string;
  description: string;
  jurisdiction: "CN" | "EU" | "US";
  formDefaults: Record<string, unknown>;
  backendFilePaths: string[];
  sourceKind: "synthetic_fixture" | "source_faithful";
  goldStatus: "unsigned";
  sourceRequestPath: string;
};

const cases = seedCaseIndex.cases as SeedDevCase[];

export const SEED_DEV_TEST_CASES = Object.freeze(
  Object.fromEntries(
    cases.map((testCase) => [testCase.moduleKey, [] as SeedDevCase[]]),
  ) as Partial<Record<DevCaseModule, SeedDevCase[]>>,
);

for (const testCase of cases) {
  SEED_DEV_TEST_CASES[testCase.moduleKey]!.push(testCase);
}

export function getSeedDevCases(module: DevCaseModule): SeedDevCase[] {
  return SEED_DEV_TEST_CASES[module] ?? [];
}
