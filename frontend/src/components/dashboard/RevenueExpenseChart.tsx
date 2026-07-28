"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatCurrency } from "@/lib/format";
import { DashboardGranularity, DashboardTrendResponse } from "@/types/dashboard";

function formatAxisLabel(periodStart: string, granularity: DashboardGranularity): string {
  const d = new Date(`${periodStart}T00:00:00`);
  if (granularity === "month") return d.toLocaleDateString("en-US", { month: "short", year: "numeric" });
  // "day" and "week" both label by their start date — the dashboard chart
  // never actually requests "week" (auto-infer only ever picks day/month),
  // but the type is shared with the Reports page's explicit picker.
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function RevenueExpenseChart({ trend }: { trend: DashboardTrendResponse }) {
  const data = trend.points.map((p) => ({
    label: formatAxisLabel(p.period_start, trend.granularity),
    revenue: Number(p.revenue),
    expenses: Number(p.expenses),
  }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="label" tick={{ fontSize: 12, fill: "#64748b" }} />
        <YAxis
          tick={{ fontSize: 12, fill: "#64748b" }}
          tickFormatter={(value: number) => formatCurrency(value)}
          width={80}
        />
        <Tooltip formatter={(value: unknown) => formatCurrency(Number(Array.isArray(value) ? value[0] : value))} />
        <Legend />
        <Line type="monotone" dataKey="revenue" name="Revenue" stroke="#059669" strokeWidth={2} dot={false} />
        <Line
          type="monotone"
          dataKey="expenses"
          name="Expenses"
          stroke="#dc2626"
          strokeWidth={2}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
