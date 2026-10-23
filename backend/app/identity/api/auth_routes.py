import logging

from fastapi import APIRouter, Depends, Request, Response

from app.api.rate_limit import limiter
from app.beta_waitlist.api.routes import get_waitlist_store
from app.beta_waitlist.application.ports import IWaitlistStore
from app.beta_waitlist.application.use_cases import is_invited, mark_onboarded_if_invited
from app.bootstrap.container import (
    get_clock,
    get_local_token_issuer,
    get_password_hasher,
    get_uow,
)
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.config.settings import get_settings
from app.identity.api.auth_schemas import (
    LocalUserResponse,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RequestPasswordResetRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
)
from app.identity.api.dependencies import get_current_local_user
from app.identity.application.commands.login_user import LoginUserCommand, LoginUserUseCase
from app.identity.application.commands.register_user import RegisterUserCommand, RegisterUserUseCase
from app.identity.application.commands.request_password_reset import (
    RequestPasswordResetCommand,
    RequestPasswordResetUseCase,
)
from app.identity.application.commands.reset_password import ResetPasswordCommand, ResetPasswordUseCase
from app.identity.application.commands.verify_email import VerifyEmailCommand, VerifyEmailUseCase
from app.identity.domain.entities import User
from app.identity.domain.exceptions import RegistrationInviteRequiredException
from app.identity.infrastructure.local_auth.token_issuer import LocalTokenIssuer
from app.shared.application.ports import IClock, IPasswordHasher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

settings = get_settings()


@router.post("/register", response_model=LocalUserResponse, status_code=201)
@limiter.limit(settings.rate_limit_write)
async def register(
    request: Request,
    body: RegisterRequest,
    uow: AppUnitOfWork = Depends(get_uow),
    password_hasher: IPasswordHasher = Depends(get_password_hasher),
    clock: IClock = Depends(get_clock),
    waitlist: IWaitlistStore = Depends(get_waitlist_store),
) -> LocalUserResponse:
    # Private beta: only invited emails may create an account. Checked before
    # anything else, so an uninvited address learns nothing about who is registered.
    if settings.registration_requires_invite and not await is_invited(waitlist, body.email):
        raise RegistrationInviteRequiredException(
            "Sign-up is by invitation during the private beta. You can register your interest "
            "on the beta page and we'll be in touch if there's a place."
        )
    use_case = RegisterUserUseCase(
        uow,
        password_hasher,
        clock,
        verification_ttl_hours=settings.email_verification_ttl_hours,
        auto_verify_email=settings.auth_auto_verify_email,
    )
    user = await use_case.execute(
        RegisterUserCommand(email=body.email, password=body.password, display_name=body.display_name)
    )
    if settings.registration_requires_invite:
        try:
            await mark_onboarded_if_invited(waitlist, body.email)
        except Exception:  # noqa: BLE001 - the account exists; bookkeeping must not fail the signup
            logger.exception("Could not mark waitlist entry onboarded for %s", body.email)
    return LocalUserResponse.from_domain(user)


@router.post("/verify-email", response_model=LocalUserResponse)
@limiter.limit(settings.rate_limit_write)
async def verify_email(
    request: Request,
    body: VerifyEmailRequest,
    uow: AppUnitOfWork = Depends(get_uow),
    clock: IClock = Depends(get_clock),
) -> LocalUserResponse:
    use_case = VerifyEmailUseCase(uow, clock)
    user = await use_case.execute(VerifyEmailCommand(user_id=body.user_id, token=body.token))
    return LocalUserResponse.from_domain(user)


@router.post("/login", response_model=LoginResponse)
@limiter.limit(settings.rate_limit_write)
async def login(
    request: Request,
    body: LoginRequest,
    uow: AppUnitOfWork = Depends(get_uow),
    password_hasher: IPasswordHasher = Depends(get_password_hasher),
    token_issuer: LocalTokenIssuer = Depends(get_local_token_issuer),
) -> LoginResponse:
    use_case = LoginUserUseCase(uow, password_hasher, token_issuer)
    result = await use_case.execute(LoginUserCommand(email=body.email, password=body.password))
    return LoginResponse(
        access_token=result.access_token,
        expires_at=result.expires_at,
        user=LocalUserResponse.from_domain(result.user),
    )


@router.post("/request-password-reset", status_code=204)
@limiter.limit(settings.rate_limit_write)
async def request_password_reset(
    request: Request,
    body: RequestPasswordResetRequest,
    uow: AppUnitOfWork = Depends(get_uow),
    clock: IClock = Depends(get_clock),
) -> Response:
    use_case = RequestPasswordResetUseCase(uow, clock, reset_ttl_hours=settings.password_reset_ttl_hours)
    await use_case.execute(RequestPasswordResetCommand(email=body.email))
    return Response(status_code=204)


@router.post("/reset-password", response_model=LocalUserResponse)
@limiter.limit(settings.rate_limit_write)
async def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    uow: AppUnitOfWork = Depends(get_uow),
    password_hasher: IPasswordHasher = Depends(get_password_hasher),
    clock: IClock = Depends(get_clock),
) -> LocalUserResponse:
    use_case = ResetPasswordUseCase(uow, password_hasher, clock)
    user = await use_case.execute(
        ResetPasswordCommand(user_id=body.user_id, token=body.token, new_password=body.new_password)
    )
    return LocalUserResponse.from_domain(user)


@router.get("/me", response_model=LocalUserResponse)
async def get_me(current_user: User = Depends(get_current_local_user)) -> LocalUserResponse:
    return LocalUserResponse.from_domain(current_user)
