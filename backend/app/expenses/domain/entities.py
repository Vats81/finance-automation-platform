import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from app.expenses.domain.events import ExpenseDetailsUpdated, ExpenseRecorded, ExpenseVoided
from app.expenses.domain.exceptions import ExpenseAlreadyVoidException
from app.expenses.domain.value_objects import ExpenseStatus, PaymentMethod
from app.shared.domain.aggregate_root import AggregateRoot
from app.shared.domain.value_objects import Money


class Expense(AggregateRoot):
    """A recorded business expense. References Vendor only by id (never
    loads/mutates it — same reasoning as every other cross-aggregate
    reference in this codebase). Deliberately net-new rather than a
    retrofit of the AP-automation `Invoice` entity — see the module
    docstring in expenses/__init__.py-equivalent reasoning in the plan:
    Invoice is PO-matching-and-approval-centric, which a generic SMB
    expense record doesn't need.
    """

    def __init__(
        self,
        *,
        entity_id: uuid.UUID | None = None,
        business_id: uuid.UUID,
        expense_date: date,
        category: str,
        description: str,
        amount: Money,
        payment_method: PaymentMethod,
        vendor_id: uuid.UUID | None = None,
        tax: Money | None = None,
        is_recurring: bool = False,
        notes: str | None = None,
        status: ExpenseStatus = ExpenseStatus.RECORDED,
        created_at: datetime | None = None,
    ) -> None:
        super().__init__(entity_id)
        self.business_id = business_id
        self.expense_date = expense_date
        self.category = category
        self.description = description
        self.amount = amount
        self.tax = tax or Money(amount=Decimal("0"))
        self.payment_method = payment_method
        self.vendor_id = vendor_id
        self.is_recurring = is_recurring
        self.notes = notes
        self.status = status
        self.created_at = created_at or datetime.now(timezone.utc)

    @classmethod
    def create(
        cls,
        *,
        business_id: uuid.UUID,
        expense_date: date,
        category: str,
        description: str,
        amount: Money,
        payment_method: PaymentMethod,
        vendor_id: uuid.UUID | None = None,
        tax: Money | None = None,
        is_recurring: bool = False,
        notes: str | None = None,
    ) -> "Expense":
        expense = cls(
            business_id=business_id,
            expense_date=expense_date,
            category=category,
            description=description,
            amount=amount,
            payment_method=payment_method,
            vendor_id=vendor_id,
            tax=tax,
            is_recurring=is_recurring,
            notes=notes,
        )
        expense._record_event(
            ExpenseRecorded(
                aggregate_id=expense.id,
                business_id=str(business_id),
                category=category,
                total_amount_cents=expense.total_amount.cents,
            )
        )
        return expense

    @property
    def total_amount(self) -> Money:
        return self.amount + self.tax

    def update_details(
        self,
        *,
        category: str | None = None,
        description: str | None = None,
        amount: Money | None = None,
        tax: Money | None = None,
        payment_method: PaymentMethod | None = None,
        is_recurring: bool | None = None,
        notes: str | None = None,
    ) -> None:
        changed: list[str] = []
        if category is not None and category != self.category:
            self.category = category
            changed.append("category")
        if description is not None and description != self.description:
            self.description = description
            changed.append("description")
        if amount is not None and amount != self.amount:
            self.amount = amount
            changed.append("amount")
        if tax is not None and tax != self.tax:
            self.tax = tax
            changed.append("tax")
        if payment_method is not None and payment_method != self.payment_method:
            self.payment_method = payment_method
            changed.append("payment_method")
        if is_recurring is not None and is_recurring != self.is_recurring:
            self.is_recurring = is_recurring
            changed.append("is_recurring")
        if notes is not None and notes != self.notes:
            self.notes = notes
            changed.append("notes")

        if changed:
            self._record_event(ExpenseDetailsUpdated(aggregate_id=self.id, changed_fields=changed))

    def void(self) -> None:
        if self.status == ExpenseStatus.VOID:
            raise ExpenseAlreadyVoidException(f"Expense {self.id} is already void")

        self.status = ExpenseStatus.VOID
        self._record_event(ExpenseVoided(aggregate_id=self.id, category=self.category))
