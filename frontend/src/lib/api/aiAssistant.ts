import { apiFetch } from "@/lib/api/client";
import { AskAssistantResponse, InsightsResponse } from "@/types/aiAssistant";

export function askAssistant(
  token: string | null,
  businessId: string,
  args: { question: string; history?: Record<string, unknown>[] | null }
): Promise<AskAssistantResponse> {
  return apiFetch<AskAssistantResponse>(`/businesses/${businessId}/ai-assistant/ask`, token, {
    method: "POST",
    body: JSON.stringify({ question: args.question, history: args.history ?? null }),
  });
}

export function getInsights(token: string | null, businessId: string): Promise<InsightsResponse> {
  return apiFetch<InsightsResponse>(`/businesses/${businessId}/ai-assistant/insights`, token);
}
