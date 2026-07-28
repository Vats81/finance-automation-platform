import logging
from datetime import datetime, timedelta, timezone
from typing import BinaryIO

from azure.core.exceptions import AzureError
from azure.storage.blob import BlobSasPermissions, ContentSettings, generate_blob_sas
from azure.storage.blob.aio import BlobServiceClient
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.shared.application.exceptions import FileStorageUnavailableException
from app.shared.application.ports import IFileStorage

logger = logging.getLogger(__name__)

_retry_transient = retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    retry=retry_if_exception_type(AzureError),
)


class AzureBlobStorageAdapter(IFileStorage):
    """Azure Blob Storage adapter. Points at Azurite in local/dev via the
    connection string; identical code path against real Azure Storage in
    higher environments (Phase 2 Terraform provisions the real account).
    """

    def __init__(self, connection_string: str) -> None:
        self._connection_string = connection_string

    @_retry_transient
    async def upload(self, *, container: str, blob_name: str, data: BinaryIO, content_type: str) -> str:
        try:
            async with BlobServiceClient.from_connection_string(self._connection_string) as client:
                container_client = client.get_container_client(container)
                if not await container_client.exists():
                    await container_client.create_container()
                blob_client = container_client.get_blob_client(blob_name)
                await blob_client.upload_blob(
                    data, overwrite=True, content_settings=ContentSettings(content_type=content_type)
                )
                return f"{container}/{blob_name}"
        except AzureError as exc:
            logger.error("Blob upload failed for %s/%s: %s", container, blob_name, exc)
            raise FileStorageUnavailableException(f"Failed to upload {blob_name}") from exc

    @_retry_transient
    async def get_download_url(
        self, *, container: str, blob_name: str, expires_in_seconds: int = 3600
    ) -> str:
        try:
            async with BlobServiceClient.from_connection_string(self._connection_string) as client:
                account_name = client.account_name
                credential = client.credential
                sas_token = generate_blob_sas(
                    account_name=account_name,
                    container_name=container,
                    blob_name=blob_name,
                    account_key=credential.account_key,
                    permission=BlobSasPermissions(read=True),
                    expiry=datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds),
                )
                blob_client = client.get_blob_client(container, blob_name)
                return f"{blob_client.url}?{sas_token}"
        except AzureError as exc:
            logger.error("Failed to generate SAS URL for %s/%s: %s", container, blob_name, exc)
            raise FileStorageUnavailableException(f"Failed to generate URL for {blob_name}") from exc

    @_retry_transient
    async def delete(self, *, container: str, blob_name: str) -> None:
        try:
            async with BlobServiceClient.from_connection_string(self._connection_string) as client:
                blob_client = client.get_blob_client(container, blob_name)
                await blob_client.delete_blob()
        except AzureError as exc:
            logger.error("Blob delete failed for %s/%s: %s", container, blob_name, exc)
            raise FileStorageUnavailableException(f"Failed to delete {blob_name}") from exc
