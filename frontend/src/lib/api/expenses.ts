import { apiFetch } from "@/lib/api/client";
import {
  CreateExpenseRequest,
  ExpenseResponse,
  PagedExpensesResponse,
  ScannedReceiptResponse,
} from "@/types/expense";

export function listExpenses(token: string | null, businessId: string): Promise<PagedExpensesResponse> {
  return apiFetch<PagedExpensesResponse>(`/businesses/${businessId}/expenses`, token);
}

export function getExpense(
  token: string | null,
  businessId: string,
  expenseId: string
): Promise<ExpenseResponse> {
  return apiFetch<ExpenseResponse>(`/businesses/${businessId}/expenses/${expenseId}`, token);
}

export function createExpense(
  token: string | null,
  businessId: string,
  body: CreateExpenseRequest
): Promise<ExpenseResponse> {
  return apiFetch<ExpenseResponse>(`/businesses/${businessId}/expenses`, token, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function voidExpense(
  token: string | null,
  businessId: string,
  expenseId: string
): Promise<ExpenseResponse> {
  return apiFetch<ExpenseResponse>(`/businesses/${businessId}/expenses/${expenseId}/void`, token, {
    method: "POST",
  });
}

export async function scanReceipt(
  token: string | null,
  businessId: string,
  file: File
): Promise<ScannedReceiptResponse> {
  const formData = new FormData();
  formData.append("file", file);
  // apiFetch always sets Content-Type: application/json, which is wrong for
  // multipart uploads — the browser needs to set its own boundary — so this
  // call bypasses it and constructs the request directly.
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_BASE_URL}/api/v1/businesses/${businessId}/expenses/scan-receipt`, {
    method: "POST",
    headers,
    body: formData,
  });

  if (!response.ok) {
    const problem = await response.json().catch(() => null);
    throw new Error(problem?.detail ?? response.statusText);
  }
  return (await response.json()) as ScannedReceiptResponse;
}
