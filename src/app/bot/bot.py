"""Telegram bot setup with aiogram."""

import asyncio
import structlog
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage

from app.config import get_settings
from app.bot.handlers import common, onboarding, jobs, applications
from app.bot.middlewares import DatabaseMiddleware, UserMiddleware

logger = structlog.get_logger()


def create_bot() -> Bot:
    """Create Telegram bot instance."""
    settings = get_settings()

    return Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher() -> Dispatcher:
    """Create dispatcher with storage and handlers."""
    settings = get_settings()

    # Use Redis for FSM storage
    storage = RedisStorage.from_url(str(settings.redis_url))

    dp = Dispatcher(storage=storage)

    # Register middlewares
    dp.message.middleware(DatabaseMiddleware())
    dp.message.middleware(UserMiddleware())
    dp.callback_query.middleware(DatabaseMiddleware())
    dp.callback_query.middleware(UserMiddleware())

    # Register handlers
    dp.include_router(common.router)
    dp.include_router(onboarding.router)
    dp.include_router(jobs.router)
    dp.include_router(applications.router)

    return dp


async def start_polling():
    """Start bot in polling mode."""
    bot = create_bot()
    dp = create_dispatcher()

    logger.info("starting_telegram_bot")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


def run_bot():
    """Run the bot."""
    asyncio.run(start_polling())


if __name__ == "__main__":
    run_bot()
