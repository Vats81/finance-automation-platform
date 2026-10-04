import { apiFetch } from "@/lib/api/client";

export interface SubmitContactRequest {
  name: string;
  email: string;
  business_name?: string;
  message?: string;
  // Honeypot — always empty from the real form; see ContactForm.
  website?: string;
}

// Public endpoint: no token.
export function submitContactRequest(body: SubmitContactRequest): Promise<{ received: boolean }> {
  return apiFetch<{ received: boolean }>("/contact", null, {
    method: "POST",
    body: JSON.stringify(body),
  });
}
