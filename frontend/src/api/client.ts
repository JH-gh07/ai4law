export class HttpTimeoutError extends Error {
  constructor(message = "Request timeout") {
    super(message);
    this.name = "HttpTimeoutError";
  }
}

export class HttpStatusError extends Error {
  readonly status: number;
  constructor(status: number, message?: string) {
    super(message ?? `HTTP ${status}`);
    this.name = "HttpStatusError";
    this.status = status;
  }
}

export type ApiRequestInit = RequestInit & {
  timeoutMs?: number;
};

/** Shared HTTP transport. Endpoint modules own URLs and payload parsing. */
export async function apiFetch(
  input: RequestInfo | URL,
  init: ApiRequestInit = {},
): Promise<Response> {
  const { timeoutMs, signal, ...requestInit } = init;
  if (timeoutMs === undefined) {
    return fetch(input, { ...requestInit, signal });
  }

  const controller = new AbortController();
  const timeoutId = window.setTimeout(
    () => controller.abort(new HttpTimeoutError()),
    timeoutMs,
  );

  function abortFromCaller(): void {
    controller.abort(signal?.reason);
  }

  signal?.addEventListener("abort", abortFromCaller, { once: true });
  try {
    return await fetch(input, { ...requestInit, signal: controller.signal });
  } catch (error) {
    if (controller.signal.aborted) {
      const reason = controller.signal.reason;
      if (reason instanceof HttpTimeoutError) throw reason;
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
    signal?.removeEventListener("abort", abortFromCaller);
  }
}

export function toReadableRequestError(error: unknown, fallback: string): string {
  if (error instanceof HttpTimeoutError) return `${fallback}（请求超时）`;
  if (error instanceof Error && error.message.trim().length > 0) return error.message;
  return fallback;
}
