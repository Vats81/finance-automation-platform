"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { AuthGuard } from "@/components/layout/AuthGuard";
import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { activateVendor, getVendor, uploadW9Document } from "@/lib/api/vendors";
import { useAuth } from "@/lib/auth/useAuth";
import { VendorResponse } from "@/types/vendor";

function VendorDetailContent() {
  const { id } = useParams<{ id: string }>();
  const { getAccessToken } = useAuth();
  const [vendor, setVendor] = useState<VendorResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isActivating, setIsActivating] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  const load = useCallback(async () => {
    const token = await getAccessToken();
    const data = await getVendor(token, id);
    setVendor(data);
  }, [getAccessToken, id]);

  useEffect(() => {
    load().catch((err) => setError(err instanceof Error ? err.message : "Failed to load vendor"));
  }, [load]);

  async function handleActivate() {
    setIsActivating(true);
    setError(null);
    try {
      const token = await getAccessToken();
      const updated = await activateVendor(token, id);
      setVendor(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to activate vendor");
    } finally {
      setIsActivating(false);
    }
  }

  async function handleW9Upload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setIsUploading(true);
    setError(null);
    try {
      const token = await getAccessToken();
      const updated = await uploadW9Document(token, id, file);
      setVendor(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to upload W-9");
    } finally {
      setIsUploading(false);
      event.target.value = "";
    }
  }

  return (
    <div className="flex">
      <Sidebar />
      <div className="flex-1">
        <Topbar user={null} />
        <main className="p-8">
          {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
          {!vendor ? (
            <div className="flex justify-center py-8">
              <Spinner />
            </div>
          ) : (
            <>
              <div className="mb-6 flex items-center justify-between">
                <div>
                  <h1 className="text-2xl font-semibold">{vendor.legal_name}</h1>
                  <Badge tone={vendor.status === "active" ? "success" : "warning"}>
                    {vendor.status.replace("_", " ")}
                  </Badge>
                </div>
                {vendor.status !== "active" && (
                  <Button
                    onClick={handleActivate}
                    disabled={!vendor.has_w9_on_file || isActivating}
                    title={!vendor.has_w9_on_file ? "W-9 must be on file before activation" : undefined}
                  >
                    {isActivating ? "Activating…" : "Activate vendor"}
                  </Button>
                )}
              </div>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Card>
                  <h2 className="mb-3 text-sm font-semibold text-slate-500">Contact</h2>
                  <p className="text-sm">{vendor.contact_email}</p>
                </Card>
                <Card>
                  <h2 className="mb-3 text-sm font-semibold text-slate-500">Tax ID</h2>
                  <p className="font-mono text-sm">{vendor.tax_id_masked}</p>
                </Card>
                <Card>
                  <h2 className="mb-3 text-sm font-semibold text-slate-500">Address</h2>
                  <p className="text-sm">
                    {vendor.address.street}, {vendor.address.city}, {vendor.address.state}{" "}
                    {vendor.address.postal_code}, {vendor.address.country}
                  </p>
                </Card>
                <Card>
                  <h2 className="mb-3 text-sm font-semibold text-slate-500">W-9 document</h2>
                  <p className="mb-3 text-sm">{vendor.has_w9_on_file ? "On file" : "Not uploaded"}</p>
                  <label className="inline-block cursor-pointer text-sm font-medium text-brand-700 hover:underline">
                    {isUploading ? "Uploading…" : vendor.has_w9_on_file ? "Replace file" : "Upload W-9"}
                    <input
                      type="file"
                      accept="application/pdf,image/*"
                      className="hidden"
                      disabled={isUploading}
                      onChange={handleW9Upload}
                    />
                  </label>
                </Card>
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}

export default function VendorDetailPage() {
  return (
    <AuthGuard>
      <VendorDetailContent />
    </AuthGuard>
  );
}
