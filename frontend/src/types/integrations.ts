export interface ProviderStatus {
  connected: boolean;
  detail: string;
  // Configured and sending, but only in a restricted test/sandbox mode that
  // won't reach real customers.
  limited?: boolean;
}

export interface IntegrationsStatusResponse {
  email: ProviderStatus;
  whatsapp: ProviderStatus;
  ai_assistant: ProviderStatus;
  document_storage: ProviderStatus;
  billing: ProviderStatus;
}
