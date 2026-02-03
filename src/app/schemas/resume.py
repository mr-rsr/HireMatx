"""Resume-related Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel


class ResumeUploadResponse(BaseModel):
    """Schema for resume upload response."""

    id: int
    filename: str
    file_type: str
    status: str
    message: str


class ResumeResponse(BaseModel):
    """Schema for resume response."""

    id: int
    filename: str
    file_type: str
    file_size: int
    status: str
    is_primary: bool
    is_active: bool
    created_at: datetime
    processed_at: datetime | None
    ai_summary: str | None
    ai_experience_level: str | None

    model_config = {"from_attributes": True}


class ResumeAnalysisResponse(BaseModel):
    """Schema for AI resume analysis."""

    summary: str
    experience_level: str
    years_of_experience: int | None
    skills_extracted: list[dict]  # [{name, proficiency, years}]
    suggested_titles: list[str]
    industries: list[str]
    strengths: list[str]
    improvement_suggestions: list[str]
    ats_score: int  # 0-100 ATS compatibility score
    ats_suggestions: list[str]


class SkillGapAnalysis(BaseModel):
    """Schema for skill gap analysis between resume and job."""

    job_id: int
    job_title: str
    matching_skills: list[str]
    missing_required_skills: list[str]
    missing_preferred_skills: list[str]
    skill_match_percentage: float
    recommendations: list[str]
    learning_resources: list[dict] | None = None  # [{skill, resource_url, resource_type}]
