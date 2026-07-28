"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { AuthGuard } from "@/components/layout/AuthGuard";
import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";
import { Card } from "@/components/ui/Card";
import { VendorForm } from "@/components/vendors/VendorForm";
import { createVendor } from "@/lib/api/vendors";
import { useAuth } from "@/lib/auth/useAuth";
import { CreateVendorRequest } from "@/types/vendor";

function NewVendorContent() {
  const { getAccessToken } = useAuth();
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(data: CreateVendorRequest) {
    setIsSubmitting(true);
    setError(null);
    try {
      const token = await getAccessToken();
      const vendor = await createVendor(token, data);
      router.push(`/vendors/${vendor.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create vendor");
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex">
      <Sidebar />
      <div className="flex-1">
        <Topbar user={null} />
        <main className="p-8">
          <h1 className="mb-6 text-2xl font-semibold">New vendor</h1>
          <Card className="max-w-lg">
            {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
            <VendorForm onSubmit={handleSubmit} isSubmitting={isSubmitting} />
          </Card>
        </main>
      </div>
    </div>
  );
}

export default function NewVendorPage() {
  return (
    <AuthGuard>
      <NewVendorContent />
    </AuthGuard>
  );
}
