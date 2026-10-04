"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { errorMessage, InlineError } from "@/components/ui/InlineError";
import { listContactRequests } from "@/lib/api/admin";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { ContactRequestsResponse } from "@/types/admin";

export default function AdminContactRequestsPage() {
  const { getAccessToken } = useLocalAuth();
  const [data, setData] = useState<ContactRequestsResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [retryToken, setRetryToken] = useState(0);

  useEffect(() => {
    setData(null);
    setLoadError(null);
    listContactRequests(getAccessToken())
      .then(setData)
      .catch((err) => setLoadError(errorMessage(err)));
  }, [getAccessToken, retryToken]);

  return (
    <div>
      <h1 className="mb-1 text-2xl font-semibold">Demo requests</h1>
      <p className="mb-6 text-sm text-slate-500">
        Submitted from the landing page, newest first. &ldquo;Emailed&rdquo; shows whether a
        notification actually went out; set CONTACT_INBOX_EMAIL to be emailed on each request.
      </p>

      <Card>
        {loadError ? (
          <InlineError message={loadError} onRetry={() => setRetryToken((n) => n + 1)} />
        ) : !data ? (
          <p className="text-sm text-slate-500">Loading...</p>
        ) : data.items.length === 0 ? (
          <p className="text-sm text-slate-500">No demo requests yet.</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {data.items.map((request) => (
              <li key={request.id} className="py-4 first:pt-0 last:pb-0">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="text-sm font-medium text-slate-900">
                    {request.name}{" "}
                    <a href={`mailto:${request.email}`} className="font-normal text-brand-600 underline">
                      {request.email}
                    </a>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-slate-500">
                    <Badge tone={request.notified ? "success" : "neutral"}>
                      {request.notified ? "emailed" : "not emailed"}
                    </Badge>
                    {new Date(request.created_at).toLocaleString("en-US")}
                  </div>
                </div>
                {request.business_name && (
                  <div className="mt-1 text-sm text-slate-600">Business: {request.business_name}</div>
                )}
                {request.message && (
                  <p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">{request.message}</p>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
