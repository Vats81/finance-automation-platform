export interface AskAssistantRequest {
  question: string;
  history?: Record<string, unknown>[] | null;
}

export interface AskAssistantResponse {
  answer: string;
  history: Record<string, unknown>[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  text: string;
}

export interface InsightsResponse {
  insights: string;
}
