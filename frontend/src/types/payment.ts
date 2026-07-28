export type PaymentStatus = "scheduled" | "paid" | "failed" | "cancelled";

export interface PaymentResponse {
  id: string;
  invoice_id: string;
  vendor_id: string;
  amount: string;
  status: PaymentStatus;
  scheduled_date: string;
  created_at: string;
}

export interface PagedPaymentsResponse {
  items: PaymentResponse[];
  total: number;
  offset: number;
  limit: number;
}
