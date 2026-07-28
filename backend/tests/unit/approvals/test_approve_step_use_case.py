import uuid

import pytest

from app.approvals.domain.entities import ApprovalWorkflow
from app.approvals.domain.exceptions import (
    InvalidApprovalStepException,
    UnauthorizedApproverException,
    WorkflowAlreadyCompletedException,
)
from app.approvals.domain.value_objects import ApprovalStepStatus, ApprovalWorkflowStatus
from app.identity.domain.value_objects import Role


def make_workflow(roles: list[Role]) -> ApprovalWorkflow:
    workflow = ApprovalWorkflow.start(invoice_id=uuid.uuid4(), required_roles=roles)
    workflow.pull_domain_events()
    return workflow


def test_start_creates_one_pending_step_per_role() -> None:
    workflow = ApprovalWorkflow.start(
        invoice_id=uuid.uuid4(), required_roles=[Role.APPROVER, Role.FINANCE_ADMIN]
    )

    assert len(workflow.steps) == 2
    assert all(s.status == ApprovalStepStatus.PENDING for s in workflow.steps)
    assert [e.event_type for e in workflow.pull_domain_events()] == ["WorkflowStarted"]


def test_single_step_approval_completes_workflow_and_records_events() -> None:
    workflow = make_workflow([Role.APPROVER])
    approver_id = uuid.uuid4()

    workflow.approve_step(step_number=1, approver_user_id=approver_id, actor_role=Role.APPROVER)

    assert workflow.status == ApprovalWorkflowStatus.APPROVED
    assert workflow.is_completed
    event_types = [e.event_type for e in workflow.pull_domain_events()]
    assert event_types == ["StepApproved", "ApprovalWorkflowCompleted"]


def test_multi_step_workflow_stays_in_progress_until_last_step() -> None:
    workflow = make_workflow([Role.APPROVER, Role.FINANCE_ADMIN])

    workflow.approve_step(step_number=1, approver_user_id=uuid.uuid4(), actor_role=Role.APPROVER)

    assert workflow.status == ApprovalWorkflowStatus.IN_PROGRESS
    assert workflow.current_step.step_number == 2


def test_cannot_approve_step_out_of_order() -> None:
    workflow = make_workflow([Role.APPROVER, Role.FINANCE_ADMIN])

    with pytest.raises(InvalidApprovalStepException):
        workflow.approve_step(step_number=2, approver_user_id=uuid.uuid4(), actor_role=Role.FINANCE_ADMIN)


def test_wrong_role_cannot_approve_step() -> None:
    workflow = make_workflow([Role.FINANCE_ADMIN])

    with pytest.raises(UnauthorizedApproverException):
        workflow.approve_step(step_number=1, approver_user_id=uuid.uuid4(), actor_role=Role.APPROVER)


def test_same_user_cannot_decide_two_steps() -> None:
    workflow = make_workflow([Role.APPROVER, Role.FINANCE_ADMIN])
    approver_id = uuid.uuid4()
    workflow.approve_step(step_number=1, approver_user_id=approver_id, actor_role=Role.APPROVER)

    with pytest.raises(UnauthorizedApproverException):
        workflow.approve_step(step_number=2, approver_user_id=approver_id, actor_role=Role.FINANCE_ADMIN)


def test_cannot_act_on_completed_workflow() -> None:
    workflow = make_workflow([Role.APPROVER])
    workflow.approve_step(step_number=1, approver_user_id=uuid.uuid4(), actor_role=Role.APPROVER)

    with pytest.raises(WorkflowAlreadyCompletedException):
        workflow.approve_step(step_number=1, approver_user_id=uuid.uuid4(), actor_role=Role.APPROVER)


def test_rejection_ends_workflow_immediately_even_with_remaining_steps() -> None:
    workflow = make_workflow([Role.APPROVER, Role.FINANCE_ADMIN])

    workflow.reject_step(
        step_number=1, approver_user_id=uuid.uuid4(), actor_role=Role.APPROVER, reason="Duplicate invoice"
    )

    assert workflow.status == ApprovalWorkflowStatus.REJECTED
    assert workflow.is_completed
    event_types = [e.event_type for e in workflow.pull_domain_events()]
    assert event_types == ["StepRejected", "ApprovalWorkflowCompleted"]
