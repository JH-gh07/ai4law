import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

const EXPECTED_IMPORTS = [
  '@import "./app/base.css";',
  '@import "./app/landing.css";',
  '@import "./app/pages.css";',
  '@import "./app/workspace.css";',
  '@import "./app/product-pages-and-overrides.css";',
  '@import "./app/report.css";',
];

const STYLE_SEGMENTS = [
  "base.css",
  "landing.css",
  "pages.css",
  "workspace.css",
  "product-pages-and-overrides.css",
  "report.css",
];

function readStyle(relativePath: string): string {
  return readFileSync(resolve(process.cwd(), "src/styles", relativePath), "utf8");
}

describe("global CSS structure", () => {
  it("keeps one ordered global stylesheet entrypoint", () => {
    const entryLines = readStyle("app.css")
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean);

    expect(entryLines).toEqual(EXPECTED_IMPORTS);
  });

  it("keeps stylesheet segments bounded and free of nested imports", () => {
    for (const name of STYLE_SEGMENTS) {
      const source = readStyle(`app/${name}`);
      const lineCount = source.split(/\r?\n/).length;
      expect(source.trim().length, name).toBeGreaterThan(0);
      expect(source, name).not.toMatch(/^\s*@import/m);
      expect(lineCount, name).toBeLessThan(5000);
    }
  });
});
