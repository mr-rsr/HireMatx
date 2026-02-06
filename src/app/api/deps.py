"""API dependencies."""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.user_service import UserService


async def get_current_user_from_telegram(
    x_telegram_id: Annotated[int, Header()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Get current user from Telegram ID header."""
    user_service = UserService(db)
    user = await user_service.get_by_telegram_id(x_telegram_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. Please register via Telegram bot first.",
        )

    # Track activity
    await user_service.track_activity(user)

    return user


# Type alias for dependency injection
CurrentUser = Annotated[User, Depends(get_current_user_from_telegram)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
