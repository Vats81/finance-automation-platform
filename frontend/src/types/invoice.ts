export type InvoiceStatus =
  | "submitted"
  | "matched"
  | "match_exception"
  | "pending_approval"
  | "approved"
  | "rejected";

export interface InvoiceLineItem {
  line_number: number;
  description: string;
  quantity: string;
  unit_price: string;
  line_total: string;
}

export interface InvoiceResponse {
  id: string;
  invoice_number: string;
  vendor_id: string;
  po_id: string;
  status: InvoiceStatus;
  line_items: InvoiceLineItem[];
  total_amount: string;
  document_reference: string | null;
  match_discrepancies: string[];
  created_at: string;
}

export interface PagedInvoicesResponse {
  items: InvoiceResponse[];
  total: number;
  offset: number;
  limit: number;
}

export interface SubmitInvoiceRequest {
  invoice_number: string;
  vendor_id: string;
  po_id: string;
  line_items: {
    line_number: number;
    description: string;
    quantity: string;
    unit_price: string;
  }[];
}
