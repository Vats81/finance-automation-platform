"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AuthGuard } from "@/components/layout/AuthGuard";
import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { VendorTable } from "@/components/vendors/VendorTable";
import { fetchMe } from "@/lib/api/identity";
import { listVendors } from "@/lib/api/vendors";
import { useAuth } from "@/lib/auth/useAuth";
import { UserResponse } from "@/types/user";
import { VendorResponse } from "@/types/vendor";

function VendorsContent() {
  const { getAccessToken } = useAuth();
  const [user, setUser] = useState<UserResponse | null>(null);
  const [vendors, setVendors] = useState<VendorResponse[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAccessToken().then((token) => {
      fetchMe(token).then(setUser).catch(() => {});
      listVendors(token)
        .then((page) => setVendors(page.items))
        .catch((err) => setError(err instanceof Error ? err.message : "Failed to load vendors"));
    });
  }, [getAccessToken]);

  return (
    <div className="flex">
      <Sidebar />
      <div className="flex-1">
        <Topbar user={user} />
        <main className="p-8">
          <div className="mb-6 flex items-center justify-between">
            <h1 className="text-2xl font-semibold">Vendors</h1>
            <Link href="/vendors/new">
              <Button>New vendor</Button>
            </Link>
          </div>
          <Card>
            {error && <p className="text-sm text-red-600">{error}</p>}
            {!vendors && !error ? (
              <div className="flex justify-center py-8">
                <Spinner />
              </div>
            ) : (
              <VendorTable vendors={vendors ?? []} />
            )}
          </Card>
        </main>
      </div>
    </div>
  );
}

export default function VendorsPage() {
  return (
    <AuthGuard>
      <VendorsContent />
    </AuthGuard>
  );
}
