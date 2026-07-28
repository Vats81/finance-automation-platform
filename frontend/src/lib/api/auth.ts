import { apiFetch } from "@/lib/api/client";
import {
  LocalUserResponse,
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  RequestPasswordResetRequest,
  ResetPasswordRequest,
  VerifyEmailRequest,
} from "@/types/auth";

export function registerUser(body: RegisterRequest): Promise<LocalUserResponse> {
  return apiFetch<LocalUserResponse>("/auth/register", null, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function verifyEmail(body: VerifyEmailRequest): Promise<LocalUserResponse> {
  return apiFetch<LocalUserResponse>("/auth/verify-email", null, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function loginUser(body: LoginRequest): Promise<LoginResponse> {
  return apiFetch<LoginResponse>("/auth/login", null, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function requestPasswordReset(body: RequestPasswordResetRequest): Promise<void> {
  return apiFetch<void>("/auth/request-password-reset", null, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function resetPassword(body: ResetPasswordRequest): Promise<LocalUserResponse> {
  return apiFetch<LocalUserResponse>("/auth/reset-password", null, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function fetchLocalMe(token: string | null): Promise<LocalUserResponse> {
  return apiFetch<LocalUserResponse>("/auth/me", token);
}
