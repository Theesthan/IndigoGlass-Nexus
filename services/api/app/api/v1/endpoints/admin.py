# =============================================================================
# IndigoGlass Nexus - Admin Endpoints
# =============================================================================
"""
Admin endpoints for user management, job control, and model promotion.
"""

from datetime import datetime, timezone
from typing import Annotated, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status, BackgroundTasks
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    TokenPayload,
    Role,
    require_admin,
    require_analyst,
    hash_password,
)
from app.db.mysql import get_session
from app.models import AuthUser, AuthAuditLog, MLModel, MLModelAssignment

logger = structlog.get_logger()

router = APIRouter()


# =============================================================================
# User Management Schemas
# =============================================================================

class CreateUserRequest(BaseModel):
    """Create user request."""
    email: EmailStr
    password: str
    full_name: str
    role: str = "viewer"


class UpdateUserRequest(BaseModel):
    """Update user request."""
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    """User response."""
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    last_login: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


# =============================================================================
# Job Management Schemas
# =============================================================================

class IngestionRunRequest(BaseModel):
    """Ingestion run request."""
    start_date: str
    end_date: str
    source: str = "synthetic"


class JobResponse(BaseModel):
    """Job response."""
    job_id: str
    status: str
    message: str
    started_at: str | None = None


class JobLogEntry(BaseModel):
    """Job log entry."""
    timestamp: str
    level: str
    message: str
    metadata: dict = {}


# =============================================================================
# Model Management Schemas
# =============================================================================

class PromoteModelRequest(BaseModel):
    """Model promotion request."""
    model_name: str
    version: str


class PromoteModelResponse(BaseModel):
    """Model promotion response."""
    model_name: str
    version: str
    previous_status: str
    new_status: str
    promoted_at: str


# =============================================================================
# User Management Endpoints
# =============================================================================

@router.get("/users", response_model=list[UserResponse])
async def list_users(
    current_user: Annotated[TokenPayload, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
    include_inactive: bool = Query(False),
) -> list[UserResponse]:
    """
    List all users (Admin only).
    """
    query = select(AuthUser).order_by(AuthUser.created_at.desc())
    
    if not include_inactive:
        query = query.where(AuthUser.is_active == True)
    
    result = await session.execute(query)
    users = result.scalars().all()
    
    return [UserResponse.model_validate(u) for u in users]


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: Request,
    body: CreateUserRequest,
    current_user: Annotated[TokenPayload, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserResponse:
    """
    Create a new user (Admin only).
    """
    # Check if email exists
    existing = await session.execute(
        select(AuthUser).where(AuthUser.email == body.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    
    # Validate role
    if body.role not in ["admin", "analyst", "viewer"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be: admin, analyst, or viewer",
        )
    
    user = AuthUser(
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
        is_active=True,
    )
    session.add(user)
    await session.flush()
    
    # Audit log
    audit = AuthAuditLog(
        user_id=int(current_user.sub),
        action="create_user",
        entity_type="auth_user",
        entity_id=str(user.id),
        ip_address=request.client.host if request.client else None,
        metadata_json={"created_email": body.email, "role": body.role},
    )
    session.add(audit)
    
    logger.info("user_created", user_id=user.id, email=user.email, by=current_user.sub)
    
    return UserResponse.model_validate(user)


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    request: Request,
    body: UpdateUserRequest,
    current_user: Annotated[TokenPayload, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserResponse:
    """
    Update user details (Admin only).
    """
    result = await session.execute(
        select(AuthUser).where(AuthUser.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )
    
    if body.full_name is not None:
        user.full_name = body.full_name
    if body.role is not None:
        if body.role not in ["admin", "analyst", "viewer"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role",
            )
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    
    # Audit log
    audit = AuthAuditLog(
        user_id=int(current_user.sub),
        action="update_user",
        entity_type="auth_user",
        entity_id=str(user_id),
        ip_address=request.client.host if request.client else None,
        metadata_json=body.model_dump(exclude_none=True),
    )
    session.add(audit)
    
    logger.info("user_updated", user_id=user_id, by=current_user.sub)
    
    return UserResponse.model_validate(user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    request: Request,
    current_user: Annotated[TokenPayload, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """
    Soft delete a user (Admin only).
    """
    if int(current_user.sub) == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )
    
    result = await session.execute(
        select(AuthUser).where(AuthUser.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )
    
    user.is_active = False
    
    # Audit log
    audit = AuthAuditLog(
        user_id=int(current_user.sub),
        action="delete_user",
        entity_type="auth_user",
        entity_id=str(user_id),
        ip_address=request.client.host if request.client else None,
    )
    session.add(audit)
    
    logger.info("user_deleted", user_id=user_id, by=current_user.sub)


# =============================================================================
# Job Management Endpoints
# =============================================================================

@router.post("/ingestion/run", response_model=JobResponse)
async def trigger_ingestion(
    body: IngestionRunRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: Annotated[TokenPayload, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> JobResponse:
    """
    Trigger data ingestion job (Admin only).
    """
    import uuid
    
    job_id = f"ING-{uuid.uuid4().hex[:8].upper()}"
    
    # In production, this would queue a Celery task
    logger.info(
        "ingestion_triggered",
        job_id=job_id,
        start_date=body.start_date,
        end_date=body.end_date,
        source=body.source,
        by=current_user.sub,
    )
    
    # Audit log
    audit = AuthAuditLog(
        user_id=int(current_user.sub),
        action="trigger_ingestion",
        entity_type="job",
        entity_id=job_id,
        ip_address=request.client.host if request.client else None,
        metadata_json={
            "start_date": body.start_date,
            "end_date": body.end_date,
            "source": body.source,
        },
    )
    session.add(audit)
    
    return JobResponse(
        job_id=job_id,
        status="queued",
        message=f"Ingestion job queued for {body.start_date} to {body.end_date}",
        started_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(
    job_id: str,
    current_user: Annotated[TokenPayload, Depends(require_analyst)],
) -> JobResponse:
    """
    Get job status by ID.
    """
    # In production, this would query Celery or a job table
    return JobResponse(
        job_id=job_id,
        status="completed",
        message="Job completed successfully",
    )


@router.get("/jobs/{job_id}/logs", response_model=list[JobLogEntry])
async def get_job_logs(
    job_id: str,
    current_user: Annotated[TokenPayload, Depends(require_analyst)],
    limit: int = Query(100, ge=1, le=1000),
) -> list[JobLogEntry]:
    """
    Get job logs.
    """
    # In production, this would query log storage
    return [
        JobLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level="INFO",
            message=f"Job {job_id} log entry",
            metadata={},
        )
    ]


# =============================================================================
# Model Management Endpoints
# =============================================================================

@router.post("/models/promote", response_model=PromoteModelResponse)
async def promote_model(
    body: PromoteModelRequest,
    request: Request,
    current_user: Annotated[TokenPayload, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PromoteModelResponse:
    """
    Promote a model from staged to prod (Admin only).
    """
    # Find the model
    result = await session.execute(
        select(MLModel).where(
            MLModel.model_name == body.model_name,
            MLModel.version == body.version,
        )
    )
    model = result.scalar_one_or_none()
    
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {body.model_name} version {body.version} not found",
        )
    
    if model.status == "prod":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Model is already in prod status",
        )
    
    previous_status = model.status
    
    # Archive current prod model (if any)
    await session.execute(
        update(MLModel)
        .where(
            MLModel.model_name == body.model_name,
            MLModel.status == "prod",
        )
        .values(status="archived")
    )
    
    # Promote the model
    model.status = "prod"
    model.promoted_at = datetime.now(timezone.utc)
    model.promoted_by = current_user.email
    
    # Audit log
    audit = AuthAuditLog(
        user_id=int(current_user.sub),
        action="promote_model",
        entity_type="ml_model",
        entity_id=f"{body.model_name}:{body.version}",
        ip_address=request.client.host if request.client else None,
        metadata_json={
            "previous_status": previous_status,
            "new_status": "prod",
        },
    )
    session.add(audit)
    
    logger.info(
        "model_promoted",
        model=body.model_name,
        version=body.version,
        by=current_user.sub,
    )
    
    return PromoteModelResponse(
        model_name=body.model_name,
        version=body.version,
        previous_status=previous_status,
        new_status="prod",
        promoted_at=model.promoted_at.isoformat(),
    )


@router.get("/audit-logs", response_model=list[dict])
async def get_audit_logs(
    current_user: Annotated[TokenPayload, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
    action: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
) -> list[dict]:
    """
    Get audit logs (Admin only).
    """
    query = (
        select(AuthAuditLog, AuthUser.email)
        .outerjoin(AuthUser, AuthAuditLog.user_id == AuthUser.id)
        .order_by(AuthAuditLog.timestamp.desc())
        .limit(limit)
    )
    
    if action:
        query = query.where(AuthAuditLog.action == action)
    if user_id:
        query = query.where(AuthAuditLog.user_id == user_id)
    
    result = await session.execute(query)
    
    logs = []
    for log, email in result.all():
        logs.append({
            "id": log.id,
            "user_id": log.user_id,
            "user_email": email,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "ip_address": log.ip_address,
            "metadata": log.metadata_json,
            "timestamp": log.timestamp.isoformat(),
        })
    
    return logs
