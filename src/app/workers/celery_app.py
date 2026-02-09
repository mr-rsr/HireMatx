"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "job_search_platform",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.tasks",
    ],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max per task
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
)

# Scheduled tasks (beat)
celery_app.conf.beat_schedule = {
    # Scrape RemoteOK every 2 hours
    "scrape-remoteok": {
        "task": "app.workers.tasks.scrape_jobs",
        "schedule": crontab(minute=0, hour="*/2"),
        "args": ["remoteok"],
    },
    # Scrape Arbeitnow every 3 hours
    "scrape-arbeitnow": {
        "task": "app.workers.tasks.scrape_jobs",
        "schedule": crontab(minute=30, hour="*/3"),
        "args": ["arbeitnow"],
    },
    # Send daily job notifications at 9 AM UTC
    "daily-notifications": {
        "task": "app.workers.tasks.send_daily_notifications",
        "schedule": crontab(minute=0, hour=9),
    },
    # Clean up expired drafts daily at midnight
    "cleanup-drafts": {
        "task": "app.workers.tasks.cleanup_expired_drafts",
        "schedule": crontab(minute=0, hour=0),
    },
    # Mark old jobs as expired daily
    "expire-old-jobs": {
        "task": "app.workers.tasks.expire_old_jobs",
        "schedule": crontab(minute=0, hour=1),
    },
}
