import type { ModuleRun, OutputArtifact } from "../../lib/domain";
import {
  INTERNAL_ARTIFACT_PATTERNS,
  OUTPUT_STEM_LABELS,
  USER_FACING_ARTIFACT_KINDS,
  USER_FACING_OUTPUT_EXTENSIONS,
} from "./config";
import type { OutputTreeEntry, ResourceLanguage } from "./contracts";
import { getFileExtension, normalizeResourcePath, prettifyStem, toFileName } from "./file-path";

const parseTime = (value: string | undefined): number | null => {
  if (!value) return null;
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : null;
};

export function filterUserFacingArtifacts(artifacts: OutputArtifact[]): OutputArtifact[] {
  const seenPaths = new Set<string>();
  return artifacts.filter((artifact) => {
    const identity = normalizeResourcePath(artifact.path);
    if (seenPaths.has(identity)) return false;
    const fileName = toFileName(artifact.path).toLowerCase();
    if (INTERNAL_ARTIFACT_PATTERNS.some((pattern) => fileName.includes(pattern))) return false;
    if (!USER_FACING_ARTIFACT_KINDS.has(artifact.kind.toLowerCase())) return false;
    if (!USER_FACING_OUTPUT_EXTENSIONS.has(getFileExtension(fileName))) return false;
    seenPaths.add(identity);
    return true;
  });
}

export function resolveArtifactDisplayName(artifact: OutputArtifact, lang: ResourceLanguage): string {
  const kind = artifact.kind.toLowerCase();
  const fileName = toFileName(artifact.path);
  const lowerName = fileName.toLowerCase();
  const extension = getFileExtension(fileName);
  const upperExtension = extension.toUpperCase();

  if (kind === "html") return lang === "zh" ? "报告预览页" : "Report Preview";
  if (kind === "pdf") return lang === "zh" ? "报告 PDF 版" : "Report PDF";
  if (kind === "docx" || kind === "annotated_docx") return lang === "zh" ? "报告 Word 版" : "Report Word";
  if (kind === "markdown" || kind === "md") return lang === "zh" ? "报告 Markdown 版" : "Report Markdown";
  if (kind === "zip") return lang === "zh" ? "完整输出包" : "Complete Output Bundle";
  if (kind === "report") {
    const suffix = upperExtension ? (lang === "zh" ? `（${upperExtension}）` : ` (${upperExtension})`) : "";
    return lang === "zh" ? `审查报告${suffix}` : `Review Report${suffix}`;
  }

  const configuredStem = Object.keys(OUTPUT_STEM_LABELS).find((stem) => lowerName.includes(stem));
  const displayStem = configuredStem
    ? OUTPUT_STEM_LABELS[configuredStem]?.[lang]
    : prettifyStem(fileName);
  return upperExtension ? `${displayStem || fileName}${lang === "zh" ? `（${upperExtension}）` : ` (${upperExtension})`}` : displayStem || fileName;
}

export function buildOutputEntries(
  artifacts: OutputArtifact[],
  runs: ModuleRun[],
  lang: ResourceLanguage,
): OutputTreeEntry[] {
  const visibleArtifacts = filterUserFacingArtifacts(artifacts);
  const runsWithTime = runs
    .map((run) => {
      const time = parseTime(run.startedAt) ?? parseTime(run.finishedAt);
      return time === null ? null : { runId: run.id, time };
    })
    .filter((run): run is { runId: string; time: number } => run !== null)
    .sort((left, right) => right.time - left.time);
  const runNumberById = new Map(runsWithTime.map((run, index) => [run.runId, index + 1]));

  const resolveRunNumber = (artifact: OutputArtifact): number | null => {
    const artifactTime = parseTime(artifact.createdAt);
    if (artifactTime === null) return null;
    for (let index = 0; index < runsWithTime.length; index += 1) {
      const lowerBound = runsWithTime[index]?.time;
      const upperBound = index === 0 ? Number.POSITIVE_INFINITY : runsWithTime[index - 1]?.time;
      if (lowerBound !== undefined && upperBound !== undefined && artifactTime >= lowerBound && artifactTime < upperBound) {
        return runNumberById.get(runsWithTime[index]?.runId ?? "") ?? null;
      }
    }
    return null;
  };

  const usedNames = new Map<string, number>();
  return visibleArtifacts.map((artifact) => {
    const runNumber = resolveRunNumber(artifact);
    const runLabel = runNumber === null
      ? (lang === "zh" ? "未知批次生成结果" : "Unknown Run Results")
      : (lang === "zh" ? `第${runNumber}次生成结果` : `Run ${runNumber} Results`);
    const baseName = resolveArtifactDisplayName(artifact, lang);
    const key = `${runLabel}/${baseName}`;
    const count = (usedNames.get(key) ?? 0) + 1;
    usedNames.set(key, count);
    return {
      virtualPath: `${runLabel}/${count === 1 ? baseName : `${baseName} (${count})`}`,
      artifact,
    };
  });
}
