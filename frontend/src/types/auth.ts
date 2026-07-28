export interface LocalUserResponse {
  id: string;
  email: string;
  display_name: string;
  is_email_verified: boolean;
  is_active: boolean;
  is_platform_admin: boolean;
  created_at: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  display_name: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  expires_at: string;
  user: LocalUserResponse;
}

export interface VerifyEmailRequest {
  user_id: string;
  token: string;
}

export interface RequestPasswordResetRequest {
  email: string;
}

export interface ResetPasswordRequest {
  user_id: string;
  token: string;
  new_password: string;
}
