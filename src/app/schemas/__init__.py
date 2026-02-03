"""Pydantic schemas for API validation."""

from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserPreferencesCreate,
    UserPreferencesUpdate,
    UserPreferencesResponse,
    UserSkillCreate,
)
from app.schemas.job import (
    JobResponse,
    JobSearchParams,
    SavedJobCreate,
    SavedJobResponse,
    JobMatchResponse,
)
from app.schemas.application import (
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationResponse,
    ApplicationDraftResponse,
    GenerateDraftRequest,
)
from app.schemas.resume import (
    ResumeUploadResponse,
    ResumeResponse,
    ResumeAnalysisResponse,
)

__all__ = [
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserPreferencesCreate",
    "UserPreferencesUpdate",
    "UserPreferencesResponse",
    "UserSkillCreate",
    "JobResponse",
    "JobSearchParams",
    "SavedJobCreate",
    "SavedJobResponse",
    "JobMatchResponse",
    "ApplicationCreate",
    "ApplicationUpdate",
    "ApplicationResponse",
    "ApplicationDraftResponse",
    "GenerateDraftRequest",
    "ResumeUploadResponse",
    "ResumeResponse",
    "ResumeAnalysisResponse",
]
