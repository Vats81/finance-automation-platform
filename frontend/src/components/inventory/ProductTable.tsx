import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { ProductResponse } from "@/types/product";
import { formatCurrency } from "@/lib/format";
import { useT } from "@/lib/i18n/LanguageProvider";
import { MessageKey } from "@/lib/i18n/messages";

function stockBadge(product: ProductResponse): { tone: "danger" | "warning" | "success"; label: MessageKey } {
  if (product.is_out_of_stock) return { tone: "danger", label: "stock.out" };
  if (product.is_low_stock) return { tone: "warning", label: "stock.low" };
  return { tone: "success", label: "stock.in" };
}

export function ProductTable({ products }: { products: ProductResponse[] }) {
  const { t } = useT();
  if (products.length === 0) {
    return <p className="text-sm text-slate-500">{t("s.no_products_yet")}</p>;
  }

  return (
    <table className="w-full text-left text-sm">
      <thead>
        <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
          <th className="py-2 pr-4">{t("common.name")}</th>
          <th className="py-2 pr-4">{t("s.sku")}</th>
          <th className="py-2 pr-4">{t("s.quantity")}</th>
          <th className="py-2 pr-4">{t("s.selling_price")}</th>
          <th className="py-2 pr-4">{t("s.stock_status")}</th>
        </tr>
      </thead>
      <tbody>
        {products.map((product) => {
          const badge = stockBadge(product);
          return (
            <tr key={product.id} className="border-b border-slate-100 last:border-0">
              <td className="py-2 pr-4">
                <Link
                  href={`/app/inventory/${product.id}`}
                  className="font-medium text-brand-700 hover:underline"
                >
                  {product.name}
                </Link>
              </td>
              <td className="py-2 pr-4 text-slate-600">{product.sku}</td>
              <td className="py-2 pr-4 text-slate-600">
                {product.current_quantity} {product.unit_of_measurement}
              </td>
              <td className="py-2 pr-4 text-slate-600">{formatCurrency(product.selling_price)}</td>
              <td className="py-2 pr-4">
                <Badge tone={badge.tone}>{t(badge.label)}</Badge>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
