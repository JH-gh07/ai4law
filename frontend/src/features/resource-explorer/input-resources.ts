import type { ModuleRun, OutputArtifact } from "../../lib/domain";
import { INPUT_CONTAINER_KEYS, INPUT_ROLE_LABELS, USER_INPUT_EXTENSIONS } from "./config";
import type { InputEntry, InputFileCandidate, ResourceLanguage } from "./contracts";
import { getFileExtension, normalizeResourcePath, prettifyStem, toFileName } from "./file-path";

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const isSupportedUserFile = (value: string): boolean => {
  const trimmed = value.trim();
  return trimmed.length > 0
    && !/^https?:\/\//i.test(trimmed)
    && USER_INPUT_EXTENSIONS.has(getFileExtension(trimmed));
};

const inferLabelKey = (path: string, hint?: string): string | undefined => {
  const normalizedHint = hint?.trim().toLowerCase();
  const exactHint = Object.keys(INPUT_ROLE_LABELS).find((key) => key === normalizedHint);
  if (exactHint) return exactHint;

  const normalizedPath = path.replace(/\\/g, "/").toLowerCase();
  return Object.keys(INPUT_ROLE_LABELS).find((key) => {
    const escapedKey = key.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    return new RegExp(`(?:^|[\\/_.-])${escapedKey}(?:[\\/_.-]|$)`).test(normalizedPath);
  });
};

export function collectUserInputFiles(payload: unknown): InputFileCandidate[] {
  const candidates = new Map<string, InputFileCandidate>();

  const append = (rawPath: string, hint?: string) => {
    const path = rawPath.trim();
    if (!isSupportedUserFile(path)) return;
    const identity = normalizeResourcePath(path);
    const existing = candidates.get(identity);
    candidates.set(identity, {
      path,
      labelKey: existing?.labelKey ?? inferLabelKey(path, hint),
    });
  };

  const scanFileContainer = (value: unknown, keyHint?: string) => {
    if (typeof value === "string") {
      append(value, keyHint);
      return;
    }
    if (Array.isArray(value)) {
      value.forEach((item) => scanFileContainer(item, keyHint));
      return;
    }
    if (!isRecord(value)) return;

    const roleHint =
      typeof value.file_role === "string"
        ? value.file_role
        : typeof value.file_name === "string"
          ? value.file_name
          : keyHint;

    for (const property of ["storage_uri", "path", "file_path"] as const) {
      const candidatePath = value[property];
      if (typeof candidatePath === "string") append(candidatePath, roleHint);
    }

    Object.entries(value).forEach(([key, nested]) => {
      if (["storage_uri", "path", "file_path"].includes(key)) return;
      if (isRecord(nested) || Array.isArray(nested)) scanFileContainer(nested, roleHint);
    });
  };

  const scanPayload = (value: unknown) => {
    if (Array.isArray(value)) {
      value.forEach(scanPayload);
      return;
    }
    if (!isRecord(value)) return;
    Object.entries(value).forEach(([key, nested]) => {
      if (INPUT_CONTAINER_KEYS.has(key)) {
        scanFileContainer(nested, key);
      } else if (isRecord(nested) || Array.isArray(nested)) {
        scanPayload(nested);
      }
    });
  };

  scanPayload(payload);
  return Array.from(candidates.values()).map((candidate) =>
    candidate.labelKey ? candidate : { path: candidate.path },
  );
}

const resolveInputDisplayName = (candidate: InputFileCandidate, lang: ResourceLanguage): string => {
  const fileName = toFileName(candidate.path);
  if (!candidate.labelKey) return fileName;
  const label = INPUT_ROLE_LABELS[candidate.labelKey]?.[lang];
  if (!label) return fileName;
  const extension = getFileExtension(fileName);
  return extension ? `${label}.${extension}` : label || prettifyStem(fileName);
};

export function buildInputEntries(
  runs: ModuleRun[],
  outputArtifacts: OutputArtifact[],
  lang: ResourceLanguage,
): InputEntry[] {
  const entries: InputEntry[] = [];
  const seenPaths = new Set<string>();
  const usedNames = new Map<string, number>();
  const outputPaths = new Set(outputArtifacts.map((artifact) => normalizeResourcePath(artifact.path)));

  const pickUniqueName = (baseName: string): string => {
    const count = (usedNames.get(baseName) ?? 0) + 1;
    usedNames.set(baseName, count);
    return count === 1 ? baseName : `${baseName} (${count})`;
  };

  [...runs]
    .sort((left, right) => right.startedAt.localeCompare(left.startedAt))
    .forEach((run) => {
      collectUserInputFiles(run.request).forEach((candidate) => {
        const identity = normalizeResourcePath(candidate.path);
        if (seenPaths.has(identity) || outputPaths.has(identity)) return;
        seenPaths.add(identity);
        entries.push({
          id: `input-file-${candidate.path}`,
          name: pickUniqueName(resolveInputDisplayName(candidate, lang)),
          kind: "file",
          sourcePath: candidate.path,
          createdAt: run.startedAt,
        });
      });
    });

  return entries;
}
