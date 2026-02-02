"""Job-related database models."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.application import Application
    from app.models.user import User


class JobStatus(str, Enum):
    """Job posting status."""

    ACTIVE = "active"
    EXPIRED = "expired"
    FILLED = "filled"
    REMOVED = "removed"


class JobType(str, Enum):
    """Employment type."""

    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    FREELANCE = "freelance"
    INTERNSHIP = "internship"


class ExperienceLevel(str, Enum):
    """Required experience level."""

    ENTRY = "entry"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    EXECUTIVE = "executive"


class JobSource(Base):
    """Job source/board configuration."""

    __tablename__ = "job_sources"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    base_url: Mapped[str] = mapped_column(String(500))
    scraper_type: Mapped[str] = mapped_column(String(50))  # api, html, playwright
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Rate limiting
    requests_per_minute: Mapped[int] = mapped_column(default=10)
    last_scraped_at: Mapped[datetime | None] = mapped_column()
    scrape_interval_minutes: Mapped[int] = mapped_column(default=60)

    # Configuration
    config: Mapped[dict | None] = mapped_column(JSONB)

    # Relationships
    jobs: Mapped[list["Job"]] = relationship(back_populates="source")


class Job(Base):
    """Job posting model."""

    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_job_source_external"),
        Index("ix_jobs_search", "title", "company", "location"),
        Index("ix_jobs_posted_at", "posted_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("job_sources.id"))
    external_id: Mapped[str] = mapped_column(String(255), index=True)

    # Basic info
    title: Mapped[str] = mapped_column(String(500), index=True)
    company: Mapped[str] = mapped_column(String(255), index=True)
    company_logo_url: Mapped[str | None] = mapped_column(String(500))

    # Location
    location: Mapped[str | None] = mapped_column(String(255), index=True)
    is_remote: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    remote_type: Mapped[str | None] = mapped_column(String(50))  # fully_remote, hybrid, onsite

    # Job details
    description: Mapped[str | None] = mapped_column(Text)
    description_html: Mapped[str | None] = mapped_column(Text)
    requirements: Mapped[str | None] = mapped_column(Text)
    benefits: Mapped[str | None] = mapped_column(Text)

    # Classification
    job_type: Mapped[JobType | None] = mapped_column(
        SQLEnum(JobType, values_callable=lambda obj: [e.value for e in obj])
    )
    experience_level: Mapped[ExperienceLevel | None] = mapped_column(
        SQLEnum(ExperienceLevel, values_callable=lambda obj: [e.value for e in obj])
    )
    industry: Mapped[str | None] = mapped_column(String(255))
    department: Mapped[str | None] = mapped_column(String(255))

    # Skills and tags
    required_skills: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    preferred_skills: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String))

    # Salary
    salary_min: Mapped[int | None] = mapped_column()
    salary_max: Mapped[int | None] = mapped_column()
    salary_currency: Mapped[str | None] = mapped_column(String(3))
    salary_period: Mapped[str | None] = mapped_column(String(20))  # hourly, monthly, yearly
    salary_text: Mapped[str | None] = mapped_column(String(255))

    # URLs
    url: Mapped[str] = mapped_column(String(1000))
    apply_url: Mapped[str | None] = mapped_column(String(1000))

    # Dates
    posted_at: Mapped[datetime | None] = mapped_column()
    expires_at: Mapped[datetime | None] = mapped_column()
    scraped_at: Mapped[datetime | None] = mapped_column()

    # Status
    status: Mapped[JobStatus] = mapped_column(
        SQLEnum(JobStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=JobStatus.ACTIVE
    )

    # Full-text search vector
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR)

    # Raw data for debugging
    raw_data: Mapped[dict | None] = mapped_column(JSONB)

    # Relationships
    source: Mapped["JobSource"] = relationship(back_populates="jobs")
    saved_by: Mapped[list["SavedJob"]] = relationship(back_populates="job")
    applications: Mapped[list["Application"]] = relationship(back_populates="job")

    @property
    def salary_range(self) -> str | None:
        """Get formatted salary range."""
        if not self.salary_min and not self.salary_max:
            return self.salary_text

        currency = self.salary_currency or "USD"
        if self.salary_min and self.salary_max:
            return f"{currency} {self.salary_min:,} - {self.salary_max:,}"
        elif self.salary_min:
            return f"{currency} {self.salary_min:,}+"
        elif self.salary_max:
            return f"Up to {currency} {self.salary_max:,}"
        return None


class SavedJob(Base):
    """User's saved/bookmarked jobs."""

    __tablename__ = "saved_jobs"
    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_saved_job_user_job"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))

    # User's notes
    notes: Mapped[str | None] = mapped_column(Text)
    match_score: Mapped[float | None] = mapped_column()  # AI-calculated match percentage
    match_reasons: Mapped[list[str] | None] = mapped_column(ARRAY(String))

    # Status
    is_interested: Mapped[bool | None] = mapped_column()  # User feedback
    dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    notified_at: Mapped[datetime | None] = mapped_column()

    # Relationships
    user: Mapped["User"] = relationship(back_populates="saved_jobs")
    job: Mapped["Job"] = relationship(back_populates="saved_by")
