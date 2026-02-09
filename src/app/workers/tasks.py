"""Celery tasks for background processing."""

import asyncio
from datetime import datetime, timedelta

import structlog
from sqlalchemy import select, update

from app.workers.celery_app import celery_app
from app.database.session import async_session_maker
from app.models.job import Job, JobSource, JobStatus
from app.models.application import ApplicationDraft
from app.models.user import User, UserStatus
from app.scrapers.remoteok import RemoteOKScraper
from app.scrapers.github_jobs import GitHubJobsScraper
from app.services.job_service import JobService

logger = structlog.get_logger()


def run_async(coro):
    """Run async coroutine in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3)
def scrape_jobs(self, source_name: str):
    """
    Scrape jobs from a specific source.

    Args:
        source_name: Name of the job source to scrape
    """
    logger.info("scrape_jobs_start", source=source_name)

    async def _scrape():
        async with async_session_maker() as db:
            # Get or create source record
            result = await db.execute(
                select(JobSource).where(JobSource.name == source_name)
            )
            source = result.scalar_one_or_none()

            if not source:
                source = JobSource(
                    name=source_name,
                    base_url=get_scraper_class(source_name).base_url,
                    scraper_type="api",
                    is_active=True,
                )
                db.add(source)
                await db.flush()

            # Initialize scraper
            scraper_class = get_scraper_class(source_name)
            if not scraper_class:
                logger.error("unknown_scraper", source=source_name)
                return

            async with scraper_class() as scraper:
                jobs = await scraper.scrape()

                # Save jobs to database
                job_service = JobService(db)
                saved_count = 0

                for job_data in jobs:
                    try:
                        await job_service.upsert_job(
                            source=source,
                            external_id=job_data["external_id"],
                            job_data=job_data,
                        )
                        saved_count += 1
                    except Exception as e:
                        logger.warning(
                            "job_save_error",
                            error=str(e),
                            external_id=job_data.get("external_id"),
                        )

                # Update source metadata
                source.last_scraped_at = datetime.utcnow()
                await db.commit()

                logger.info(
                    "scrape_jobs_complete",
                    source=source_name,
                    jobs_scraped=len(jobs),
                    jobs_saved=saved_count,
                )

    try:
        run_async(_scrape())
    except Exception as e:
        logger.error("scrape_jobs_error", source=source_name, error=str(e))
        raise self.retry(exc=e, countdown=60)


def get_scraper_class(source_name: str):
    """Get scraper class by source name."""
    scrapers = {
        "remoteok": RemoteOKScraper,
        "arbeitnow": GitHubJobsScraper,
    }
    return scrapers.get(source_name)


@celery_app.task
def process_resume(resume_id: int):
    """Process a resume with AI analysis."""
    logger.info("process_resume_start", resume_id=resume_id)

    async def _process():
        from app.models.resume import Resume
        from app.services.resume_service import ResumeService

        async with async_session_maker() as db:
            result = await db.execute(
                select(Resume).where(Resume.id == resume_id)
            )
            resume = result.scalar_one_or_none()

            if not resume:
                logger.error("resume_not_found", resume_id=resume_id)
                return

            resume_service = ResumeService(db)
            await resume_service.process_resume(resume)
            await db.commit()

            logger.info("process_resume_complete", resume_id=resume_id)

    run_async(_process())


@celery_app.task
def send_daily_notifications():
    """Send daily job recommendations to users."""
    logger.info("send_daily_notifications_start")

    async def _send_notifications():
        from app.bot.bot import create_bot
        from app.services.job_service import JobService

        async with async_session_maker() as db:
            # Get active users with notifications enabled
            result = await db.execute(
                select(User)
                .where(
                    User.status == UserStatus.ACTIVE,
                    User.onboarding_completed == True,
                )
            )
            users = result.scalars().all()

            bot = create_bot()
            job_service = JobService(db)

            for user in users:
                if not user.preferences or not user.preferences.notifications_enabled:
                    continue

                try:
                    # Get job recommendations
                    jobs = await job_service.get_jobs_for_user(user, limit=5)

                    if not jobs:
                        continue

                    # Format notification
                    text = "<b>🎯 Your Daily Job Recommendations</b>\n\n"
                    for i, job in enumerate(jobs, 1):
                        text += f"{i}. <b>{job.title}</b>\n"
                        text += f"   🏢 {job.company}\n"
                        text += f"   📍 {job.location or 'Remote'}\n\n"

                    text += "Use /jobs to see more recommendations!"

                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=text,
                        parse_mode="HTML",
                    )

                except Exception as e:
                    logger.warning(
                        "notification_send_error",
                        user_id=user.id,
                        error=str(e),
                    )

            await bot.session.close()

        logger.info("send_daily_notifications_complete", users_notified=len(users))

    run_async(_send_notifications())


@celery_app.task
def cleanup_expired_drafts():
    """Clean up expired application drafts."""
    logger.info("cleanup_expired_drafts_start")

    async def _cleanup():
        async with async_session_maker() as db:
            now = datetime.utcnow()

            result = await db.execute(
                update(ApplicationDraft)
                .where(
                    ApplicationDraft.expires_at < now,
                    ApplicationDraft.is_approved == False,
                )
                .values(is_approved=False)  # Mark as expired
            )

            await db.commit()
            logger.info("cleanup_expired_drafts_complete", cleaned=result.rowcount)

    run_async(_cleanup())


@celery_app.task
def expire_old_jobs():
    """Mark jobs older than 30 days as expired."""
    logger.info("expire_old_jobs_start")

    async def _expire():
        async with async_session_maker() as db:
            cutoff = datetime.utcnow() - timedelta(days=30)

            result = await db.execute(
                update(Job)
                .where(
                    Job.posted_at < cutoff,
                    Job.status == JobStatus.ACTIVE,
                )
                .values(status=JobStatus.EXPIRED)
            )

            await db.commit()
            logger.info("expire_old_jobs_complete", expired=result.rowcount)

    run_async(_expire())


@celery_app.task
def generate_cover_letter(user_id: int, job_id: int, tone: str = "professional"):
    """Generate cover letter asynchronously."""
    logger.info("generate_cover_letter_start", user_id=user_id, job_id=job_id)

    async def _generate():
        from app.services.application_service import ApplicationService

        async with async_session_maker() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

            result = await db.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()

            if not user or not job:
                logger.error("user_or_job_not_found", user_id=user_id, job_id=job_id)
                return

            app_service = ApplicationService(db)
            draft = await app_service.generate_draft(user=user, job=job, tone=tone)
            await db.commit()

            logger.info(
                "generate_cover_letter_complete",
                draft_id=draft.id,
            )

            return draft.id

    return run_async(_generate())
