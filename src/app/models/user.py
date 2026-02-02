"""User-related database models."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Enum as SQLEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.application import Application, ApplicationDraft
    from app.models.job import SavedJob
    from app.models.resume import Resume


class UserStatus(str, Enum):
    """User account status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class JobSearchStatus(str, Enum):
    """User's job search status."""

    ACTIVELY_LOOKING = "actively_looking"
    CASUALLY_LOOKING = "casually_looking"
    NOT_LOOKING = "not_looking"


class User(Base):
    """User model - represents a job seeker."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    telegram_username: Mapped[str | None] = mapped_column(String(255))

    # Profile info
    first_name: Mapped[str | None] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(50))

    # Professional info
    headline: Mapped[str | None] = mapped_column(String(500))
    summary: Mapped[str | None] = mapped_column(Text)
    years_of_experience: Mapped[int | None] = mapped_column()
    current_title: Mapped[str | None] = mapped_column(String(255))
    current_company: Mapped[str | None] = mapped_column(String(255))

    # Location
    location: Mapped[str | None] = mapped_column(String(255))
    willing_to_relocate: Mapped[bool] = mapped_column(Boolean, default=False)
    remote_preference: Mapped[str | None] = mapped_column(String(50))  # remote, hybrid, onsite

    # Status
    status: Mapped[UserStatus] = mapped_column(
        SQLEnum(UserStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=UserStatus.ACTIVE
    )
    job_search_status: Mapped[JobSearchStatus] = mapped_column(
        SQLEnum(JobSearchStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=JobSearchStatus.ACTIVELY_LOOKING
    )

    # Onboarding
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    onboarding_step: Mapped[int] = mapped_column(default=0)

    # Usage tracking
    ai_calls_today: Mapped[int] = mapped_column(default=0)
    ai_calls_reset_at: Mapped[datetime | None] = mapped_column()
    last_active_at: Mapped[datetime | None] = mapped_column()

    # Relationships
    preferences: Mapped["UserPreferences"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    skills: Mapped[list["UserSkill"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    resumes: Mapped[list["Resume"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    saved_jobs: Mapped[list["SavedJob"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    applications: Mapped[list["Application"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    application_drafts: Mapped[list["ApplicationDraft"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def full_name(self) -> str:
        """Get user's full name."""
        parts = [self.first_name, self.last_name]
        return " ".join(p for p in parts if p) or "Unknown"


class UserPreferences(Base):
    """User job search preferences."""

    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )

    # Job preferences
    desired_titles: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    desired_industries: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    excluded_companies: Mapped[list[str] | None] = mapped_column(ARRAY(String))

    # Salary
    min_salary: Mapped[int | None] = mapped_column()
    max_salary: Mapped[int | None] = mapped_column()
    salary_currency: Mapped[str] = mapped_column(String(3), default="USD")

    # Location preferences
    preferred_locations: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    max_commute_minutes: Mapped[int | None] = mapped_column()

    # Job type
    job_types: Mapped[list[str] | None] = mapped_column(ARRAY(String))  # full-time, part-time, contract
    experience_levels: Mapped[list[str] | None] = mapped_column(ARRAY(String))  # entry, mid, senior

    # Notification settings
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    notification_frequency: Mapped[str] = mapped_column(String(50), default="daily")
    quiet_hours_start: Mapped[int | None] = mapped_column()  # Hour in UTC
    quiet_hours_end: Mapped[int | None] = mapped_column()

    # AI preferences
    ai_matching_strictness: Mapped[str] = mapped_column(String(50), default="balanced")
    auto_generate_cover_letters: Mapped[bool] = mapped_column(Boolean, default=True)

    # Custom filters as JSON
    custom_filters: Mapped[dict | None] = mapped_column(JSONB)

    # Relationship
    user: Mapped["User"] = relationship(back_populates="preferences")


class UserSkill(Base):
    """User skills with proficiency levels."""

    __tablename__ = "user_skills"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    name: Mapped[str] = mapped_column(String(255), index=True)
    proficiency: Mapped[str | None] = mapped_column(String(50))  # beginner, intermediate, expert
    years_experience: Mapped[int | None] = mapped_column()
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationship
    user: Mapped["User"] = relationship(back_populates="skills")
