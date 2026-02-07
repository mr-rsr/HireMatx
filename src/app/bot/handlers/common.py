"""Common bot handlers (start, help, etc.)."""

from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.bot.keyboards import main_menu_keyboard, onboarding_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, user: User, db: AsyncSession):
    """Handle /start command."""
    if not user.onboarding_completed:
        welcome_text = f"""
👋 <b>Welcome to Job Search AI, {user.first_name or 'there'}!</b>

I'm your personal AI assistant for finding your dream job. Here's what I can do:

🔍 <b>Smart Job Search</b> - Find jobs matching your skills
📝 <b>AI Applications</b> - Generate tailored cover letters
📊 <b>Match Analysis</b> - See how well you fit each role
📈 <b>Track Progress</b> - Monitor all your applications

Let's set up your profile to get personalized recommendations!
"""
        await message.answer(welcome_text, reply_markup=onboarding_keyboard())
    else:
        await message.answer(
            f"Welcome back, {user.first_name}! 👋\n\nWhat would you like to do today?",
            reply_markup=main_menu_keyboard(),
        )


@router.message(Command("help"))
@router.message(F.text == "❓ Help")
async def cmd_help(message: Message):
    """Handle /help command."""
    help_text = """
<b>📚 Job Search AI Help</b>

<b>Commands:</b>
/start - Start or restart the bot
/search - Search for jobs
/jobs - View job recommendations
/applications - View your applications
/resume - Manage your resume
/settings - Update preferences
/stats - View your statistics
/help - Show this help message

<b>Quick Actions:</b>
• Send a job title to search
• Upload a PDF/DOCX resume
• Use the menu buttons below

<b>Tips:</b>
• Complete your profile for better matches
• Upload your resume for AI-powered analysis
• Review AI drafts before applying

Need more help? Contact support at support@jobsearch.ai
"""
    await message.answer(help_text)


@router.message(F.text == "📊 Stats")
async def show_stats(message: Message, user: User, db: AsyncSession):
    """Show user statistics."""
    from app.services.application_service import ApplicationService

    app_service = ApplicationService(db)
    stats = await app_service.get_application_stats(user)

    stats_text = f"""
<b>📊 Your Job Search Statistics</b>

<b>Applications:</b>
• Total: {stats['total_applications']}
• Submitted: {stats.get('submitted', 0)}
• In Progress: {stats.get('in_progress', 0)}
• Offers: {stats.get('offer', 0)}
• Rejected: {stats.get('rejected', 0)}

<b>Response Rate:</b> {stats['response_rate']:.1f}%

Keep applying! Consistency is key to landing your dream job. 💪
"""
    await message.answer(stats_text)


@router.message(F.text == "⚙️ Settings")
async def show_settings(message: Message, user: User):
    """Show settings menu."""
    from app.bot.keyboards import settings_keyboard

    settings_text = f"""
<b>⚙️ Settings</b>

<b>Current Profile:</b>
• Name: {user.full_name}
• Title: {user.current_title or 'Not set'}
• Location: {user.location or 'Not set'}
• Remote: {user.remote_preference or 'Any'}

Select what you'd like to update:
"""
    await message.answer(settings_text, reply_markup=settings_keyboard())


@router.message(Command("cancel"))
async def cmd_cancel(message: Message):
    """Cancel current operation."""
    await message.answer(
        "Operation cancelled. What would you like to do?",
        reply_markup=main_menu_keyboard(),
    )
