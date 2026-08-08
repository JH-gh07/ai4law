import type { TreeNode } from "./contracts";

type MutableTreeNode = TreeNode & {
  childrenMap: Map<string, MutableTreeNode>;
};

const makeNode = (id: string, type: "folder" | "file", name: string, path?: string): MutableTreeNode => ({
  id,
  type,
  name,
  path,
  children: [],
  childrenMap: new Map<string, MutableTreeNode>(),
});

const finalizeTree = (nodes: MutableTreeNode[]): TreeNode[] =>
  nodes
    .map((node) => ({
      id: node.id,
      type: node.type,
      name: node.name,
      path: node.path,
      children: finalizeTree(Array.from(node.childrenMap.values())),
    }))
    .sort((left, right) => {
      if (left.type !== right.type) return left.type === "folder" ? -1 : 1;
      return left.name.localeCompare(right.name);
    });

export function buildPathTree(paths: string[], prefix: string): TreeNode[] {
  const rootMap = new Map<string, MutableTreeNode>();
  paths.forEach((rawPath) => {
    const normalized = rawPath.replace(/\\/g, "/");
    const chunks = normalized.split("/").filter(Boolean);
    let cursor = rootMap;
    const breadcrumb: string[] = [];

    chunks.forEach((chunk, index) => {
      breadcrumb.push(chunk);
      const type = index === chunks.length - 1 ? "file" : "folder";
      const key = `${type}:${chunk}`;
      if (!cursor.has(key)) {
        cursor.set(key, makeNode(`${prefix}:${type}:${breadcrumb.join("/")}`, type, chunk, type === "file" ? normalized : undefined));
      }
      const node = cursor.get(key);
      if (node && type === "folder") cursor = node.childrenMap;
    });
  });
  return finalizeTree(Array.from(rootMap.values()));
}
