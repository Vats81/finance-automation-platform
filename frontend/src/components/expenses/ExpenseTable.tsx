import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { ExpenseResponse } from "@/types/expense";

export function ExpenseTable({ expenses }: { expenses: ExpenseResponse[] }) {
  if (expenses.length === 0) {
    return <p className="text-sm text-slate-500">No expenses recorded yet.</p>;
  }

  return (
    <table className="w-full text-left text-sm">
      <thead>
        <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
          <th className="py-2 pr-4">Date</th>
          <th className="py-2 pr-4">Category</th>
          <th className="py-2 pr-4">Description</th>
          <th className="py-2 pr-4">Total</th>
          <th className="py-2 pr-4">Payment method</th>
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
              {expense.status === "void" && <span className="ml-2 text-xs text-slate-400">(void)</span>}
            </td>
            <td className="py-2 pr-4 text-slate-600">{expense.description}</td>
            <td className="py-2 pr-4 text-slate-600">${expense.total_amount}</td>
            <td className="py-2 pr-4">
              <Badge tone="neutral">{expense.payment_method.replace("_", " ")}</Badge>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
