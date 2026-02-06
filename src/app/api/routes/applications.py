"""Application management endpoints."""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.models.application import ApplicationStatus
from app.schemas.application import (
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationResponse,
    ApplicationDraftResponse,
    GenerateDraftRequest,
    ApplicationStatsResponse,
)
from app.services.application_service import ApplicationService
from app.services.job_service import JobService
from app.services.user_service import UserService

router = APIRouter()


@router.post("/drafts/generate", response_model=ApplicationDraftResponse)
async def generate_application_draft(
    data: GenerateDraftRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    """Generate an AI draft for a job application."""
    # Verify job exists
    job_service = JobService(db)
    job = await job_service.get_job_by_id(data.job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    # Check AI rate limit
    user_service = UserService(db)
    if not await user_service.increment_ai_calls(current_user):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily AI usage limit reached",
        )

    # Generate draft
    app_service = ApplicationService(db)
    draft = await app_service.generate_draft(
        user=current_user,
        job=job,
        tone=data.cover_letter_tone,
        custom_instructions=data.custom_instructions,
    )

    return draft


@router.get("/drafts", response_model=list[ApplicationDraftResponse])
async def get_drafts(db: DbSession, current_user: CurrentUser):
    """Get all pending drafts."""
    app_service = ApplicationService(db)
    drafts = await app_service.get_user_drafts(current_user)
    return drafts


@router.get("/drafts/{draft_id}", response_model=ApplicationDraftResponse)
async def get_draft(
    draft_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Get a specific draft."""
    app_service = ApplicationService(db)
    draft = await app_service.get_draft_by_id(draft_id, current_user.id)

    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found",
        )

    return draft


@router.post("/drafts/{draft_id}/regenerate", response_model=ApplicationDraftResponse)
async def regenerate_draft(
    draft_id: int,
    feedback: str | None = None,
    tone: str | None = None,
    db: DbSession = None,
    current_user: CurrentUser = None,
):
    """Regenerate a draft with feedback."""
    app_service = ApplicationService(db)
    draft = await app_service.get_draft_by_id(draft_id, current_user.id)

    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found",
        )

    # Check AI rate limit
    user_service = UserService(db)
    if not await user_service.increment_ai_calls(current_user):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily AI usage limit reached",
        )

    updated_draft = await app_service.regenerate_draft(
        draft=draft,
        user=current_user,
        feedback=feedback,
        new_tone=tone,
    )

    return updated_draft


@router.post("/drafts/{draft_id}/approve", response_model=ApplicationDraftResponse)
async def approve_draft(
    draft_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Approve a draft for application."""
    app_service = ApplicationService(db)
    draft = await app_service.get_draft_by_id(draft_id, current_user.id)

    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found",
        )

    approved = await app_service.approve_draft(draft)
    return approved


@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_application(
    data: ApplicationCreate,
    db: DbSession,
    current_user: CurrentUser,
):
    """Create an application from an approved draft."""
    app_service = ApplicationService(db)
    draft = await app_service.get_draft_by_id(data.draft_id, current_user.id)

    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found",
        )

    if not draft.is_approved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Draft must be approved before creating application",
        )

    application = await app_service.create_application(
        user=current_user,
        draft=draft,
        cover_letter_override=data.cover_letter,
        notes=data.user_notes,
    )

    return application


@router.get("", response_model=list[ApplicationResponse])
async def get_applications(
    db: DbSession,
    current_user: CurrentUser,
    status: str | None = None,
):
    """Get all applications."""
    app_service = ApplicationService(db)

    status_filter = None
    if status:
        try:
            status_filter = ApplicationStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}",
            )

    applications = await app_service.get_user_applications(
        current_user, status=status_filter
    )
    return applications


@router.get("/stats", response_model=ApplicationStatsResponse)
async def get_application_stats(db: DbSession, current_user: CurrentUser):
    """Get application statistics."""
    app_service = ApplicationService(db)
    stats = await app_service.get_application_stats(current_user)

    return ApplicationStatsResponse(
        total_applications=stats["total_applications"],
        pending_review=stats.get("pending_review", 0),
        submitted=stats.get("submitted", 0),
        in_progress=stats.get("in_progress", 0),
        offers=stats.get("offer", 0),
        rejected=stats.get("rejected", 0),
        withdrawn=stats.get("withdrawn", 0),
        response_rate=stats["response_rate"],
    )


@router.get("/{app_id}", response_model=ApplicationResponse)
async def get_application(
    app_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Get a specific application."""
    app_service = ApplicationService(db)
    application = await app_service.get_application_by_id(app_id, current_user.id)

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    return application


@router.patch("/{app_id}", response_model=ApplicationResponse)
async def update_application(
    app_id: int,
    data: ApplicationUpdate,
    db: DbSession,
    current_user: CurrentUser,
):
    """Update application status or notes."""
    app_service = ApplicationService(db)
    application = await app_service.get_application_by_id(app_id, current_user.id)

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    if data.status:
        try:
            status_enum = ApplicationStatus(data.status)
            application = await app_service.update_application_status(
                application, status_enum, data.user_notes
            )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {data.status}",
            )

    return application


@router.post("/{app_id}/submit", response_model=ApplicationResponse)
async def submit_application(
    app_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Mark application as submitted."""
    app_service = ApplicationService(db)
    application = await app_service.get_application_by_id(app_id, current_user.id)

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    submitted = await app_service.submit_application(application)
    return submitted
