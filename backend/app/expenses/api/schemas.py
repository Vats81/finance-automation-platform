import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.expenses.application.scan_receipt import ScannedReceiptData
from app.expenses.domain.entities import Expense
from app.expenses.domain.value_objects import ExpenseStatus, PaymentMethod


class CreateExpenseRequest(BaseModel):
    expense_date: date
    category: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=500)
    amount: Decimal = Field(gt=0)
    payment_method: PaymentMethod
    vendor_id: uuid.UUID | None = None
    tax: Decimal | None = None
    is_recurring: bool = False
    notes: str | None = None


class UpdateExpenseRequest(BaseModel):
    category: str | None = None
    description: str | None = None
    amount: Decimal | None = None
    tax: Decimal | None = None
    payment_method: PaymentMethod | None = None
    is_recurring: bool | None = None
    notes: str | None = None


class ExpenseResponse(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    expense_date: date
    vendor_id: uuid.UUID | None
    category: str
    description: str
    amount: Decimal
    tax: Decimal
    total_amount: Decimal
    payment_method: PaymentMethod
    is_recurring: bool
    notes: str | None
    status: ExpenseStatus
    created_at: datetime

    @classmethod
    def from_domain(cls, expense: Expense) -> "ExpenseResponse":
        return cls(
            id=expense.id,
            business_id=expense.business_id,
            expense_date=expense.expense_date,
            vendor_id=expense.vendor_id,
            category=expense.category,
            description=expense.description,
            amount=expense.amount.amount,
            tax=expense.tax.amount,
            total_amount=expense.total_amount.amount,
            payment_method=expense.payment_method,
            is_recurring=expense.is_recurring,
            notes=expense.notes,
            status=expense.status,
            created_at=expense.created_at,
        )


class PagedExpensesResponse(BaseModel):
    items: list[ExpenseResponse]
    total: int
    offset: int
    limit: int


class ScannedLineItemResponse(BaseModel):
    description: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal


class ScannedReceiptResponse(BaseModel):
    vendor_name: str | None
    amount: Decimal | None
    expense_date: date | None
    category_guess: str | None
    description_guess: str | None
    raw_text: str
    invoice_number: str | None = None
    tax: Decimal | None = None
    line_items: list[ScannedLineItemResponse] = []
    items_total: Decimal | None = None
    totals_match: bool | None = None

    @classmethod
    def from_domain(cls, data: ScannedReceiptData) -> "ScannedReceiptResponse":
        return cls(
            vendor_name=data.vendor_name,
            amount=data.amount,
            expense_date=data.expense_date,
            category_guess=data.category_guess,
            description_guess=data.description_guess,
            raw_text=data.raw_text,
            invoice_number=data.invoice_number,
            tax=data.tax,
            line_items=[
                ScannedLineItemResponse(
                    description=i.description,
                    quantity=i.quantity,
                    unit_price=i.unit_price,
                    line_total=i.line_total,
                )
                for i in data.line_items
            ],
            items_total=data.items_total,
            totals_match=data.totals_match,
        )
