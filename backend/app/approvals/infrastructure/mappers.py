import uuid

from app.approvals.domain.entities import ApprovalStep, ApprovalWorkflow
from app.approvals.domain.value_objects import ApprovalStepStatus, ApprovalWorkflowStatus
from app.approvals.infrastructure.models import ApprovalStepModel, ApprovalWorkflowModel
from app.identity.domain.value_objects import Role


def _step_model_to_domain(model: ApprovalStepModel) -> ApprovalStep:
    return ApprovalStep(
        entity_id=model.id,
        step_number=model.step_number,
        required_role=Role(model.required_role),
        status=ApprovalStepStatus(model.status),
        approver_user_id=model.approver_user_id,
        decided_at=model.decided_at,
        comment=model.comment,
    )


def _step_domain_to_model(step: ApprovalStep, workflow_id: uuid.UUID) -> ApprovalStepModel:
    return ApprovalStepModel(
        id=step.id,
        workflow_id=workflow_id,
        step_number=step.step_number,
        required_role=step.required_role.value,
        status=step.status.value,
        approver_user_id=step.approver_user_id,
        decided_at=step.decided_at,
        comment=step.comment,
    )


def model_to_domain(model: ApprovalWorkflowModel) -> ApprovalWorkflow:
    return ApprovalWorkflow(
        entity_id=model.id,
        invoice_id=model.invoice_id,
        steps=[_step_model_to_domain(s) for s in model.steps],
        status=ApprovalWorkflowStatus(model.status),
        created_at=model.created_at,
    )


def domain_to_model(workflow: ApprovalWorkflow) -> ApprovalWorkflowModel:
    return ApprovalWorkflowModel(
        id=workflow.id,
        invoice_id=workflow.invoice_id,
        status=workflow.status.value,
        created_at=workflow.created_at,
        steps=[_step_domain_to_model(s, workflow.id) for s in workflow.steps],
    )


def apply_domain_to_existing_model(workflow: ApprovalWorkflow, model: ApprovalWorkflowModel) -> None:
    model.status = workflow.status.value
    steps_by_id = {s.id: s for s in model.steps}
    for step in workflow.steps:
        step_model = steps_by_id.get(step.id)
        if step_model is not None:
            step_model.status = step.status.value
            step_model.approver_user_id = step.approver_user_id
            step_model.decided_at = step.decided_at
            step_model.comment = step.comment
