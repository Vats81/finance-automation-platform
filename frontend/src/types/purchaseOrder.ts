export type PurchaseOrderStatus = "open" | "closed" | "cancelled";

export interface PurchaseOrderLineItem {
  line_number: number;
  description: string;
  quantity: string;
  unit_price: string;
  line_total: string;
}

export interface PurchaseOrderResponse {
  id: string;
  po_number: string;
  vendor_id: string;
  status: PurchaseOrderStatus;
  line_items: PurchaseOrderLineItem[];
  total_amount: string;
  created_at: string;
}

export interface PagedPurchaseOrdersResponse {
  items: PurchaseOrderResponse[];
  total: number;
  offset: number;
  limit: number;
}

export interface CreatePurchaseOrderRequest {
  vendor_id: string;
  line_items: {
    line_number: number;
    description: string;
    quantity: string;
    unit_price: string;
  }[];
}
