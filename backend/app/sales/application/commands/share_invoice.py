import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from app.sales.application.ports import SalesUnitOfWork
from app.sales.domain.entities import Sale
from app.sales.domain.exceptions import InvoiceLinkNotFoundException, SaleNotFoundException
from app.sales.domain.share_link import InvoiceShareLink, hash_share_token
from app.sales.domain.value_objects import SaleStatus
from app.shared.domain.exceptions import ValidationException


@dataclass(frozen=True)
class CreateInvoiceShareLinkCommand:
    business_id: uuid.UUID
    sale_id: uuid.UUID


class CreateInvoiceShareLinkUseCase:
    """Makes a private link to the invoice's PDF. The token is returned once and never stored, so a lost
    link is replaced by making a new one (links made earlier keep working until revoked or expired).
    """

    def __init__(self, uow: SalesUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: CreateInvoiceShareLinkCommand) -> tuple[InvoiceShareLink, str]:
        sale = await self._uow.sales.get_by_id_for_business(command.sale_id, command.business_id)
        if sale is None:
            raise SaleNotFoundException(f"Sale {command.sale_id} not found")
        if sale.status == SaleStatus.VOID:
            raise ValidationException("A voided invoice cannot be shared.")
        link, token = InvoiceShareLink.issue(business_id=command.business_id, sale_id=command.sale_id)
        self._uow.invoice_share_links.add(link)
        await self._uow.commit()
        return link, token


@dataclass(frozen=True)
class RevokeInvoiceShareLinksCommand:
    business_id: uuid.UUID
    sale_id: uuid.UUID


class RevokeInvoiceShareLinksUseCase:
    """Stops every link to this invoice from working. Returns how many were still live."""

    def __init__(self, uow: SalesUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: RevokeInvoiceShareLinksCommand) -> int:
        sale = await self._uow.sales.get_by_id_for_business(command.sale_id, command.business_id)
        if sale is None:
            raise SaleNotFoundException(f"Sale {command.sale_id} not found")
        revoked = await self._uow.invoice_share_links.revoke_all_for_sale(
            command.sale_id, command.business_id, datetime.now(timezone.utc)
        )
        await self._uow.commit()
        return revoked


class ResolveInvoiceShareLinkUseCase:
    """The invoice a (public) link opens. Unknown, expired and revoked links are the same not-found."""

    def __init__(self, uow: SalesUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, token: str) -> Sale:
        link = await self._uow.invoice_share_links.get_by_token_hash(hash_share_token(token))
        if link is None or not link.is_active():
            raise InvoiceLinkNotFoundException("This invoice link is not valid.")
        sale = await self._uow.sales.get_by_id_for_business(link.sale_id, link.business_id)
        if sale is None:
            raise InvoiceLinkNotFoundException("This invoice link is not valid.")
        return sale
