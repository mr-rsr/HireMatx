"""Application management handlers."""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, ContentType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.application import ApplicationStatus
from app.services.application_service import ApplicationService
from app.services.job_service import JobService
from app.services.user_service import UserService
from app.services.resume_service import ResumeService
from app.bot.keyboards import (
    draft_action_keyboard,
    tone_selection_keyboard,
    application_status_keyboard,
    main_menu_keyboard,
)

router = Router()


class ApplicationStates(StatesGroup):
    """Application FSM states."""

    waiting_feedback = State()
    viewing_draft = State()


@router.callback_query(F.data.startswith("job_apply_"))
async def start_application(callback: CallbackQuery, user: User, db: AsyncSession):
    """Start application process for a job."""
    job_id = int(callback.data.split("_")[-1])

    # Check if user has a resume
    resume_service = ResumeService(db)
    primary_resume = await resume_service.get_primary_resume(user)

    if not primary_resume:
        await callback.answer()
        await callback.message.answer(
            "📄 <b>Resume Required</b>\n\n"
            "Please upload your resume first for better cover letters!\n\n"
            "Send me a PDF or DOCX file, or use /resume to manage your resumes."
        )
        return

    # Check AI rate limit
    user_service = UserService(db)
    if not await user_service.increment_ai_calls(user):
        await callback.answer("Daily AI limit reached. Try again tomorrow!", show_alert=True)
        return

    await callback.answer("🤖 Generating cover letter...")

    # Get job and generate draft
    job_service = JobService(db)
    job = await job_service.get_job_by_id(job_id)

    if not job:
        await callback.answer("Job no longer available.", show_alert=True)
        return

    app_service = ApplicationService(db)
    draft = await app_service.generate_draft(user=user, job=job)

    # Show draft
    draft_text = f"""
<b>📝 Cover Letter Draft</b>

<b>Position:</b> {job.title}
<b>Company:</b> {job.company}
<b>Tone:</b> {draft.cover_letter_tone}

---

{draft.cover_letter}

---

<i>Review the draft above. You can approve it, regenerate with feedback, or change the tone.</i>
"""

    await callback.message.answer(
        draft_text,
        reply_markup=draft_action_keyboard(draft.id),
    )


@router.callback_query(F.data.startswith("draft_approve_"))
async def approve_draft(callback: CallbackQuery, user: User, db: AsyncSession):
    """Approve a draft and create application."""
    draft_id = int(callback.data.split("_")[-1])

    app_service = ApplicationService(db)
    draft = await app_service.get_draft_by_id(draft_id, user.id)

    if not draft:
        await callback.answer("Draft not found.", show_alert=True)
        return

    # Approve and create application
    await app_service.approve_draft(draft)
    application = await app_service.create_application(user, draft)

    await callback.answer()
    await callback.message.edit_text(
        f"✅ <b>Application Created!</b>\n\n"
        f"Your application for <b>{draft.job.title}</b> at <b>{draft.job.company}</b> "
        f"has been created.\n\n"
        f"<b>Next Steps:</b>\n"
        f"1. Visit the job posting: {draft.job.url}\n"
        f"2. Submit your application manually\n"
        f"3. Update the status here when done\n\n"
        f"Use /applications to track your progress."
    )


@router.callback_query(F.data.startswith("draft_regen_"))
async def request_regeneration_feedback(callback: CallbackQuery, state: FSMContext):
    """Request feedback for regeneration."""
    draft_id = int(callback.data.split("_")[-1])

    await callback.answer()
    await callback.message.answer(
        "<b>🔄 Regenerate Cover Letter</b>\n\n"
        "What would you like to change? Send me your feedback.\n\n"
        "<i>Examples:\n"
        "• Make it more specific to the job requirements\n"
        "• Emphasize my leadership experience\n"
        "• Make it shorter and more concise\n"
        "• Highlight my Python skills more</i>"
    )
    await state.set_state(ApplicationStates.waiting_feedback)
    await state.update_data(draft_id=draft_id)


@router.message(ApplicationStates.waiting_feedback)
async def process_regeneration_feedback(
    message: Message, state: FSMContext, user: User, db: AsyncSession
):
    """Process feedback and regenerate draft."""
    feedback = message.text.strip()
    data = await state.get_data()
    draft_id = data.get("draft_id")

    # Check AI rate limit
    user_service = UserService(db)
    if not await user_service.increment_ai_calls(user):
        await message.answer("Daily AI limit reached. Try again tomorrow!")
        await state.clear()
        return

    app_service = ApplicationService(db)
    draft = await app_service.get_draft_by_id(draft_id, user.id)

    if not draft:
        await message.answer("Draft not found.")
        await state.clear()
        return

    await message.answer("🤖 Regenerating with your feedback...")

    updated_draft = await app_service.regenerate_draft(
        draft=draft,
        user=user,
        feedback=feedback,
    )

    draft_text = f"""
<b>📝 Updated Cover Letter (Revision {updated_draft.revision_count})</b>

---

{updated_draft.cover_letter}

---

<i>Happy with this version?</i>
"""

    await message.answer(
        draft_text,
        reply_markup=draft_action_keyboard(draft_id),
    )
    await state.clear()


@router.callback_query(F.data.startswith("draft_tone_"))
async def show_tone_options(callback: CallbackQuery):
    """Show tone selection options."""
    draft_id = int(callback.data.split("_")[-1])
    await callback.answer()
    await callback.message.answer(
        "<b>✏️ Select Cover Letter Tone</b>\n\n"
        "Choose the tone for your cover letter:",
        reply_markup=tone_selection_keyboard(draft_id),
    )


@router.callback_query(F.data.startswith("tone_"))
async def change_tone(callback: CallbackQuery, user: User, db: AsyncSession):
    """Regenerate draft with new tone."""
    parts = callback.data.split("_")
    tone = parts[1]
    draft_id = int(parts[2])

    # Check AI rate limit
    user_service = UserService(db)
    if not await user_service.increment_ai_calls(user):
        await callback.answer("Daily AI limit reached!", show_alert=True)
        return

    await callback.answer(f"Regenerating with {tone} tone...")

    app_service = ApplicationService(db)
    draft = await app_service.get_draft_by_id(draft_id, user.id)

    if not draft:
        await callback.answer("Draft not found.", show_alert=True)
        return

    updated_draft = await app_service.regenerate_draft(
        draft=draft,
        user=user,
        new_tone=tone,
    )

    draft_text = f"""
<b>📝 Cover Letter ({tone.title()} Tone)</b>

---

{updated_draft.cover_letter}

---
"""

    await callback.message.answer(
        draft_text,
        reply_markup=draft_action_keyboard(draft_id),
    )


@router.message(Command("applications"))
@router.message(F.text == "💼 My Applications")
async def show_applications(message: Message, user: User, db: AsyncSession):
    """Show user's applications."""
    app_service = ApplicationService(db)
    applications = await app_service.get_user_applications(user)

    if not applications:
        await message.answer(
            "You haven't applied to any jobs yet.\n\n"
            "Use /search to find jobs and start applying!",
            reply_markup=main_menu_keyboard(),
        )
        return

    text = f"<b>💼 Your Applications ({len(applications)})</b>\n\n"

    status_emoji = {
        "draft": "📝",
        "pending_review": "⏳",
        "approved": "✅",
        "submitted": "📤",
        "viewed": "👀",
        "in_progress": "📞",
        "offer": "🎉",
        "rejected": "❌",
        "withdrawn": "🔙",
    }

    for app in applications[:10]:
        emoji = status_emoji.get(app.status.value, "📋")
        text += f"{emoji} <b>{app.job.title}</b> at {app.job.company}\n"
        text += f"   Status: {app.status.value.replace('_', ' ').title()}\n"
        text += f"   /app_{app.id}\n\n"

    await message.answer(text)


@router.message(F.text.startswith("/app_"))
async def view_application(message: Message, user: User, db: AsyncSession):
    """View specific application details."""
    try:
        app_id = int(message.text.split("_")[1])
    except (IndexError, ValueError):
        await message.answer("Invalid application ID.")
        return

    app_service = ApplicationService(db)
    application = await app_service.get_application_by_id(app_id, user.id)

    if not application:
        await message.answer("Application not found.")
        return

    job = application.job

    text = f"""
<b>📋 Application Details</b>

<b>Position:</b> {job.title}
<b>Company:</b> {job.company}
<b>Status:</b> {application.status.value.replace('_', ' ').title()}

<b>Applied:</b> {application.submitted_at.strftime('%Y-%m-%d') if application.submitted_at else 'Not yet'}

<b>Cover Letter:</b>
{application.cover_letter[:500] if application.cover_letter else 'No cover letter'}...

<b>Update the status:</b>
"""

    await message.answer(
        text,
        reply_markup=application_status_keyboard(app_id),
    )


@router.callback_query(F.data.startswith("appstatus_"))
async def update_application_status(callback: CallbackQuery, user: User, db: AsyncSession):
    """Update application status."""
    parts = callback.data.split("_")
    status_str = parts[1]
    app_id = int(parts[2])

    try:
        new_status = ApplicationStatus(status_str)
    except ValueError:
        await callback.answer("Invalid status.", show_alert=True)
        return

    app_service = ApplicationService(db)
    application = await app_service.get_application_by_id(app_id, user.id)

    if not application:
        await callback.answer("Application not found.", show_alert=True)
        return

    await app_service.update_application_status(application, new_status)

    status_messages = {
        ApplicationStatus.SUBMITTED: "📤 Marked as submitted! Good luck!",
        ApplicationStatus.VIEWED: "👀 They viewed your application!",
        ApplicationStatus.IN_PROGRESS: "📞 Interview stage - exciting!",
        ApplicationStatus.OFFER: "🎉 Congratulations on the offer!",
        ApplicationStatus.REJECTED: "❌ Sorry to hear. Keep going!",
        ApplicationStatus.WITHDRAWN: "🔙 Application withdrawn.",
    }

    await callback.answer(status_messages.get(new_status, "Status updated!"), show_alert=True)
    await callback.message.edit_text(
        f"✅ Application status updated to: <b>{new_status.value.replace('_', ' ').title()}</b>"
    )


# Resume upload handler
@router.message(F.text == "📄 My Resume")
@router.message(Command("resume"))
async def resume_menu(message: Message, user: User, db: AsyncSession):
    """Show resume management options."""
    resume_service = ResumeService(db)
    resumes = await resume_service.get_user_resumes(user)

    if not resumes:
        await message.answer(
            "<b>📄 Resume</b>\n\n"
            "You haven't uploaded a resume yet.\n\n"
            "Send me a <b>PDF</b> or <b>DOCX</b> file to get started!\n\n"
            "Your resume helps me:\n"
            "• Generate better cover letters\n"
            "• Analyze your skills\n"
            "• Find better job matches"
        )
        return

    text = "<b>📄 Your Resumes</b>\n\n"
    for resume in resumes:
        primary = "⭐ " if resume.is_primary else ""
        status = "✅" if resume.status.value == "processed" else "⏳"
        text += f"{primary}{status} {resume.filename}\n"
        text += f"   Uploaded: {resume.created_at.strftime('%Y-%m-%d')}\n\n"

    text += "\nSend a new PDF/DOCX to upload another resume."

    await message.answer(text)


@router.message(F.content_type == ContentType.DOCUMENT)
async def handle_document_upload(message: Message, user: User, db: AsyncSession):
    """Handle document uploads (resumes)."""
    document = message.document

    # Check file type
    if document.mime_type not in [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]:
        await message.answer(
            "Please upload a PDF or DOCX file.\n"
            "Other file types are not supported."
        )
        return

    # Check file size (10MB limit)
    if document.file_size > 10 * 1024 * 1024:
        await message.answer("File too large. Maximum size is 10MB.")
        return

    await message.answer("📤 Uploading resume...")

    # Download file
    file = await message.bot.get_file(document.file_id)
    file_content = await message.bot.download_file(file.file_path)

    file_type = "pdf" if document.mime_type == "application/pdf" else "docx"

    resume_service = ResumeService(db)

    try:
        resume = await resume_service.upload_resume(
            user=user,
            filename=document.file_name,
            content=file_content.read(),
            file_type=file_type,
        )
    except ValueError as e:
        await message.answer(f"Upload failed: {str(e)}")
        return

    await message.answer(
        f"✅ Resume uploaded: <b>{document.file_name}</b>\n\n"
        f"Processing your resume for AI analysis..."
    )

    # Process resume with AI
    user_service = UserService(db)
    if await user_service.increment_ai_calls(user):
        processed = await resume_service.process_resume(resume)

        if processed.status.value == "processed":
            await message.answer(
                f"🤖 <b>Resume Analysis Complete!</b>\n\n"
                f"<b>Summary:</b>\n{processed.ai_summary}\n\n"
                f"<b>Experience Level:</b> {processed.ai_experience_level or 'Unknown'}\n\n"
                f"Your resume is now ready for generating cover letters!"
            )
        else:
            await message.answer(
                "Resume uploaded but analysis failed. You can still use it for applications."
            )
    else:
        await message.answer(
            "Resume uploaded! AI analysis will be available tomorrow (daily limit reached)."
        )
