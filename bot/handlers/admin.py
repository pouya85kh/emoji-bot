from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.filters.admin import IsAdmin
from bot.keyboards.inline import admin_panel_buttons, back_button, cancel_button
from bot.services import admin as admin_service
from bot.services import support as support_service
from bot.states.states import AdminBroadcastStates, AdminUnlimitStates
from bot.telethon_client.inline import edit_deco_message
from bot.utils.i18n import t, t_raw

router = Router(name="admin")


@router.callback_query(F.data == "admin_panel")
async def on_admin_panel(callback: CallbackQuery, lang: str | None) -> None:
    if not admin_service.is_admin(callback.from_user.id):
        await callback.answer(t(lang, "admin_no_access"), show_alert=True)
        return
    await callback.answer()
    await edit_deco_message(callback.message.chat.id, callback.message.message_id,
                             t(lang, "admin_panel_header"), None, admin_panel_buttons(lang))


@router.callback_query(F.data == "admin_stats")
async def on_admin_stats(callback: CallbackQuery, lang: str | None) -> None:
    if not admin_service.is_admin(callback.from_user.id):
        await callback.answer(t(lang, "admin_no_access_short"), show_alert=True)
        return
    await callback.answer()
    s = admin_service.get_stats()
    text = t(lang, "admin_stats_text", users=s["users"], emojis=s["emojis"],
              channels=s["channels"], open_tickets=s["open_tickets"],
              unlimited_users=s["unlimited_users"])
    await edit_deco_message(callback.message.chat.id, callback.message.message_id, text, None,
                             back_button(lang, callback="admin_panel"))


@router.callback_query(F.data == "admin_unlimit")
async def on_admin_unlimit(callback: CallbackQuery, state: FSMContext, lang: str | None) -> None:
    if not admin_service.is_admin(callback.from_user.id):
        await callback.answer(t(lang, "admin_no_access_short"), show_alert=True)
        return
    await callback.answer()
    await state.set_state(AdminUnlimitStates.awaiting_target_id)
    await edit_deco_message(callback.message.chat.id, callback.message.message_id,
                             t(lang, "admin_unlimit_prompt"), None,
                             cancel_button(lang, callback="admin_panel"))


@router.message(StateFilter(AdminUnlimitStates.awaiting_target_id), IsAdmin(), F.chat.type == "private")
async def on_unlimit_target_input(message: Message, state: FSMContext, lang: str | None) -> None:
    await state.clear()
    raw = (message.text or "").strip()
    if not raw.isdigit():
        await message.reply(t(lang, "admin_unlimit_invalid"))
        return
    target_id = int(raw)
    admin_service.unlimit_user(target_id)
    await message.reply(t(lang, "admin_unlimit_done", user_id=target_id))
    await support_service.send_admin_reply(target_id, t(lang, "admin_unlimit_notify_user"))


@router.callback_query(F.data == "admin_broadcast")
async def on_admin_broadcast(callback: CallbackQuery, state: FSMContext, lang: str | None) -> None:
    if not admin_service.is_admin(callback.from_user.id):
        await callback.answer(t(lang, "admin_no_access_short"), show_alert=True)
        return
    await callback.answer()
    await state.set_state(AdminBroadcastStates.awaiting_message)
    await edit_deco_message(callback.message.chat.id, callback.message.message_id,
                             t(lang, "admin_broadcast_prompt"), None,
                             cancel_button(lang, callback="admin_panel"))


@router.message(StateFilter(AdminBroadcastStates.awaiting_message), IsAdmin(), F.chat.type == "private")
async def on_broadcast_msg_input(message: Message, state: FSMContext, lang: str | None) -> None:
    await state.clear()
    text = message.text or ""
    from bot.database import database as db
    ids_count = len(db.all_user_ids())
    status = await message.reply(t(lang, "admin_broadcast_sending", count=ids_count))
    sent, failed = await admin_service.broadcast(text, t_raw(lang, "admin_broadcast_msg"))
    await status.edit_text(t(lang, "admin_broadcast_done", sent=sent, failed=failed))
