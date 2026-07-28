import { apiFetch } from "@/lib/api/client";
import { NotificationsResponse } from "@/types/notifications";

export function getNotifications(
  token: string | null,
  businessId: string
): Promise<NotificationsResponse> {
  return apiFetch<NotificationsResponse>(`/businesses/${businessId}/notifications`, token);
}
