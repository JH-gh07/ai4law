const DEFAULT_TIMEOUT_MS = 12000;

export class HttpTimeoutError extends Error {
  constructor(message = "Request timeout") {
    super(message);
    this.name = "HttpTimeoutError";
  }
}

type FetchWithTimeoutOptions = RequestInit & {
  timeoutMs?: number;
};

export async function fetchWithTimeout(input: RequestInfo | URL, init: FetchWithTimeoutOptions = {}): Promise<Response> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, signal, ...requestInit } = init;
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(new HttpTimeoutError()), timeoutMs);

  const abortFromCaller = () => controller.abort(signal?.reason);
  signal?.addEventListener("abort", abortFromCaller, { once: true });

  try {
    return await fetch(input, {
      ...requestInit,
      signal: controller.signal,
    });
  } catch (error) {
    if (controller.signal.aborted) {
      const reason = controller.signal.reason;
      if (reason instanceof HttpTimeoutError) {
        throw reason;
      }
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
    signal?.removeEventListener("abort", abortFromCaller);
  }
}

export function toReadableRequestError(error: unknown, fallback: string): string {
  if (error instanceof HttpTimeoutError) {
    return `${fallback}（请求超时）`;
  }
  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message;
  }
  return fallback;
}
