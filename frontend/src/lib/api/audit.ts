import { apiFetch } from "@/lib/api/client";
import { PagedAuditLogResponse } from "@/types/audit";

export function listAuditLog(token: string | null, aggregateId?: string): Promise<PagedAuditLogResponse> {
  const query = aggregateId ? `?aggregate_id=${aggregateId}` : "";
  return apiFetch<PagedAuditLogResponse>(`/audit-log${query}`, token);
}
