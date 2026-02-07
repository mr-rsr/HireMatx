"""Onboarding flow handlers."""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.user_service import UserService
from app.schemas.user import UserUpdate, UserPreferencesUpdate, UserSkillCreate
from app.bot.keyboards import (
    main_menu_keyboard,
    job_type_keyboard,
    remote_preference_keyboard,
    experience_level_keyboard,
)

router = Router()


class OnboardingStates(StatesGroup):
    """Onboarding FSM states."""

    waiting_title = State()
    waiting_experience = State()
    waiting_location = State()
    waiting_skills = State()
    waiting_job_types = State()
    waiting_remote = State()
    waiting_exp_levels = State()
    waiting_salary_min = State()
    waiting_salary_max = State()


@router.callback_query(F.data == "onboarding_start")
async def start_onboarding(callback: CallbackQuery, state: FSMContext, user: User):
    """Start the onboarding process."""
    await callback.answer()
    await callback.message.edit_text(
        "<b>Step 1/7: Your Current Role</b>\n\n"
        "What's your current or most recent job title?\n\n"
        "<i>Example: Software Engineer, Product Manager, Data Analyst</i>"
    )
    await state.set_state(OnboardingStates.waiting_title)


@router.message(OnboardingStates.waiting_title)
async def process_title(message: Message, state: FSMContext, user: User, db: AsyncSession):
    """Process job title input."""
    title = message.text.strip()

    user_service = UserService(db)
    await user_service.update(user, UserUpdate(current_title=title))
    await user_service.update_onboarding_step(user, 1)

    await state.update_data(current_title=title)
    await message.answer(
        f"<b>Step 2/7: Experience</b>\n\n"
        f"Great! You're a <b>{title}</b>.\n\n"
        f"How many years of professional experience do you have?\n\n"
        f"<i>Just enter a number (e.g., 5)</i>"
    )
    await state.set_state(OnboardingStates.waiting_experience)


@router.message(OnboardingStates.waiting_experience)
async def process_experience(message: Message, state: FSMContext, user: User, db: AsyncSession):
    """Process years of experience input."""
    try:
        years = int(message.text.strip())
        if years < 0 or years > 50:
            raise ValueError()
    except ValueError:
        await message.answer("Please enter a valid number of years (0-50).")
        return

    user_service = UserService(db)
    await user_service.update(user, UserUpdate(years_of_experience=years))
    await user_service.update_onboarding_step(user, 2)

    await state.update_data(years_of_experience=years)
    await message.answer(
        f"<b>Step 3/7: Location</b>\n\n"
        f"Nice! {years} years of experience.\n\n"
        f"Where are you located? This helps us find relevant jobs.\n\n"
        f"<i>Example: New York, NY or London, UK or Remote</i>"
    )
    await state.set_state(OnboardingStates.waiting_location)


@router.message(OnboardingStates.waiting_location)
async def process_location(message: Message, state: FSMContext, user: User, db: AsyncSession):
    """Process location input."""
    location = message.text.strip()

    user_service = UserService(db)
    await user_service.update(user, UserUpdate(location=location))
    await user_service.update_onboarding_step(user, 3)

    await state.update_data(location=location)
    await message.answer(
        "<b>Step 4/7: Skills</b>\n\n"
        "What are your top skills? Enter them separated by commas.\n\n"
        "<i>Example: Python, JavaScript, Project Management, Data Analysis</i>"
    )
    await state.set_state(OnboardingStates.waiting_skills)


@router.message(OnboardingStates.waiting_skills)
async def process_skills(message: Message, state: FSMContext, user: User, db: AsyncSession):
    """Process skills input."""
    skills = [s.strip() for s in message.text.split(",") if s.strip()]

    if not skills:
        await message.answer("Please enter at least one skill.")
        return

    user_service = UserService(db)
    for i, skill in enumerate(skills[:10]):  # Limit to 10 skills
        await user_service.add_skill(
            user,
            UserSkillCreate(name=skill, is_primary=i < 3),  # First 3 are primary
        )
    await user_service.update_onboarding_step(user, 4)

    await state.update_data(skills=skills)
    await message.answer(
        f"<b>Step 5/7: Job Types</b>\n\n"
        f"Saved {len(skills)} skills! 🎯\n\n"
        f"What type of employment are you looking for?\n"
        f"<i>Select all that apply, then press Done.</i>",
        reply_markup=job_type_keyboard(),
    )
    await state.set_state(OnboardingStates.waiting_job_types)
    await state.update_data(selected_job_types=[])


@router.callback_query(OnboardingStates.waiting_job_types, F.data.startswith("jobtype_"))
async def process_job_type(callback: CallbackQuery, state: FSMContext):
    """Process job type selection."""
    data = await state.get_data()
    selected = data.get("selected_job_types", [])
    job_type = callback.data.replace("jobtype_", "")

    if job_type == "done":
        if not selected:
            await callback.answer("Please select at least one job type!", show_alert=True)
            return

        await callback.answer()
        await callback.message.edit_text(
            "<b>Step 6/7: Remote Preference</b>\n\n"
            "What's your preference for remote work?",
            reply_markup=remote_preference_keyboard(),
        )
        await state.set_state(OnboardingStates.waiting_remote)
        return

    if job_type in selected:
        selected.remove(job_type)
        await callback.answer(f"Removed {job_type.replace('_', ' ')}")
    else:
        selected.append(job_type)
        await callback.answer(f"Added {job_type.replace('_', ' ')}")

    await state.update_data(selected_job_types=selected)


@router.callback_query(OnboardingStates.waiting_remote, F.data.startswith("remote_"))
async def process_remote_preference(
    callback: CallbackQuery, state: FSMContext, user: User, db: AsyncSession
):
    """Process remote preference selection."""
    remote_pref = callback.data.replace("remote_", "")
    await callback.answer()

    user_service = UserService(db)
    await user_service.update(user, UserUpdate(remote_preference=remote_pref))
    await user_service.update_onboarding_step(user, 6)

    await state.update_data(remote_preference=remote_pref)
    await callback.message.edit_text(
        "<b>Step 7/7: Experience Level</b>\n\n"
        "What experience level positions are you targeting?\n"
        "<i>Select all that apply, then press Done.</i>",
        reply_markup=experience_level_keyboard(),
    )
    await state.set_state(OnboardingStates.waiting_exp_levels)
    await state.update_data(selected_exp_levels=[])


@router.callback_query(OnboardingStates.waiting_exp_levels, F.data.startswith("exp_"))
async def process_exp_level(
    callback: CallbackQuery, state: FSMContext, user: User, db: AsyncSession
):
    """Process experience level selection."""
    data = await state.get_data()
    selected = data.get("selected_exp_levels", [])
    exp_level = callback.data.replace("exp_", "")

    if exp_level == "done":
        if not selected:
            await callback.answer("Please select at least one level!", show_alert=True)
            return

        # Save all preferences
        user_service = UserService(db)
        await user_service.update_preferences(
            user,
            UserPreferencesUpdate(
                job_types=data.get("selected_job_types", []),
                experience_levels=selected,
                preferred_locations=[data.get("location")] if data.get("location") else None,
            ),
        )
        await user_service.complete_onboarding(user)

        await callback.answer()
        await callback.message.edit_text(
            "🎉 <b>Onboarding Complete!</b>\n\n"
            "Your profile is all set up. Here's what you can do now:\n\n"
            "🔍 <b>Search Jobs</b> - Find opportunities matching your profile\n"
            "📄 <b>Upload Resume</b> - Get AI-powered analysis\n"
            "📝 <b>Apply</b> - Generate tailored cover letters\n\n"
            "Let's find your dream job! 🚀"
        )
        await callback.message.answer(
            "Use the menu below to get started:",
            reply_markup=main_menu_keyboard(),
        )
        await state.clear()
        return

    if exp_level in selected:
        selected.remove(exp_level)
        await callback.answer(f"Removed {exp_level}")
    else:
        selected.append(exp_level)
        await callback.answer(f"Added {exp_level}")

    await state.update_data(selected_exp_levels=selected)
