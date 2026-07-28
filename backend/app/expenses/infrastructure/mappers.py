from app.expenses.domain.entities import Expense
from app.expenses.domain.value_objects import ExpenseStatus, PaymentMethod
from app.expenses.infrastructure.models import ExpenseModel
from app.shared.domain.value_objects import Money


def model_to_domain(model: ExpenseModel) -> Expense:
    return Expense(
        entity_id=model.id,
        business_id=model.business_id,
        expense_date=model.expense_date,
        category=model.category,
        description=model.description,
        amount=Money.from_cents(model.amount_cents),
        tax=Money.from_cents(model.tax_cents),
        payment_method=PaymentMethod(model.payment_method),
        vendor_id=model.vendor_id,
        is_recurring=model.is_recurring,
        notes=model.notes,
        status=ExpenseStatus(model.status),
        created_at=model.created_at,
    )


def domain_to_model(expense: Expense) -> ExpenseModel:
    return ExpenseModel(
        id=expense.id,
        business_id=expense.business_id,
        expense_date=expense.expense_date,
        vendor_id=expense.vendor_id,
        category=expense.category,
        description=expense.description,
        amount_cents=expense.amount.cents,
        tax_cents=expense.tax.cents,
        payment_method=expense.payment_method.value,
        is_recurring=expense.is_recurring,
        notes=expense.notes,
        status=expense.status.value,
        created_at=expense.created_at,
    )


def apply_domain_to_existing_model(expense: Expense, model: ExpenseModel) -> None:
    model.category = expense.category
    model.description = expense.description
    model.amount_cents = expense.amount.cents
    model.tax_cents = expense.tax.cents
    model.payment_method = expense.payment_method.value
    model.is_recurring = expense.is_recurring
    model.notes = expense.notes
    model.status = expense.status.value
