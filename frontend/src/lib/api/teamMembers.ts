import { apiFetch } from "@/lib/api/client";
import { InviteTeamMemberRequest, TeamMemberResponse, UpdateTeamMemberRoleRequest } from "@/types/business";

export function listTeamMembers(token: string | null, businessId: string): Promise<TeamMemberResponse[]> {
  return apiFetch<TeamMemberResponse[]>(`/businesses/${businessId}/team-members`, token);
}

export function inviteTeamMember(
  token: string | null,
  businessId: string,
  body: InviteTeamMemberRequest
): Promise<TeamMemberResponse> {
  return apiFetch<TeamMemberResponse>(`/businesses/${businessId}/team-members`, token, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateTeamMemberRole(
  token: string | null,
  businessId: string,
  membershipId: string,
  body: UpdateTeamMemberRoleRequest
): Promise<TeamMemberResponse> {
  return apiFetch<TeamMemberResponse>(`/businesses/${businessId}/team-members/${membershipId}`, token, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function removeTeamMember(
  token: string | null,
  businessId: string,
  membershipId: string
): Promise<TeamMemberResponse> {
  return apiFetch<TeamMemberResponse>(
    `/businesses/${businessId}/team-members/${membershipId}/remove`,
    token,
    { method: "POST" }
  );
}
