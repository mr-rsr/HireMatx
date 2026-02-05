"""Application management service."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.application import Application, ApplicationDraft, ApplicationStatus
from app.models.job import Job
from app.models.user import User
from app.services.ai_service import AIService
from app.services.resume_service import ResumeService


class ApplicationService:
    """Service for job application management."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_service = AIService()

    async def generate_draft(
        self,
        user: User,
        job: Job,
        tone: str = "professional",
        custom_instructions: str | None = None,
    ) -> ApplicationDraft:
        """Generate an AI draft for a job application."""
        # Get user's resume text
        resume_service = ResumeService(self.db)
        primary_resume = await resume_service.get_primary_resume(user)
        resume_text = None
        if primary_resume:
            resume_text = await resume_service.get_resume_text(primary_resume)

        # Generate cover letter
        cover_letter, input_tokens, output_tokens = await self.ai_service.generate_cover_letter(
            user=user,
            job=job,
            resume_text=resume_text,
            tone=tone,
            custom_instructions=custom_instructions,
        )

        # Create draft
        draft = ApplicationDraft(
            user_id=user.id,
            job_id=job.id,
            cover_letter=cover_letter,
            cover_letter_tone=tone,
            ai_model_used="claude-3-sonnet",
            ai_prompt_tokens=input_tokens,
            ai_completion_tokens=output_tokens,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        self.db.add(draft)
        await self.db.flush()

        return draft

    async def regenerate_draft(
        self,
        draft: ApplicationDraft,
        user: User,
        feedback: str | None = None,
        new_tone: str | None = None,
    ) -> ApplicationDraft:
        """Regenerate a draft with user feedback."""
        # Get the job
        result = await self.db.execute(
            select(Job).where(Job.id == draft.job_id)
        )
        job = result.scalar_one()

        # Build custom instructions from feedback
        custom_instructions = feedback

        # Generate new cover letter
        resume_service = ResumeService(self.db)
        primary_resume = await resume_service.get_primary_resume(user)
        resume_text = None
        if primary_resume:
            resume_text = await resume_service.get_resume_text(primary_resume)

        tone = new_tone or draft.cover_letter_tone or "professional"

        cover_letter, input_tokens, output_tokens = await self.ai_service.generate_cover_letter(
            user=user,
            job=job,
            resume_text=resume_text,
            tone=tone,
            custom_instructions=custom_instructions,
        )

        # Update draft
        draft.cover_letter = cover_letter
        draft.cover_letter_tone = tone
        draft.user_feedback = feedback
        draft.revision_count += 1
        draft.ai_prompt_tokens = (draft.ai_prompt_tokens or 0) + input_tokens
        draft.ai_completion_tokens = (draft.ai_completion_tokens or 0) + output_tokens

        await self.db.flush()
        return draft

    async def approve_draft(self, draft: ApplicationDraft) -> ApplicationDraft:
        """Mark a draft as approved."""
        draft.is_approved = True
        draft.approved_at = datetime.now(timezone.utc)
        await self.db.flush()
        return draft

    async def create_application(
        self,
        user: User,
        draft: ApplicationDraft,
        cover_letter_override: str | None = None,
        notes: str | None = None,
    ) -> Application:
        """Create an application from an approved draft."""
        application = Application(
            user_id=user.id,
            job_id=draft.job_id,
            draft_id=draft.id,
            cover_letter=cover_letter_override or draft.cover_letter,
            application_answers=draft.application_answers,
            status=ApplicationStatus.APPROVED,
            user_notes=notes,
        )
        self.db.add(application)
        await self.db.flush()

        return application

    async def submit_application(self, application: Application) -> Application:
        """Mark application as submitted."""
        application.status = ApplicationStatus.SUBMITTED
        application.submitted_at = datetime.now(timezone.utc)
        application.submission_method = "manual"

        # Update status history
        history = application.status_history or []
        history.append({
            "status": "submitted",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        application.status_history = history

        await self.db.flush()
        return application

    async def update_application_status(
        self,
        application: Application,
        status: ApplicationStatus,
        notes: str | None = None,
    ) -> Application:
        """Update application status."""
        old_status = application.status
        application.status = status

        # Update timestamps based on status
        if status == ApplicationStatus.VIEWED:
            application.response_received_at = datetime.now(timezone.utc)
        elif status in [ApplicationStatus.IN_PROGRESS, ApplicationStatus.OFFER]:
            application.interview_scheduled_at = datetime.now(timezone.utc)

        # Update status history
        history = application.status_history or []
        history.append({
            "status": status.value,
            "previous_status": old_status.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "notes": notes,
        })
        application.status_history = history

        if notes:
            if status == ApplicationStatus.REJECTED:
                application.rejection_reason = notes
            else:
                application.user_notes = notes

        await self.db.flush()
        return application

    async def get_user_applications(
        self,
        user: User,
        status: ApplicationStatus | None = None,
    ) -> list[Application]:
        """Get all applications for a user."""
        query = (
            select(Application)
            .options(selectinload(Application.job))
            .where(Application.user_id == user.id)
        )

        if status:
            query = query.where(Application.status == status)

        query = query.order_by(Application.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_user_drafts(self, user: User) -> list[ApplicationDraft]:
        """Get all pending drafts for a user."""
        result = await self.db.execute(
            select(ApplicationDraft)
            .options(selectinload(ApplicationDraft.job))
            .where(
                ApplicationDraft.user_id == user.id,
                ApplicationDraft.is_approved == False,
                ApplicationDraft.expires_at > datetime.now(timezone.utc),
            )
            .order_by(ApplicationDraft.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_application_stats(self, user: User) -> dict:
        """Get application statistics for a user."""
        stats = {}

        # Total applications
        result = await self.db.execute(
            select(func.count())
            .select_from(Application)
            .where(Application.user_id == user.id)
        )
        stats["total_applications"] = result.scalar() or 0

        # Count by status
        for status in ApplicationStatus:
            result = await self.db.execute(
                select(func.count())
                .select_from(Application)
                .where(
                    Application.user_id == user.id,
                    Application.status == status,
                )
            )
            stats[status.value] = result.scalar() or 0

        # Response rate
        responded_statuses = [
            ApplicationStatus.VIEWED,
            ApplicationStatus.IN_PROGRESS,
            ApplicationStatus.OFFER,
            ApplicationStatus.REJECTED,
        ]
        result = await self.db.execute(
            select(func.count())
            .select_from(Application)
            .where(
                Application.user_id == user.id,
                Application.status.in_(responded_statuses),
            )
        )
        responded = result.scalar() or 0
        submitted = stats.get("submitted", 0) + responded
        stats["response_rate"] = (responded / submitted * 100) if submitted > 0 else 0

        return stats

    async def get_draft_by_id(self, draft_id: int, user_id: int) -> ApplicationDraft | None:
        """Get a draft by ID for a specific user."""
        result = await self.db.execute(
            select(ApplicationDraft)
            .options(selectinload(ApplicationDraft.job))
            .where(
                ApplicationDraft.id == draft_id,
                ApplicationDraft.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_application_by_id(self, app_id: int, user_id: int) -> Application | None:
        """Get an application by ID for a specific user."""
        result = await self.db.execute(
            select(Application)
            .options(selectinload(Application.job))
            .where(
                Application.id == app_id,
                Application.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()
