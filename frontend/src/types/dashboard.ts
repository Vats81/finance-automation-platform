export interface DashboardSummaryResponse {
  total_revenue: string;
  total_expenses: string;
  net_profit: string;
  outstanding_receivables: string;
  period_start: string | null;
  period_end: string | null;
}

export interface DashboardTrendPoint {
  period_start: string;
  revenue: string;
  expenses: string;
}

export type DashboardGranularity = "day" | "week" | "month";

export interface DashboardTrendResponse {
  granularity: DashboardGranularity;
  points: DashboardTrendPoint[];
}

export type DashboardPeriod = "this_month" | "this_quarter" | "this_year" | "all_time";

export const DASHBOARD_PERIODS: { value: DashboardPeriod; label: string }[] = [
  { value: "this_month", label: "This month" },
  { value: "this_quarter", label: "This quarter" },
  { value: "this_year", label: "This year" },
  { value: "all_time", label: "All time" },
];

export interface BusinessHealthScoreResponse {
  // null when there isn't enough data to score at all.
  overall_score: number | null;
  label: string;
  breakdown: Record<string, number | null>;
}

export interface ForecastPoint {
  period_start: string;
  projected_revenue: string;
  projected_expenses: string;
  projected_net_profit: string;
}

export interface DashboardForecastResponse {
  history_months_used: number;
  points: ForecastPoint[];
}
