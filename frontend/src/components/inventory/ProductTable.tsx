import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { ProductResponse } from "@/types/product";

function stockBadge(product: ProductResponse): { tone: "danger" | "warning" | "success"; label: string } {
  if (product.is_out_of_stock) return { tone: "danger", label: "out of stock" };
  if (product.is_low_stock) return { tone: "warning", label: "low stock" };
  return { tone: "success", label: "in stock" };
}

export function ProductTable({ products }: { products: ProductResponse[] }) {
  if (products.length === 0) {
    return <p className="text-sm text-slate-500">No products yet.</p>;
  }

  return (
    <table className="w-full text-left text-sm">
      <thead>
        <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
          <th className="py-2 pr-4">Name</th>
          <th className="py-2 pr-4">SKU</th>
          <th className="py-2 pr-4">Quantity</th>
          <th className="py-2 pr-4">Selling price</th>
          <th className="py-2 pr-4">Stock status</th>
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
              <td className="py-2 pr-4 text-slate-600">${product.selling_price}</td>
              <td className="py-2 pr-4">
                <Badge tone={badge.tone}>{badge.label}</Badge>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
