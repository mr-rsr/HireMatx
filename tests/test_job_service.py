"""Tests for job service."""

import pytest

from app.models.job import JobSource
from app.services.job_service import JobService
from app.services.user_service import UserService
from app.schemas.user import UserCreate
from app.schemas.job import JobSearchParams


@pytest.mark.asyncio
async def test_upsert_job(db_session, sample_job_data):
    """Test creating/updating a job."""
    job_service = JobService(db_session)

    # Create a source first
    source = JobSource(
        name="test_source",
        base_url="https://example.com",
        scraper_type="api",
    )
    db_session.add(source)
    await db_session.flush()

    # Create job
    job = await job_service.upsert_job(
        source=source,
        external_id=sample_job_data["external_id"],
        job_data=sample_job_data,
    )

    assert job.id is not None
    assert job.title == sample_job_data["title"]
    assert job.company == sample_job_data["company"]
    assert job.is_remote is True


@pytest.mark.asyncio
async def test_search_jobs(db_session, sample_job_data):
    """Test searching for jobs."""
    job_service = JobService(db_session)

    # Create a source and job
    source = JobSource(
        name="test_source",
        base_url="https://example.com",
        scraper_type="api",
    )
    db_session.add(source)
    await db_session.flush()

    await job_service.upsert_job(
        source=source,
        external_id=sample_job_data["external_id"],
        job_data=sample_job_data,
    )
    await db_session.flush()

    # Search for jobs
    params = JobSearchParams(query="Software Engineer")
    jobs, total = await job_service.search_jobs(params)

    assert total >= 1
    assert len(jobs) >= 1
    assert jobs[0].title == sample_job_data["title"]


@pytest.mark.asyncio
async def test_search_jobs_by_remote(db_session, sample_job_data):
    """Test filtering jobs by remote status."""
    job_service = JobService(db_session)

    source = JobSource(
        name="test_source",
        base_url="https://example.com",
        scraper_type="api",
    )
    db_session.add(source)
    await db_session.flush()

    await job_service.upsert_job(
        source=source,
        external_id=sample_job_data["external_id"],
        job_data=sample_job_data,
    )
    await db_session.flush()

    # Search for remote jobs
    params = JobSearchParams(is_remote=True)
    jobs, total = await job_service.search_jobs(params)

    assert total >= 1
    assert all(job.is_remote for job in jobs)


@pytest.mark.asyncio
async def test_get_job_by_id(db_session, sample_job_data):
    """Test getting job by ID."""
    job_service = JobService(db_session)

    source = JobSource(
        name="test_source",
        base_url="https://example.com",
        scraper_type="api",
    )
    db_session.add(source)
    await db_session.flush()

    job = await job_service.upsert_job(
        source=source,
        external_id=sample_job_data["external_id"],
        job_data=sample_job_data,
    )
    await db_session.flush()

    found_job = await job_service.get_job_by_id(job.id)

    assert found_job is not None
    assert found_job.id == job.id
    assert found_job.title == sample_job_data["title"]
