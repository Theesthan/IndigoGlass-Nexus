# =============================================================================
# IndigoGlass Nexus - Authentication Endpoints
# =============================================================================
"""
JWT-based authentication with login, refresh, and user info endpoints.
"""

from datetime import datetime, timezone
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    Role,
    TokenPayload,
    TokenResponse,
    create_tokens,
    decode_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.db.mysql import get_session
from app.models import AuthUser, AuthAuditLog

logger = structlog.get_logger()

router = APIRouter()


# =============================================================================
# Request/Response Schemas
# =============================================================================

class LoginRequest(BaseModel):
    """Login request schema."""
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Token refresh request schema."""
    refresh_token: str


class UserResponse(BaseModel):
    """User info response schema."""
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    last_login: datetime | None

    model_config = {"from_attributes": True}


class RegisterRequest(BaseModel):
    """User registration request (admin only)."""
    email: EmailStr
    password: str
    full_name: str
    role: str = "viewer"


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    body: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    """
    Authenticate user and issue JWT tokens.
    
    Returns access token (15 min) and refresh token (7 days).
    """
    # Find user
    result = await session.execute(
        select(AuthUser).where(AuthUser.email == body.email)
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(body.password, user.password_hash):
        logger.warning("login_failed", email=body.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    
    # Update last login
    user.last_login = datetime.now(timezone.utc)
    
    # Create audit log
    audit = AuthAuditLog(
        user_id=user.id,
        action="login",
        entity_type="auth_user",
        entity_id=str(user.id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    session.add(audit)
    
    logger.info("login_success", user_id=user.id, email=user.email)
    
    return create_tokens(
        user_id=str(user.id),
        email=user.email,
        role=Role(user.role),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    body: RefreshRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    """
    Refresh access token using a valid refresh token.
    """
    # Decode and validate refresh token
    payload = decode_token(body.refresh_token)
    
    if payload.type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token type, expected refresh token",
        )
    
    # Verify user still exists and is active
    result = await session.execute(
        select(AuthUser).where(AuthUser.id == int(payload.sub))
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or disabled",
        )
    
    return create_tokens(
        user_id=str(user.id),
        email=user.email,
        role=Role(user.role),
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserResponse:
    """
    Get current authenticated user information.
    """
    result = await session.execute(
        select(AuthUser).where(AuthUser.id == int(current_user.sub))
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return UserResponse.model_validate(user)


@router.post("/logout")
async def logout(
    request: Request,
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """
    Logout current user (audit log only - client should discard tokens).
    """
    audit = AuthAuditLog(
        user_id=int(current_user.sub),
        action="logout",
        entity_type="auth_user",
        entity_id=current_user.sub,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    session.add(audit)
    
    logger.info("logout", user_id=current_user.sub)
    
    return {"message": "Logged out successfully"}
