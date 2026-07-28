from pydantic import BaseModel, Field

from app.ai_assistant.application.ask_assistant import AskAssistantResult
from app.ai_assistant.application.generate_insights import GenerateInsightsResult


class AskAssistantRequest(BaseModel):
    question: str = Field(min_length=1)
    history: list[dict] | None = None


class AskAssistantResponse(BaseModel):
    answer: str
    history: list[dict]

    @classmethod
    def from_domain(cls, result: AskAssistantResult) -> "AskAssistantResponse":
        return cls(answer=result.answer, history=result.history)


class InsightsResponse(BaseModel):
    insights: str

    @classmethod
    def from_domain(cls, result: GenerateInsightsResult) -> "InsightsResponse":
        return cls(insights=result.insights)
