import { ApiError, apiFetch } from "@/lib/api/client";
import {
  BusinessHealthScoreResponse,
  DashboardForecastResponse,
  DashboardGranularity,
  DashboardSummaryResponse,
  DashboardTrendResponse,
} from "@/types/dashboard";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function getDashboardSummary(
  token: string | null,
  businessId: string,
  range?: { startDate?: string; endDate?: string }
): Promise<DashboardSummaryResponse> {
  const params = new URLSearchParams();
  if (range?.startDate) params.set("start_date", range.startDate);
  if (range?.endDate) params.set("end_date", range.endDate);
  const query = params.toString();
  return apiFetch<DashboardSummaryResponse>(
    `/businesses/${businessId}/dashboard/summary${query ? `?${query}` : ""}`,
    token
  );
}

export function getDashboardTrend(
  token: string | null,
  businessId: string,
  range: { startDate: string; endDate: string; granularity?: DashboardGranularity }
): Promise<DashboardTrendResponse> {
  const params = new URLSearchParams({ start_date: range.startDate, end_date: range.endDate });
  if (range.granularity) params.set("granularity", range.granularity);
  return apiFetch<DashboardTrendResponse>(
    `/businesses/${businessId}/dashboard/trend?${params.toString()}`,
    token
  );
}

export async function downloadProfitLossPdf(
  token: string | null,
  businessId: string,
  range: { startDate: string; endDate: string; granularity?: DashboardGranularity }
): Promise<void> {
  const params = new URLSearchParams({ start_date: range.startDate, end_date: range.endDate });
  if (range.granularity) params.set("granularity", range.granularity);

  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(
    `${API_BASE_URL}/api/v1/businesses/${businessId}/dashboard/profit-loss-pdf?${params.toString()}`,
    { headers }
  );
  if (!response.ok) {
    throw new ApiError(response.statusText, response.status, "unknown_error");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `profit-loss-${range.granularity ?? "report"}.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export function getBusinessHealthScore(
  token: string | null,
  businessId: string
): Promise<BusinessHealthScoreResponse> {
  return apiFetch<BusinessHealthScoreResponse>(`/businesses/${businessId}/dashboard/health-score`, token);
}

export function getForecast(
  token: string | null,
  businessId: string
): Promise<DashboardForecastResponse> {
  return apiFetch<DashboardForecastResponse>(`/businesses/${businessId}/dashboard/forecast`, token);
}

export function sendReportEmail(
  token: string | null,
  businessId: string,
  args: { recipientEmail: string; startDate: string; endDate: string; granularity?: DashboardGranularity }
): Promise<void> {
  const params = new URLSearchParams({ start_date: args.startDate, end_date: args.endDate });
  if (args.granularity) params.set("granularity", args.granularity);
  return apiFetch<void>(
    `/businesses/${businessId}/dashboard/profit-loss-pdf/email?${params.toString()}`,
    token,
    { method: "POST", body: JSON.stringify({ recipient_email: args.recipientEmail }) }
  );
}

export function sendReportWhatsApp(
  token: string | null,
  businessId: string,
  args: { recipientPhone: string; startDate: string; endDate: string; granularity?: DashboardGranularity }
): Promise<void> {
  const params = new URLSearchParams({ start_date: args.startDate, end_date: args.endDate });
  if (args.granularity) params.set("granularity", args.granularity);
  return apiFetch<void>(
    `/businesses/${businessId}/dashboard/profit-loss-pdf/whatsapp?${params.toString()}`,
    token,
    { method: "POST", body: JSON.stringify({ recipient_phone: args.recipientPhone }) }
  );
}
