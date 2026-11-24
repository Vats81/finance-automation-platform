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
import { formatCurrency } from "@/lib/format";
import { useT } from "@/lib/i18n/LanguageProvider";
import { MessageKey } from "@/lib/i18n/messages";

function stockBadge(product: ProductResponse): { tone: "danger" | "warning" | "success"; label: MessageKey } {
  if (product.is_out_of_stock) return { tone: "danger", label: "stock.out" };
  if (product.is_low_stock) return { tone: "warning", label: "stock.low" };
  return { tone: "success", label: "stock.in" };
}

export default function ProductDetailPage() {
  const { t } = useT();
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
      setError(err instanceof Error ? err.message : t("s.failed_to_load_product"));
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
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
      setError(err instanceof Error ? err.message : t("s.failed_to_adjust_stock"));
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
      setError(err instanceof Error ? err.message : t("s.failed_to_update_product"));
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
          {product.status === "inactive" && <Badge tone="neutral">{t("cust.status.inactive")}</Badge>}
          <Badge tone={badge.tone}>{t(badge.label)}</Badge>
        </div>
      </div>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

      <Card className="mb-6 max-w-lg space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-slate-500">{t("s.current_quantity")}</span>
          <span>
            {product.current_quantity} {product.unit_of_measurement}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">{t("s.minimum_stock_level")}</span>
          <span>{product.minimum_stock_level}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">{t("s.reorder_quantity")}</span>
          <span>{product.reorder_quantity}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">{t("s.selling_price")}</span>
          <span>{formatCurrency(product.selling_price)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">{t("s.purchase_cost")}</span>
          <span>{formatCurrency(product.purchase_cost)}</span>
        </div>
        <div className="flex justify-between font-semibold">
          <span>{t("s.stock_value")}</span>
          <span>{formatCurrency(product.stock_value)}</span>
        </div>
      </Card>

      <Card className="max-w-lg space-y-4">
        <form onSubmit={handleAdjustStock} className="space-y-3">
          <label className="block text-sm font-medium">{t("s.adjust_stock")}</label>
          <div className="grid grid-cols-2 gap-2">
            <Input
              required
              type="number"
              step="any"
              placeholder={t("s.10_or_5")}
              value={delta}
              onChange={(e) => setDelta(e.target.value)}
            />
            <Input
              required
              placeholder={t("s.reason")}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </div>
          <Button type="submit" disabled={isUpdating}>
            {t("s.apply_adjustment")}
          </Button>
        </form>

        <Button
          variant={product.status === "active" ? "danger" : "primary"}
          disabled={isUpdating}
          onClick={handleToggleActive}
        >
          {product.status === "active" ? t("cust.deactivate") : t("cust.reactivate")}
        </Button>
      </Card>
    </div>
  );
}
