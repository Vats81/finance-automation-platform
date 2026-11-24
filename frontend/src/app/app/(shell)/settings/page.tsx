"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { FormField } from "@/components/ui/FormField";
import { errorMessage, InlineError } from "@/components/ui/InlineError";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { LanguageSwitcher } from "@/components/layout/LanguageSwitcher";
import { InstallAppButton } from "@/components/pwa/InstallAppButton";
import { startBillingPortalSession, startCheckoutSession } from "@/lib/api/billing";
import { changeBusinessPlan, completeOnboarding } from "@/lib/api/business";
import { getIntegrationsStatus } from "@/lib/api/integrations";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { CURRENCY_OPTIONS } from "@/lib/format";
import { GST_STATES, stateCodeFromGstin, stateName } from "@/lib/gst";
import { useT } from "@/lib/i18n/LanguageProvider";
import { MessageKey, messages } from "@/lib/i18n/messages";
import {
  inviteTeamMember,
  listTeamMembers,
  removeTeamMember,
  updateTeamMemberRole,
} from "@/lib/api/teamMembers";
import {
  BusinessPlan,
  BusinessRole,
  CompleteOnboardingRequest,
  PLAN_LIMITS,
  TeamMemberResponse,
} from "@/types/business";

const BUSINESS_ROLES: BusinessRole[] = ["owner", "admin", "accountant", "viewer"];
const BUSINESS_PLANS: BusinessPlan[] = ["free", "starter", "pro"];

const MEMBERSHIP_STATUS_TONE: Record<string, "success" | "warning" | "neutral"> = {
  active: "success",
  invited: "warning",
  removed: "neutral",
};

const PERSONAL_PLANS: BusinessPlan[] = ["free", "starter"];
const FREE_PERSONAL_BUDGETS = 5; // mirrors backend personal_finance/domain/rules.py
// A personal account is shared with a few people at most (backend PERSONAL_PLAN_LIMITS).
const PERSONAL_TEAM_LIMITS: Record<BusinessPlan, number> = { free: 2, starter: 5, pro: 5 };

export default function SettingsPage() {
  const { getAccessToken } = useLocalAuth();
  const { currentBusiness, firms, refresh } = useCurrentBusiness();
  const { t, lang } = useT();
  // A label for a value the server sends (a role, a status); anything unknown is shown as it came.
  const label = (prefix: string, value: string) =>
    `${prefix}.${value}` in messages ? t(`${prefix}.${value}` as MessageKey) : value;
  const [form, setForm] = useState<CompleteOnboardingRequest>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [members, setMembers] = useState<TeamMemberResponse[] | null>(null);
  const [selectedPlan, setSelectedPlan] = useState<BusinessPlan>("free");
  const [isChangingPlan, setIsChangingPlan] = useState(false);
  const [planError, setPlanError] = useState<string | null>(null);
  const [billingConnected, setBillingConnected] = useState(false);
  const [isRedirectingToBilling, setIsRedirectingToBilling] = useState(false);

  useEffect(() => {
    getIntegrationsStatus(getAccessToken())
      .then((status) => setBillingConnected(status.billing.connected))
      .catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleUpgrade(plan: BusinessPlan) {
    if (!currentBusiness) return;
    setIsRedirectingToBilling(true);
    setPlanError(null);
    try {
      const { checkout_url } = await startCheckoutSession(getAccessToken(), currentBusiness.business.id, {
        plan,
      });
      window.location.href = checkout_url;
    } catch (err) {
      setPlanError(err instanceof Error ? err.message : t("set.plan.checkoutFailed"));
      setIsRedirectingToBilling(false);
    }
  }

  async function handleManageBilling() {
    if (!currentBusiness) return;
    setIsRedirectingToBilling(true);
    setPlanError(null);
    try {
      const { portal_url } = await startBillingPortalSession(getAccessToken(), currentBusiness.business.id);
      window.location.href = portal_url;
    } catch (err) {
      setPlanError(err instanceof Error ? err.message : t("set.plan.portalFailed"));
      setIsRedirectingToBilling(false);
    }
  }

  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<BusinessRole>("viewer");
  const [isInviting, setIsInviting] = useState(false);
  const [inviteError, setInviteError] = useState<string | null>(null);

  const isOwner = currentBusiness?.role === "owner";
  const isPersonal = currentBusiness?.business.kind === "personal";
  // A personal account has two plans: Free and Plus (the second tier of a workspace).
  const planLabel = (plan: BusinessPlan) =>
    isPersonal ? (plan === "free" ? "Free" : "Plus") : PLAN_LIMITS[plan].label;
  const teamLimit = (plan: BusinessPlan) =>
    isPersonal ? PERSONAL_TEAM_LIMITS[plan] : PLAN_LIMITS[plan].maxTeamMembers;
  const canManageMembers = isOwner || currentBusiness?.role === "admin";

  const [membersError, setMembersError] = useState<string | null>(null);
  const [memberActionError, setMemberActionError] = useState<string | null>(null);

  const refreshMembers = async () => {
    if (!currentBusiness) return;
    const list = await listTeamMembers(getAccessToken(), currentBusiness.business.id);
    setMembers(list);
    setMembersError(null);
  };

  const loadMembers = () => {
    setMembers(null);
    setMembersError(null);
    refreshMembers().catch((err) => setMembersError(errorMessage(err)));
  };

  useEffect(() => {
    if (!currentBusiness) return;
    setSelectedPlan(currentBusiness.business.plan);
    loadMembers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentBusiness?.business.id]);

  async function handleChangePlan() {
    if (!currentBusiness) return;
    setIsChangingPlan(true);
    setPlanError(null);
    try {
      await changeBusinessPlan(getAccessToken(), currentBusiness.business.id, { plan: selectedPlan });
      await refresh();
    } catch (err) {
      setPlanError(err instanceof Error ? err.message : t("set.plan.changeFailed"));
    } finally {
      setIsChangingPlan(false);
    }
  }

  async function handleInvite(event: FormEvent) {
    event.preventDefault();
    if (!currentBusiness || !inviteEmail.trim()) return;
    setIsInviting(true);
    setInviteError(null);
    try {
      await inviteTeamMember(getAccessToken(), currentBusiness.business.id, {
        email: inviteEmail.trim(),
        role: inviteRole,
      });
      setInviteEmail("");
      await refreshMembers();
    } catch (err) {
      setInviteError(err instanceof Error ? err.message : t("set.team.inviteFailed"));
    } finally {
      setIsInviting(false);
    }
  }

  // Previously both of these did `.catch(() => undefined)`, so a rejected
  // removal or role change (e.g. a 403, or "can't remove the last owner")
  // looked like the click did nothing. Surface the server's message, then
  // refresh anyway so the table shows the real current state.
  async function runMemberAction(action: () => Promise<unknown>) {
    setMemberActionError(null);
    try {
      await action();
    } catch (err) {
      setMemberActionError(errorMessage(err, t("set.team.cantSave")));
    }
    await refreshMembers().catch((err) => setMembersError(errorMessage(err)));
  }

  async function handleRemove(membershipId: string) {
    if (!currentBusiness) return;
    await runMemberAction(() =>
      removeTeamMember(getAccessToken(), currentBusiness.business.id, membershipId)
    );
  }

  async function handleRoleChange(membershipId: string, role: BusinessRole) {
    if (!currentBusiness) return;
    await runMemberAction(() =>
      updateTeamMemberRole(getAccessToken(), currentBusiness.business.id, membershipId, { role })
    );
  }

  useEffect(() => {
    if (!currentBusiness) return;
    const { business } = currentBusiness;
    setForm({
      business_type: business.business_type ?? undefined,
      industry: business.industry ?? undefined,
      country: business.country ?? undefined,
      currency: business.currency,
      financial_year_start_month: business.financial_year_start_month,
      gst_registered: business.gst_registered,
      number_of_branches: business.number_of_branches,
      whatsapp_number: business.whatsapp_number ?? undefined,
      contact_email: business.contact_email ?? undefined,
      gstin: business.gstin ?? undefined,
      address_line: business.address_line ?? undefined,
      city: business.city ?? undefined,
      state_code: business.state_code ?? undefined,
      pincode: business.pincode ?? undefined,
      phone: business.phone ?? undefined,
      upi_id: business.upi_id ?? undefined,
    });
  }, [currentBusiness]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!currentBusiness) return;
    setIsSubmitting(true);
    setError(null);
    setSaved(false);
    try {
      const token = getAccessToken();
      await completeOnboarding(token, currentBusiness.business.id, form);
      await refresh();
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("set.saveFailed"));
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!currentBusiness) return null;

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">{t("set.title")}</h1>

      <Card className="max-w-2xl">
        <h2 className="mb-1 text-lg font-semibold">{isPersonal ? t("set.profilePersonal") : t("set.profileBusiness")}</h2>
        <p className="mb-6 text-sm text-slate-500">{currentBusiness.business.name}</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <p className="text-sm text-red-600">{error}</p>}
          {saved && <p className="text-sm text-emerald-600">{t("set.saved")}</p>}

          {!isPersonal && (
            <>
              <FormField label={t("set.businessType")}>
                <Input
                  value={form.business_type ?? ""}
                  onChange={(e) => setForm({ ...form, business_type: e.target.value })}
                />
              </FormField>
              <FormField label={t("set.industry")}>
                <Input
                  value={form.industry ?? ""}
                  onChange={(e) => setForm({ ...form, industry: e.target.value })}
                />
              </FormField>
            </>
          )}
          <div className="grid grid-cols-2 gap-4">
            <FormField label={t("set.country")}>
              <Input
                value={form.country ?? ""}
                onChange={(e) => setForm({ ...form, country: e.target.value })}
              />
            </FormField>
            <FormField label={t("set.currency")}>
              <Select
                value={form.currency ?? "USD"}
                onChange={(e) => setForm({ ...form, currency: e.target.value })}
              >
                {CURRENCY_OPTIONS.map(({ code }) => (
                  <option key={code} value={code}>
                    {t(`set.currency.${code}` as MessageKey)}
                  </option>
                ))}
              </Select>
            </FormField>
          </div>
          {!isPersonal && (
            <div className="grid grid-cols-2 gap-4">
              <FormField label={t("set.branches")}>
                <Input
                  type="number"
                  min={1}
                  value={form.number_of_branches ?? 1}
                  onChange={(e) => setForm({ ...form, number_of_branches: Number(e.target.value) })}
                />
              </FormField>
              <FormField label={t("set.whatsapp")}>
                <Input
                  value={form.whatsapp_number ?? ""}
                  onChange={(e) => setForm({ ...form, whatsapp_number: e.target.value })}
                />
              </FormField>
            </div>
          )}
          {!isPersonal && (
            <div className="space-y-4 border-t border-slate-200 pt-4">
              <div>
                <h3 className="text-base font-semibold">{t("set.inv.title")}</h3>
                <p className="text-sm text-slate-500">
                  {t("set.inv.text")}
                </p>
              </div>
              <FormField label={t("set.inv.gstin")}>
                <Input
                  maxLength={15}
                  placeholder={t("set.inv.gstinHint")}
                  value={form.gstin ?? ""}
                  onChange={(e) => {
                    const gstin = e.target.value.toUpperCase();
                    const state = stateCodeFromGstin(gstin);
                    setForm({ ...form, gstin, ...(state ? { state_code: state } : {}) });
                  }}
                />
              </FormField>
              <FormField label={t("set.inv.address")}>
                <Input
                  maxLength={255}
                  placeholder={t("set.inv.addressHint")}
                  value={form.address_line ?? ""}
                  onChange={(e) => setForm({ ...form, address_line: e.target.value })}
                />
              </FormField>
              <div className="grid grid-cols-2 gap-4">
                <FormField label={t("set.inv.city")}>
                  <Input
                    maxLength={120}
                    value={form.city ?? ""}
                    onChange={(e) => setForm({ ...form, city: e.target.value })}
                  />
                </FormField>
                <FormField label={t("set.inv.pin")}>
                  <Input
                    inputMode="numeric"
                    maxLength={6}
                    value={form.pincode ?? ""}
                    onChange={(e) => setForm({ ...form, pincode: e.target.value.replace(/\D/g, "") })}
                  />
                </FormField>
              </div>
              <FormField label={t("set.inv.state")}>
                <Select
                  value={form.state_code ?? ""}
                  onChange={(e) => setForm({ ...form, state_code: e.target.value })}
                >
                  <option value="">{t("set.inv.chooseState")}</option>
                  {GST_STATES.map((s) => (
                    <option key={s.code} value={s.code}>
                      {stateName(s.code, lang)} ({s.code})
                    </option>
                  ))}
                </Select>
              </FormField>
              <div className="grid grid-cols-2 gap-4">
                <FormField label={t("set.inv.phone")}>
                  <Input
                    maxLength={32}
                    value={form.phone ?? ""}
                    onChange={(e) => setForm({ ...form, phone: e.target.value })}
                  />
                </FormField>
                <FormField label={t("set.inv.upi")}>
                  <Input
                    maxLength={100}
                    placeholder="name@bank"
                    value={form.upi_id ?? ""}
                    onChange={(e) => setForm({ ...form, upi_id: e.target.value })}
                  />
                </FormField>
              </div>
            </div>
          )}
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? t("common.saving") : t("set.saveChanges")}
          </Button>
        </form>
      </Card>

      <Card className="mt-6 max-w-2xl">
        <h2 className="mb-1 text-lg font-semibold">{t("set.plan.title")}</h2>
        <p className="mb-4 text-sm text-slate-500">
          {t("set.plan.summary", {
            plan: planLabel(currentBusiness.business.plan),
            used: members ? members.filter((m) => m.status === "active").length : "…",
            limit: teamLimit(currentBusiness.business.plan),
            unit: isPersonal ? t("set.plan.people") : t("set.plan.teamMembers"),
          })}
          {isPersonal && currentBusiness.business.plan === "free"
            ? t("set.plan.budgetsUpTo", { n: FREE_PERSONAL_BUDGETS })
            : isPersonal
              ? t("set.plan.budgetsUnlimited")
              : t("set.plan.end")}
        </p>
        {planError && <p className="mb-3 text-sm text-red-600">{planError}</p>}
        {isOwner ? (
          billingConnected ? (
            currentBusiness.business.plan === "free" ? (
              <div className="flex gap-3">
                {(isPersonal ? (["starter"] as BusinessPlan[]) : (["starter", "pro"] as BusinessPlan[])).map(
                  (plan) => (
                    <Button key={plan} onClick={() => handleUpgrade(plan)} disabled={isRedirectingToBilling}>
                      {isRedirectingToBilling ? t("set.plan.redirecting") : t("set.plan.upgrade", { plan: planLabel(plan) })}
                    </Button>
                  )
                )}
              </div>
            ) : (
              <Button onClick={handleManageBilling} disabled={isRedirectingToBilling}>
                {isRedirectingToBilling ? t("set.plan.redirecting") : t("set.plan.manageBilling")}
              </Button>
            )
          ) : (
            <div className="flex items-end gap-3">
              <FormField label={t("set.plan.change")}>
                <Select
                  value={selectedPlan}
                  onChange={(e) => setSelectedPlan(e.target.value as BusinessPlan)}
                >
                  {(isPersonal ? PERSONAL_PLANS : BUSINESS_PLANS).map((plan) => (
                    <option key={plan} value={plan}>
                      {planLabel(plan)} ({teamLimit(plan)} {isPersonal ? t("set.plan.people") : t("set.plan.members")})
                    </option>
                  ))}
                </Select>
              </FormField>
              <Button
                onClick={handleChangePlan}
                disabled={isChangingPlan || selectedPlan === currentBusiness.business.plan}
              >
                {isChangingPlan ? t("common.saving") : t("set.plan.change")}
              </Button>
            </div>
          )
        ) : (
          <p className="text-xs text-slate-400">{t("set.plan.ownerOnly")}</p>
        )}
        {!billingConnected && (
          <p className="mt-2 text-xs text-slate-400">
            {t("set.plan.beta")}
          </p>
        )}
      </Card>

      <Card className="mt-6 max-w-2xl">
        <h2 className="mb-4 text-lg font-semibold">{t("set.team.title")}</h2>

        {memberActionError && <p className="mb-3 text-sm text-red-600">{memberActionError}</p>}
        {membersError ? (
          <div className="mb-4">
            <InlineError message={membersError} onRetry={loadMembers} />
          </div>
        ) : !members ? (
          <p className="text-sm text-slate-500">{t("common.loading")}</p>
        ) : (
          <table className="mb-4 w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-slate-500">
                <th className="py-2 pr-4 font-medium">{t("common.name")}</th>
                <th className="py-2 pr-4 font-medium">{t("common.email")}</th>
                <th className="py-2 pr-4 font-medium">{t("set.team.role")}</th>
                <th className="py-2 pr-4 font-medium">{t("set.team.status")}</th>
                {canManageMembers && <th className="py-2 pr-4 font-medium">{t("set.team.actions")}</th>}
              </tr>
            </thead>
            <tbody>
              {members.map((member) => {
                const isOwnerRow = member.user_id === currentBusiness.business.owner_user_id;
                return (
                  <tr key={member.membership_id} className="border-b border-slate-100">
                    <td className="py-2 pr-4">{member.display_name}</td>
                    <td className="py-2 pr-4">{member.email}</td>
                    <td className="py-2 pr-4">
                      {canManageMembers && !isOwnerRow && member.status === "active" ? (
                        <Select
                          value={member.role}
                          onChange={(e) =>
                            handleRoleChange(member.membership_id, e.target.value as BusinessRole)
                          }
                        >
                          {BUSINESS_ROLES.filter((r) => r !== "owner").map((role) => (
                            <option key={role} value={role}>
                              {label("set.role", role)}
                            </option>
                          ))}
                        </Select>
                      ) : (
                        label("set.role", member.role)
                      )}
                    </td>
                    <td className="py-2 pr-4">
                      <Badge tone={MEMBERSHIP_STATUS_TONE[member.status] ?? "neutral"}>{label("set.member", member.status)}</Badge>
                    </td>
                    {canManageMembers && (
                      <td className="py-2 pr-4">
                        {!isOwnerRow && member.status === "active" && (
                          <Button variant="danger" onClick={() => handleRemove(member.membership_id)}>
                            {t("set.team.remove")}
                          </Button>
                        )}
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}

        {canManageMembers && (
          <>
          {inviteError && <p className="mb-2 text-sm text-red-600">{inviteError}</p>}
          <form onSubmit={handleInvite} className="flex items-end gap-3">
            <FormField label={t("set.team.inviteByEmail")}>
              <Input
                type="email"
                required
                placeholder="teammate@example.com"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
              />
            </FormField>
            <FormField label={t("set.team.role")}>
              <Select value={inviteRole} onChange={(e) => setInviteRole(e.target.value as BusinessRole)}>
                {BUSINESS_ROLES.filter((r) => r !== "owner").map((role) => (
                  <option key={role} value={role}>
                    {label("set.role", role)}
                  </option>
                ))}
              </Select>
            </FormField>
            <Button type="submit" disabled={isInviting}>
              {isInviting ? t("set.team.inviting") : t("set.team.invite")}
            </Button>
          </form>
          </>
        )}
        <p className="mt-3 text-xs text-slate-400">
          {t("set.team.accountOnly")}
        </p>
      </Card>

      {!isPersonal && (
        <Card className="mt-6 max-w-2xl">
          <h2 className="mb-1 text-lg font-semibold">{t("set.firm.title")}</h2>
          {firms.length > 0 ? (
            <>
              <p className="mb-4 text-sm text-slate-500">
                {t("set.firm.member", { names: firms.map((f) => f.name).join(", ") })}
              </p>
              <Link href="/app/firm">
                <Button variant="secondary">{t("set.firm.open")}</Button>
              </Link>
            </>
          ) : (
            <>
              <p className="mb-4 text-sm text-slate-500">
                {t("set.firm.pitch")}
              </p>
              <Link href="/app/firm/new">
                <Button variant="secondary">{t("set.firm.setup")}</Button>
              </Link>
            </>
          )}
        </Card>
      )}

      <Card className="mt-6 max-w-2xl">
        <h2 className="mb-1 text-lg font-semibold">{t("set.language.title")}</h2>
        <p className="mb-4 text-sm text-slate-500">{t("set.language.text")}</p>
        <LanguageSwitcher />
      </Card>

      <Card className="mt-6 max-w-2xl">
        <h2 className="mb-1 text-lg font-semibold">{t("set.install.title")}</h2>
        <p className="mb-4 text-sm text-slate-500">
          {t("set.install.text")}
        </p>
        <InstallAppButton />
        <p className="mt-2 text-xs text-slate-400">
          {t("set.install.ios")}
        </p>
      </Card>
    </div>
  );
}
