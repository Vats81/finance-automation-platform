import { apiFetch } from "@/lib/api/client";
import { UserResponse } from "@/types/user";

export function fetchMe(token: string | null): Promise<UserResponse> {
  return apiFetch<UserResponse>("/me", token);
}
