"use client";

import { useParams } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Spinner } from "@/components/ui/Spinner";
import {
  adjustStock,
  deactivateProduct,
  getProduct,
  reactivateProduct,
} from "@/lib/api/products";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { ProductResponse } from "@/types/product";

function stockBadge(product: ProductResponse): { tone: "danger" | "warning" | "success"; label: string } {
  if (product.is_out_of_stock) return { tone: "danger", label: "out of stock" };
  if (product.is_low_stock) return { tone: "warning", label: "low stock" };
  return { tone: "success", label: "in stock" };
}

export default function ProductDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { getAccessToken } = useLocalAuth();
  const { currentBusinessId } = useCurrentBusiness();
  const [product, setProduct] = useState<ProductResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [delta, setDelta] = useState("");
  const [reason, setReason] = useState("");
  const [isUpdating, setIsUpdating] = useState(false);

  const load = useCallback(async () => {
    if (!currentBusinessId) return;
    const token = getAccessToken();
    try {
      setProduct(await getProduct(token, currentBusinessId, id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load product");
    }
  }, [currentBusinessId, getAccessToken, id]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleAdjustStock(event: FormEvent) {
    event.preventDefault();
    if (!currentBusinessId) return;
    setIsUpdating(true);
    setError(null);
    try {
      const token = getAccessToken();
      setProduct(await adjustStock(token, currentBusinessId, id, delta, reason));
      setDelta("");
      setReason("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to adjust stock");
    } finally {
      setIsUpdating(false);
    }
  }

  async function handleToggleActive() {
    if (!currentBusinessId || !product) return;
    setIsUpdating(true);
    setError(null);
    try {
      const token = getAccessToken();
      setProduct(
        product.status === "active"
          ? await deactivateProduct(token, currentBusinessId, id)
          : await reactivateProduct(token, currentBusinessId, id)
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update product");
    } finally {
      setIsUpdating(false);
    }
  }

  if (!product) {
    return (
      <div className="flex justify-center py-8">
        {error ? <p className="text-sm text-red-600">{error}</p> : <Spinner />}
      </div>
    );
  }

  const badge = stockBadge(product);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{product.name}</h1>
          <p className="text-sm text-slate-500">{product.sku}</p>
        </div>
        <div className="flex items-center gap-2">
          {product.status === "inactive" && <Badge tone="neutral">inactive</Badge>}
          <Badge tone={badge.tone}>{badge.label}</Badge>
        </div>
      </div>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

      <Card className="mb-6 max-w-lg space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-slate-500">Current quantity</span>
          <span>
            {product.current_quantity} {product.unit_of_measurement}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Minimum stock level</span>
          <span>{product.minimum_stock_level}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Reorder quantity</span>
          <span>{product.reorder_quantity}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Selling price</span>
          <span>${product.selling_price}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Purchase cost</span>
          <span>${product.purchase_cost}</span>
        </div>
        <div className="flex justify-between font-semibold">
          <span>Stock value</span>
          <span>${product.stock_value}</span>
        </div>
      </Card>

      <Card className="max-w-lg space-y-4">
        <form onSubmit={handleAdjustStock} className="space-y-3">
          <label className="block text-sm font-medium">Adjust stock</label>
          <div className="grid grid-cols-2 gap-2">
            <Input
              required
              type="number"
              step="any"
              placeholder="+10 or -5"
              value={delta}
              onChange={(e) => setDelta(e.target.value)}
            />
            <Input
              required
              placeholder="Reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </div>
          <Button type="submit" disabled={isUpdating}>
            Apply adjustment
          </Button>
        </form>

        <Button
          variant={product.status === "active" ? "danger" : "primary"}
          disabled={isUpdating}
          onClick={handleToggleActive}
        >
          {product.status === "active" ? "Deactivate" : "Reactivate"}
        </Button>
      </Card>
    </div>
  );
}
