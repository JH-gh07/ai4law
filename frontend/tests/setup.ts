import "@testing-library/jest-dom/vitest";

function createMemoryStorage(): Storage {
  const items = new Map<string, string>();
  return {
    get length() {
      return items.size;
    },
    clear: () => items.clear(),
    getItem: (key) => items.get(String(key)) ?? null,
    key: (index) => Array.from(items.keys())[index] ?? null,
    removeItem: (key) => items.delete(String(key)),
    setItem: (key, value) => items.set(String(key), String(value)),
  };
}

// Newer Node releases expose incomplete storage globals unless launched with
// --localstorage-file. Keep Vitest storage deterministic and isolated.
Object.defineProperties(globalThis, {
  localStorage: {
    configurable: true,
    value: createMemoryStorage(),
  },
  sessionStorage: {
    configurable: true,
    value: createMemoryStorage(),
  },
});
