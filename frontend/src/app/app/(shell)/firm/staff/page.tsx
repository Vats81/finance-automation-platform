"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { errorMessage, InlineError } from "@/components/ui/InlineError";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import {
  changeFirmStaffRole,
  inviteFirmStaff,
  listFirmAuditEvents,
  listFirmStaff,
  removeFirmStaff,
} from "@/lib/api/firms";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { ASSIGNABLE_FIRM_ROLES, FirmAuditEvent, FirmRole, FirmStaffResponse } from "@/types/firm";
import { useT } from "@/lib/i18n/LanguageProvider";
import { MessageKey } from "@/lib/i18n/messages";

function describeAction(action: string): MessageKey | null {
  if (action === "POST /firms") return "firm.action.created";
  if (action.endsWith("/staff/{membership_id}/remove")) return "firm.action.removed";
  if (action.endsWith("/staff/{membership_id}")) return "firm.action.roleChanged";
  if (action.endsWith("/staff")) return "firm.action.invited";
  if (action.endsWith("/release")) return "firm.action.released";
  if (action.endsWith("/clients")) return "firm.action.addedClient";
  return null;
}

export default function FirmStaffPage() {
  const { t, label, lang } = useT();
  const { getAccessToken, user } = useLocalAuth();
  const { currentFirm } = useCurrentBusiness();
  const [staff, setStaff] = useState<FirmStaffResponse[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<FirmRole>("accountant");
  const [isInviting, setIsInviting] = useState(false);

  const canManage = currentFirm?.my_role === "owner" || currentFirm?.my_role === "admin";
  const [activity, setActivity] = useState<FirmAuditEvent[] | null>(null);

  useEffect(() => {
    if (!currentFirm || !canManage) return;
    listFirmAuditEvents(getAccessToken(), currentFirm.id)
      .then(setActivity)
      .catch(() => setActivity([]));
  }, [currentFirm, canManage, getAccessToken, staff]);

  const load = useCallback(() => {
    if (!currentFirm) return;
    setLoadError(null);
    listFirmStaff(getAccessToken(), currentFirm.id)
      .then(setStaff)
      .catch((err) => setLoadError(errorMessage(err)));
  }, [currentFirm, getAccessToken]);

  useEffect(() => {
    setStaff(null);
    load();
  }, [load]);

  async function handleInvite(event: FormEvent) {
    event.preventDefault();
    if (!currentFirm) return;
    setIsInviting(true);
    setActionError(null);
    try {
      await inviteFirmStaff(getAccessToken(), currentFirm.id, { email, role });
      setEmail("");
      load();
    } catch (err) {
      setActionError(errorMessage(err, t("s.the_invitation_couldn_t_be_saved")));
    } finally {
      setIsInviting(false);
    }
  }

  async function handleRole(member: FirmStaffResponse, newRole: FirmRole) {
    if (!currentFirm) return;
    setActionError(null);
    try {
      await changeFirmStaffRole(getAccessToken(), currentFirm.id, member.membership_id, newRole);
      load();
    } catch (err) {
      setActionError(errorMessage(err, t("s.the_role_couldn_t_be_changed")));
    }
  }

  async function handleRemove(member: FirmStaffResponse) {
    if (!currentFirm) return;
    if (!window.confirm(t("x.removeStaff", { name: member.display_name }))) {
      return;
    }
    setActionError(null);
    try {
      await removeFirmStaff(getAccessToken(), currentFirm.id, member.membership_id);
      load();
    } catch (err) {
      setActionError(errorMessage(err, t("s.the_person_couldn_t_be_removed")));
    }
  }

  if (!currentFirm) {
    return <p className="text-sm text-slate-500">{t("s.you_are_not_part_of_an_accounting")}</p>;
  }

  const active = staff?.filter((s) => s.status === "active") ?? [];

  return (
    <div>
      <h1 className="mb-1 text-2xl font-semibold">{t("s.firm_staff")}</h1>
      <p className="mb-6 text-sm text-slate-500">
        {t("firm.staffIntro", { name: currentFirm.name })}
      </p>

      {actionError && <p className="mb-3 text-sm text-red-600">{actionError}</p>}

      {canManage && (
        <Card className="mb-6">
          <form onSubmit={handleInvite} className="grid gap-3 sm:grid-cols-[1fr_12rem_auto] sm:items-end">
            <label className="block text-sm">
              <span className="mb-1 block font-medium">{t("s.add_a_colleague_by_email")}</span>
              <Input
                required
                type="email"
                placeholder={t("s.they_must_already_have_an_account")}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium">{t("set.team.role")}</span>
              <Select value={role} onChange={(e) => setRole(e.target.value as FirmRole)}>
                {ASSIGNABLE_FIRM_ROLES.map((r) => (
                  <option key={r} value={r}>
                    {label("set.role", r)}
                  </option>
                ))}
              </Select>
            </label>
            <Button type="submit" disabled={isInviting}>
              {isInviting ? t("s.adding") : t("s.add")}
            </Button>
          </form>
          <p className="mt-2 text-xs text-slate-500">{t(`firm.roleHelp.${role}` as MessageKey)}</p>
        </Card>
      )}

      <Card>
        {loadError ? (
          <InlineError message={loadError} onRetry={load} />
        ) : !staff ? (
          <p className="text-sm text-slate-500">{t("common.loading")}</p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                <th className="py-2 pr-4">{t("common.name")}</th>
                <th className="py-2 pr-4">{t("common.email")}</th>
                <th className="py-2 pr-4">{t("set.team.role")}</th>
                <th className="py-2 pr-4">
                  <span className="sr-only">{t("set.team.actions")}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {active.map((member) => {
                const isOwner = member.role === "owner";
                const isSelf = member.user_id === user?.id;
                return (
                  <tr key={member.membership_id} className="border-b border-slate-100 last:border-0">
                    <td className="py-2 pr-4 font-medium">{member.display_name}</td>
                    <td className="py-2 pr-4 text-slate-600">{member.email}</td>
                    <td className="py-2 pr-4">
                      {canManage && !isOwner && !isSelf ? (
                        <Select
                          aria-label={t("firm.roleFor", { name: member.display_name })}
                          value={member.role}
                          onChange={(e) => handleRole(member, e.target.value as FirmRole)}
                          className="max-w-[10rem]"
                        >
                          {ASSIGNABLE_FIRM_ROLES.map((r) => (
                            <option key={r} value={r}>
                              {label("set.role", r)}
                            </option>
                          ))}
                        </Select>
                      ) : (
                        <Badge tone={isOwner ? "success" : "neutral"}>{label("set.role", member.role)}</Badge>
                      )}
                    </td>
                    <td className="py-2 pr-4">
                      {canManage && !isOwner && (
                        <Button variant="ghost" onClick={() => handleRemove(member)}>
                          {t("set.team.remove")}
                        </Button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </Card>

      {canManage && (
        <Card className="mt-6">
          <h2 className="mb-1 text-lg font-semibold">{t("s.recent_activity")}</h2>
          <p className="mb-4 text-sm text-slate-500">
            {t("s.who_changed_the_firm_s_staff_and_c")}
          </p>
          {!activity ? (
            <p className="text-sm text-slate-500">{t("common.loading")}</p>
          ) : activity.length === 0 ? (
            <p className="text-sm text-slate-500">{t("s.nothing_yet")}</p>
          ) : (
            <ul className="divide-y divide-slate-100 text-sm">
              {activity.map((event) => {
                const who = staff?.find((s) => s.user_id === event.actor_user_id);
                return (
                  <li key={event.id} className="flex flex-wrap justify-between gap-2 py-2">
                    <span>
                      <span className="font-medium">{who?.display_name ?? t("s.someone")}</span>{" "}
                      <span className="text-slate-500">({label("set.role", event.actor_role)})</span> ·{" "}
                      {(() => {
                        const key = describeAction(event.action);
                        return key ? t(key) : event.action;
                      })()}
                    </span>
                    <span className="text-slate-400">{new Date(event.occurred_at).toLocaleString(lang === "hi" ? "hi-IN" : undefined)}</span>
                  </li>
                );
              })}
            </ul>
          )}
        </Card>
      )}
    </div>
  );
}
