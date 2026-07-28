"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { askAssistant } from "@/lib/api/aiAssistant";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { ChatMessage } from "@/types/aiAssistant";

export default function AiAssistantPage() {
  const { getAccessToken } = useLocalAuth();
  const { currentBusinessId } = useCurrentBusiness();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [history, setHistory] = useState<Record<string, unknown>[] | null>(null);
  const [question, setQuestion] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSend() {
    if (!currentBusinessId || !question.trim() || isLoading) return;
    const userQuestion = question.trim();
    setMessages((prev) => [...prev, { role: "user", text: userQuestion }]);
    setQuestion("");
    setIsLoading(true);
    setError(null);
    try {
      const res = await askAssistant(getAccessToken(), currentBusinessId, {
        question: userQuestion,
        history,
      });
      setMessages((prev) => [...prev, { role: "assistant", text: res.answer }]);
      setHistory(res.history);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reach the assistant");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div>
      <h1 className="mb-1 text-2xl font-semibold">AI Assistant</h1>
      <p className="mb-6 text-sm text-slate-500">
        Ask questions about your business data and get answers backed by your own numbers.
      </p>

      <Card className="flex h-[60vh] flex-col">
        <div className="flex-1 space-y-3 overflow-y-auto pr-1">
          {messages.length === 0 && (
            <p className="text-sm text-slate-500">
              Try asking &ldquo;What was my revenue this month?&rdquo; or &ldquo;Who owes me
              money?&rdquo;
            </p>
          )}
          {messages.map((message, i) => (
            <div
              key={i}
              className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-lg px-4 py-2 text-sm whitespace-pre-wrap ${
                  message.role === "user"
                    ? "bg-brand-600 text-white"
                    : "bg-slate-100 text-slate-800"
                }`}
              >
                {message.text}
              </div>
            </div>
          ))}
          {isLoading && <p className="text-sm text-slate-400">Thinking...</p>}
        </div>

        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}

        <div className="mt-4 flex gap-2 border-t border-slate-200 pt-4">
          <Input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void handleSend();
              }
            }}
            placeholder="Ask a question about your business..."
            disabled={isLoading}
          />
          <Button onClick={handleSend} disabled={isLoading || !question.trim()}>
            Send
          </Button>
        </div>
      </Card>
    </div>
  );
}
