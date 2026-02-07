"""Telegram keyboard builders."""

from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Build main menu keyboard."""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="🔍 Search Jobs"),
        KeyboardButton(text="💼 My Applications"),
    )
    builder.row(
        KeyboardButton(text="📄 My Resume"),
        KeyboardButton(text="⚙️ Settings"),
    )
    builder.row(
        KeyboardButton(text="📊 Stats"),
        KeyboardButton(text="❓ Help"),
    )
    return builder.as_markup(resize_keyboard=True)


def onboarding_keyboard() -> InlineKeyboardMarkup:
    """Build onboarding start keyboard."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🚀 Let's Get Started!",
            callback_data="onboarding_start",
        )
    )
    return builder.as_markup()


def job_type_keyboard() -> InlineKeyboardMarkup:
    """Build job type selection keyboard."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Full-time", callback_data="jobtype_full_time"),
        InlineKeyboardButton(text="Part-time", callback_data="jobtype_part_time"),
    )
    builder.row(
        InlineKeyboardButton(text="Contract", callback_data="jobtype_contract"),
        InlineKeyboardButton(text="Freelance", callback_data="jobtype_freelance"),
    )
    builder.row(
        InlineKeyboardButton(text="✅ Done", callback_data="jobtype_done"),
    )
    return builder.as_markup()


def remote_preference_keyboard() -> InlineKeyboardMarkup:
    """Build remote preference keyboard."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏠 Remote Only", callback_data="remote_remote"),
    )
    builder.row(
        InlineKeyboardButton(text="🏢 On-site Only", callback_data="remote_onsite"),
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Hybrid OK", callback_data="remote_hybrid"),
    )
    builder.row(
        InlineKeyboardButton(text="🌍 Any", callback_data="remote_any"),
    )
    return builder.as_markup()


def experience_level_keyboard() -> InlineKeyboardMarkup:
    """Build experience level keyboard."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Entry Level", callback_data="exp_entry"),
        InlineKeyboardButton(text="Mid Level", callback_data="exp_mid"),
    )
    builder.row(
        InlineKeyboardButton(text="Senior", callback_data="exp_senior"),
        InlineKeyboardButton(text="Lead/Manager", callback_data="exp_lead"),
    )
    builder.row(
        InlineKeyboardButton(text="✅ Done", callback_data="exp_done"),
    )
    return builder.as_markup()


def job_action_keyboard(job_id: int) -> InlineKeyboardMarkup:
    """Build job action keyboard."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💾 Save", callback_data=f"job_save_{job_id}"),
        InlineKeyboardButton(text="📝 Apply", callback_data=f"job_apply_{job_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="🔍 Match Analysis", callback_data=f"job_match_{job_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="👎 Not Interested", callback_data=f"job_dismiss_{job_id}"),
        InlineKeyboardButton(text="➡️ Next", callback_data="job_next"),
    )
    return builder.as_markup()


def draft_action_keyboard(draft_id: int) -> InlineKeyboardMarkup:
    """Build draft action keyboard."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Approve", callback_data=f"draft_approve_{draft_id}"),
        InlineKeyboardButton(text="🔄 Regenerate", callback_data=f"draft_regen_{draft_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="✏️ Edit Tone", callback_data=f"draft_tone_{draft_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="❌ Cancel", callback_data=f"draft_cancel_{draft_id}"),
    )
    return builder.as_markup()


def tone_selection_keyboard(draft_id: int) -> InlineKeyboardMarkup:
    """Build tone selection keyboard."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Professional", callback_data=f"tone_professional_{draft_id}"),
        InlineKeyboardButton(text="Enthusiastic", callback_data=f"tone_enthusiastic_{draft_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="Casual", callback_data=f"tone_casual_{draft_id}"),
        InlineKeyboardButton(text="Formal", callback_data=f"tone_formal_{draft_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Back", callback_data=f"draft_view_{draft_id}"),
    )
    return builder.as_markup()


def application_status_keyboard(app_id: int) -> InlineKeyboardMarkup:
    """Build application status update keyboard."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📤 Submitted", callback_data=f"appstatus_submitted_{app_id}"),
        InlineKeyboardButton(text="👀 Viewed", callback_data=f"appstatus_viewed_{app_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="📞 Interview", callback_data=f"appstatus_in_progress_{app_id}"),
        InlineKeyboardButton(text="🎉 Offer!", callback_data=f"appstatus_offer_{app_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="❌ Rejected", callback_data=f"appstatus_rejected_{app_id}"),
        InlineKeyboardButton(text="🔙 Withdrawn", callback_data=f"appstatus_withdrawn_{app_id}"),
    )
    return builder.as_markup()


def confirmation_keyboard(action: str, item_id: int) -> InlineKeyboardMarkup:
    """Build confirmation keyboard."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Yes", callback_data=f"confirm_{action}_{item_id}"),
        InlineKeyboardButton(text="❌ No", callback_data=f"cancel_{action}_{item_id}"),
    )
    return builder.as_markup()


def pagination_keyboard(
    current_page: int,
    total_pages: int,
    callback_prefix: str,
) -> InlineKeyboardMarkup:
    """Build pagination keyboard."""
    builder = InlineKeyboardBuilder()
    buttons = []

    if current_page > 1:
        buttons.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"{callback_prefix}_{current_page - 1}")
        )

    buttons.append(
        InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data="noop")
    )

    if current_page < total_pages:
        buttons.append(
            InlineKeyboardButton(text="➡️", callback_data=f"{callback_prefix}_{current_page + 1}")
        )

    builder.row(*buttons)
    return builder.as_markup()


def settings_keyboard() -> InlineKeyboardMarkup:
    """Build settings keyboard."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🎯 Job Preferences", callback_data="settings_preferences"),
    )
    builder.row(
        InlineKeyboardButton(text="🔔 Notifications", callback_data="settings_notifications"),
    )
    builder.row(
        InlineKeyboardButton(text="🤖 AI Settings", callback_data="settings_ai"),
    )
    builder.row(
        InlineKeyboardButton(text="🗑️ Delete Account", callback_data="settings_delete"),
    )
    return builder.as_markup()
