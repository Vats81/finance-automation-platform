"use client";

import { Button } from "@/components/ui/Button";
import { useAuth } from "@/lib/auth/useAuth";
import { UserResponse } from "@/types/user";

export function Topbar({ user }: { user: UserResponse | null }) {
  const { logout } = useAuth();

  return (
    <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-6">
      <div />
      <div className="flex items-center gap-4">
        {user && (
          <div className="text-right text-sm">
            <div className="font-medium">{user.display_name}</div>
            <div className="text-xs uppercase tracking-wide text-slate-500">
              {user.role.replace("_", " ")}
            </div>
          </div>
        )}
        <Button variant="secondary" onClick={logout}>
          Sign out
        </Button>
      </div>
    </header>
  );
}
