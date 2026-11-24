import re
import uuid
from dataclasses import dataclass

from app.sales.application.ports import SalesUnitOfWork

_TRAILING_NUMBER = re.compile(r"^(.*?)(\d+)$")
_DEFAULT = "INV-0001"
_RECENT = 50


@dataclass(frozen=True)
class NextInvoiceNumberQuery:
    business_id: uuid.UUID


class NextInvoiceNumberUseCase:
    """The next number in the business's own series: "INV-0041" after "INV-0040" (same prefix, same width).
    GST invoices need consecutive numbers, so the app offers the next one instead of leaving it to be made up.
    """

    def __init__(self, uow: SalesUnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: NextInvoiceNumberQuery) -> str:
        recent, _ = await self._uow.sales.list_for_business(query.business_id, offset=0, limit=_RECENT)
        candidate = _DEFAULT
        for sale in sorted(recent, key=lambda s: s.created_at, reverse=True):
            match = _TRAILING_NUMBER.match(sale.invoice_number)
            if match:
                prefix, digits = match.groups()
                candidate = f"{prefix}{str(int(digits) + 1).zfill(len(digits))}"
                break
        # Skip over any number already used (for example after an invoice was entered out of order).
        while await self._uow.sales.invoice_number_in_use(query.business_id, candidate):
            match = _TRAILING_NUMBER.match(candidate)
            assert match is not None  # the default and every generated candidate end in digits
            prefix, digits = match.groups()
            candidate = f"{prefix}{str(int(digits) + 1).zfill(len(digits))}"
        return candidate
