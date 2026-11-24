import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { ExpenseResponse } from "@/types/expense";
import { formatCurrency } from "@/lib/format";
import { useT } from "@/lib/i18n/LanguageProvider";
import { MessageKey } from "@/lib/i18n/messages";

export function ExpenseTable({ expenses }: { expenses: ExpenseResponse[] }) {
  const { t } = useT();
  if (expenses.length === 0) {
    return <p className="text-sm text-slate-500">{t("exp.none")}</p>;
  }

  return (
    <table className="w-full text-left text-sm">
      <thead>
        <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
          <th className="py-2 pr-4">{t("common.date")}</th>
          <th className="py-2 pr-4">{t("exp.category")}</th>
          <th className="py-2 pr-4">{t("common.description")}</th>
          <th className="py-2 pr-4">{t("common.total")}</th>
          <th className="py-2 pr-4">{t("exp.method")}</th>
        </tr>
      </thead>
      <tbody>
        {expenses.map((expense) => (
          <tr key={expense.id} className="border-b border-slate-100 last:border-0">
            <td className="py-2 pr-4 text-slate-600">{expense.expense_date}</td>
            <td className="py-2 pr-4">
              <Link
                href={`/app/expenses/${expense.id}`}
                className="font-medium text-brand-700 hover:underline"
              >
                {expense.category}
              </Link>
              {expense.status === "void" && <span className="ml-2 text-xs text-slate-400">({t("sales.void")})</span>}
            </td>
            <td className="py-2 pr-4 text-slate-600">{expense.description}</td>
            <td className="py-2 pr-4 text-slate-600">{formatCurrency(expense.total_amount)}</td>
            <td className="py-2 pr-4">
              <Badge tone="neutral">{t(`exp.method.${expense.payment_method}` as MessageKey)}</Badge>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
