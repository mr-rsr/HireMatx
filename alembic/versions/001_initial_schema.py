"""Initial database schema

Revision ID: 001
Revises:
Create Date: 2024-02-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('telegram_username', sa.String(255), nullable=True),
        sa.Column('first_name', sa.String(255), nullable=True),
        sa.Column('last_name', sa.String(255), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('headline', sa.String(500), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('years_of_experience', sa.Integer(), nullable=True),
        sa.Column('current_title', sa.String(255), nullable=True),
        sa.Column('current_company', sa.String(255), nullable=True),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('willing_to_relocate', sa.Boolean(), default=False),
        sa.Column('remote_preference', sa.String(50), nullable=True),
        sa.Column('status', sa.Enum('active', 'inactive', 'suspended', name='userstatus'), default='active'),
        sa.Column('job_search_status', sa.Enum('actively_looking', 'casually_looking', 'not_looking', name='jobsearchstatus'), default='actively_looking'),
        sa.Column('onboarding_completed', sa.Boolean(), default=False),
        sa.Column('onboarding_step', sa.Integer(), default=0),
        sa.Column('ai_calls_today', sa.Integer(), default=0),
        sa.Column('ai_calls_reset_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_active_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_telegram_id', 'users', ['telegram_id'], unique=True)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # User preferences table
    op.create_table(
        'user_preferences',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('desired_titles', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('desired_industries', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('excluded_companies', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('min_salary', sa.Integer(), nullable=True),
        sa.Column('max_salary', sa.Integer(), nullable=True),
        sa.Column('salary_currency', sa.String(3), default='USD'),
        sa.Column('preferred_locations', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('max_commute_minutes', sa.Integer(), nullable=True),
        sa.Column('job_types', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('experience_levels', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('notifications_enabled', sa.Boolean(), default=True),
        sa.Column('notification_frequency', sa.String(50), default='daily'),
        sa.Column('quiet_hours_start', sa.Integer(), nullable=True),
        sa.Column('quiet_hours_end', sa.Integer(), nullable=True),
        sa.Column('ai_matching_strictness', sa.String(50), default='balanced'),
        sa.Column('auto_generate_cover_letters', sa.Boolean(), default=True),
        sa.Column('custom_filters', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id')
    )

    # User skills table
    op.create_table(
        'user_skills',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('proficiency', sa.String(50), nullable=True),
        sa.Column('years_experience', sa.Integer(), nullable=True),
        sa.Column('is_primary', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('ix_user_skills_name', 'user_skills', ['name'])

    # Job sources table
    op.create_table(
        'job_sources',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('base_url', sa.String(500), nullable=False),
        sa.Column('scraper_type', sa.String(50), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('requests_per_minute', sa.Integer(), default=10),
        sa.Column('last_scraped_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scrape_interval_minutes', sa.Integer(), default=60),
        sa.Column('config', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Jobs table
    op.create_table(
        'jobs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('external_id', sa.String(255), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('company', sa.String(255), nullable=False),
        sa.Column('company_logo_url', sa.String(500), nullable=True),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('is_remote', sa.Boolean(), default=False),
        sa.Column('remote_type', sa.String(50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('description_html', sa.Text(), nullable=True),
        sa.Column('requirements', sa.Text(), nullable=True),
        sa.Column('benefits', sa.Text(), nullable=True),
        sa.Column('job_type', sa.Enum('full_time', 'part_time', 'contract', 'freelance', 'internship', name='jobtype'), nullable=True),
        sa.Column('experience_level', sa.Enum('entry', 'mid', 'senior', 'lead', 'executive', name='experiencelevel'), nullable=True),
        sa.Column('industry', sa.String(255), nullable=True),
        sa.Column('department', sa.String(255), nullable=True),
        sa.Column('required_skills', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('preferred_skills', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('salary_min', sa.Integer(), nullable=True),
        sa.Column('salary_max', sa.Integer(), nullable=True),
        sa.Column('salary_currency', sa.String(3), nullable=True),
        sa.Column('salary_period', sa.String(20), nullable=True),
        sa.Column('salary_text', sa.String(255), nullable=True),
        sa.Column('url', sa.String(1000), nullable=False),
        sa.Column('apply_url', sa.String(1000), nullable=True),
        sa.Column('posted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scraped_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.Enum('active', 'expired', 'filled', 'removed', name='jobstatus'), default='active'),
        sa.Column('search_vector', postgresql.TSVECTOR(), nullable=True),
        sa.Column('raw_data', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['source_id'], ['job_sources.id']),
        sa.UniqueConstraint('source_id', 'external_id', name='uq_job_source_external')
    )
    op.create_index('ix_jobs_external_id', 'jobs', ['external_id'])
    op.create_index('ix_jobs_title', 'jobs', ['title'])
    op.create_index('ix_jobs_company', 'jobs', ['company'])
    op.create_index('ix_jobs_location', 'jobs', ['location'])
    op.create_index('ix_jobs_is_remote', 'jobs', ['is_remote'])
    op.create_index('ix_jobs_posted_at', 'jobs', ['posted_at'])
    op.create_index('ix_jobs_search', 'jobs', ['title', 'company', 'location'])

    # Resumes table
    op.create_table(
        'resumes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('file_type', sa.String(50), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('file_hash', sa.String(64), nullable=True),
        sa.Column('status', sa.Enum('pending', 'processing', 'processed', 'failed', name='resumestatus'), default='pending'),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('parsed_data', postgresql.JSONB(), nullable=True),
        sa.Column('ai_summary', sa.Text(), nullable=True),
        sa.Column('ai_skills_extracted', postgresql.JSONB(), nullable=True),
        sa.Column('ai_experience_level', sa.String(50), nullable=True),
        sa.Column('ai_job_titles', postgresql.JSONB(), nullable=True),
        sa.Column('is_primary', sa.Boolean(), default=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )

    # Saved jobs table
    op.create_table(
        'saved_jobs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('match_score', sa.Float(), nullable=True),
        sa.Column('match_reasons', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('is_interested', sa.Boolean(), nullable=True),
        sa.Column('dismissed', sa.Boolean(), default=False),
        sa.Column('notified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'job_id', name='uq_saved_job_user_job')
    )

    # Application drafts table
    op.create_table(
        'application_drafts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('cover_letter', sa.Text(), nullable=True),
        sa.Column('cover_letter_tone', sa.String(50), nullable=True),
        sa.Column('application_answers', postgresql.JSONB(), nullable=True),
        sa.Column('ai_model_used', sa.String(100), nullable=True),
        sa.Column('ai_prompt_tokens', sa.Integer(), nullable=True),
        sa.Column('ai_completion_tokens', sa.Integer(), nullable=True),
        sa.Column('user_feedback', sa.Text(), nullable=True),
        sa.Column('revision_count', sa.Integer(), default=0),
        sa.Column('is_approved', sa.Boolean(), default=False),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE')
    )

    # Applications table
    op.create_table(
        'applications',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('draft_id', sa.Integer(), nullable=True),
        sa.Column('cover_letter', sa.Text(), nullable=True),
        sa.Column('resume_version', sa.String(255), nullable=True),
        sa.Column('application_answers', postgresql.JSONB(), nullable=True),
        sa.Column('status', sa.Enum('draft', 'pending_review', 'approved', 'submitted', 'viewed', 'in_progress', 'offer', 'rejected', 'withdrawn', name='applicationstatus'), default='draft'),
        sa.Column('status_history', postgresql.JSONB(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('submission_method', sa.String(50), nullable=True),
        sa.Column('external_application_id', sa.String(255), nullable=True),
        sa.Column('follow_up_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('follow_up_sent', sa.Boolean(), default=False),
        sa.Column('user_notes', sa.Text(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('response_received_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('interview_scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['draft_id'], ['application_drafts.id']),
        sa.UniqueConstraint('user_id', 'job_id', name='uq_application_user_job')
    )


def downgrade() -> None:
    op.drop_table('applications')
    op.drop_table('application_drafts')
    op.drop_table('saved_jobs')
    op.drop_table('resumes')
    op.drop_table('jobs')
    op.drop_table('job_sources')
    op.drop_table('user_skills')
    op.drop_table('user_preferences')
    op.drop_table('users')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS applicationstatus')
    op.execute('DROP TYPE IF EXISTS resumestatus')
    op.execute('DROP TYPE IF EXISTS jobstatus')
    op.execute('DROP TYPE IF EXISTS experiencelevel')
    op.execute('DROP TYPE IF EXISTS jobtype')
    op.execute('DROP TYPE IF EXISTS jobsearchstatus')
    op.execute('DROP TYPE IF EXISTS userstatus')
