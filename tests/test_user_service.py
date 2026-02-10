"""Tests for user service."""

import pytest

from app.services.user_service import UserService
from app.schemas.user import UserCreate, UserUpdate, UserPreferencesUpdate


@pytest.mark.asyncio
async def test_create_user(db_session, sample_user_data):
    """Test creating a new user."""
    user_service = UserService(db_session)
    user_data = UserCreate(**sample_user_data)

    user = await user_service.create(user_data)

    assert user.id is not None
    assert user.telegram_id == sample_user_data["telegram_id"]
    assert user.telegram_username == sample_user_data["telegram_username"]
    assert user.first_name == sample_user_data["first_name"]
    assert user.preferences is not None


@pytest.mark.asyncio
async def test_get_user_by_telegram_id(db_session, sample_user_data):
    """Test retrieving user by Telegram ID."""
    user_service = UserService(db_session)
    user_data = UserCreate(**sample_user_data)

    created_user = await user_service.create(user_data)
    await db_session.flush()

    found_user = await user_service.get_by_telegram_id(sample_user_data["telegram_id"])

    assert found_user is not None
    assert found_user.id == created_user.id


@pytest.mark.asyncio
async def test_get_or_create_existing_user(db_session, sample_user_data):
    """Test get_or_create returns existing user."""
    user_service = UserService(db_session)
    user_data = UserCreate(**sample_user_data)

    user1, created1 = await user_service.get_or_create(user_data)
    await db_session.flush()

    user2, created2 = await user_service.get_or_create(user_data)

    assert created1 is True
    assert created2 is False
    assert user1.id == user2.id


@pytest.mark.asyncio
async def test_update_user(db_session, sample_user_data):
    """Test updating user profile."""
    user_service = UserService(db_session)
    user_data = UserCreate(**sample_user_data)

    user = await user_service.create(user_data)
    await db_session.flush()

    update_data = UserUpdate(
        current_title="Senior Engineer",
        years_of_experience=5,
        location="San Francisco, CA",
    )

    updated_user = await user_service.update(user, update_data)

    assert updated_user.current_title == "Senior Engineer"
    assert updated_user.years_of_experience == 5
    assert updated_user.location == "San Francisco, CA"


@pytest.mark.asyncio
async def test_complete_onboarding(db_session, sample_user_data):
    """Test marking onboarding as complete."""
    user_service = UserService(db_session)
    user_data = UserCreate(**sample_user_data)

    user = await user_service.create(user_data)
    await db_session.flush()

    assert user.onboarding_completed is False

    await user_service.complete_onboarding(user)

    assert user.onboarding_completed is True
