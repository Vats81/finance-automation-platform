import { apiFetch } from "@/lib/api/client";
import { IdempotencyOptions, idempotencyHeaders } from "@/lib/idempotency";
import {
  BudgetResponse,
  IncomeResponse,
  PagedIncomeResponse,
  PersonalSummaryResponse,
  RecordIncomeRequest,
} from "@/types/personal";

export function getPersonalSummary(
  token: string | null,
  businessId: string,
  year: number,
  month: number
): Promise<PersonalSummaryResponse> {
  return apiFetch<PersonalSummaryResponse>(
    `/businesses/${businessId}/personal/summary?year=${year}&month=${month}`,
    token
  );
}

export function listIncome(token: string | null, businessId: string): Promise<PagedIncomeResponse> {
  return apiFetch<PagedIncomeResponse>(`/businesses/${businessId}/incomes?limit=200`, token);
}

export function recordIncome(
  token: string | null,
  businessId: string,
  body: RecordIncomeRequest,
  options?: IdempotencyOptions
): Promise<IncomeResponse> {
  return apiFetch<IncomeResponse>(`/businesses/${businessId}/incomes`, token, {
    method: "POST",
    headers: idempotencyHeaders(options),
    body: JSON.stringify(body),
  });
}

export function voidIncome(token: string | null, businessId: string, incomeId: string): Promise<IncomeResponse> {
  return apiFetch<IncomeResponse>(`/businesses/${businessId}/incomes/${incomeId}/void`, token, {
    method: "POST",
  });
}

export function listBudgets(token: string | null, businessId: string): Promise<BudgetResponse[]> {
  return apiFetch<BudgetResponse[]>(`/businesses/${businessId}/budgets`, token);
}

export function setBudget(
  token: string | null,
  businessId: string,
  category: string,
  monthlyLimit: string
): Promise<BudgetResponse> {
  return apiFetch<BudgetResponse>(`/businesses/${businessId}/budgets`, token, {
    method: "PUT",
    body: JSON.stringify({ category, monthly_limit: monthlyLimit }),
  });
}

export function removeBudget(token: string | null, businessId: string, budgetId: string): Promise<void> {
  return apiFetch<void>(`/businesses/${businessId}/budgets/${budgetId}`, token, { method: "DELETE" });
}
