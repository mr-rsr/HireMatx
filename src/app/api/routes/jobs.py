"""Job search endpoints."""

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.job import (
    JobResponse,
    JobSearchParams,
    JobMatchResponse,
    SavedJobCreate,
    SavedJobResponse,
)
from app.services.job_service import JobService
from app.services.ai_service import AIService
from app.services.user_service import UserService

router = APIRouter()


@router.get("", response_model=list[JobResponse])
async def search_jobs(
    db: DbSession,
    current_user: CurrentUser,
    query: str | None = None,
    locations: list[str] | None = Query(None),
    is_remote: bool | None = None,
    job_types: list[str] | None = Query(None),
    experience_levels: list[str] | None = Query(None),
    min_salary: int | None = None,
    max_salary: int | None = None,
    posted_within_days: int | None = None,
    page: int = 1,
    page_size: int = 20,
):
    """Search for jobs with filters."""
    params = JobSearchParams(
        query=query,
        locations=locations,
        is_remote=is_remote,
        job_types=job_types,
        experience_levels=experience_levels,
        min_salary=min_salary,
        max_salary=max_salary,
        posted_within_days=posted_within_days,
        page=page,
        page_size=page_size,
    )

    job_service = JobService(db)
    jobs, total = await job_service.search_jobs(params, current_user)

    return jobs


@router.get("/recommendations", response_model=list[JobResponse])
async def get_job_recommendations(
    db: DbSession,
    current_user: CurrentUser,
    limit: int = Query(default=20, le=50),
):
    """Get personalized job recommendations based on user profile."""
    job_service = JobService(db)
    jobs = await job_service.get_jobs_for_user(current_user, limit=limit)
    return jobs


@router.get("/match/{job_id}", response_model=JobMatchResponse)
async def get_job_match(
    job_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Get AI-powered match analysis for a specific job."""
    job_service = JobService(db)
    job = await job_service.get_job_by_id(job_id)

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

    # Get AI match analysis
    ai_service = AIService()
    match_data = await ai_service.match_job(current_user, job)

    return JobMatchResponse(
        job=JobResponse.model_validate(job),
        match_score=match_data["match_score"],
        match_reasons=match_data["match_reasons"],
        missing_skills=match_data["missing_skills"],
        matching_skills=match_data["matching_skills"],
        salary_match=match_data["salary_match"],
        location_match=match_data["location_match"],
        recommendation=match_data["recommendation"],
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: int, db: DbSession, current_user: CurrentUser):
    """Get job details by ID."""
    job_service = JobService(db)
    job = await job_service.get_job_by_id(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    return job


@router.post("/saved", response_model=SavedJobResponse, status_code=status.HTTP_201_CREATED)
async def save_job(
    data: SavedJobCreate,
    db: DbSession,
    current_user: CurrentUser,
):
    """Save a job for later."""
    job_service = JobService(db)

    # Verify job exists
    job = await job_service.get_job_by_id(data.job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    saved = await job_service.save_job(current_user, data)
    return saved


@router.get("/saved/list", response_model=list[SavedJobResponse])
async def get_saved_jobs(db: DbSession, current_user: CurrentUser):
    """Get all saved jobs."""
    job_service = JobService(db)
    saved_jobs = await job_service.get_saved_jobs(current_user)
    return saved_jobs


@router.post("/{job_id}/dismiss")
async def dismiss_job(
    job_id: int,
    db: DbSession,
    current_user: CurrentUser,
):
    """Dismiss a job from recommendations."""
    job_service = JobService(db)
    await job_service.dismiss_job(current_user, job_id)
    return {"status": "dismissed"}


@router.post("/{job_id}/feedback")
async def provide_job_feedback(
    job_id: int,
    is_interested: bool,
    db: DbSession,
    current_user: CurrentUser,
):
    """Provide feedback on a job match."""
    job_service = JobService(db)
    await job_service.update_job_feedback(current_user, job_id, is_interested)
    return {"status": "feedback recorded"}
