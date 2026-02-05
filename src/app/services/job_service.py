"""Job search and matching service."""

from datetime import datetime, timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.job import Job, JobSource, JobStatus, SavedJob
from app.models.user import User
from app.schemas.job import JobSearchParams, SavedJobCreate


class JobService:
    """Service for job-related operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def search_jobs(
        self, params: JobSearchParams, user: User | None = None
    ) -> tuple[list[Job], int]:
        """Search jobs with filters. Returns (jobs, total_count)."""
        query = select(Job).where(Job.status == JobStatus.ACTIVE)

        # Text search
        if params.query:
            search_term = f"%{params.query}%"
            query = query.where(
                or_(
                    Job.title.ilike(search_term),
                    Job.company.ilike(search_term),
                    Job.description.ilike(search_term),
                )
            )

        # Title filter
        if params.titles:
            title_filters = [Job.title.ilike(f"%{t}%") for t in params.titles]
            query = query.where(or_(*title_filters))

        # Location filter
        if params.locations:
            location_filters = [Job.location.ilike(f"%{loc}%") for loc in params.locations]
            query = query.where(or_(*location_filters))

        # Remote filter
        if params.is_remote is not None:
            query = query.where(Job.is_remote == params.is_remote)

        # Job type filter
        if params.job_types:
            query = query.where(Job.job_type.in_(params.job_types))

        # Experience level filter
        if params.experience_levels:
            query = query.where(Job.experience_level.in_(params.experience_levels))

        # Salary filter
        if params.min_salary:
            query = query.where(
                or_(
                    Job.salary_max >= params.min_salary,
                    Job.salary_max.is_(None),
                )
            )
        if params.max_salary:
            query = query.where(
                or_(
                    Job.salary_min <= params.max_salary,
                    Job.salary_min.is_(None),
                )
            )

        # Skills filter
        if params.skills:
            skill_filters = [
                or_(
                    Job.required_skills.contains([skill]),
                    Job.preferred_skills.contains([skill]),
                )
                for skill in params.skills
            ]
            query = query.where(or_(*skill_filters))

        # Company filters
        if params.companies:
            company_filters = [Job.company.ilike(f"%{c}%") for c in params.companies]
            query = query.where(or_(*company_filters))
        if params.exclude_companies:
            for company in params.exclude_companies:
                query = query.where(~Job.company.ilike(f"%{company}%"))

        # Posted date filter
        if params.posted_within_days:
            cutoff = datetime.utcnow() - timedelta(days=params.posted_within_days)
            query = query.where(Job.posted_at >= cutoff)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total_count = total_result.scalar() or 0

        # Pagination
        offset = (params.page - 1) * params.page_size
        query = (
            query.order_by(Job.posted_at.desc())
            .offset(offset)
            .limit(params.page_size)
        )

        result = await self.db.execute(query)
        jobs = list(result.scalars().all())

        return jobs, total_count

    async def get_job_by_id(self, job_id: int) -> Job | None:
        """Get a job by ID."""
        result = await self.db.execute(
            select(Job).where(Job.id == job_id)
        )
        return result.scalar_one_or_none()

    async def get_jobs_for_user(
        self, user: User, limit: int = 20
    ) -> list[Job]:
        """Get job recommendations for a user based on their preferences."""
        if not user.preferences:
            return []

        query = select(Job).where(Job.status == JobStatus.ACTIVE)

        # Apply user preferences
        prefs = user.preferences

        if prefs.desired_titles:
            title_filters = [Job.title.ilike(f"%{t}%") for t in prefs.desired_titles]
            query = query.where(or_(*title_filters))

        if prefs.preferred_locations:
            location_filters = [
                Job.location.ilike(f"%{loc}%") for loc in prefs.preferred_locations
            ]
            # Include remote jobs if user has any location preference
            query = query.where(or_(Job.is_remote == True, *location_filters))

        if prefs.job_types:
            # Include jobs with matching type OR NULL (unspecified)
            query = query.where(
                or_(Job.job_type.in_(prefs.job_types), Job.job_type.is_(None))
            )

        if prefs.experience_levels:
            # Include jobs with matching level OR NULL (unspecified)
            query = query.where(
                or_(Job.experience_level.in_(prefs.experience_levels), Job.experience_level.is_(None))
            )

        if prefs.min_salary:
            query = query.where(
                or_(
                    Job.salary_max >= prefs.min_salary,
                    Job.salary_max.is_(None),
                )
            )

        if prefs.excluded_companies:
            for company in prefs.excluded_companies:
                query = query.where(~Job.company.ilike(f"%{company}%"))

        # Exclude already saved/dismissed jobs
        saved_job_ids = select(SavedJob.job_id).where(SavedJob.user_id == user.id)
        query = query.where(~Job.id.in_(saved_job_ids))

        # Order by most recent
        query = query.order_by(Job.posted_at.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def save_job(
        self, user: User, data: SavedJobCreate, match_score: float | None = None
    ) -> SavedJob:
        """Save a job for a user."""
        saved = SavedJob(
            user_id=user.id,
            job_id=data.job_id,
            notes=data.notes,
            match_score=match_score,
        )
        self.db.add(saved)
        await self.db.flush()
        return saved

    async def get_saved_jobs(self, user: User) -> list[SavedJob]:
        """Get all saved jobs for a user."""
        result = await self.db.execute(
            select(SavedJob)
            .options(selectinload(SavedJob.job))
            .where(
                SavedJob.user_id == user.id,
                SavedJob.dismissed == False,
            )
            .order_by(SavedJob.created_at.desc())
        )
        return list(result.scalars().all())

    async def dismiss_job(self, user: User, job_id: int) -> bool:
        """Dismiss a job recommendation."""
        result = await self.db.execute(
            select(SavedJob).where(
                SavedJob.user_id == user.id,
                SavedJob.job_id == job_id,
            )
        )
        saved = result.scalar_one_or_none()

        if saved:
            saved.dismissed = True
        else:
            saved = SavedJob(
                user_id=user.id,
                job_id=job_id,
                dismissed=True,
            )
            self.db.add(saved)

        await self.db.flush()
        return True

    async def update_job_feedback(
        self, user: User, job_id: int, is_interested: bool
    ) -> SavedJob | None:
        """Update user's interest feedback on a job."""
        result = await self.db.execute(
            select(SavedJob).where(
                SavedJob.user_id == user.id,
                SavedJob.job_id == job_id,
            )
        )
        saved = result.scalar_one_or_none()

        if saved:
            saved.is_interested = is_interested
            await self.db.flush()

        return saved

    async def get_job_sources(self, active_only: bool = True) -> list[JobSource]:
        """Get all job sources."""
        query = select(JobSource)
        if active_only:
            query = query.where(JobSource.is_active == True)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def upsert_job(self, source: JobSource, external_id: str, job_data: dict) -> Job:
        """Create or update a job from scraper data."""
        result = await self.db.execute(
            select(Job).where(
                Job.source_id == source.id,
                Job.external_id == external_id,
            )
        )
        job = result.scalar_one_or_none()

        if job:
            # Update existing job
            for field, value in job_data.items():
                if hasattr(job, field):
                    setattr(job, field, value)
            job.scraped_at = datetime.utcnow()
        else:
            # Create new job - remove external_id from job_data to avoid duplicate
            job_data_clean = {k: v for k, v in job_data.items() if k != "external_id"}
            job = Job(
                source_id=source.id,
                external_id=external_id,
                scraped_at=datetime.utcnow(),
                **job_data_clean,
            )
            self.db.add(job)

        await self.db.flush()
        return job
