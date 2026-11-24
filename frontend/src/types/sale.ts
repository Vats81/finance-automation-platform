export type SaleStatus = "recorded" | "void";
export type SalePaymentStatus = "unpaid" | "partially_paid" | "paid";

export interface SaleLineItem {
  line_number: number;
  description: string;
  quantity: string;
  unit_price: string;
  line_total: string;
  gst_rate?: string | null;
  hsn_code?: string | null;
}

export interface GstGroup {
  rate: string;
  taxable_value: string;
  tax: string;
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
  place_of_supply?: string | null;
  gst_breakdown?: GstGroup[];
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
  gst_rate?: string;
  hsn_code?: string;
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
  place_of_supply?: string;
}

// Same shape as CreateSaleRequest — the edit form always resends the full
// record rather than a sparse patch, matching how the backend's
// Sale.update_details works (see its docstring).
export type UpdateSaleRequest = CreateSaleRequest;

export interface ReceivableInvoice {
  sale_id: string;
  invoice_number: string;
  invoice_date: string;
  due_date: string | null;
  outstanding: string;
  days_overdue: number;
}

export interface ReceivableCustomer {
  customer_id: string | null;
  name: string;
  phone: string | null;
  outstanding: string;
  days_overdue: number;
  invoices: ReceivableInvoice[];
}

export interface ReceivablesResponse {
  total_outstanding: string;
  customers: ReceivableCustomer[];
}
