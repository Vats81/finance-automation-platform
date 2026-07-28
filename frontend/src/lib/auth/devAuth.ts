// Local-dev-only auth: mirrors the backend's `dev.<base64-json>` bearer
// token format (see backend/app/identity/infrastructure/entra/jwt_validator.py)
// so the platform is runnable end-to-end without a real Entra ID tenant.
// Gated by NEXT_PUBLIC_AUTH_DEV_MODE, which must match the backend's
// AUTH_DEV_MODE — never enabled outside local development.

const STORAGE_KEY = "fap.devAuth.session";

export interface DevSession {
  oid: string;
  email: string;
  name: string;
}

function base64UrlEncode(json: string): string {
  return btoa(json).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function buildDevToken(session: DevSession): string {
  return `dev.${base64UrlEncode(JSON.stringify(session))}`;
}

export function saveDevSession(session: DevSession): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
}

export function loadDevSession(): DevSession | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(STORAGE_KEY);
  return raw ? (JSON.parse(raw) as DevSession) : null;
}

export function clearDevSession(): void {
  localStorage.removeItem(STORAGE_KEY);
}
