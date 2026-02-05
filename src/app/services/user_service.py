"""User management service."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User, UserPreferences, UserSkill, JobSearchStatus
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserPreferencesCreate,
    UserPreferencesUpdate,
    UserSkillCreate,
)


class UserService:
    """Service for user-related operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Get user by Telegram ID."""
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.preferences), selectinload(User.skills))
            .where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> User | None:
        """Get user by internal ID."""
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.preferences), selectinload(User.skills))
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(self, data: UserCreate) -> User:
        """Create a new user from Telegram registration."""
        user = User(
            telegram_id=data.telegram_id,
            telegram_username=data.telegram_username,
            first_name=data.first_name,
            last_name=data.last_name,
            job_search_status=JobSearchStatus.ACTIVELY_LOOKING,
        )
        self.db.add(user)
        await self.db.flush()

        # Create default preferences
        preferences = UserPreferences(user_id=user.id)
        self.db.add(preferences)
        await self.db.flush()

        return user

    async def update(self, user: User, data: UserUpdate) -> User:
        """Update user profile."""
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)

        user.last_active_at = datetime.utcnow()
        await self.db.flush()
        return user

    async def update_preferences(
        self, user: User, data: UserPreferencesUpdate
    ) -> UserPreferences:
        """Update user preferences."""
        if not user.preferences:
            user.preferences = UserPreferences(user_id=user.id)
            self.db.add(user.preferences)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user.preferences, field, value)

        await self.db.flush()
        return user.preferences

    async def add_skill(self, user: User, data: UserSkillCreate) -> UserSkill:
        """Add a skill to user profile."""
        skill = UserSkill(
            user_id=user.id,
            name=data.name,
            proficiency=data.proficiency,
            years_experience=data.years_experience,
            is_primary=data.is_primary,
        )
        self.db.add(skill)
        await self.db.flush()
        return skill

    async def remove_skill(self, user: User, skill_name: str) -> bool:
        """Remove a skill from user profile."""
        result = await self.db.execute(
            select(UserSkill).where(
                UserSkill.user_id == user.id,
                UserSkill.name == skill_name,
            )
        )
        skill = result.scalar_one_or_none()
        if skill:
            await self.db.delete(skill)
            await self.db.flush()
            return True
        return False

    async def complete_onboarding(self, user: User) -> User:
        """Mark user onboarding as complete."""
        user.onboarding_completed = True
        user.onboarding_step = -1  # Completed
        await self.db.flush()
        return user

    async def update_onboarding_step(self, user: User, step: int) -> User:
        """Update user's onboarding progress."""
        user.onboarding_step = step
        await self.db.flush()
        return user

    async def track_activity(self, user: User) -> None:
        """Update user's last active timestamp."""
        user.last_active_at = datetime.utcnow()
        await self.db.flush()

    async def increment_ai_calls(self, user: User) -> bool:
        """Increment AI call counter, return False if limit reached."""
        from app.config import get_settings

        settings = get_settings()
        now = datetime.utcnow()

        # Reset counter if it's a new day
        if user.ai_calls_reset_at is None or user.ai_calls_reset_at.date() < now.date():
            user.ai_calls_today = 0
            user.ai_calls_reset_at = now

        if user.ai_calls_today >= settings.ai_calls_per_user_daily:
            return False

        user.ai_calls_today += 1
        await self.db.flush()
        return True

    async def get_or_create(self, data: UserCreate) -> tuple[User, bool]:
        """Get existing user or create new one. Returns (user, created)."""
        user = await self.get_by_telegram_id(data.telegram_id)
        if user:
            return user, False
        user = await self.create(data)
        return user, True
