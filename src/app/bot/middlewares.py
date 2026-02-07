"""Bot middlewares for database and user injection."""

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

from app.database import async_session_maker
from app.services.user_service import UserService
from app.schemas.user import UserCreate


class DatabaseMiddleware(BaseMiddleware):
    """Middleware to inject database session into handlers."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with async_session_maker() as session:
            data["db"] = session
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise


class UserMiddleware(BaseMiddleware):
    """Middleware to inject current user into handlers."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # Get telegram user from event
        telegram_user = None
        if isinstance(event, Message):
            telegram_user = event.from_user
        elif isinstance(event, CallbackQuery):
            telegram_user = event.from_user

        if not telegram_user:
            return await handler(event, data)

        # Get or create user
        db = data.get("db")
        if db:
            user_service = UserService(db)
            user_data = UserCreate(
                telegram_id=telegram_user.id,
                telegram_username=telegram_user.username,
                first_name=telegram_user.first_name,
                last_name=telegram_user.last_name,
            )
            user, _ = await user_service.get_or_create(user_data)
            data["user"] = user

        return await handler(event, data)
