"""Job search and browsing handlers."""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.job import Job
from app.services.job_service import JobService
from app.services.ai_service import AIService
from app.services.user_service import UserService
from app.schemas.job import JobSearchParams, SavedJobCreate
from app.bot.keyboards import job_action_keyboard, main_menu_keyboard

router = Router()


class JobSearchStates(StatesGroup):
    """Job search FSM states."""

    waiting_query = State()
    browsing_jobs = State()


def format_job_card(job: Job, index: int = None, total: int = None) -> str:
    """Format a job as a Telegram message."""
    header = ""
    if index is not None and total is not None:
        header = f"<b>Job {index}/{total}</b>\n\n"

    location = job.location or "Location not specified"
    if job.is_remote:
        location = f"🏠 Remote" + (f" ({job.remote_type})" if job.remote_type else "")

    salary = job.salary_range or "Salary not disclosed"

    skills = ""
    if job.required_skills:
        skills = f"\n<b>Skills:</b> {', '.join(job.required_skills[:5])}"

    description = ""
    if job.description:
        desc_preview = job.description[:300].replace("<", "&lt;").replace(">", "&gt;")
        if len(job.description) > 300:
            desc_preview += "..."
        description = f"\n\n{desc_preview}"

    return f"""{header}<b>{job.title}</b>
🏢 {job.company}
📍 {location}
💰 {salary}{skills}

{description}

🔗 <a href="{job.url}">View Original Posting</a>"""


@router.message(Command("search"))
@router.message(F.text == "🔍 Search Jobs")
async def start_job_search(message: Message, state: FSMContext, user: User):
    """Start job search."""
    if not user.onboarding_completed:
        await message.answer(
            "Please complete your profile setup first! Use /start to begin.",
        )
        return

    await message.answer(
        "<b>🔍 Job Search</b>\n\n"
        "What kind of job are you looking for?\n\n"
        "<i>Enter a job title, keyword, or skill.\n"
        "Example: Python Developer, Marketing Manager, Remote Data Analyst</i>"
    )
    await state.set_state(JobSearchStates.waiting_query)


@router.message(JobSearchStates.waiting_query)
async def process_search_query(
    message: Message, state: FSMContext, user: User, db: AsyncSession
):
    """Process search query and show results."""
    query = message.text.strip()

    job_service = JobService(db)
    params = JobSearchParams(query=query, page_size=10)
    jobs, total = await job_service.search_jobs(params, user)

    if not jobs:
        await message.answer(
            f"No jobs found for '<b>{query}</b>'. Try different keywords or check your preferences.",
            reply_markup=main_menu_keyboard(),
        )
        await state.clear()
        return

    # Store jobs in state for browsing
    job_ids = [job.id for job in jobs]
    await state.update_data(
        job_ids=job_ids,
        current_index=0,
        total_jobs=total,
        search_query=query,
    )
    await state.set_state(JobSearchStates.browsing_jobs)

    # Show first job
    job = jobs[0]
    await message.answer(
        format_job_card(job, 1, len(jobs)),
        reply_markup=job_action_keyboard(job.id),
        disable_web_page_preview=True,
    )


@router.message(Command("jobs"))
async def show_recommended_jobs(message: Message, state: FSMContext, user: User, db: AsyncSession):
    """Show personalized job recommendations."""
    if not user.onboarding_completed:
        await message.answer("Please complete your profile first! Use /start to begin.")
        return

    job_service = JobService(db)
    jobs = await job_service.get_jobs_for_user(user, limit=10)

    if not jobs:
        await message.answer(
            "No job recommendations available yet. Try searching for jobs or updating your preferences!",
            reply_markup=main_menu_keyboard(),
        )
        return

    job_ids = [job.id for job in jobs]
    await state.update_data(
        job_ids=job_ids,
        current_index=0,
        total_jobs=len(jobs),
        search_query=None,
    )
    await state.set_state(JobSearchStates.browsing_jobs)

    job = jobs[0]
    await message.answer(
        f"<b>🎯 Jobs For You</b>\n\n{format_job_card(job, 1, len(jobs))}",
        reply_markup=job_action_keyboard(job.id),
        disable_web_page_preview=True,
    )


@router.callback_query(F.data == "job_next")
async def show_next_job(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    """Show next job in the list."""
    data = await state.get_data()
    job_ids = data.get("job_ids", [])
    current_index = data.get("current_index", 0)

    if current_index + 1 >= len(job_ids):
        await callback.answer("No more jobs! Try a new search.", show_alert=True)
        return

    current_index += 1
    await state.update_data(current_index=current_index)

    job_service = JobService(db)
    job = await job_service.get_job_by_id(job_ids[current_index])

    if not job:
        await callback.answer("Job no longer available.")
        return

    await callback.answer()
    await callback.message.edit_text(
        format_job_card(job, current_index + 1, len(job_ids)),
        reply_markup=job_action_keyboard(job.id),
        disable_web_page_preview=True,
    )


@router.callback_query(F.data.startswith("job_save_"))
async def save_job(callback: CallbackQuery, user: User, db: AsyncSession):
    """Save a job."""
    job_id = int(callback.data.split("_")[-1])

    job_service = JobService(db)
    try:
        await job_service.save_job(user, SavedJobCreate(job_id=job_id))
        await callback.answer("✅ Job saved! View saved jobs with /saved", show_alert=True)
    except Exception:
        await callback.answer("This job is already saved!", show_alert=True)


@router.callback_query(F.data.startswith("job_dismiss_"))
async def dismiss_job(callback: CallbackQuery, state: FSMContext, user: User, db: AsyncSession):
    """Dismiss a job and show next."""
    job_id = int(callback.data.split("_")[-1])

    job_service = JobService(db)
    await job_service.dismiss_job(user, job_id)

    # Move to next job
    await callback.answer("Job dismissed")
    await show_next_job(callback, state, db)


@router.callback_query(F.data.startswith("job_match_"))
async def show_match_analysis(callback: CallbackQuery, user: User, db: AsyncSession):
    """Show AI match analysis for a job."""
    job_id = int(callback.data.split("_")[-1])

    # Check rate limit
    user_service = UserService(db)
    if not await user_service.increment_ai_calls(user):
        await callback.answer("Daily AI limit reached. Try again tomorrow!", show_alert=True)
        return

    await callback.answer("🤖 Analyzing match...")

    job_service = JobService(db)
    job = await job_service.get_job_by_id(job_id)

    if not job:
        await callback.answer("Job not found.", show_alert=True)
        return

    ai_service = AIService()
    match_data = await ai_service.match_job(user, job)

    # Format match result
    score = match_data["match_score"]
    emoji = "🟢" if score >= 70 else "🟡" if score >= 50 else "🔴"

    matching_skills = ", ".join(match_data["matching_skills"][:5]) or "None identified"
    missing_skills = ", ".join(match_data["missing_skills"][:5]) or "None"

    match_reasons = "\n".join(f"• {r}" for r in match_data["match_reasons"][:3])

    analysis_text = f"""
<b>🎯 Match Analysis</b>

{emoji} <b>Match Score: {score}%</b>

<b>Recommendation:</b> {match_data["recommendation"].replace("_", " ").title()}

<b>Why this matches:</b>
{match_reasons}

<b>✅ Matching Skills:</b>
{matching_skills}

<b>📚 Skills to Develop:</b>
{missing_skills}

<b>Summary:</b>
{match_data.get("summary", "Analysis complete.")}
"""

    await callback.message.answer(analysis_text)


@router.message(Command("saved"))
async def show_saved_jobs(message: Message, user: User, db: AsyncSession):
    """Show saved jobs."""
    job_service = JobService(db)
    saved_jobs = await job_service.get_saved_jobs(user)

    if not saved_jobs:
        await message.answer(
            "You haven't saved any jobs yet. Use /search to find jobs!",
            reply_markup=main_menu_keyboard(),
        )
        return

    text = f"<b>💾 Saved Jobs ({len(saved_jobs)})</b>\n\n"

    for i, saved in enumerate(saved_jobs[:10], 1):
        job = saved.job
        score = f" - {saved.match_score:.0f}% match" if saved.match_score else ""
        text += f"{i}. <b>{job.title}</b> at {job.company}{score}\n"
        text += f"   /view_{job.id}\n\n"

    await message.answer(text)


@router.message(F.text.startswith("/view_"))
async def view_saved_job(message: Message, state: FSMContext, db: AsyncSession):
    """View a specific saved job."""
    try:
        job_id = int(message.text.split("_")[1])
    except (IndexError, ValueError):
        await message.answer("Invalid job ID.")
        return

    job_service = JobService(db)
    job = await job_service.get_job_by_id(job_id)

    if not job:
        await message.answer("Job not found.")
        return

    await message.answer(
        format_job_card(job),
        reply_markup=job_action_keyboard(job.id),
        disable_web_page_preview=True,
    )
