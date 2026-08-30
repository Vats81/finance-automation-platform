export interface ProviderStatus {
  connected: boolean;
  detail: string;
}

export interface IntegrationsStatusResponse {
  email: ProviderStatus;
  whatsapp: ProviderStatus;
  ai_assistant: ProviderStatus;
  document_storage: ProviderStatus;
  billing: ProviderStatus;
}
