const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

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
 * base, and translates the backend's RFC 7807 problem+json error shape
 * (see backend/app/api/exception_handlers.py) into a typed ApiError.
 */
export async function apiFetch<T>(
  path: string,
  token: string | null,
  init: RequestInit = {}
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_BASE_URL}/api/v1${path}`, { ...init, headers });

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
