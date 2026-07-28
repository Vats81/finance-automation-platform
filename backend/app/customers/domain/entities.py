import uuid
from datetime import datetime, timezone

from app.customers.domain.events import CustomerCreated, CustomerDeactivated, CustomerDetailsUpdated
from app.customers.domain.value_objects import CustomerAddress, CustomerEmailAddress, CustomerStatus
from app.shared.domain.aggregate_root import AggregateRoot


class Customer(AggregateRoot):
    """A business's customer — the AR-side counterpart to Vendor. Unlike
    Vendor (AP-automation compliance workflow: PENDING_REVIEW -> ACTIVE only
    after a W-9 is on file), a Customer is immediately usable on creation —
    there's no equivalent compliance gate for the SMB product's customer
    directory, so it defaults straight to ACTIVE.

    business_id is required (not optional like Vendor's, which stays
    optional only to keep the AP-automation product's existing vendors
    valid) — Customer is a net-new table with no pre-existing single-tenant
    data to be compatible with.
    """

    def __init__(
        self,
        *,
        entity_id: uuid.UUID | None = None,
        business_id: uuid.UUID,
        name: str,
        phone: str | None = None,
        email: CustomerEmailAddress | None = None,
        address: CustomerAddress | None = None,
        gst_number: str | None = None,
        status: CustomerStatus = CustomerStatus.ACTIVE,
        created_at: datetime | None = None,
    ) -> None:
        super().__init__(entity_id)
        self.business_id = business_id
        self.name = name
        self.phone = phone
        self.email = email
        self.address = address
        self.gst_number = gst_number
        self.status = status
        self.created_at = created_at or datetime.now(timezone.utc)

    @classmethod
    def create(
        cls,
        *,
        business_id: uuid.UUID,
        name: str,
        phone: str | None = None,
        email: CustomerEmailAddress | None = None,
        address: CustomerAddress | None = None,
        gst_number: str | None = None,
    ) -> "Customer":
        customer = cls(
            business_id=business_id,
            name=name,
            phone=phone,
            email=email,
            address=address,
            gst_number=gst_number,
        )
        customer._record_event(
            CustomerCreated(aggregate_id=customer.id, name=name, business_id=str(business_id))
        )
        return customer

    def update_details(
        self,
        *,
        name: str | None = None,
        phone: str | None = None,
        email: CustomerEmailAddress | None = None,
        address: CustomerAddress | None = None,
        gst_number: str | None = None,
    ) -> None:
        changed: list[str] = []
        if name is not None and name != self.name:
            self.name = name
            changed.append("name")
        if phone is not None and phone != self.phone:
            self.phone = phone
            changed.append("phone")
        if email is not None and email != self.email:
            self.email = email
            changed.append("email")
        if address is not None and address != self.address:
            self.address = address
            changed.append("address")
        if gst_number is not None and gst_number != self.gst_number:
            self.gst_number = gst_number
            changed.append("gst_number")

        if changed:
            self._record_event(CustomerDetailsUpdated(aggregate_id=self.id, changed_fields=changed))

    def deactivate(self) -> None:
        self.status = CustomerStatus.INACTIVE
        self._record_event(CustomerDeactivated(aggregate_id=self.id, name=self.name))

    def reactivate(self) -> None:
        self.status = CustomerStatus.ACTIVE

    @property
    def is_active(self) -> bool:
        return self.status == CustomerStatus.ACTIVE
