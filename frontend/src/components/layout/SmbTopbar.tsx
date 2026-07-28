"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { getNotifications } from "@/lib/api/notifications";
import { MyBusinessResponse } from "@/types/business";

export function SmbTopbar({
  onMenuClick,
  businesses,
  currentBusinessId,
  onBusinessChange,
}: {
  onMenuClick: () => void;
  businesses: MyBusinessResponse[];
  currentBusinessId: string | null;
  onBusinessChange: (businessId: string) => void;
}) {
  const { user, logout, getAccessToken } = useLocalAuth();
  const [notificationCount, setNotificationCount] = useState(0);

  useEffect(() => {
    if (!currentBusinessId) return;
    getNotifications(getAccessToken(), currentBusinessId)
      .then((res) => setNotificationCount(res.count))
      .catch(() => undefined);
  }, [currentBusinessId, getAccessToken]);

  return (
    <header className="flex h-16 items-center justify-between gap-4 border-b border-slate-200 bg-white px-4 sm:px-6">
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuClick}
          aria-label="Open menu"
          className="rounded-md p-2 text-slate-600 hover:bg-slate-100 md:hidden"
        >
          ☰
        </button>

        {businesses.length > 0 && (
          <Select
            value={currentBusinessId ?? ""}
            onChange={(e) => onBusinessChange(e.target.value)}
            className="max-w-[10rem] sm:max-w-xs"
            aria-label="Select business"
          >
            {businesses.map(({ business }) => (
              <option key={business.id} value={business.id}>
                {business.name}
              </option>
            ))}
          </Select>
        )}
      </div>

      <div className="flex items-center gap-2 sm:gap-4">
        <button
          className="hidden rounded-md p-2 text-slate-500 hover:bg-slate-100 sm:block"
          aria-label="Search"
          title="Search (coming soon)"
        >
          🔍
        </button>
        <Link
          href="/app/automations"
          className="relative rounded-md p-2 text-slate-500 hover:bg-slate-100"
          aria-label="Notifications"
          title="Notifications & Alerts"
        >
          🔔
          {notificationCount > 0 && (
            <span className="absolute right-0.5 top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-600 px-1 text-[10px] font-medium text-white">
              {notificationCount > 99 ? "99+" : notificationCount}
            </span>
          )}
        </Link>
        {user && (
          <div className="hidden text-right text-sm sm:block">
            <div className="font-medium">{user.display_name}</div>
          </div>
        )}
        <Button variant="secondary" onClick={logout}>
          Sign out
        </Button>
      </div>
    </header>
  );
}
