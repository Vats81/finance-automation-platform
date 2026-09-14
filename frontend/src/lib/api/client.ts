const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// No previous version of this file bounded how long a request could take,
// so a hung backend (or, on Render's free tier, one asleep and taking its
// time to cold-start) left callers spinning ("Signing in…", "Loading…")
// forever with no error and no way to recover short of a page reload.
// 45s is deliberately more generous than a typical API timeout — the goal
// is "never hang forever," not "fail fast on every cold start," since a
// free-tier cold start alone can take most of a minute.
const REQUEST_TIMEOUT_MS = 45_000;

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public errorCode: string,
    public details?: unknown
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * Thin fetch wrapper: attaches the bearer token, targets the versioned API
 * base, bounds every request to REQUEST_TIMEOUT_MS, and translates both the
 * backend's RFC 7807 problem+json error shape (see
 * backend/app/api/exception_handlers.py) and network/timeout failures into
 * a typed ApiError, so every caller gets one consistent shape to catch.
 */
export async function apiFetch<T>(
  path: string,
  token: string | null,
  init: RequestInit = {}
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/v1${path}`, {
      ...init,
      headers,
      signal: init.signal ?? controller.signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError(
        "The server is taking too long to respond — it may be waking up after being idle. Please try again.",
        0,
        "request_timeout"
      );
    }
    throw new ApiError("Could not reach the server. Check your connection and try again.", 0, "network_error");
  } finally {
    clearTimeout(timeoutId);
  }

  if (!response.ok) {
    const problem = await response.json().catch(() => null);
    throw new ApiError(
      problem?.detail ?? response.statusText,
      response.status,
      problem?.error_code ?? "unknown_error",
      problem?.details
    );
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
