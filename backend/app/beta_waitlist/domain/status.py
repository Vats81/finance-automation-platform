import enum

from app.shared.domain.exceptions import ValidationException


class WaitlistStatus(str, enum.Enum):
    INTERESTED = "interested"
    QUALIFIED = "qualified"
    WAITING_FOR_CHECKS = "waiting_for_checks"
    INVITED = "invited"
    ONBOARDED = "onboarded"
    PAUSED = "paused"


# Interest is tracked separately from account access: a waitlist entry never
# creates an account, and nobody becomes "invited" without first being
# qualified (and, if checks are pending, waiting for them to pass).
ALLOWED_TRANSITIONS: dict[WaitlistStatus, frozenset[WaitlistStatus]] = {
    WaitlistStatus.INTERESTED: frozenset({WaitlistStatus.QUALIFIED, WaitlistStatus.PAUSED}),
    WaitlistStatus.QUALIFIED: frozenset(
        {WaitlistStatus.WAITING_FOR_CHECKS, WaitlistStatus.INVITED, WaitlistStatus.PAUSED}
    ),
    WaitlistStatus.WAITING_FOR_CHECKS: frozenset(
        {WaitlistStatus.QUALIFIED, WaitlistStatus.INVITED, WaitlistStatus.PAUSED}
    ),
    WaitlistStatus.INVITED: frozenset(
        {WaitlistStatus.ONBOARDED, WaitlistStatus.QUALIFIED, WaitlistStatus.PAUSED}
    ),
    WaitlistStatus.ONBOARDED: frozenset({WaitlistStatus.PAUSED}),
    WaitlistStatus.PAUSED: frozenset({WaitlistStatus.INTERESTED, WaitlistStatus.QUALIFIED}),
}


class InvalidWaitlistTransitionException(ValidationException):
    error_code = "invalid_waitlist_transition"


def check_transition(current: WaitlistStatus, target: WaitlistStatus) -> None:
    if target == current:
        return
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidWaitlistTransitionException(
            f"Cannot move a waitlist entry from {current.value} to {target.value}."
        )
