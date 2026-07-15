import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { LazyRouteErrorBoundary } from "./LazyRouteErrorBoundary";

function BrokenPage(): never {
  throw new Error("chunk load failed");
}

describe("LazyRouteErrorBoundary", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows a Chinese recovery action when a lazy page fails", () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);

    render(
      <LazyRouteErrorBoundary>
        <BrokenPage />
      </LazyRouteErrorBoundary>,
    );

    expect(
      screen.getByText("页面资源加载失败，请检查网络连接后重试。"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "重新加载" }),
    ).toBeInTheDocument();
  });
});
