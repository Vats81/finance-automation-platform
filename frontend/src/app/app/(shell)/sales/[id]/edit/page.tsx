"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { SaleForm } from "@/components/sales/SaleForm";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { getSale, updateSale } from "@/lib/api/sales";
import { listCustomers } from "@/lib/api/customers";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { useT } from "@/lib/i18n/LanguageProvider";
import { CustomerResponse } from "@/types/customer";
import { CreateSaleRequest } from "@/types/sale";

export default function EditSalePage() {
  const { id } = useParams<{ id: string }>();
  const { getAccessToken } = useLocalAuth();
  const { currentBusinessId } = useCurrentBusiness();
  const router = useRouter();
  const { t } = useT();
  const [customers, setCustomers] = useState<CustomerResponse[]>([]);
  const [initialValues, setInitialValues] = useState<CreateSaleRequest | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!currentBusinessId) return;
    const token = getAccessToken();
    listCustomers(token, currentBusinessId)
      .then((page) => setCustomers(page.items))
      .catch(() => setCustomers([]));
    getSale(token, currentBusinessId, id)
      .then((sale) =>
        setInitialValues({
          invoice_number: sale.invoice_number,
          invoice_date: sale.invoice_date,
          due_date: sale.due_date ?? undefined,
          customer_id: sale.customer_id ?? undefined,
          line_items: sale.line_items.map((item) => ({
            line_number: item.line_number,
            description: item.description,
            quantity: item.quantity,
            unit_price: item.unit_price,
            gst_rate: item.gst_rate ?? undefined,
            hsn_code: item.hsn_code ?? undefined,
          })),
          discount: sale.discount,
          tax: sale.tax,
          notes: sale.notes ?? undefined,
          place_of_supply: sale.place_of_supply ?? undefined,
        })
      )
      .catch((err) => setError(err instanceof Error ? err.message : t("sale.loadFailed")));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentBusinessId, getAccessToken, id]);

  async function handleSubmit(data: CreateSaleRequest) {
    if (!currentBusinessId) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const token = getAccessToken();
      await updateSale(token, currentBusinessId, id, data);
      router.push(`/app/sales/${id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("sale.saveFailed"));
      setIsSubmitting(false);
    }
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">{t("sales.edit")}</h1>
      <Card className="max-w-2xl">
        {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
        {initialValues ? (
          <SaleForm
            customers={customers}
            onSubmit={handleSubmit}
            isSubmitting={isSubmitting}
            initialValues={initialValues}
            submitLabel={t("saleForm.saveChanges")}
          />
        ) : (
          !error && (
            <div className="flex justify-center py-8">
              <Spinner />
            </div>
          )
        )}
      </Card>
    </div>
  );
}
