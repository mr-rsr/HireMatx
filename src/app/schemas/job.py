"""Job-related Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class JobResponse(BaseModel):
    """Schema for job response."""

    id: int
    title: str
    company: str
    company_logo_url: str | None
    location: str | None
    is_remote: bool
    remote_type: str | None
    description: str | None
    job_type: str | None
    experience_level: str | None
    required_skills: list[str] | None
    salary_min: int | None
    salary_max: int | None
    salary_currency: str | None
    salary_text: str | None
    url: str
    apply_url: str | None
    posted_at: datetime | None
    source_name: str | None = None

    model_config = {"from_attributes": True}


class JobSearchParams(BaseModel):
    """Schema for job search parameters."""

    query: str | None = None
    titles: list[str] | None = None
    locations: list[str] | None = None
    is_remote: bool | None = None
    job_types: list[str] | None = None
    experience_levels: list[str] | None = None
    min_salary: int | None = None
    max_salary: int | None = None
    skills: list[str] | None = None
    companies: list[str] | None = None
    exclude_companies: list[str] | None = None
    posted_within_days: int | None = Field(None, ge=1, le=90)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class SavedJobCreate(BaseModel):
    """Schema for saving a job."""

    job_id: int
    notes: str | None = None


class SavedJobResponse(BaseModel):
    """Schema for saved job response."""

    id: int
    job: JobResponse
    notes: str | None
    match_score: float | None
    match_reasons: list[str] | None
    is_interested: bool | None
    created_at: datetime

    model_config = {"from_attributes": True}


class JobMatchResponse(BaseModel):
    """Schema for AI job match response."""

    job: JobResponse
    match_score: float = Field(..., ge=0, le=100)
    match_reasons: list[str]
    missing_skills: list[str]
    matching_skills: list[str]
    salary_match: bool | None
    location_match: bool
    recommendation: str  # "strong_match", "good_match", "consider", "weak_match"
