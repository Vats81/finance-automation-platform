from app.shared.domain.exceptions import NotFoundException, ValidationException


class PersonalWorkspaceRequiredException(ValidationException):
    """Income and budgets belong to personal workspaces; a business keeps its
    money in sales and expenses instead.
    """

    error_code = "personal_workspace_required"


class IncomeNotFoundException(NotFoundException):
    error_code = "income_not_found"


class BudgetNotFoundException(NotFoundException):
    error_code = "budget_not_found"


class IncomeAlreadyVoidException(ValidationException):
    error_code = "income_already_void"
