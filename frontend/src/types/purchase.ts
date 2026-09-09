export type PurchaseStatus = "recorded" | "void";
export type PurchasePaymentStatus = "unpaid" | "partially_paid" | "paid";

export interface PurchaseLineItem {
  line_number: number;
  description: string;
  quantity: string;
  unit_cost: string;
  line_total: string;
  product_id: string | null;
}

export interface PurchaseResponse {
  id: string;
  business_id: string;
  purchase_number: string;
  vendor_id: string;
  purchase_date: string;
  due_date: string | null;
  line_items: PurchaseLineItem[];
  subtotal: string;
  tax: string;
  total_amount: string;
  amount_paid: string;
  outstanding_amount: string;
  payment_status: PurchasePaymentStatus;
  notes: string | null;
  status: PurchaseStatus;
  created_at: string;
}

export interface PagedPurchasesResponse {
  items: PurchaseResponse[];
  total: number;
  offset: number;
  limit: number;
}

export interface CreatePurchaseLineItemRequest {
  line_number: number;
  description: string;
  quantity: string;
  unit_cost: string;
  product_id?: string;
}

export interface CreatePurchaseRequest {
  purchase_number: string;
  vendor_id: string;
  purchase_date: string;
  due_date?: string;
  line_items: CreatePurchaseLineItemRequest[];
  tax?: string;
  notes?: string;
}

// Same shape as CreatePurchaseRequest — see UpdateSaleRequest's comment
// in types/sale.ts for why.
export type UpdatePurchaseRequest = CreatePurchaseRequest;
