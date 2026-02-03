"""User-related Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserSkillCreate(BaseModel):
    """Schema for creating a user skill."""

    name: str = Field(..., max_length=255)
    proficiency: str | None = Field(None, max_length=50)
    years_experience: int | None = Field(None, ge=0)
    is_primary: bool = False


class UserSkillResponse(BaseModel):
    """Schema for skill response."""

    id: int
    name: str
    proficiency: str | None
    years_experience: int | None
    is_primary: bool

    model_config = {"from_attributes": True}


class UserPreferencesCreate(BaseModel):
    """Schema for creating user preferences."""

    desired_titles: list[str] | None = None
    desired_industries: list[str] | None = None
    excluded_companies: list[str] | None = None
    min_salary: int | None = Field(None, ge=0)
    max_salary: int | None = Field(None, ge=0)
    salary_currency: str = Field(default="USD", max_length=3)
    preferred_locations: list[str] | None = None
    max_commute_minutes: int | None = Field(None, ge=0)
    job_types: list[str] | None = None
    experience_levels: list[str] | None = None
    notifications_enabled: bool = True
    notification_frequency: str = Field(default="daily", max_length=50)


class UserPreferencesUpdate(BaseModel):
    """Schema for updating user preferences."""

    desired_titles: list[str] | None = None
    desired_industries: list[str] | None = None
    excluded_companies: list[str] | None = None
    min_salary: int | None = None
    max_salary: int | None = None
    salary_currency: str | None = None
    preferred_locations: list[str] | None = None
    max_commute_minutes: int | None = None
    job_types: list[str] | None = None
    experience_levels: list[str] | None = None
    notifications_enabled: bool | None = None
    notification_frequency: str | None = None
    ai_matching_strictness: str | None = None
    auto_generate_cover_letters: bool | None = None


class UserPreferencesResponse(BaseModel):
    """Schema for preferences response."""

    id: int
    desired_titles: list[str] | None
    desired_industries: list[str] | None
    excluded_companies: list[str] | None
    min_salary: int | None
    max_salary: int | None
    salary_currency: str
    preferred_locations: list[str] | None
    max_commute_minutes: int | None
    job_types: list[str] | None
    experience_levels: list[str] | None
    notifications_enabled: bool
    notification_frequency: str
    ai_matching_strictness: str
    auto_generate_cover_letters: bool

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    """Schema for creating a user from Telegram."""

    telegram_id: int
    telegram_username: str | None = None
    first_name: str | None = None
    last_name: str | None = None


class UserUpdate(BaseModel):
    """Schema for updating user profile."""

    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=50)
    headline: str | None = Field(None, max_length=500)
    summary: str | None = None
    years_of_experience: int | None = Field(None, ge=0)
    current_title: str | None = Field(None, max_length=255)
    current_company: str | None = Field(None, max_length=255)
    location: str | None = Field(None, max_length=255)
    willing_to_relocate: bool | None = None
    remote_preference: str | None = Field(None, max_length=50)
    job_search_status: str | None = None


class UserResponse(BaseModel):
    """Schema for user response."""

    id: int
    telegram_id: int
    telegram_username: str | None
    first_name: str | None
    last_name: str | None
    email: str | None
    headline: str | None
    current_title: str | None
    current_company: str | None
    location: str | None
    remote_preference: str | None
    job_search_status: str
    onboarding_completed: bool
    created_at: datetime
    last_active_at: datetime | None
    preferences: UserPreferencesResponse | None = None
    skills: list[UserSkillResponse] = []

    model_config = {"from_attributes": True}
