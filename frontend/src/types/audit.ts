export interface AuditLogEntryResponse {
  id: string;
  event_type: string;
  aggregate_id: string;
  payload: Record<string, unknown>;
  occurred_at: string;
  recorded_at: string;
}

export interface PagedAuditLogResponse {
  items: AuditLogEntryResponse[];
  total: number;
  offset: number;
  limit: number;
}
