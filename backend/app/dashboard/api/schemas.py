from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from app.dashboard.application.queries.get_business_health_score import BusinessHealthScore
from app.dashboard.application.queries.get_dashboard_summary import DashboardSummary
from app.dashboard.application.queries.get_dashboard_trend import DashboardTrend, TrendPoint
from app.dashboard.application.queries.get_forecast import Forecast, ForecastPoint


class DashboardSummaryResponse(BaseModel):
    total_revenue: Decimal
    total_expenses: Decimal
    net_profit: Decimal
    outstanding_receivables: Decimal
    period_start: date | None
    period_end: date | None

    @classmethod
    def from_domain(cls, summary: DashboardSummary) -> "DashboardSummaryResponse":
        return cls(
            total_revenue=summary.total_revenue,
            total_expenses=summary.total_expenses,
            net_profit=summary.net_profit,
            outstanding_receivables=summary.outstanding_receivables,
            period_start=summary.period_start,
            period_end=summary.period_end,
        )


class TrendPointResponse(BaseModel):
    period_start: date
    revenue: Decimal
    expenses: Decimal

    @classmethod
    def from_domain(cls, point: TrendPoint) -> "TrendPointResponse":
        return cls(period_start=point.period_start, revenue=point.revenue, expenses=point.expenses)


class DashboardTrendResponse(BaseModel):
    granularity: Literal["day", "week", "month"]
    points: list[TrendPointResponse]

    @classmethod
    def from_domain(cls, trend: DashboardTrend) -> "DashboardTrendResponse":
        return cls(
            granularity=trend.granularity,
            points=[TrendPointResponse.from_domain(p) for p in trend.points],
        )


class SendReportEmailRequest(BaseModel):
    recipient_email: EmailStr


class SendReportWhatsAppRequest(BaseModel):
    recipient_phone: str = Field(min_length=1)


class BusinessHealthScoreResponse(BaseModel):
    overall_score: int
    label: str
    breakdown: dict[str, float | None]

    @classmethod
    def from_domain(cls, score: BusinessHealthScore) -> "BusinessHealthScoreResponse":
        return cls(overall_score=score.overall_score, label=score.label, breakdown=score.breakdown)


class ForecastPointResponse(BaseModel):
    period_start: date
    projected_revenue: Decimal
    projected_expenses: Decimal
    projected_net_profit: Decimal

    @classmethod
    def from_domain(cls, point: ForecastPoint) -> "ForecastPointResponse":
        return cls(
            period_start=point.period_start,
            projected_revenue=point.projected_revenue,
            projected_expenses=point.projected_expenses,
            projected_net_profit=point.projected_net_profit,
        )


class ForecastResponse(BaseModel):
    history_months_used: int
    points: list[ForecastPointResponse]

    @classmethod
    def from_domain(cls, forecast: Forecast) -> "ForecastResponse":
        return cls(
            history_months_used=forecast.history_months_used,
            points=[ForecastPointResponse.from_domain(p) for p in forecast.points],
        )
