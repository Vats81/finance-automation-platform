import { apiFetch } from "@/lib/api/client";
import { IntegrationsStatusResponse } from "@/types/integrations";

export function getIntegrationsStatus(token: string | null): Promise<IntegrationsStatusResponse> {
  return apiFetch<IntegrationsStatusResponse>("/integrations/status", token);
}
