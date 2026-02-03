"""Application-related Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.job import JobResponse


class GenerateDraftRequest(BaseModel):
    """Schema for requesting AI draft generation."""

    job_id: int
    cover_letter_tone: str = Field(default="professional", max_length=50)
    custom_instructions: str | None = None


class ApplicationDraftResponse(BaseModel):
    """Schema for application draft response."""

    id: int
    job_id: int
    cover_letter: str | None
    cover_letter_tone: str | None
    application_answers: dict | None
    revision_count: int
    is_approved: bool
    created_at: datetime
    expires_at: datetime | None
    job: JobResponse | None = None

    model_config = {"from_attributes": True}


class ApplicationCreate(BaseModel):
    """Schema for creating an application from approved draft."""

    draft_id: int
    cover_letter: str | None = None  # Allow user to override
    user_notes: str | None = None


class ApplicationUpdate(BaseModel):
    """Schema for updating application status."""

    status: str | None = None
    user_notes: str | None = None
    follow_up_date: datetime | None = None


class ApplicationResponse(BaseModel):
    """Schema for application response."""

    id: int
    job: JobResponse
    status: str
    cover_letter: str | None
    submitted_at: datetime | None
    follow_up_date: datetime | None
    user_notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ApplicationStatsResponse(BaseModel):
    """Schema for application statistics."""

    total_applications: int
    pending_review: int
    submitted: int
    in_progress: int
    offers: int
    rejected: int
    withdrawn: int
    response_rate: float
