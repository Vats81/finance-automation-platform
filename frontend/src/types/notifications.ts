export type NotificationCategory = "overdue_sale" | "overdue_purchase" | "low_stock";
export type NotificationSeverity = "warning" | "critical";

export interface NotificationItem {
  id: string;
  category: NotificationCategory;
  severity: NotificationSeverity;
  message: string;
  link: string;
}

export interface NotificationsResponse {
  count: number;
  items: NotificationItem[];
}
