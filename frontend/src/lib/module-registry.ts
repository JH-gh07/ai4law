import registryData from "../../../config/module_registry.json";
import type { Jurisdiction, ModuleKey } from "./domain";

export type ModuleIdentity = {
  module_id: string;
  jurisdiction: "cn" | "eu" | "us";
  frontend_key: ModuleKey;
  task_template_id: string;
  implementation_package: string;
  v1_api_prefix: string;
  lifecycle: "active" | "legacy-compatible";
  note?: string;
};

const MODULE_IDENTITIES = registryData as ModuleIdentity[];
const MODULE_IDENTITIES_BY_KEY = new Map(
  MODULE_IDENTITIES.map((item) => [item.frontend_key, item])
);

export function listModuleIdentities(): ModuleIdentity[] {
  return MODULE_IDENTITIES;
}

export function findModuleIdentity(frontendKey: string): ModuleIdentity | undefined {
  return MODULE_IDENTITIES_BY_KEY.get(frontendKey as ModuleKey);
}

export function getModuleIdentity(frontendKey: ModuleKey): ModuleIdentity {
  const identity = findModuleIdentity(frontendKey);
  if (!identity) {
    throw new Error(`Unknown module identity: ${frontendKey}`);
  }
  return identity;
}

export function getModuleJurisdiction(frontendKey: string): Jurisdiction | undefined {
  const jurisdiction = findModuleIdentity(frontendKey)?.jurisdiction;
  return jurisdiction?.toUpperCase() as Jurisdiction | undefined;
}

export function getModuleTaskTemplateId(frontendKey: string): string | undefined {
  return findModuleIdentity(frontendKey)?.task_template_id;
}
