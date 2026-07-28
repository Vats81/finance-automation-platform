"use client";

import { FormEvent, useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { FormField } from "@/components/ui/FormField";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { changeBusinessPlan, completeOnboarding } from "@/lib/api/business";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
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

export default function SettingsPage() {
  const { getAccessToken } = useLocalAuth();
  const { currentBusiness, refresh } = useCurrentBusiness();
  const [form, setForm] = useState<CompleteOnboardingRequest>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [members, setMembers] = useState<TeamMemberResponse[] | null>(null);
  const [selectedPlan, setSelectedPlan] = useState<BusinessPlan>("free");
  const [isChangingPlan, setIsChangingPlan] = useState(false);
  const [planError, setPlanError] = useState<string | null>(null);

  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<BusinessRole>("viewer");
  const [isInviting, setIsInviting] = useState(false);
  const [inviteError, setInviteError] = useState<string | null>(null);

  const isOwner = currentBusiness?.role === "owner";
  const canManageMembers = isOwner || currentBusiness?.role === "admin";

  const refreshMembers = async () => {
    if (!currentBusiness) return;
    const list = await listTeamMembers(getAccessToken(), currentBusiness.business.id);
    setMembers(list);
  };

  useEffect(() => {
    if (!currentBusiness) return;
    setSelectedPlan(currentBusiness.business.plan);
    refreshMembers().catch(() => undefined);
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
      setPlanError(err instanceof Error ? err.message : "Failed to change plan");
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
      setInviteError(err instanceof Error ? err.message : "Failed to invite team member");
    } finally {
      setIsInviting(false);
    }
  }

  async function handleRemove(membershipId: string) {
    if (!currentBusiness) return;
    await removeTeamMember(getAccessToken(), currentBusiness.business.id, membershipId).catch(() => undefined);
    await refreshMembers();
  }

  async function handleRoleChange(membershipId: string, role: BusinessRole) {
    if (!currentBusiness) return;
    await updateTeamMemberRole(getAccessToken(), currentBusiness.business.id, membershipId, { role }).catch(
      () => undefined
    );
    await refreshMembers();
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
      setError(err instanceof Error ? err.message : "Failed to save changes");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!currentBusiness) return null;

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">Settings</h1>

      <Card className="max-w-2xl">
        <h2 className="mb-1 text-lg font-semibold">Business profile</h2>
        <p className="mb-6 text-sm text-slate-500">{currentBusiness.business.name}</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <p className="text-sm text-red-600">{error}</p>}
          {saved && <p className="text-sm text-emerald-600">Saved.</p>}

          <FormField label="Business type">
            <Input
              value={form.business_type ?? ""}
              onChange={(e) => setForm({ ...form, business_type: e.target.value })}
            />
          </FormField>
          <FormField label="Industry">
            <Input
              value={form.industry ?? ""}
              onChange={(e) => setForm({ ...form, industry: e.target.value })}
            />
          </FormField>
          <div className="grid grid-cols-2 gap-4">
            <FormField label="Country">
              <Input
                value={form.country ?? ""}
                onChange={(e) => setForm({ ...form, country: e.target.value })}
              />
            </FormField>
            <FormField label="Currency">
              <Select
                value={form.currency ?? "USD"}
                onChange={(e) => setForm({ ...form, currency: e.target.value })}
              >
                {["USD", "EUR", "GBP", "INR", "AUD", "CAD"].map((code) => (
                  <option key={code} value={code}>
                    {code}
                  </option>
                ))}
              </Select>
            </FormField>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <FormField label="Number of branches">
              <Input
                type="number"
                min={1}
                value={form.number_of_branches ?? 1}
                onChange={(e) => setForm({ ...form, number_of_branches: Number(e.target.value) })}
              />
            </FormField>
            <FormField label="WhatsApp number">
              <Input
                value={form.whatsapp_number ?? ""}
                onChange={(e) => setForm({ ...form, whatsapp_number: e.target.value })}
              />
            </FormField>
          </div>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Saving…" : "Save changes"}
          </Button>
        </form>
      </Card>

      <Card className="mt-6 max-w-2xl">
        <h2 className="mb-1 text-lg font-semibold">Plan</h2>
        <p className="mb-4 text-sm text-slate-500">
          {PLAN_LIMITS[currentBusiness.business.plan].label} plan —{" "}
          {members ? members.filter((m) => m.status === "active").length : "…"} of{" "}
          {PLAN_LIMITS[currentBusiness.business.plan].maxTeamMembers} team members used.
        </p>
        {planError && <p className="mb-3 text-sm text-red-600">{planError}</p>}
        {isOwner ? (
          <div className="flex items-end gap-3">
            <FormField label="Change plan">
              <Select value={selectedPlan} onChange={(e) => setSelectedPlan(e.target.value as BusinessPlan)}>
                {BUSINESS_PLANS.map((plan) => (
                  <option key={plan} value={plan}>
                    {PLAN_LIMITS[plan].label} ({PLAN_LIMITS[plan].maxTeamMembers} members)
                  </option>
                ))}
              </Select>
            </FormField>
            <Button
              onClick={handleChangePlan}
              disabled={isChangingPlan || selectedPlan === currentBusiness.business.plan}
            >
              {isChangingPlan ? "Saving…" : "Change plan"}
            </Button>
          </div>
        ) : (
          <p className="text-xs text-slate-400">Only the business owner can change the plan.</p>
        )}
        <p className="mt-2 text-xs text-slate-400">No payment required — plans are modeled, not billed, yet.</p>
      </Card>

      <Card className="mt-6 max-w-2xl">
        <h2 className="mb-4 text-lg font-semibold">Team members</h2>

        {!members ? (
          <p className="text-sm text-slate-500">Loading...</p>
        ) : (
          <table className="mb-4 w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-left text-slate-500">
                <th className="py-2 pr-4 font-medium">Name</th>
                <th className="py-2 pr-4 font-medium">Email</th>
                <th className="py-2 pr-4 font-medium">Role</th>
                <th className="py-2 pr-4 font-medium">Status</th>
                {canManageMembers && <th className="py-2 pr-4 font-medium">Actions</th>}
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
                              {role}
                            </option>
                          ))}
                        </Select>
                      ) : (
                        member.role
                      )}
                    </td>
                    <td className="py-2 pr-4">
                      <Badge tone={MEMBERSHIP_STATUS_TONE[member.status] ?? "neutral"}>{member.status}</Badge>
                    </td>
                    {canManageMembers && (
                      <td className="py-2 pr-4">
                        {!isOwnerRow && member.status === "active" && (
                          <Button variant="danger" onClick={() => handleRemove(member.membership_id)}>
                            Remove
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
            <FormField label="Invite by email">
              <Input
                type="email"
                required
                placeholder="teammate@example.com"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
              />
            </FormField>
            <FormField label="Role">
              <Select value={inviteRole} onChange={(e) => setInviteRole(e.target.value as BusinessRole)}>
                {BUSINESS_ROLES.filter((r) => r !== "owner").map((role) => (
                  <option key={role} value={role}>
                    {role}
                  </option>
                ))}
              </Select>
            </FormField>
            <Button type="submit" disabled={isInviting}>
              {isInviting ? "Inviting…" : "Invite"}
            </Button>
          </form>
          </>
        )}
        <p className="mt-3 text-xs text-slate-400">
          Only people who already have a FinanceAI account can be invited.
        </p>
      </Card>
    </div>
  );
}
