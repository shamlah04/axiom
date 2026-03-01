"""
Auth endpoints: register, login, me, refresh.
"""
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db, AsyncSessionLocal
from app.core.security import hash_password, verify_password, create_access_token
from app.core.deps import get_current_user
from app.models.models import User
from app.models.audit import AuditEventType
from app.repositories.repositories import UserRepository
from app.repositories.audit_repository import AuditRepository
from app.schemas.schemas import UserRegister, UserOut, Token

router = APIRouter(prefix="/auth", tags=["Auth"])


async def _run_audit(coro):
    """If in test mode, wait for the audit task to finish to avoid race conditions."""
    if settings.TESTING:
        await coro
    else:
        asyncio.create_task(coro)


def _ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


async def _log_audit(event_type: str, actor_id=None, fleet_id=None, subject_id=None, metadata=None, ip=None):
    """Background task for auditing."""
    async with AsyncSessionLocal() as db:
        audit = AuditRepository(db)
        await audit.log(
            event_type,
            actor_user_id=actor_id,
            fleet_id=fleet_id,
            subject_id=subject_id,
            metadata=metadata,
            ip_address=ip
        )


@router.post("/register", response_model=UserOut, status_code=201)
async def register(
    payload: UserRegister,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    repo = UserRepository(db)
    existing = await repo.get_by_email(payload.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = await repo.create(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
    )
    
    await _run_audit(
        _log_audit(
            AuditEventType.USER_REGISTERED,
            actor_id=user.id,
            subject_id=user.email,
            ip=_ip(request)
        )
    )
    return user


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    repo = UserRepository(db)
    user = await repo.get_by_email(form_data.username)
    
    ip = _ip(request)
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        await _run_audit(
            _log_audit(
                AuditEventType.USER_LOGIN_FAILED,
                actor_id=user.id if user else None,
                subject_id=form_data.username,
                ip=ip
            )
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = create_access_token(subject=user.id)
    
    await _run_audit(
        _log_audit(
            AuditEventType.USER_LOGIN,
            actor_id=user.id,
            fleet_id=user.fleet_id,
            ip=ip
        )
    )
    return Token(access_token=token)


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/refresh", response_model=Token)
async def refresh(current_user: User = Depends(get_current_user)):
    """Issue a fresh token while the current token is still valid."""
    token = create_access_token(subject=current_user.id)
    return Token(access_token=token)

