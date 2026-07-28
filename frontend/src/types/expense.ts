export type ExpenseStatus = "recorded" | "void";
export type PaymentMethod = "cash" | "card" | "bank_transfer" | "upi" | "other";

export interface ExpenseResponse {
  id: string;
  business_id: string;
  expense_date: string;
  vendor_id: string | null;
  category: string;
  description: string;
  amount: string;
  tax: string;
  total_amount: string;
  payment_method: PaymentMethod;
  is_recurring: boolean;
  notes: string | null;
  status: ExpenseStatus;
  created_at: string;
}

export interface PagedExpensesResponse {
  items: ExpenseResponse[];
  total: number;
  offset: number;
  limit: number;
}

export interface CreateExpenseRequest {
  expense_date: string;
  category: string;
  description: string;
  amount: string;
  payment_method: PaymentMethod;
  vendor_id?: string;
  tax?: string;
  is_recurring?: boolean;
  notes?: string;
}

export interface ScannedReceiptResponse {
  vendor_name: string | null;
  amount: string | null;
  expense_date: string | null;
  category_guess: string | null;
  description_guess: string | null;
  raw_text: string;
}
