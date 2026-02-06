"""User management endpoints."""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserPreferencesUpdate,
    UserPreferencesResponse,
    UserSkillCreate,
)
from app.services.user_service import UserService

router = APIRouter()


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(data: UserCreate, db: DbSession):
    """Create or get existing user (called from Telegram bot)."""
    user_service = UserService(db)
    user, created = await user_service.get_or_create(data)

    if not created:
        # User already exists, update basic info
        from app.schemas.user import UserUpdate
        update_data = UserUpdate(
            first_name=data.first_name,
            last_name=data.last_name,
        )
        user = await user_service.update(user, update_data)

    return user


@router.get("/me", response_model=UserResponse)
async def get_current_user(current_user: CurrentUser):
    """Get current user profile."""
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    data: UserUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    """Update current user profile."""
    user_service = UserService(db)
    return await user_service.update(current_user, data)


@router.get("/me/preferences", response_model=UserPreferencesResponse)
async def get_preferences(current_user: CurrentUser):
    """Get current user's job preferences."""
    if not current_user.preferences:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Preferences not set",
        )
    return current_user.preferences


@router.patch("/me/preferences", response_model=UserPreferencesResponse)
async def update_preferences(
    data: UserPreferencesUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    """Update current user's job preferences."""
    user_service = UserService(db)
    return await user_service.update_preferences(current_user, data)


@router.post("/me/skills", status_code=status.HTTP_201_CREATED)
async def add_skill(
    data: UserSkillCreate,
    current_user: CurrentUser,
    db: DbSession,
):
    """Add a skill to user profile."""
    user_service = UserService(db)
    skill = await user_service.add_skill(current_user, data)
    return {"id": skill.id, "name": skill.name, "proficiency": skill.proficiency}


@router.delete("/me/skills/{skill_name}")
async def remove_skill(
    skill_name: str,
    current_user: CurrentUser,
    db: DbSession,
):
    """Remove a skill from user profile."""
    user_service = UserService(db)
    removed = await user_service.remove_skill(current_user, skill_name)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill not found",
        )
    return {"status": "removed"}


@router.post("/me/onboarding/complete")
async def complete_onboarding(
    current_user: CurrentUser,
    db: DbSession,
):
    """Mark onboarding as complete."""
    user_service = UserService(db)
    await user_service.complete_onboarding(current_user)
    return {"status": "completed"}


@router.patch("/me/onboarding/step/{step}")
async def update_onboarding_step(
    step: int,
    current_user: CurrentUser,
    db: DbSession,
):
    """Update onboarding progress."""
    user_service = UserService(db)
    await user_service.update_onboarding_step(current_user, step)
    return {"step": step}
