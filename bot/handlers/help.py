from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.keyboards.inline import back_button
from bot.telethon_client.inline import edit_deco_message
from bot.utils.i18n import t

router = Router(name="help")


@router.callback_query(F.data == "menu_help")
async def on_help(callback: CallbackQuery, lang: str | None) -> None:
    await callback.answer()
    await edit_deco_message(callback.message.chat.id, callback.message.message_id,
                             t(lang, "help_text"), None, back_button(lang, callback="back_main"))
