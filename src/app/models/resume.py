"""Resume model."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum as SQLEnum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class ResumeStatus(str, Enum):
    """Resume processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class Resume(Base):
    """User resume model."""

    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    # File info
    filename: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[str] = mapped_column(String(50))  # pdf, docx
    file_size: Mapped[int] = mapped_column()  # bytes
    file_path: Mapped[str] = mapped_column(String(500))  # S3 path or local path
    file_hash: Mapped[str | None] = mapped_column(String(64))  # SHA-256 for dedup

    # Processing status
    status: Mapped[ResumeStatus] = mapped_column(
        SQLEnum(ResumeStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=ResumeStatus.PENDING
    )
    processed_at: Mapped[datetime | None] = mapped_column()
    error_message: Mapped[str | None] = mapped_column(Text)

    # Parsed content
    raw_text: Mapped[str | None] = mapped_column(Text)
    parsed_data: Mapped[dict | None] = mapped_column(JSONB)  # Structured resume data

    # AI analysis
    ai_summary: Mapped[str | None] = mapped_column(Text)
    ai_skills_extracted: Mapped[dict | None] = mapped_column(JSONB)
    ai_experience_level: Mapped[str | None] = mapped_column(String(50))
    ai_job_titles: Mapped[dict | None] = mapped_column(JSONB)  # Suggested job titles

    # Flags
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationship
    user: Mapped["User"] = relationship(back_populates="resumes")
