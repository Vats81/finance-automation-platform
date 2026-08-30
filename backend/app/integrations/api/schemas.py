from pydantic import BaseModel

from app.integrations.application.queries.get_integration_status import IntegrationsStatus, ProviderStatus


class ProviderStatusResponse(BaseModel):
    connected: bool
    detail: str

    @classmethod
    def from_domain(cls, status: ProviderStatus) -> "ProviderStatusResponse":
        return cls(connected=status.connected, detail=status.detail)


class IntegrationsStatusResponse(BaseModel):
    email: ProviderStatusResponse
    whatsapp: ProviderStatusResponse
    ai_assistant: ProviderStatusResponse
    document_storage: ProviderStatusResponse
    billing: ProviderStatusResponse

    @classmethod
    def from_domain(cls, status: IntegrationsStatus) -> "IntegrationsStatusResponse":
        return cls(
            email=ProviderStatusResponse.from_domain(status.email),
            whatsapp=ProviderStatusResponse.from_domain(status.whatsapp),
            ai_assistant=ProviderStatusResponse.from_domain(status.ai_assistant),
            document_storage=ProviderStatusResponse.from_domain(status.document_storage),
            billing=ProviderStatusResponse.from_domain(status.billing),
        )
