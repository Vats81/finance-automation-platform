export type SaleStatus = "recorded" | "void";
export type SalePaymentStatus = "unpaid" | "partially_paid" | "paid";

export interface SaleLineItem {
  line_number: number;
  description: string;
  quantity: string;
  unit_price: string;
  line_total: string;
}

export interface SaleResponse {
  id: string;
  business_id: string;
  invoice_number: string;
  customer_id: string | null;
  invoice_date: string;
  due_date: string | null;
  line_items: SaleLineItem[];
  subtotal: string;
  discount: string;
  tax: string;
  total_amount: string;
  amount_received: string;
  outstanding_amount: string;
  payment_status: SalePaymentStatus;
  notes: string | null;
  status: SaleStatus;
  created_at: string;
}

export interface PagedSalesResponse {
  items: SaleResponse[];
  total: number;
  offset: number;
  limit: number;
}

export interface CreateSaleLineItemRequest {
  line_number: number;
  description: string;
  quantity: string;
  unit_price: string;
}

export interface CreateSaleRequest {
  invoice_number: string;
  invoice_date: string;
  due_date?: string;
  customer_id?: string;
  line_items: CreateSaleLineItemRequest[];
  discount?: string;
  tax?: string;
  notes?: string;
}
