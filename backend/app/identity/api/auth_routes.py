from fastapi import APIRouter, Depends, Request, Response

from app.api.rate_limit import limiter
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
from app.identity.infrastructure.local_auth.token_issuer import LocalTokenIssuer
from app.shared.application.ports import IClock, IPasswordHasher

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
) -> LocalUserResponse:
    use_case = RegisterUserUseCase(
        uow, password_hasher, clock, verification_ttl_hours=settings.email_verification_ttl_hours
    )
    user = await use_case.execute(
        RegisterUserCommand(email=body.email, password=body.password, display_name=body.display_name)
    )
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
