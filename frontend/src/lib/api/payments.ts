import { apiFetch } from "@/lib/api/client";
import { PagedPaymentsResponse } from "@/types/payment";

export function listPayments(token: string | null): Promise<PagedPaymentsResponse> {
  return apiFetch<PagedPaymentsResponse>("/payments", token);
}
