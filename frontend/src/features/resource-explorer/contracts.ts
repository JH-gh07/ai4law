import type { OutputArtifact } from "../../lib/domain";

export type ResourceLanguage = "zh" | "en";

export type InputFileCandidate = {
  path: string;
  labelKey?: string;
};

export type InputEntry = {
  id: string;
  name: string;
  kind: "file";
  sourcePath: string;
  createdAt: string;
};

export type OutputTreeEntry = {
  virtualPath: string;
  artifact: OutputArtifact;
};

export type TreeNode = {
  id: string;
  type: "folder" | "file";
  name: string;
  path?: string;
  children: TreeNode[];
};

export type ResourceOpenTarget = { kind: "output"; artifact: OutputArtifact };
