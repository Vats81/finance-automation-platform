import uuid
from datetime import datetime, timezone

from app.shared.domain.aggregate_root import AggregateRoot
from app.vendors.domain.events import (
    VendorActivated,
    VendorCreated,
    VendorDeactivated,
    VendorDetailsUpdated,
    VendorW9DocumentUploaded,
)
from app.vendors.domain.exceptions import VendorAlreadyActiveException, VendorMissingW9Exception
from app.vendors.domain.value_objects import Address, TaxId, VendorEmailAddress, VendorStatus


class Vendor(AggregateRoot):
    """A vendor/supplier the platform pays. Own aggregate, referenced by
    Invoice and PurchaseOrder only by id (never loaded/mutated across
    aggregate boundaries) — see approvals/domain for why ApprovalWorkflow
    is similarly kept separate from Invoice.
    """

    def __init__(
        self,
        *,
        entity_id: uuid.UUID | None = None,
        legal_name: str,
        contact_email: VendorEmailAddress,
        tax_id: TaxId,
        address: Address,
        status: VendorStatus = VendorStatus.PENDING_REVIEW,
        w9_document_reference: str | None = None,
        business_id: uuid.UUID | None = None,
        created_at: datetime | None = None,
    ) -> None:
        super().__init__(entity_id)
        self.legal_name = legal_name
        self.contact_email = contact_email
        self.tax_id = tax_id
        self.address = address
        self.status = status
        self.w9_document_reference = w9_document_reference
        # None for every vendor created by the AP-automation product (its
        # routes never pass this) — set only for vendors created through the
        # SMB Finance Manager product's /businesses/{business_id}/vendors
        # routes (see vendors/application/commands/create_business_vendor.py).
        self.business_id = business_id
        self.created_at = created_at or datetime.now(timezone.utc)

    @classmethod
    def create(
        cls,
        *,
        legal_name: str,
        contact_email: VendorEmailAddress,
        tax_id: TaxId,
        address: Address,
        business_id: uuid.UUID | None = None,
    ) -> "Vendor":
        vendor = cls(
            legal_name=legal_name,
            contact_email=contact_email,
            tax_id=tax_id,
            address=address,
            business_id=business_id,
        )
        vendor._record_event(
            VendorCreated(aggregate_id=vendor.id, legal_name=legal_name, contact_email=str(contact_email))
        )
        return vendor

    def record_w9_document(self, document_reference: str) -> None:
        self.w9_document_reference = document_reference
        self._record_event(
            VendorW9DocumentUploaded(aggregate_id=self.id, document_reference=document_reference)
        )

    def activate(self) -> None:
        if self.status == VendorStatus.ACTIVE:
            raise VendorAlreadyActiveException(f"Vendor {self.id} is already active")
        if self.w9_document_reference is None:
            raise VendorMissingW9Exception(
                f"Vendor {self.id} cannot be activated without a W-9 on file"
            )
        self.status = VendorStatus.ACTIVE
        self._record_event(VendorActivated(aggregate_id=self.id, legal_name=self.legal_name))

    def deactivate(self) -> None:
        self.status = VendorStatus.INACTIVE
        self._record_event(VendorDeactivated(aggregate_id=self.id, legal_name=self.legal_name))

    def update_details(
        self,
        *,
        legal_name: str | None = None,
        contact_email: VendorEmailAddress | None = None,
        address: Address | None = None,
    ) -> None:
        changed: list[str] = []
        if legal_name is not None and legal_name != self.legal_name:
            self.legal_name = legal_name
            changed.append("legal_name")
        if contact_email is not None and contact_email != self.contact_email:
            self.contact_email = contact_email
            changed.append("contact_email")
        if address is not None and address != self.address:
            self.address = address
            changed.append("address")

        if changed:
            self._record_event(VendorDetailsUpdated(aggregate_id=self.id, changed_fields=changed))

    @property
    def is_active(self) -> bool:
        return self.status == VendorStatus.ACTIVE
