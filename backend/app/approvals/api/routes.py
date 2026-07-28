import uuid

from fastapi import APIRouter, Depends, Request

from app.api.rate_limit import limiter
from app.approvals.api.dependencies import require_approver
from app.approvals.api.schemas import (
    ApprovalWorkflowResponse,
    PagedApprovalWorkflowsResponse,
    RejectStepRequest,
)
from app.approvals.application.commands.approve_step import ApproveStepCommand, ApproveStepUseCase
from app.approvals.application.commands.reject_step import RejectStepCommand, RejectStepUseCase
from app.approvals.application.queries.get_workflow_for_invoice import (
    GetWorkflowForInvoiceQuery,
    GetWorkflowForInvoiceUseCase,
)
from app.approvals.application.queries.list_pending_approvals_for_user import (
    ListPendingApprovalsForUserQuery,
    ListPendingApprovalsForUserUseCase,
)
from app.bootstrap.container import get_uow
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.config.settings import get_settings
from app.identity.domain.entities import User
from app.shared.application.pagination import PageRequest

router = APIRouter(prefix="/approvals", tags=["approvals"])

settings = get_settings()


@router.get("/pending", response_model=PagedApprovalWorkflowsResponse)
async def list_pending_approvals(
    offset: int = 0,
    limit: int = 50,
    actor: User = Depends(require_approver),
    uow: AppUnitOfWork = Depends(get_uow),
) -> PagedApprovalWorkflowsResponse:
    use_case = ListPendingApprovalsForUserUseCase(uow)
    page = await use_case.execute(
        ListPendingApprovalsForUserQuery(role=actor.role, page=PageRequest(offset=offset, limit=limit))
    )
    return PagedApprovalWorkflowsResponse(
        items=[ApprovalWorkflowResponse.from_domain(w) for w in page.items],
        total=page.total,
        offset=page.offset,
        limit=page.limit,
    )


@router.get("/invoice/{invoice_id}", response_model=ApprovalWorkflowResponse)
async def get_workflow_for_invoice(
    invoice_id: uuid.UUID,
    _actor: User = Depends(require_approver),
    uow: AppUnitOfWork = Depends(get_uow),
) -> ApprovalWorkflowResponse:
    use_case = GetWorkflowForInvoiceUseCase(uow)
    workflow = await use_case.execute(GetWorkflowForInvoiceQuery(invoice_id=invoice_id))
    return ApprovalWorkflowResponse.from_domain(workflow)


@router.post("/{workflow_id}/steps/{step_number}/approve", response_model=ApprovalWorkflowResponse)
@limiter.limit(settings.rate_limit_write)
async def approve_step(
    request: Request,
    workflow_id: uuid.UUID,
    step_number: int,
    actor: User = Depends(require_approver),
    uow: AppUnitOfWork = Depends(get_uow),
) -> ApprovalWorkflowResponse:
    use_case = ApproveStepUseCase(uow)
    workflow = await use_case.execute(
        ApproveStepCommand(
            workflow_id=workflow_id,
            step_number=step_number,
            approver_user_id=actor.id,
            actor_role=actor.role,
        )
    )
    return ApprovalWorkflowResponse.from_domain(workflow)


@router.post("/{workflow_id}/steps/{step_number}/reject", response_model=ApprovalWorkflowResponse)
@limiter.limit(settings.rate_limit_write)
async def reject_step(
    request: Request,
    workflow_id: uuid.UUID,
    step_number: int,
    body: RejectStepRequest,
    actor: User = Depends(require_approver),
    uow: AppUnitOfWork = Depends(get_uow),
) -> ApprovalWorkflowResponse:
    use_case = RejectStepUseCase(uow)
    workflow = await use_case.execute(
        RejectStepCommand(
            workflow_id=workflow_id,
            step_number=step_number,
            approver_user_id=actor.id,
            actor_role=actor.role,
            reason=body.reason,
        )
    )
    return ApprovalWorkflowResponse.from_domain(workflow)
