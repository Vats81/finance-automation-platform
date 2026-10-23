export interface IncomeResponse {
  id: string;
  income_date: string;
  source: string;
  category: string;
  amount: string;
  notes: string | null;
  status: "recorded" | "void";
  created_at: string;
}

export interface PagedIncomeResponse {
  items: IncomeResponse[];
  total: number;
  offset: number;
  limit: number;
}

export interface RecordIncomeRequest {
  income_date: string;
  source: string;
  category: string;
  amount: string;
  notes?: string;
}

export interface BudgetResponse {
  id: string;
  category: string;
  monthly_limit: string;
}

export type BudgetStatus = "ok" | "near" | "over";

export interface BudgetProgressResponse {
  id: string;
  category: string;
  monthly_limit: string;
  spent: string;
  remaining: string;
  percent_used: string;
  status: BudgetStatus;
}

export interface CategorySpendResponse {
  category: string;
  amount: string;
  share: string;
}

export interface PersonalSummaryResponse {
  period_start: string;
  period_end: string;
  income: string;
  spending: string;
  saved: string;
  savings_rate: string | null;
  spending_by_category: CategorySpendResponse[];
  budgets: BudgetProgressResponse[];
}
