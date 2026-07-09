from aiogram import F, Router
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.filters.admin import IsAdmin
from bot.keyboards.inline import cancel_button, support_menu_buttons
from bot.services import support as support_service
from bot.states.states import SupportStates, TicketStates
from bot.telethon_client.inline import edit_deco_message
from bot.utils.i18n import t

router = Router(name="support")


@router.callback_query(F.data == "menu_support")
async def on_support(callback: CallbackQuery, state: FSMContext, lang: str | None) -> None:
    await callback.answer()
    await state.clear()
    await edit_deco_message(callback.message.chat.id, callback.message.message_id,
                             t(lang, "support_text"), None, support_menu_buttons(lang))


@router.callback_query(F.data == "support_chat")
async def on_support_chat(callback: CallbackQuery, state: FSMContext, lang: str | None) -> None:
    await callback.answer()
    await state.set_state(SupportStates.awaiting_message)
    await edit_deco_message(callback.message.chat.id, callback.message.message_id,
                             t(lang, "support_chat_prompt"), None,
                             cancel_button(lang, callback="menu_support"))


@router.message(StateFilter(SupportStates.awaiting_message), F.chat.type == "private")
async def on_support_msg_input(message: Message, state: FSMContext, lang: str | None) -> None:
    await state.clear()
    user = message.from_user
    msg = message.text or ""
    admin_text = t(lang, "support_new_msg_admin", name=user.first_name or "",
                    username=user.username or "-", user_id=user.id, message=msg)
    await support_service.notify_admins(admin_text)
    await message.reply(t(lang, "support_msg_sent"))


@router.callback_query(F.data == "support_ticket")
async def on_support_ticket(callback: CallbackQuery, state: FSMContext, lang: str | None) -> None:
    await callback.answer()
    await state.set_state(TicketStates.awaiting_message)
    await edit_deco_message(callback.message.chat.id, callback.message.message_id,
                             t(lang, "ticket_prompt"), None,
                             cancel_button(lang, callback="menu_support"))


@router.message(StateFilter(TicketStates.awaiting_message), F.chat.type == "private")
async def on_ticket_msg_input(message: Message, state: FSMContext, lang: str | None) -> None:
    await state.clear()
    support_service.add_ticket(message.from_user.id, message.text or "")
    user = message.from_user
    admin_text = t(lang, "ticket_new_admin", name=user.first_name or "",
                    username=user.username or "-", user_id=user.id, message=message.text or "")
    await support_service.notify_admins(admin_text)
    await message.reply(t(lang, "ticket_registered"))


@router.message(Command("reply"), IsAdmin(), F.chat.type == "private")
async def on_admin_reply(message: Message, command: CommandObject, lang: str | None) -> None:
    args = (command.args or "").split(maxsplit=1)
    if len(args) != 2 or not args[0].isdigit():
        return
    target_id = int(args[0])
    text = args[1]
    ok = await support_service.send_admin_reply(target_id, t(lang, "support_reply_sent", text=text))
    await message.reply(t(lang, "support_reply_ok") if ok else t(lang, "support_reply_fail"))
