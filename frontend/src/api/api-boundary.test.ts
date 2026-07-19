import { describe, expect, it } from "vitest";

const sourceFiles = import.meta.glob<string>("../**/*.{ts,tsx}", {
  eager: true,
  import: "default",
  query: "?raw",
});

describe("frontend API boundary", () => {
  it("keeps backend URLs inside the api directory", () => {
    for (const [path, source] of Object.entries(sourceFiles)) {
      if (path.startsWith("./") || path.endsWith(".test.ts") || path.endsWith(".test.tsx")) {
        continue;
      }
      expect(source, path).not.toMatch(/["'`]\/(?:api\/|health\b)/);
    }
  });

  it("allows direct fetch calls only in the shared client", () => {
    for (const [path, source] of Object.entries(sourceFiles)) {
      if (path === "./client.ts" || path.endsWith(".test.ts") || path.endsWith(".test.tsx")) {
        continue;
      }
      expect(source, path).not.toMatch(/\bfetch\s*\(/);
    }
  });
});
