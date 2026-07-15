import { Component, type ErrorInfo, type ReactNode } from "react";

type LazyRouteErrorBoundaryProps = {
  children: ReactNode;
};

type LazyRouteErrorBoundaryState = {
  hasError: boolean;
};

export class LazyRouteErrorBoundary extends Component<
  LazyRouteErrorBoundaryProps,
  LazyRouteErrorBoundaryState
> {
  state: LazyRouteErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): LazyRouteErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Lazy route loading failed.", error, info);
  }

  private reloadPage = () => {
    globalThis.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <section className="page-loading" role="alert">
          <p>页面资源加载失败，请检查网络连接后重试。</p>
          <button type="button" onClick={this.reloadPage}>
            重新加载
          </button>
        </section>
      );
    }

    return this.props.children;
  }
}
