"""Application-related database models."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum as SQLEnum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.job import Job
    from app.models.user import User


class ApplicationStatus(str, Enum):
    """Application status."""

    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"  # User needs to review AI draft
    APPROVED = "approved"  # User approved, ready to apply
    SUBMITTED = "submitted"  # Application sent
    VIEWED = "viewed"  # Employer viewed
    IN_PROGRESS = "in_progress"  # Interview process started
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class ApplicationDraft(Base):
    """AI-generated application draft for user review."""

    __tablename__ = "application_drafts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))

    # Generated content
    cover_letter: Mapped[str | None] = mapped_column(Text)
    cover_letter_tone: Mapped[str | None] = mapped_column(String(50))  # professional, casual, enthusiastic

    # Application answers (for sites with questions)
    application_answers: Mapped[dict | None] = mapped_column(JSONB)

    # AI metadata
    ai_model_used: Mapped[str | None] = mapped_column(String(100))
    ai_prompt_tokens: Mapped[int | None] = mapped_column()
    ai_completion_tokens: Mapped[int | None] = mapped_column()

    # User interaction
    user_feedback: Mapped[str | None] = mapped_column(Text)
    revision_count: Mapped[int] = mapped_column(default=0)

    # Status
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_at: Mapped[datetime | None] = mapped_column()
    expires_at: Mapped[datetime | None] = mapped_column()  # Drafts expire after X days

    # Relationships
    user: Mapped["User"] = relationship(back_populates="application_drafts")
    job: Mapped["Job"] = relationship()


class Application(Base):
    """Submitted job application."""

    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_application_user_job"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    draft_id: Mapped[int | None] = mapped_column(ForeignKey("application_drafts.id"))

    # Application content
    cover_letter: Mapped[str | None] = mapped_column(Text)
    resume_version: Mapped[str | None] = mapped_column(String(255))  # Which resume was used
    application_answers: Mapped[dict | None] = mapped_column(JSONB)

    # Status tracking
    status: Mapped[ApplicationStatus] = mapped_column(
        SQLEnum(ApplicationStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=ApplicationStatus.DRAFT
    )
    status_history: Mapped[dict | None] = mapped_column(JSONB)  # [{status, timestamp, notes}]

    # Submission details
    submitted_at: Mapped[datetime | None] = mapped_column()
    submission_method: Mapped[str | None] = mapped_column(String(50))  # manual, automated
    external_application_id: Mapped[str | None] = mapped_column(String(255))

    # Follow-up
    follow_up_date: Mapped[datetime | None] = mapped_column()
    follow_up_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    # Notes
    user_notes: Mapped[str | None] = mapped_column(Text)
    rejection_reason: Mapped[str | None] = mapped_column(Text)

    # Response tracking
    response_received_at: Mapped[datetime | None] = mapped_column()
    interview_scheduled_at: Mapped[datetime | None] = mapped_column()

    # Relationships
    user: Mapped["User"] = relationship(back_populates="applications")
    job: Mapped["Job"] = relationship(back_populates="applications")
    draft: Mapped["ApplicationDraft"] = relationship()
