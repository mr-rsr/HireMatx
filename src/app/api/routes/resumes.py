"""Resume management endpoints."""

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.api.deps import CurrentUser, DbSession
from app.config import get_settings
from app.schemas.resume import (
    ResumeUploadResponse,
    ResumeResponse,
    ResumeAnalysisResponse,
)
from app.services.resume_service import ResumeService
from app.services.user_service import UserService

router = APIRouter()


@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(
    file: UploadFile = File(...),
    db: DbSession = None,
    current_user: CurrentUser = None,
):
    """Upload a resume file (PDF or DOCX)."""
    settings = get_settings()

    # Validate file type
    allowed_types = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF and DOCX files are supported",
        )

    # Read file content
    content = await file.read()

    # Validate file size
    max_size = settings.resume_max_size_mb * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds {settings.resume_max_size_mb}MB limit",
        )

    # Determine file type
    file_type = "pdf" if file.content_type == "application/pdf" else "docx"

    resume_service = ResumeService(db)

    try:
        resume = await resume_service.upload_resume(
            user=current_user,
            filename=file.filename,
            content=content,
            file_type=file_type,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return ResumeUploadResponse(
        id=resume.id,
        filename=resume.filename,
        file_type=resume.file_type,
        status=resume.status.value,
        message="Resume uploaded successfully. Processing will begin shortly.",
    )


@router.post("/{resume_id}/process", response_model=ResumeResponse)
async def process_resume(
    resume_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Trigger AI processing of a resume."""
    resume_service = ResumeService(db)
    resumes = await resume_service.get_user_resumes(current_user)

    resume = next((r for r in resumes if r.id == resume_id), None)
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )

    # Check AI rate limit
    user_service = UserService(db)
    if not await user_service.increment_ai_calls(current_user):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily AI usage limit reached",
        )

    processed = await resume_service.process_resume(resume)
    return processed


@router.get("", response_model=list[ResumeResponse])
async def get_resumes(db: DbSession, current_user: CurrentUser):
    """Get all user resumes."""
    resume_service = ResumeService(db)
    resumes = await resume_service.get_user_resumes(current_user)
    return resumes


@router.get("/{resume_id}", response_model=ResumeResponse)
async def get_resume(
    resume_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Get a specific resume."""
    resume_service = ResumeService(db)
    resumes = await resume_service.get_user_resumes(current_user)

    resume = next((r for r in resumes if r.id == resume_id), None)
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )

    return resume


@router.get("/{resume_id}/analysis", response_model=ResumeAnalysisResponse)
async def get_resume_analysis(
    resume_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Get AI analysis of a processed resume."""
    resume_service = ResumeService(db)
    resumes = await resume_service.get_user_resumes(current_user)

    resume = next((r for r in resumes if r.id == resume_id), None)
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )

    if resume.status.value != "processed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resume has not been processed yet",
        )

    parsed = resume.parsed_data or {}
    skills = resume.ai_skills_extracted or {}

    return ResumeAnalysisResponse(
        summary=resume.ai_summary or "",
        experience_level=resume.ai_experience_level or "unknown",
        years_of_experience=None,
        skills_extracted=skills.get("skills", []),
        suggested_titles=(resume.ai_job_titles or {}).get("titles", []),
        industries=parsed.get("industries", []),
        strengths=parsed.get("strengths", []),
        improvement_suggestions=parsed.get("improvement_suggestions", []),
        ats_score=parsed.get("ats_score", 0),
        ats_suggestions=parsed.get("ats_suggestions", []),
    )


@router.post("/{resume_id}/set-primary")
async def set_primary_resume(
    resume_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Set a resume as the primary resume."""
    resume_service = ResumeService(db)
    resume = await resume_service.set_primary_resume(current_user, resume_id)

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )

    return {"status": "primary", "resume_id": resume_id}


@router.delete("/{resume_id}")
async def delete_resume(
    resume_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Delete a resume."""
    resume_service = ResumeService(db)
    deleted = await resume_service.delete_resume(current_user, resume_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )

    return {"status": "deleted"}
